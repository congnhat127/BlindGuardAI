#!/usr/bin/env python3
"""
BlindGuard AI - Video Object Detection & ByteTrack Tracking System
==================================================================
- Mô hình: YOLO11n (Ultralytics) trained trên 8 lớp Việt Nam:
  ['bicycle', 'bus', 'car', 'motorcycle', 'person', 'truck', 'xe_keo', 'xich_lo']
- Preprocessing: Kéo giãn (stretch) frame về 640x640 bằng cv2.resize trước khi suy luận,
  sau đó quy đổi tọa độ bounding box về kích thước frame gốc.
- Tracking: ByteTrack (model.track với persist=True và file cấu hình bytetrack_bg.yaml).
- Quỹ đạo: Vẽ vệt chuyển động (trajectory trail) 30 điểm gần nhất dựa trên tâm đáy box.
- Giao diện: Click chuột trực tiếp trên Top Panel GUI, hỗ trợ lưu video .mp4.
- Thống kê: Báo cáo số lượng Unique ID theo từng lớp khi kết thúc để phát hiện ID Drift.

HƯỚNG DẪN CÀI ĐẶT (PIP INSTALLATION):
-------------------------------------
pip install ultralytics opencv-python numpy torch python-dotenv

LỆNH CHẠY MẪU (USAGE EXAMPLES):
-------------------------------
1. Chạy trực tiếp (giao diện chọn file tự chọn video & model):
   python 1_AI_Processing_Edge/object_detection/test_video.py

2. Truyền tham số tùy chỉnh:
   python 1_AI_Processing_Edge/object_detection/test_video.py --weights 1_AI_Processing_Edge/object_detection/weights/best.pt --video my_video.mp4 --conf 0.1 --save-output
"""

import os
import sys
import time
import argparse
from collections import defaultdict, deque
import cv2
import numpy as np
import torch

# Force tkinter dialog to front on Windows
try:
    import tkinter as tk
    from tkinter import filedialog
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False


# Danh sách 8 lớp giao thông Việt Nam theo đúng thứ tự huấn luyện
CLASS_NAMES = [
    'bicycle', 'bus', 'car', 'motorcycle', 
    'person', 'truck', 'xe_keo', 'xich_lo'
]


def create_bytetrack_yaml_if_missing(yaml_path="bytetrack_bg.yaml"):
    """Tự động tìm hoặc tạo file cấu hình ByteTrack."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        yaml_path,
        "1_AI_Processing_Edge/object_detection/bytetrack_bg.yaml",
        os.path.join(script_dir, "bytetrack_bg.yaml")
    ]
    for p in possible_paths:
        if os.path.exists(p):
            return p

    target_path = os.path.join(script_dir, "bytetrack_bg.yaml")
    content = """# ByteTrack Configuration for BlindGuard AI
tracker_type: bytetrack
track_high_thresh: 0.25
track_low_thresh: 0.1
new_track_thresh: 0.3
track_buffer: 30
match_thresh: 0.8
fuse_score: True
"""
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[✓] Đã tạo file cấu hình ByteTrack: {target_path}")
    except Exception as e:
        print(f"[!] Không thể tạo file {target_path}: {e}")
    return target_path


def get_unique_color(track_id):
    """Tạo màu BGR cố định dựa trên Track ID để dễ nhận biết ID bị đổi/nhảy."""
    if track_id is None:
        return (0, 255, 0)
    # Tự sinh màu cố định duy nhất theo seed
    tid = int(track_id)
    b = int((tid * 67 + 35) % 200 + 55)
    g = int((tid * 131 + 85) % 200 + 55)
    r = int((tid * 197 + 135) % 200 + 55)
    return (b, g, r)


def select_file_dialog(title="Select File", filetypes=[("All Files", "*.*")]):
    """Mở hộp thoại chọn file native bằng Tkinter."""
    if not HAS_TKINTER:
        return ""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    file_path = filedialog.askopenfilename(title=title, filetypes=filetypes)
    root.destroy()
    return file_path


def find_default_weights():
    """Tìm file trọng số best.pt mặc định trong dự án."""
    possible_paths = [
        "1_AI_Processing_Edge/object_detection/weights/best.pt",
        "1_AI_Processing_Edge/weights/best.pt",
        "weights/best.pt",
        "best.pt",
        "1_AI_Processing_Edge/object_detection/best.pt",
        "1_AI_Processing_Edge/best.pt",
    ]
    for p in possible_paths:
        if os.path.exists(p):
            return p
    return ""


def parse_args():
    parser = argparse.ArgumentParser(description="BlindGuard AI - Video ByteTrack Tester")
    parser.add_argument("--weights", "-w", type=str, default="", help="Path to YOLO best.pt weights file")
    parser.add_argument("--video", "-v", type=str, default="", help="Path to input video file")
    parser.add_argument("--conf", "-c", type=float, default=0.1, help="Confidence threshold (default: 0.1 for 2nd ByteTrack match)")
    parser.add_argument("--tracker-cfg", type=str, default="bytetrack_bg.yaml", help="ByteTrack config file path")
    parser.add_argument("--device", type=str, default="", help="Device (e.g. cpu, cuda:0). Auto detects GPU if available.")
    parser.add_argument("--save-output", action="store_true", help="Save annotated video to outputs/videos/ directory")
    return parser.parse_args()


class VideoByteTracker:
    def __init__(self, model_path, video_path, conf=0.1, tracker_cfg="bytetrack_bg.yaml", device="", save_output=False):
        self.model_path = model_path
        self.video_path = video_path
        self.conf = conf
        self.tracker_cfg = create_bytetrack_yaml_if_missing(tracker_cfg)
        
        # Tự động chọn GPU nếu có, ngược lại dùng CPU
        if not device:
            self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.save_output = save_output

        # Điều khiển tốc độ & giao diện
        self.speed_levels = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 5.0]
        self.speed_idx = 3  # Mặc định 1.0x
        self.paused = False
        self.show_hud = True
        self.should_exit = False
        self.change_video_requested = False
        self.change_weight_requested = False
        self.replay_requested = False
        self.video_finished = False

        # Các mức conf để thay đổi nhanh
        self.conf_levels = [0.05, 0.10, 0.25, 0.35, 0.50, 0.65]

        # Kích thước màn hình hiển thị Canvas (1280x720)
        self.canvas_w = 1280
        self.canvas_h = 720

        # Lưu trữ lịch sử quỹ đạo (30 điểm gần nhất cho từng Track ID)
        self.trajectory_history = defaultdict(lambda: deque(maxlen=30))
        # Thống kê tập hợp ID duy nhất theo từng lớp
        self.class_unique_ids = defaultdict(set)

        # Trạng thái nút bấm & video
        self.buttons = []
        self.end_modal_buttons = []
        self.model = None
        self.cap = None
        self.writer = None
        self.current_frame = None

        # Trạng thái tua (seek) video
        self.total_frames = 0
        self.seeking_requested = False
        self.seek_target_frame = 0
        self.is_dragging_seekbar = False
        self.updating_trackbar_pos = False
        self.seekbar_area = {"x1": 15, "y1": 52, "x2": 1265, "y2": 72}

        # Stats counters
        self.total_processed_frames = 0
        self.start_processing_time = 0
        self.total_processing_time = 0

        # Load YOLO model
        self.load_model()

    def seek_to_frame(self, target_frame):
        """Tua video đến khung hình chỉ định."""
        if self.cap is not None and self.cap.isOpened() and self.total_frames > 0:
            target_frame = max(0, min(self.total_frames - 1, int(target_frame)))
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            self.trajectory_history.clear()
            self.seek_target_frame = target_frame
            self.seeking_requested = True

    def load_model(self):
        print(f"\n[+] Đang tải mô hình YOLO từ: {self.model_path}")
        print(f"[+] Thiết bị tính toán: {self.device.upper()}")
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
            print("[✓] Mô hình đã được tải thành công!")
        except Exception as e:
            print(f"[!] Lỗi khi tải mô hình: {e}")
            sys.exit(1)

    def select_new_video(self):
        """Mở dialog chọn video mới."""
        filetypes = [
            ("Video Files", "*.mp4 *.avi *.mkv *.mov *.webm *.flv *.wmv *.m4v"),
            ("All Files", "*.*")
        ]
        new_video = select_file_dialog("Chọn file video để thử nghiệm (Select Video)", filetypes)
        if new_video and os.path.exists(new_video):
            self.video_path = new_video
            return True
        return False

    def select_new_weights(self):
        """Mở dialog chọn weights mới."""
        filetypes = [("PyTorch Weights", "*.pt"), ("All Files", "*.*")]
        new_weights = select_file_dialog("Chọn file trọng số model YOLO (.pt)", filetypes)
        if new_weights and os.path.exists(new_weights):
            self.model_path = new_weights
            self.load_model()
            return True
        return False

    def letterbox_frame(self, frame):
        """Căn giữa khung hình gốc vào màn hình 1280x720 để hiển thị chuẩn tỉ lệ."""
        h, w = frame.shape[:2]
        scale = min(self.canvas_w / w, self.canvas_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        canvas = np.zeros((self.canvas_h, self.canvas_w, 3), dtype=np.uint8)

        x_offset = (self.canvas_w - new_w) // 2
        y_offset = (self.canvas_h - new_h) // 2
        canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

        return canvas

    def draw_button(self, canvas, text, x1, y1, x2, y2, bg_color, text_color=(255, 255, 255)):
        """Vẽ nút bấm dạng bo góc đẹp trên Top Panel."""
        cv2.rectangle(canvas, (x1, y1), (x2, y2), bg_color, -1)
        cv2.rectangle(canvas, (x1, y1), (x2, y2), (90, 95, 110), 1)

        font_scale = 0.44
        thickness = 1
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        tx = x1 + (x2 - x1 - text_size[0]) // 2
        ty = y1 + (y2 - y1 + text_size[1]) // 2
        cv2.putText(canvas, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, thickness, cv2.LINE_AA)

    def draw_hud(self, canvas, fps, frame_idx, total_frames, det_summary_str, inference_time_ms):
        """Vẽ thanh Top Panel HUD chứa thông số, thanh kéo tua video & các nút bấm tương tác bằng chuột."""
        if not self.show_hud:
            return canvas

        h, w, _ = canvas.shape
        self.buttons = []

        # Top Header Panel (Height 126px)
        overlay = canvas.copy()
        header_h = 126
        cv2.rectangle(overlay, (0, 0), (w, header_h), (16, 18, 24), -1)
        cv2.rectangle(overlay, (0, header_h - 2), (w, header_h), (240, 180, 0), -1)

        alpha = 0.88
        cv2.addWeighted(overlay, alpha, canvas, 1 - alpha, 0, canvas)

        # Colors (BGR)
        CYAN = (255, 200, 0)
        GREEN = (0, 230, 120)
        YELLOW = (0, 215, 255)
        WHITE = (245, 245, 245)
        GRAY = (180, 180, 180)
        RED = (60, 60, 255)
        BTN_BG = (42, 46, 58)

        speed_val = self.speed_levels[self.speed_idx]
        video_name = os.path.basename(self.video_path)
        weight_name = os.path.basename(self.model_path)

        # --- Dòng 1: Trạng thái & Thống kê (Y=22) ---
        cv2.putText(canvas, "BlindGuard AI ByteTrack", (15, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, CYAN, 2, cv2.LINE_AA)
        
        status_str = "PAUSED" if self.paused else "RUNNING"
        status_color = RED if self.paused else GREEN
        cv2.putText(canvas, f"[{status_str}]", (240, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.52, status_color, 2, cv2.LINE_AA)

        metrics = f"FPS: {fps:.1f}  |  Inf: {inference_time_ms:.1f}ms  |  ImgSize: 640x640 (Stretch)  |  Speed: {speed_val}x  |  Conf: {self.conf:.2f}"
        cv2.putText(canvas, metrics, (340, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.46, YELLOW, 2, cv2.LINE_AA)

        frame_str = f"Frame: {frame_idx}/{total_frames}"
        f_size = cv2.getTextSize(frame_str, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)[0]
        cv2.putText(canvas, frame_str, (w - f_size[0] - 15, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.48, WHITE, 1, cv2.LINE_AA)

        # --- Dòng 2: Chi tiết File & Object Detections (Y=44) ---
        info_str = f"Video: {video_name[:25]}  |  Weight: {weight_name[:20]}  |  Device: {self.device.upper()}"
        cv2.putText(canvas, info_str, (15, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.46, GRAY, 1, cv2.LINE_AA)

        det_str = f"Tracked Objects: {det_summary_str}"
        cv2.putText(canvas, det_str, (520, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.5, GREEN, 2, cv2.LINE_AA)

        # --- Dòng 3: THANH KÉO TUA VIDEO (SEEKBAR SLIDER) (Y=56 -> 66) ---
        sb_x1, sb_y1 = 15, 56
        sb_x2, sb_y2 = w - 15, 66
        self.seekbar_area = {"x1": sb_x1, "y1": sb_y1 - 4, "x2": sb_x2, "y2": sb_y2 + 4}

        # Nền thanh kéo
        cv2.rectangle(canvas, (sb_x1, sb_y1), (sb_x2, sb_y2), (38, 42, 54), -1)
        cv2.rectangle(canvas, (sb_x1, sb_y1), (sb_x2, sb_y2), (75, 80, 95), 1)

        # Tiến trình đã chạy (màu cyan/vàng)
        progress_ratio = max(0.0, min(1.0, frame_idx / float(max(1, total_frames))))
        fill_w = int((sb_x2 - sb_x1) * progress_ratio)
        if fill_w > 0:
            cv2.rectangle(canvas, (sb_x1, sb_y1), (sb_x1 + fill_w, sb_y2), (0, 215, 255), -1)

        # Nút tròn kéo tay (Thumb knob)
        knob_x = sb_x1 + fill_w
        knob_y = (sb_y1 + sb_y2) // 2
        cv2.circle(canvas, (knob_x, knob_y), 6, (0, 230, 120), -1)
        cv2.circle(canvas, (knob_x, knob_y), 7, (255, 255, 255), 1)

        # --- Dòng 4: HÀNG NÚT BẤM GUI CLICK CHUỘT (Y=78 -> 116) ---
        btn_y1 = 78
        btn_y2 = 116

        btn_defs = [
            ("Play/Pause", 95, "toggle_pause", (40, 90, 180) if self.paused else BTN_BG),
            ("- Toc do", 85, "speed_down", BTN_BG),
            ("+ Toc do", 85, "speed_up", BTN_BG),
            (f"Conf: {self.conf:.2f}", 100, "cycle_conf", (0, 110, 160)),
            ("Chon Video", 110, "select_video", (140, 90, 0)),
            ("Chon Weight", 110, "select_weight", (0, 130, 110)),
            ("Chup Anh", 95, "snapshot", (50, 110, 50)),
            ("An HUD", 80, "toggle_hud", BTN_BG),
            ("Thoat (Q)", 85, "quit", (40, 40, 170)),
        ]

        curr_x = 15
        for text, bw, action, bg_c in btn_defs:
            x1, y1, x2, y2 = curr_x, btn_y1, curr_x + bw, btn_y2
            self.draw_button(canvas, text, x1, y1, x2, y2, bg_c)
            self.buttons.append({"name": text, "x1": x1, "y1": y1, "x2": x2, "y2": y2, "action": action})
            curr_x += bw + 10

        return canvas

    def draw_end_video_modal(self, canvas):
        """Vẽ cửa sổ Modal khi kết thúc video."""
        h, w, _ = canvas.shape
        self.end_modal_buttons = []

        overlay = canvas.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (10, 12, 16), -1)
        cv2.addWeighted(overlay, 0.75, canvas, 0.25, 0, canvas)

        mw, mh = 580, 310
        mx1 = (w - mw) // 2
        my1 = (h - mh) // 2
        mx2 = mx1 + mw
        my2 = my1 + mh

        cv2.rectangle(canvas, (mx1, my1), (mx2, my2), (25, 28, 36), -1)
        cv2.rectangle(canvas, (mx1, my1), (mx2, my2), (240, 180, 0), 2)

        cv2.putText(canvas, "HOAN TAT XU LY VIDEO!", (mx1 + 130, my1 + 45), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 230, 120), 2, cv2.LINE_AA)
        
        cv2.putText(canvas, "Ban vui long click chon hanh dong tiep theo:", (mx1 + 85, my1 + 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (200, 200, 200), 1, cv2.LINE_AA)

        btn_w, btn_h = 460, 45
        bx1 = mx1 + (mw - btn_w) // 2
        
        modal_btns = [
            ("Mo Video Moi (Open New Video)", my1 + 115, "select_video", (140, 90, 0)),
            ("Phat Lai Video Nay (Replay)", my1 + 172, "replay", (0, 130, 80)),
            ("Thoat Chuong Trinh & Xem Thong Ke (Exit)", my1 + 229, "quit", (40, 40, 160))
        ]

        for text, by1, action, bg_c in modal_btns:
            by2 = by1 + btn_h
            bx2 = bx1 + btn_w
            self.draw_button(canvas, text, bx1, by1, bx2, by2, bg_c)
            self.end_modal_buttons.append({"name": text, "x1": bx1, "y1": by1, "x2": bx2, "y2": by2, "action": action})

    def handle_mouse_click(self, event, x, y, flags, param):
        """Xử lý sự kiện click & kéo chuột trên thanh tua video và các nút bấm GUI."""
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.video_finished:
                for btn in self.end_modal_buttons:
                    if btn["x1"] <= x <= btn["x2"] and btn["y1"] <= y <= btn["y2"]:
                        self.execute_action(btn["action"])
                        return
                return

            # Click trên Thanh Kéo Tua (Seekbar)
            if self.show_hud and self.total_frames > 0:
                sb = self.seekbar_area
                if sb["x1"] <= x <= sb["x2"] and sb["y1"] <= y <= sb["y2"]:
                    self.is_dragging_seekbar = True
                    ratio = (x - sb["x1"]) / float(sb["x2"] - sb["x1"])
                    target_frame = int(ratio * self.total_frames)
                    self.seek_to_frame(target_frame)
                    return

            if self.show_hud:
                for btn in self.buttons:
                    if btn["x1"] <= x <= btn["x2"] and btn["y1"] <= y <= btn["y2"]:
                        self.execute_action(btn["action"])
                        return

        elif event == cv2.EVENT_MOUSEMOVE:
            # Kéo chuột trên thanh tua
            if self.is_dragging_seekbar and (flags & cv2.EVENT_FLAG_LBUTTON) and self.total_frames > 0:
                sb = self.seekbar_area
                ratio = max(0.0, min(1.0, (x - sb["x1"]) / float(sb["x2"] - sb["x1"])))
                target_frame = int(ratio * self.total_frames)
                self.seek_to_frame(target_frame)

        elif event == cv2.EVENT_LBUTTONUP:
            self.is_dragging_seekbar = False

    def execute_action(self, action):
        """Thực thi hành động của nút bấm GUI."""
        if action == "toggle_pause":
            self.paused = not self.paused
            print(f"[*] Trạng thái: {'Tạm dừng' if self.paused else 'Đang chạy'}")

        elif action == "speed_up":
            if self.speed_idx < len(self.speed_levels) - 1:
                self.speed_idx += 1
                print(f"[*] Tốc độ: {self.speed_levels[self.speed_idx]}x")

        elif action == "speed_down":
            if self.speed_idx > 0:
                self.speed_idx -= 1
                print(f"[*] Tốc độ: {self.speed_levels[self.speed_idx]}x")

        elif action == "cycle_conf":
            curr_conf_idx = self.conf_levels.index(self.conf) if self.conf in self.conf_levels else 1
            next_conf_idx = (curr_conf_idx + 1) % len(self.conf_levels)
            self.conf = self.conf_levels[next_conf_idx]
            print(f"[*] Ngưỡng tin cậy Conf: {self.conf}")

        elif action == "toggle_hud":
            self.show_hud = not self.show_hud
            print(f"[*] Hiển thị HUD: {'Bật' if self.show_hud else 'Tắt'}")

        elif action == "select_video":
            print("[*] Mở hộp thoại chọn video...")
            self.change_video_requested = True

        elif action == "select_weight":
            print("[*] Mở hộp thoại chọn weight...")
            self.change_weight_requested = True

        elif action == "replay":
            print("[*] Phát lại video...")
            self.replay_requested = True

        elif action == "snapshot":
            if self.current_frame is not None:
                os.makedirs("outputs/snapshots", exist_ok=True)
                snap_name = f"outputs/snapshots/frame_{int(time.time())}.jpg"
                cv2.imwrite(snap_name, self.current_frame[0])
                print(f"[✓] Đã lưu ảnh chụp khung hình tại: {snap_name}")

        elif action == "quit":
            print("[*] Thoát chương trình...")
            self.should_exit = True

    def process_and_draw_frame(self, raw_frame):
        """
        Xử lý từng khung hình:
        1. Kéo giãn (stretch) frame gốc về 640x640 bằng cv2.resize
        2. Chạy model.track(...) với ByteTrack
        3. Quy đổi tọa độ box về kích thước frame gốc
        4. Vẽ box, tên class, ID track, confidence score (mỗi ID 1 màu cố định)
        5. Vẽ vệt quỹ đạo (30 điểm gần nhất tính từ tâm đáy box)
        """
        h_orig, w_orig = raw_frame.shape[:2]

        # 1. Kéo giãn (stretch) frame gốc về 640x640 theo đúng yêu cầu huấn luyện
        resized_640 = cv2.resize(raw_frame, (640, 640), interpolation=cv2.INTER_LINEAR)

        # 2. Gọi model.track với persist=True và cấu hình bytetrack_bg.yaml
        t0 = time.time()
        results = self.model.track(
            source=resized_640,
            conf=self.conf,
            persist=True,
            tracker=self.tracker_cfg,
            imgsz=640,
            device=self.device,
            verbose=False
        )[0]
        t1 = time.time()
        inference_time_ms = (t1 - t0) * 1000.0

        # Frame đã vẽ hoàn chỉnh trên kích thước gốc
        annotated_orig_frame = raw_frame.copy()
        boxes = results.boxes
        det_class_counts = {}

        if boxes is not None and len(boxes) > 0:
            for box in boxes:
                # 3. Lấy tọa độ trên 640x640 và quy đổi về frame gốc
                xyxy_640 = box.xyxy[0].cpu().numpy()
                x1 = int(xyxy_640[0] * w_orig / 640.0)
                y1 = int(xyxy_640[1] * h_orig / 640.0)
                x2 = int(xyxy_640[2] * w_orig / 640.0)
                y2 = int(xyxy_640[3] * h_orig / 640.0)

                cls_id = int(box.cls[0].item())
                conf_val = float(box.conf[0].item())
                track_id = int(box.id[0].item()) if box.id is not None else None

                # Lấy tên lớp
                if 0 <= cls_id < len(CLASS_NAMES):
                    cls_name = CLASS_NAMES[cls_id]
                else:
                    cls_name = self.model.names.get(cls_id, str(cls_id))

                det_class_counts[cls_name] = det_class_counts.get(cls_name, 0) + 1

                # Màu sắc cố định theo Track ID
                color = get_unique_color(track_id)

                # 4. Vẽ Bounding Box lên frame gốc
                cv2.rectangle(annotated_orig_frame, (x1, y1), (x2, y2), color, 2)

                # Nhãn hiển thị: ID, Tên Class, Conf
                if track_id is not None:
                    label = f"ID:{track_id} {cls_name} {conf_val:.2f}"
                    self.class_unique_ids[cls_name].add(track_id)
                else:
                    label = f"{cls_name} {conf_val:.2f}"

                # Background badge cho chữ dễ đọc
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(annotated_orig_frame, (x1, max(0, y1 - 20)), (x1 + tw + 6, max(0, y1)), color, -1)
                cv2.putText(annotated_orig_frame, label, (x1 + 3, max(14, y1 - 5)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

                # 5. Vẽ vệt quỹ đạo 30 điểm gần nhất (lấy tâm giữa cạnh dưới box)
                if track_id is not None:
                    bottom_center = (int((x1 + x2) / 2), int(y2))
                    self.trajectory_history[track_id].append(bottom_center)

                    # Vẽ đường nối các điểm quỹ đạo
                    pts = list(self.trajectory_history[track_id])
                    for i in range(1, len(pts)):
                        pt1 = pts[i - 1]
                        pt2 = pts[i]
                        # Vẽ vệt mờ dần/dày dần
                        thickness = max(1, int(np.sqrt(i / float(len(pts))) * 3))
                        cv2.line(annotated_orig_frame, pt1, pt2, color, thickness, cv2.LINE_AA)
                        cv2.circle(annotated_orig_frame, pt2, 2, color, -1)

        det_summary_str = ", ".join([f"{count} {name}" for name, count in det_class_counts.items()]) if det_class_counts else "0"

        return annotated_orig_frame, inference_time_ms, det_summary_str

    def print_final_statistics(self):
        """In thống kê chi tiết theo yêu cầu khi kết thúc video."""
        avg_fps = (self.total_processed_frames / self.total_processing_time) if self.total_processing_time > 0 else 0.0

        print("\n" + "=" * 67)
        print("📊 BÁO CÁO THỐNG KÊ KẾT QUẢ THEO DÕI (TRACKING SUMMARY REPORT)")
        print("=" * 67)
        print(f"Tệp video đã xử lý:                    {os.path.basename(self.video_path)}")
        print(f"Tệp trọng số model:                    {os.path.basename(self.model_path)}")
        print(f"Tổng số khung hình (Total Frames):     {self.total_processed_frames}")
        print(f"Tổng thời gian xử lý:                  {self.total_processing_time:.2f} giây")
        print(f"Tốc độ xử lý trung bình (Average FPS): {avg_fps:.2f} FPS")
        print("-" * 67)
        print("SỐ LƯỢNG UNIQUE TRACK ID THEO TỪNG LỚP (UNIQUE IDs GENERATED):")
        
        total_unique_ids_all = 0
        for cls_name in CLASS_NAMES:
            id_set = self.class_unique_ids.get(cls_name, set())
            count = len(id_set)
            total_unique_ids_all += count
            print(f"  - {cls_name:<15}: {count} unique IDs")

        print("-" * 67)
        print(f"Tổng số Track ID tạo ra trên tất cả lớp: {total_unique_ids_all}")
        print("-" * 67)
        print("⚠️ ĐÁNH GIÁ CHẤT LƯỢNG TRACKING:")
        print("  - Nếu số lượng ID của một lớp lớn bất thường so với số vật thể thực tế trong video,")
        print("    đây là dấu hiệu mô hình bị đổi ID liên tục (ID Switch / Drift).")
        print("  - Bạn có thể tinh chỉnh các tham số trong file bytetrack_bg.yaml:")
        print("    + Tăng 'track_buffer' (ví dụ 50) để giữ lại ID khi bị che khuất lâu.")
        print("    + Tăng/Giảm 'match_thresh' và 'track_high_thresh' để tối ưu ghép cặp.")
        print("=" * 67 + "\n")

    def run(self):
        while not self.should_exit:
            if not self.video_path or not os.path.exists(self.video_path):
                print("\n[!] Chưa chọn video hoặc file video không tồn tại.")
                if not self.select_new_video():
                    print("Không chọn video nào. Thoát chương trình.")
                    break

            print(f"\n[+] Đang mở video: {self.video_path}")
            self.cap = cv2.VideoCapture(self.video_path)
            if not self.cap.isOpened():
                print(f"[!] Không thể mở file video: {self.video_path}")
                self.video_path = ""
                continue

            orig_fps = self.cap.get(cv2.CAP_PROP_FPS)
            if orig_fps <= 0 or np.isnan(orig_fps):
                orig_fps = 30.0
            
            total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.total_frames = max(1, total_frames)

            window_name = "BlindGuard AI - Test Video Player (ByteTrack)"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, self.canvas_w, self.canvas_h)
            cv2.setMouseCallback(window_name, self.handle_mouse_click)

            # Tạo thanh kéo tua mặc định của OpenCV ở viền cửa sổ
            def on_trackbar_seek(pos):
                if not self.updating_trackbar_pos:
                    self.seek_to_frame(pos)

            cv2.createTrackbar("Tua Video", window_name, 0, max(1, total_frames - 1), on_trackbar_seek)

            # Setup video recorder nếu bật save_output
            if self.save_output:
                os.makedirs("outputs/videos", exist_ok=True)
                out_path = f"outputs/videos/result_{os.path.basename(self.video_path)}"
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                self.writer = cv2.VideoWriter(out_path, fourcc, orig_fps, (self.canvas_w, self.canvas_h))
                print(f"[+] Lưu video kết quả tại: {out_path}")

            frame_idx = 0
            prev_time = time.time()
            fps = 0.0
            self.video_finished = False

            # Reset stats cho video mới
            self.total_processed_frames = 0
            self.start_processing_time = time.time()
            self.trajectory_history.clear()
            self.class_unique_ids.clear()

            while self.cap.isOpened() and not self.should_exit:
                if self.change_video_requested:
                    self.change_video_requested = False
                    if self.select_new_video():
                        break

                if self.change_weight_requested:
                    self.change_weight_requested = False
                    self.select_new_weights()

                if not self.paused or self.seeking_requested:
                    if self.seeking_requested:
                        self.seeking_requested = False
                        frame_idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))

                    ret, raw_frame = self.cap.read()
                    if not ret:
                        print("\n[✓] Đã chạy xong video. Chờ thao tác của người dùng...")
                        self.video_finished = True
                        break
                    
                    frame_idx += 1
                    self.total_processed_frames += 1

                    # Cập nhật vị trí thanh kéo tua OpenCV
                    self.updating_trackbar_pos = True
                    try:
                        cv2.setTrackbarPos("Tua Video", window_name, max(0, min(total_frames - 1, frame_idx - 1)))
                    except Exception:
                        pass
                    self.updating_trackbar_pos = False

                    # Xử lý frame, resize 640x640 stretch, chạy ByteTrack & vẽ quỹ đạo
                    annotated_orig_frame, inference_time_ms, det_summary_str = self.process_and_draw_frame(raw_frame)

                    # Tính FPS thời gian thực
                    curr_time = time.time()
                    fps = 1.0 / max(0.001, (curr_time - prev_time))
                    prev_time = curr_time

                    # Căn giữa vào Canvas 1280x720 để hiển thị không bị co méo
                    canvas = self.letterbox_frame(annotated_orig_frame)

                    # Vẽ Top Panel HUD Dashboard
                    display_frame = self.draw_hud(canvas, fps, frame_idx, total_frames, det_summary_str, inference_time_ms)
                    self.current_frame = (canvas, fps, frame_idx, total_frames, det_summary_str)

                    if self.writer is not None:
                        self.writer.write(display_frame)
                else:
                    # Trạng thái Pause: vẽ lại frame hiện tại
                    canvas_bg, fps_p, f_idx, tot_f, det_str = self.current_frame
                    display_frame = self.draw_hud(canvas_bg.copy(), fps_p, f_idx, tot_f, det_str, 0.0)

                cv2.imshow(window_name, display_frame)

                # Tính độ trễ theo tốc độ phát
                speed_factor = self.speed_levels[self.speed_idx]
                target_delay_ms = max(1, int((1000.0 / (orig_fps * speed_factor))))
                
                key = cv2.waitKey(target_delay_ms) & 0xFF

                # Phím tắt điều khiển (Q để thoát)
                if key == ord('q') or key == 27:
                    self.should_exit = True
                    break
                elif key == 32 or key == ord('k'):
                    self.paused = not self.paused
                elif key == ord('h') or key == ord('H'):
                    self.show_hud = not self.show_hud
                elif key == ord('+') or key == ord('='):
                    self.execute_action("speed_up")
                elif key == ord('-') or key == ord('_'):
                    self.execute_action("speed_down")
                elif key == 81 or key == 2425856 or key == ord(',') or key == ord('a'):  # Tua lùi 5 giây
                    self.seek_to_frame(frame_idx - int(5 * orig_fps))
                elif key == 83 or key == 2555904 or key == ord('.') or key == ord('d'):  # Tua tới 5 giây
                    self.seek_to_frame(frame_idx + int(5 * orig_fps))
                elif key == ord('r'):
                    self.speed_idx = 3
                elif key == ord('c'):
                    self.execute_action("cycle_conf")
                elif key == ord('o'):
                    if self.select_new_video():
                        break
                elif key == ord('s'):
                    self.execute_action("snapshot")

            self.total_processing_time = time.time() - self.start_processing_time

            # In thống kê ngay khi kết thúc xử lý video
            if self.total_processed_frames > 0:
                self.print_final_statistics()

            # Lặp chờ thao tác ở cửa sổ End Video Modal
            while self.video_finished and not self.should_exit:
                if self.change_video_requested:
                    self.change_video_requested = False
                    if self.select_new_video():
                        self.video_finished = False
                        break

                if self.replay_requested:
                    self.replay_requested = False
                    self.video_finished = False
                    break

                if self.current_frame is not None:
                    modal_frame = self.current_frame[0].copy()
                    self.draw_end_video_modal(modal_frame)
                    cv2.imshow(window_name, modal_frame)

                key = cv2.waitKey(30) & 0xFF
                if key == ord('q') or key == 27:
                    self.should_exit = True
                    break

            self.cap.release()
            if self.writer:
                self.writer.release()
            cv2.destroyAllWindows()

        print("\n[✓] Đã đóng trình kiểm thử BlindGuard AI ByteTrack.")


def main():
    args = parse_args()

    # 1. Tìm tệp trọng số best.pt
    weights_path = args.weights
    if not weights_path:
        weights_path = find_default_weights()
    
    if not weights_path or not os.path.exists(weights_path):
        print("\n[!] Chưa thấy file best.pt ở thư mục mặc định (1_AI_Processing_Edge/object_detection/weights/best.pt).")
        print("[+] Đang mở hộp thoại chọn file trọng số (.pt)...")
        filetypes = [("PyTorch Weights", "*.pt"), ("All Files", "*.*")]
        weights_path = select_file_dialog("Chọn file trọng số model YOLO (best.pt)", filetypes)

    if not weights_path or not os.path.exists(weights_path):
        print("[!] Không có file trọng số model được chọn. Thoát chương trình.")
        sys.exit(1)

    print(f"[✓] Đã chọn trọng số model: {weights_path}")

    # 2. Tìm tệp Video
    video_path = args.video
    if not video_path or not os.path.exists(video_path):
        print("\n[+] Đang mở hộp thoại chọn file Video...")
        filetypes = [
            ("Video Files", "*.mp4 *.avi *.mkv *.mov *.webm *.flv *.wmv *.m4v"),
            ("All Files", "*.*")
        ]
        video_path = select_file_dialog("Chọn file Video để test (Select Video File)", filetypes)

    if not video_path:
        print("[!] Không có video nào được chọn. Thoát chương trình.")
        sys.exit(0)

    # 3. Chạy Video ByteTracker System
    tracker_sys = VideoByteTracker(
        model_path=weights_path,
        video_path=video_path,
        conf=args.conf,
        tracker_cfg=args.tracker_cfg,
        device=args.device,
        save_output=args.save_output
    )
    tracker_sys.run()


if __name__ == "__main__":
    main()
