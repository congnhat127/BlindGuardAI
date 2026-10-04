"""
Script: test_video.py
Mô tả: Công cụ kiểm thử trực quan mô hình YOLOv11n trên video camera Fisheye 180 độ.

Tính năng:
1. Tự động nhận diện chính xác tên Class từ `model.names` của từng mô hình (tránh lệch index giữa COCO 80 class và Custom 8 class).
2. Khi dùng MÔ HÌNH GỐC (YOLOv11n COCO):
   - Tự động lọc CHỈ NHẬN DIỆN 6 CLASS GIAO THÔNG: person, bicycle, car, motorcycle, bus, truck.
   - Triệt để loại bỏ toàn bộ 74 class tạp dư (cell phone, chair, dog, cat, backpack, ...).
   - Tuyệt đối không còn hiện tượng cls_67 hay xe tải bị gán nhãn nhầm thành xích lô.
3. Hỗ trợ ĐỔI MODEL TRỰC TIẾP (Model v2 <-> Model v1 <-> YOLOv11n Gốc) mọi lúc:
   - Nút [🔄 Đổi Model: {name}] xuất hiện ở CẢ 3 MÀN HÌNH: Khởi động, Đang chiếu (Top Bar), và Khi video kết thúc.
   - Nhấn phím tắt 'M' để chuyển đổi tức thì giữa các mô hình mà không cần dừng video.
   - Nhấn phím tắt 'F' để chuyển đổi bộ lọc (6 Class chuẩn giao thông <-> Tất cả 8 Class).
   - Nhấn phím tắt 'B' để nạp file trọng số .pt bất kỳ ngoài máy.
4. Kích thước cửa sổ tự động căn chỉnh vừa với màn hình theo chiều dài (trục Y máy tính), chiều còn lại co giãn theo đúng tỷ lệ gốc của video (Aspect Ratio), luôn căn chính giữa màn hình.
5. Đồng bộ tốc độ phát video thời gian thực chuẩn theo FPS gốc của video.
6. Nút bấm & phím tắt điều chỉnh tốc độ phát: 0.5x, 0.75x, 1.0x (gốc), 1.25x, 1.5x, 2.0x.
7. Điều khiển tương tác trực tiếp bằng Chuột (Click nút) hoặc Phím tắt:
   - [🔄 Đổi Model] (hoặc phím M): Đổi qua lại các model thời gian thực.
   - [🎯 Lọc Class] (hoặc phím F): Lọc 6 class hoặc hiển thị đủ 8 class.
   - [📂 Đổi Video] (hoặc phím R / C): Đổi video khác bất kỳ lúc nào.
   - [⚡ Tốc độ: 1.0x] (hoặc phím T để đổi tuần hoàn, [ để giảm, ] để tăng).
   - [⏸ Tạm dừng / Tiếp tục] (hoặc phím SPACE).
   - [📸 Chụp ảnh] (hoặc phím S): Lưu ảnh kèm box vào runs/screenshots/.
   - [❌ Thoát] (hoặc phím Q / ESC).
"""

import os
import sys
import time
import ctypes
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
import cv2
import numpy as np
from collections import defaultdict

# Thiết lập thư mục
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent if SCRIPT_DIR.name == "1_AI_Processing_Edge" else SCRIPT_DIR

# 6 Class giao thông chuẩn (theo COCO ID: 0: person, 1: bicycle, 2: car, 3: motorcycle, 5: bus, 7: truck)
COCO_TRAFFIC_IDS = [0, 1, 2, 3, 5, 7]
STANDARD_6_CLASSES = {'person', 'bicycle', 'car', 'motorcycle', 'bus', 'truck'}

# Bảng màu BGR theo tên class
CLASS_COLORS = {
    'person':     (255, 0, 200),    # Tím hồng
    'bicycle':    (255, 200, 0),    # Vàng xanh
    'car':        (0, 230, 0),      # Xanh lá
    'motorcycle': (0, 255, 255),    # Vàng rực
    'bus':        (0, 140, 255),    # Cam
    'truck':      (255, 100, 50),   # Xanh lam
    'xe_keo':     (0, 0, 255),      # ĐỎ (Nổi bật cho xe kéo)
    'xich_lo':    (50, 180, 255)    # Cam vàng (Nổi bật cho xích lô)
}

# Biến toàn cục theo dõi chuột
mouse_pos = (0, 0)
mouse_clicked = False

def on_mouse_event(event, x, y, flags, param):
    global mouse_pos, mouse_clicked
    mouse_pos = (x, y)
    if event == cv2.EVENT_LBUTTONDOWN:
        mouse_clicked = True

def get_screen_resolution():
    """Lấy độ phân giải màn hình chính của Windows"""
    try:
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except Exception:
        return 1920, 1080

def compute_window_size(orig_w, orig_h, screen_w, screen_h):
    """
    Tính toán kích thước cửa sổ hiển thị:
    - Khi video có chiều dài > chiều rộng (orig_h > orig_w, video dọc):
      Chiều dài (Height) bằng với chiều cao trục Y của máy tính (trừ hao taskbar/titlebar: usable_h),
      chiều rộng (Width) scale lên theo đúng tỷ lệ gốc của video (Aspect Ratio).
    - Khi video ngang (orig_w >= orig_h):
      Chiều cao ưu tiên vừa khít trục Y của máy tính (usable_h), chiều rộng scale theo tỷ lệ gốc;
      nếu chiều rộng vượt quá màn hình (usable_w) thì giới hạn lại theo usable_w.
    - Đảm bảo cửa sổ không bị tràn màn hình và hình ảnh luôn đúng tỷ lệ gốc.
    """
    usable_h = max(400, screen_h - 80)
    usable_w = max(400, screen_w - 40)

    target_h = usable_h
    target_w = int(target_h * (orig_w / float(orig_h)))

    if target_w > usable_w:
        target_w = usable_w
        target_h = int(target_w * (orig_h / float(orig_w)))

    return max(400, target_w), max(300, target_h)

def update_window_geometry(window_name, app_w, app_h, screen_w, screen_h):
    """
    Thay đổi kích thước và căn cửa sổ ra CHÍNH GIỮA màn hình máy tính (cả trục X và trục Y)
    """
    cv2.resizeWindow(window_name, app_w, app_h)
    win_x = max(0, (screen_w - app_w) // 2)
    win_y = max(10, (screen_h - app_h - 35) // 2)
    cv2.moveWindow(window_name, win_x, win_y)

# Các mức tốc độ hỗ trợ
SPEED_PRESETS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]

def setup_video_capture(video_path, screen_w, screen_h):
    """
    Mở video, trích xuất thông số FPS gốc và tính kích thước cửa sổ chuẩn.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None, 0, 0, 30.0
    vw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    vh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 1.0 or fps > 120.0 or np.isnan(fps):
        fps = 30.0
    app_w, app_h = compute_window_size(vw, vh, screen_w, screen_h)
    return cap, app_w, app_h, fps

def discover_available_models():
    """Tự động phát hiện danh sách các mô hình YOLO có sẵn trong dự án"""
    models = []
    seen = set()

    def add_model(label, path_obj):
        if path_obj and path_obj.is_file():
            resolved = str(path_obj.resolve())
            if resolved not in seen:
                seen.add(resolved)
                models.append({"label": label, "path": resolved})

    # 0. Model V4 (Mới nhất - Tối ưu Person, Bicycle và Xe kéo Fisheye)
    for p in [
        SCRIPT_DIR / "object_detection" / "runs" / "yolo11n_blindguard_v4" / "weights" / "best.pt",
        ROOT_DIR / "1_AI_Processing_Edge" / "object_detection" / "runs" / "yolo11n_blindguard_v4" / "weights" / "best.pt",
    ]:
        add_model("Model v4 (Toi uu Person/Xe dap)", p)

    # 1. Model V3 (Bổ sung xe kéo thật fisheye)
    for p in [
        SCRIPT_DIR / "object_detection" / "runs" / "yolo11n_blindguard_v3" / "weights" / "best.pt",
        ROOT_DIR / "1_AI_Processing_Edge" / "object_detection" / "runs" / "yolo11n_blindguard_v3" / "weights" / "best.pt",
    ]:
        add_model("Model v3 (Xe keo Fisheye)", p)

    # 1. Model V2 (mới nhất từ data/new)
    for p in [
        SCRIPT_DIR / "object_detection" / "runs" / "yolo11n_blindguard_v2" / "weights" / "best.pt",
        ROOT_DIR / "1_AI_Processing_Edge" / "object_detection" / "runs" / "yolo11n_blindguard_v2" / "weights" / "best.pt",
    ]:
        add_model("Model v2 (Cu hon)", p)

    # 2. Model V1 (huấn luyện ban đầu)
    for p in [
        SCRIPT_DIR / "object_detection" / "runs" / "yolo11n_blindguard" / "weights" / "best.pt",
        ROOT_DIR / "1_AI_Processing_Edge" / "object_detection" / "runs" / "yolo11n_blindguard" / "weights" / "best.pt",
    ]:
        add_model("Model v1 (Cu)", p)

    # 3. Model COCO Pretrained (YOLOv11n gốc lọc 6 class)
    for p in [
        SCRIPT_DIR / "yolo11n.pt",
        ROOT_DIR / "yolo11n.pt",
        ROOT_DIR / "1_AI_Processing_Edge" / "yolo11n.pt",
    ]:
        if any(m["label"].startswith("YOLOv11n Goc") for m in models):
            break
        add_model("YOLOv11n Goc (Loc 6 Class)", p)

    return models

def choose_model_dialog():
    """Bật hộp thoại Windows chọn file trọng số model .pt bất kỳ"""
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)

    initial_dir = str((SCRIPT_DIR / "object_detection" / "runs").resolve()) if (SCRIPT_DIR / "object_detection" / "runs").exists() else str(SCRIPT_DIR)
    filetypes = [
        ("YOLO Weights (*.pt)", "*.pt"),
        ("Tất cả tập tin", "*.*")
    ]
    selected_path = filedialog.askopenfilename(
        title="BlindGuard AI - Chọn file trọng số mô hình YOLO (.pt)",
        filetypes=filetypes,
        initialdir=initial_dir
    )
    root.destroy()
    return selected_path if selected_path else None

def choose_video_dialog():
    """Bật hộp thoại Windows chọn file video"""
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)

    filetypes = [
        ("Tất cả Video", "*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm"),
        ("MP4 Video", "*.mp4"),
        ("AVI Video", "*.avi"),
        ("Tất cả tập tin", "*.*")
    ]
    selected_path = filedialog.askopenfilename(
        title="BlindGuard AI - Chọn video kiểm thử nhận diện",
        filetypes=filetypes
    )
    root.destroy()
    return selected_path if selected_path else None

def draw_interactive_button(frame, rect, text, is_hover, bg_color=(45, 45, 45), hover_color=(70, 70, 70), text_color=(255, 255, 255), border_color=(120, 120, 120)):
    """Vẽ nút bấm tương tác (hỗ trợ hover và viền sáng)"""
    x1, y1, x2, y2 = rect
    color = hover_color if is_hover else bg_color
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1)
    b_col = (0, 220, 255) if is_hover else border_color
    cv2.rectangle(frame, (x1, y1), (x2, y2), b_col, 2 if is_hover else 1)
    
    font = cv2.FONT_HERSHEY_DUPLEX
    scale = 0.48 if (y2 - y1) < 40 else 0.58
    (tw, th), _ = cv2.getTextSize(text, font, scale, 1)
    tx = x1 + (x2 - x1 - tw) // 2
    ty = y1 + (y2 - y1 + th) // 2
    cv2.putText(frame, text, (tx, ty), font, scale, text_color, 1, cv2.LINE_AA)

def is_point_in_rect(pt, rect):
    x, y = pt
    x1, y1, x2, y2 = rect
    return x1 <= x <= x2 and y1 <= y <= y2

def is_coco_model(model):
    """Kiểm tra mô hình có phải là mô hình COCO gốc (80 class) hay không"""
    return len(model.names) >= 80 or 67 in model.names

def main_app(model_path=None, conf_thres=0.35, iou_thres=0.45):
    global mouse_pos, mouse_clicked

    print("="*75)
    print(f"{'BLINDGUARD AI - TRÌNH KIỂM THỬ TRỰC QUAN FISHEYE 180°':^75}")
    print("="*75)

    # 1. Quản lý danh sách Model có sẵn
    available_models = discover_available_models()
    if model_path:
        mp = Path(model_path).resolve()
        if mp.is_file():
            lbl = mp.stem
            if "v4" in str(mp).lower():
                lbl = "Model v4 (Toi uu Person/Xe dap)"
            elif "v3" in str(mp).lower():
                lbl = "Model v3 (Xe keo Fisheye)"
            elif "v2" in str(mp).lower():
                lbl = "Model v2 (Cu hon)"
            elif "v1" in str(mp).lower():
                lbl = "Model v1 (Cu)"
            available_models.insert(0, {"label": lbl, "path": str(mp)})

    if not available_models:
        print("[!] Không tìm thấy best.pt trong các thư mục mặc định.")
        print("[*] Vui lòng chọn file trọng số mô hình YOLO (.pt)...")
        chosen = choose_model_dialog()
        if chosen and Path(chosen).is_file():
            available_models.append({"label": Path(chosen).stem, "path": str(Path(chosen).resolve())})
        else:
            print("[Error] Không có mô hình nào được chọn. Đang thoát.")
            return

    current_model_idx = 0
    curr_info = available_models[current_model_idx]
    print(f"[*] Danh sách mô hình tìm thấy ({len(available_models)}):")
    for idx, m in enumerate(available_models):
        prefix = "-> [HIENTAI]" if idx == current_model_idx else "  "
        print(f"    {prefix} [{idx+1}] {m['label']} : {m['path']}")

    # Nạp mô hình ban đầu
    try:
        from ultralytics import YOLO
        print(f"[*] Đang nạp mô hình: {curr_info['label']} ({curr_info['path']})...")
        model = YOLO(curr_info['path'])
        print(f"[+] Nạp thành công! Số lượng class của mô hình: {len(model.names)}")
    except Exception as e:
        print(f"[Error] Lỗi nạp mô hình ban đầu: {e}")
        return

    # Chế độ Tracking ByteTrack (True = BẬT ByteTrack theo dõi liên tục + làm mượt box, False = Single-frame)
    use_tracking = True
    tracker_yaml = str((SCRIPT_DIR / "mot_tracking" / "bytetrack_fisheye.yaml").resolve())
    if not Path(tracker_yaml).exists():
        tracker_yaml = "bytetrack.yaml"

    # Bộ đệm làm mượt box (EMA), vệt quỹ đạo (Trail), dự đoán vận tốc và chống nhấp nháy
    smoothed_boxes = {}       # track_id -> np.array([x1, y1, x2, y2], dtype=float)
    track_velocities = {}     # track_id -> np.array([vx1, vy1, vx2, vy2], dtype=float)
    track_trails = {}         # track_id -> list of (center_x, bottom_y)
    track_last_seen = {}      # track_id -> frame_idx
    track_class_scores = {}   # track_id -> defaultdict(float) điểm tích lũy class để chống nhấp nháy nhãn
    track_last_conf = {}      # track_id -> float
    frame_counter = 0

    def reset_tracking_state():
        nonlocal smoothed_boxes, track_velocities, track_trails, track_last_seen, track_class_scores, track_last_conf, frame_counter
        smoothed_boxes.clear()
        track_velocities.clear()
        track_trails.clear()
        track_last_seen.clear()
        track_class_scores.clear()
        track_last_conf.clear()
        frame_counter = 0
        if hasattr(model, 'predictor') and model.predictor is not None:
            if hasattr(model.predictor, 'trackers'):
                for t in model.predictor.trackers:
                    try:
                        t.reset()
                    except Exception:
                        pass

    # Toast thông báo trên giao diện khi đổi model / tracking
    toast_msg = f"Đã nạp: {curr_info['label']}"
    toast_time = time.time() + 2.5

    def switch_to_next_model():
        nonlocal current_model_idx, model, toast_msg, toast_time
        if len(available_models) > 1:
            current_model_idx = (current_model_idx + 1) % len(available_models)
            target = available_models[current_model_idx]
            try:
                print(f"[*] Đang chuyển sang mô hình: {target['label']} ({target['path']})")
                model = YOLO(target['path'])
                reset_tracking_state()
                toast_msg = f"Da doi: {target['label']}"
                toast_time = time.time() + 2.5
                print(f"[+] Đổi thành công: {target['label']} ({len(model.names)} classes)")
            except Exception as err:
                print(f"[Error] Lỗi khi đổi mô hình: {err}")
                toast_msg = f"Loi doi model: {err}"
                toast_time = time.time() + 3.0
        else:
            browse_and_add_model()

    def toggle_tracking_mode():
        nonlocal use_tracking, toast_msg, toast_time
        use_tracking = not use_tracking
        reset_tracking_state()
        status = "BAT (ByteTrack + Smoothing)" if use_tracking else "TAT (Single-frame)"
        toast_msg = f"Tracking: {status}"
        toast_time = time.time() + 2.0
        print(f"[*] Chế độ Tracking: {status}")

    def browse_and_add_model():
        nonlocal current_model_idx, model, toast_msg, toast_time
        chosen = choose_model_dialog()
        if chosen and Path(chosen).is_file():
            resolved = str(Path(chosen).resolve())
            for i, m in enumerate(available_models):
                if m["path"] == resolved:
                    current_model_idx = i
                    try:
                        model = YOLO(resolved)
                        toast_msg = f"Da doi: {m['label']}"
                        toast_time = time.time() + 2.5
                    except Exception as err:
                        toast_msg = f"Loi: {err}"
                        toast_time = time.time() + 3.0
                    return
            lbl = Path(chosen).stem
            if "v3" in resolved.lower():
                lbl = "Model v3 (Xe keo Fisheye)"
            elif "v2" in resolved.lower():
                lbl = "Model v2 (Cu hon)"
            elif "v1" in resolved.lower():
                lbl = "Model v1 (Cu)"
            available_models.append({"label": lbl, "path": resolved})
            current_model_idx = len(available_models) - 1
            try:
                model = YOLO(resolved)
                toast_msg = f"Da nap: {lbl}"
                toast_time = time.time() + 2.5
                print(f"[+] Đã nạp thành công mô hình: {lbl}")
            except Exception as err:
                toast_msg = f"Loi: {err}"
                toast_time = time.time() + 3.0

    screen_w, screen_h = get_screen_resolution()
    print(f"[*] Màn hình máy tính: {screen_w} x {screen_h}")

    window_name = "BlindGuard AI - Visual Detector"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window_name, on_mouse_event)

    # Khởi tạo kích thước màn hình ban đầu (căn giữa màn hình)
    app_w = min(900, int(screen_w * 0.60))
    app_h = min(620, int(screen_h * 0.60))
    update_window_geometry(window_name, app_w, app_h, screen_w, screen_h)

    current_video_path = None
    state = "START"  # Các trạng thái: "START", "PLAYING", "PAUSED", "ENDED"
    cap = None
    fps_list = []
    current_frame = None
    detected_counts = {}
    avg_fps = 0.0

    # Biến kiểm soát tốc độ phát & FPS gốc
    speed_idx = 2  # Mặc định mức 1.0x (Chuẩn tốc độ gốc của video)
    current_speed = SPEED_PRESETS[speed_idx]
    video_fps = 30.0
    last_frame_timestamp = time.time()

    while True:
        curr_label = available_models[current_model_idx]["label"]
        model_is_coco = is_coco_model(model)

        # -------------------------------------------------------------
        # 1. TRẠNG THÁI: START (Màn hình mở đầu có nút CHỌN VIDEO & ĐỔI MODEL)
        # -------------------------------------------------------------
        if state == "START":
            start_canvas = np.zeros((app_h, app_w, 3), dtype=np.uint8)
            for r in range(app_h):
                val = int(25 + 15 * (r / app_h))
                start_canvas[r, :] = (val, val, val)

            # Logo & Tiêu đề
            cv2.putText(start_canvas, "BLINDGUARD AI", (app_w // 2 - 180, app_h // 2 - 150),
                        cv2.FONT_HERSHEY_DUPLEX, 1.25, (0, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(start_canvas, "Edge Traffic Vehicle Detection (Fisheye 180 deg)", (app_w // 2 - 240, app_h // 2 - 115),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.60, (200, 200, 200), 1, cv2.LINE_AA)

            # Khung thông tin Model đang chọn
            box_w, box_h = min(580, app_w - 40), 54
            bx1 = (app_w - box_w) // 2
            by1 = app_h // 2 - 92
            cv2.rectangle(start_canvas, (bx1, by1), (bx1 + box_w, by1 + box_h), (35, 30, 45), -1)
            cv2.rectangle(start_canvas, (bx1, by1), (bx1 + box_w, by1 + box_h), (130, 80, 180), 1)
            
            m_path = available_models[current_model_idx]["path"]
            m_path_short = ("..." + m_path[-42:]) if len(m_path) > 45 else m_path
            mode_desc = "Theo doi: ByteTrack (ON)" if use_tracking else "Nhan dien: Tinh (OFF)"
            cv2.putText(start_canvas, f"Model: {curr_label}  |  {mode_desc}", (bx1 + 15, by1 + 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 200), 1, cv2.LINE_AA)
            cv2.putText(start_canvas, f"Tap tin: {m_path_short}", (bx1 + 15, by1 + 44),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, (180, 180, 190), 1, cv2.LINE_AA)

            # Nút 1: [ 📂 CHỌN VIDEO ĐỂ KIỂM THỬ ]
            btn_w = min(480, app_w - 60)
            btn_bx1 = (app_w - btn_w) // 2
            btn_bx2 = btn_bx1 + btn_w

            btn_choose_rect = (btn_bx1, app_h // 2 - 22, btn_bx2, app_h // 2 + 26)
            hover_choose = is_point_in_rect(mouse_pos, btn_choose_rect)
            draw_interactive_button(start_canvas, btn_choose_rect, "[ CHON VIDEO DE KIEM THU ]",
                                    hover_choose, bg_color=(30, 80, 160), hover_color=(45, 120, 230))

            # Nút 2: [ 🔄 ĐỔI MODEL ]
            next_idx = (current_model_idx + 1) % len(available_models)
            next_label = available_models[next_idx]["label"] if len(available_models) > 1 else "Duyệt .pt"
            btn_model_rect = (btn_bx1, app_h // 2 + 34, btn_bx2, app_h // 2 + 76)
            hover_model = is_point_in_rect(mouse_pos, btn_model_rect)
            draw_interactive_button(start_canvas, btn_model_rect, f"[ DOI MODEL: Chuyen sang {next_label} ]",
                                    hover_model, bg_color=(90, 35, 130), hover_color=(135, 55, 195),
                                    text_color=(255, 255, 255))

            # Nút 3: [ 🛰️ CHẾ ĐỘ TRACKING: BYTETRACK BẬT / TẮT ]
            track_btn_txt = "Tracking: [ BAT ] (ByteTrack + Khu giat)" if use_tracking else "Tracking: [ TAT ] (Nhan dien Tinh)"
            btn_track_rect = (btn_bx1, app_h // 2 + 84, btn_bx2, app_h // 2 + 122)
            hover_track = is_point_in_rect(mouse_pos, btn_track_rect)
            draw_interactive_button(start_canvas, btn_track_rect, track_btn_txt, hover_track,
                                    bg_color=(25, 75, 75) if use_tracking else (50, 50, 50),
                                    hover_color=(35, 110, 110) if use_tracking else (70, 70, 70),
                                    text_color=(0, 255, 220) if use_tracking else (180, 180, 180))

            # Nút 4: [ 📁 Duyệt file .pt khác ]
            btn_browse_rect = (btn_bx1, app_h // 2 + 130, btn_bx2, app_h // 2 + 166)
            hover_browse = is_point_in_rect(mouse_pos, btn_browse_rect)
            draw_interactive_button(start_canvas, btn_browse_rect, "Duyet file model khac (.pt)",
                                    hover_browse, bg_color=(45, 60, 75), hover_color=(65, 90, 115),
                                    text_color=(210, 230, 255))

            # Nút 5: [ ❌ Thoát ]
            btn_exit_rect = ((app_w - 200) // 2, app_h // 2 + 176, (app_w + 200) // 2, app_h // 2 + 210)
            hover_exit = is_point_in_rect(mouse_pos, btn_exit_rect)
            draw_interactive_button(start_canvas, btn_exit_rect, "Thoat (Quit)",
                                    hover_exit, bg_color=(50, 30, 30), hover_color=(120, 40, 40), text_color=(200, 200, 200))

            # Hướng dẫn phím tắt dưới đáy
            cv2.putText(start_canvas, "Phim tat: [Enter/O] Chon Video  |  [M] Doi Model  |  [T] Tracking BAT/TAT  |  [B] Duyet .pt  |  [Q] Thoat",
                        (app_w // 2 - 330, app_h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (140, 140, 140), 1, cv2.LINE_AA)

            cv2.imshow(window_name, start_canvas)
            key = cv2.waitKey(20) & 0xFF

            if mouse_clicked:
                mouse_clicked = False
                if hover_choose:
                    vid = choose_video_dialog()
                    if vid:
                        cap, app_w, app_h, video_fps = setup_video_capture(vid, screen_w, screen_h)
                        if cap:
                            current_video_path = vid
                            update_window_geometry(window_name, app_w, app_h, screen_w, screen_h)
                            state = "PLAYING"
                            fps_list = []
                            avg_fps = video_fps
                            detected_counts = {}
                            last_frame_timestamp = time.time()
                elif hover_model:
                    switch_to_next_model()
                elif hover_track:
                    toggle_tracking_mode()
                elif hover_browse:
                    browse_and_add_model()
                elif hover_exit:
                    break

            if key in [ord('q'), ord('Q'), 27]:
                break
            elif key in [ord('m'), ord('M')]:
                switch_to_next_model()
            elif key in [ord('t'), ord('T')]:
                toggle_tracking_mode()
            elif key in [ord('b'), ord('B')]:
                browse_and_add_model()
            elif key in [ord('o'), ord('O'), 13]:
                vid = choose_video_dialog()
                if vid:
                    cap, app_w, app_h, video_fps = setup_video_capture(vid, screen_w, screen_h)
                    if cap:
                        current_video_path = vid
                        update_window_geometry(window_name, app_w, app_h, screen_w, screen_h)
                        state = "PLAYING"
                        fps_list = []
                        avg_fps = video_fps
                        detected_counts = {}
                        last_frame_timestamp = time.time()

        # -------------------------------------------------------------
        # 2. TRẠNG THÁI: PLAYING / PAUSED (Đang chiếu video & AI)
        # -------------------------------------------------------------
        elif state in ["PLAYING", "PAUSED"]:
            t_frame_start = time.time()
            if state == "PLAYING":
                ret, frame = cap.read()
                if not ret:
                    state = "ENDED"
                    continue

                current_frame = cv2.resize(frame, (app_w, app_h), interpolation=cv2.INTER_LINEAR)

                frame_counter += 1

                # Xác định danh sách class cần nhận diện (nếu dùng model COCO gốc 80 class thì chỉ lấy 6 class giao thông)
                predict_classes = COCO_TRAFFIC_IDS if model_is_coco else None

                # Thực hiện suy luận (ByteTrack Tracking hoặc Single-frame Detection)
                if use_tracking:
                    # Truyền conf=0.12 vào model.track() để ByteTrack kích hoạt trọn vẹn Stage 2 (cứu box mờ / méo mắt cá)
                    # File bytetrack_fisheye.yaml sẽ quản lý việc chỉ cấp ID mới khi conf >= 0.40 (tránh sinh track rác)
                    results = model.track(
                        source=current_frame,
                        tracker=tracker_yaml,
                        conf=0.12,
                        iou=iou_thres,
                        classes=predict_classes,
                        persist=True,
                        device=0 if cv2.cuda.getCudaEnabledDeviceCount() > 0 else "0",
                        verbose=False
                    )
                else:
                    results = model.predict(
                        source=current_frame,
                        conf=conf_thres,
                        iou=iou_thres,
                        classes=predict_classes,
                        device=0 if cv2.cuda.getCudaEnabledDeviceCount() > 0 else "0",
                        verbose=False
                    )

                detected_counts = {}
                active_track_ids = set()

                for r in results:
                    boxes = r.boxes
                    has_id = (boxes.id is not None) if use_tracking else False

                    for idx_b, box in enumerate(boxes):
                        cls_id = int(box.cls[0].item())
                        conf = float(box.conf[0].item())

                        # Lấy tên class CHÍNH XÁC từ model.names
                        cname = model.names.get(cls_id, f"cls_{cls_id}")

                        # Lọc an toàn cho mô hình COCO (chỉ giữ 6 class giao thông chuẩn)
                        if model_is_coco and cname not in STANDARD_6_CLASSES:
                            continue

                        xyxy_raw = box.xyxy[0].cpu().numpy().astype(float)

                        # Bỏ qua box bất thường che kín > 85% diện tích màn hình (ví dụ người đứng bám sát mắt cá camera)
                        bw = xyxy_raw[2] - xyxy_raw[0]
                        bh = xyxy_raw[3] - xyxy_raw[1]
                        if (bw * bh) > 0.85 * (app_w * app_h):
                            continue

                        track_id = int(boxes.id[idx_b].item()) if (has_id and idx_b < len(boxes.id)) else None

                        if track_id is not None:
                            active_track_ids.add(track_id)
                            track_last_seen[track_id] = frame_counter
                            track_last_conf[track_id] = conf

                            # Tích lũy điểm phân loại (Class Voting) để triệt tiêu hiện tượng nhấp nháy nhãn (ví dụ xe kéo <-> người)
                            if track_id not in track_class_scores:
                                track_class_scores[track_id] = defaultdict(float)
                            track_class_scores[track_id][cname] += conf
                            stable_cname = max(track_class_scores[track_id].items(), key=lambda x: x[1])[0]

                            # Tính vận tốc chuyển động & làm mượt tọa độ Box (EMA Smoothing - alpha=0.65)
                            if track_id in smoothed_boxes:
                                old_box = smoothed_boxes[track_id]
                                xyxy_smooth = 0.65 * xyxy_raw + 0.35 * old_box
                                track_velocities[track_id] = 0.6 * track_velocities.get(track_id, np.zeros(4)) + 0.4 * (xyxy_smooth - old_box)
                            else:
                                xyxy_smooth = xyxy_raw
                                track_velocities[track_id] = np.zeros(4)
                            smoothed_boxes[track_id] = xyxy_smooth
                            x1, y1, x2, y2 = xyxy_smooth.astype(int)

                            # Cập nhật vệt quỹ đạo di chuyển (Trajectory Trail)
                            bot_center = ((x1 + x2) // 2, y2)
                            if track_id not in track_trails:
                                track_trails[track_id] = []
                            track_trails[track_id].append(bot_center)
                            if len(track_trails[track_id]) > 20:
                                track_trails[track_id].pop(0)

                            detected_counts[stable_cname] = detected_counts.get(stable_cname, 0) + 1
                            label_str = f"#{track_id} {stable_cname} {conf:.2f}"
                            display_cname = stable_cname
                        else:
                            x1, y1, x2, y2 = xyxy_raw.astype(int)
                            label_str = f"{cname} {conf:.2f}"
                            display_cname = cname
                            detected_counts[cname] = detected_counts.get(cname, 0) + 1

                        color = CLASS_COLORS.get(display_cname, (0, 255, 120))
                        thick = 3 if display_cname in ['xe_keo', 'xich_lo'] else 2
                        cv2.rectangle(current_frame, (x1, y1), (x2, y2), color, thick)

                        (tw, th), _ = cv2.getTextSize(label_str, cv2.FONT_HERSHEY_DUPLEX, 0.48, 1)
                        label_y1 = max(y1 - th - 8, 50)
                        cv2.rectangle(current_frame, (x1, label_y1), (x1 + tw + 6, label_y1 + th + 6), color, -1)
                        cv2.putText(current_frame, label_str, (x1 + 3, label_y1 + th + 1),
                                    cv2.FONT_HERSHEY_DUPLEX, 0.48, (0, 0, 0), 1, cv2.LINE_AA)

                # Duy trì Track Coasting (giữ box khi ByteTrack/YOLO tạm thời mất dấu 1-5 frames do chớp sáng hoặc che khuất)
                if use_tracking:
                    MAX_COAST_FRAMES = 5  # ~0.16 giây ở 30 FPS
                    for tid, last_f in list(track_last_seen.items()):
                        missed_frames = frame_counter - last_f
                        if tid not in active_track_ids and 1 <= missed_frames <= MAX_COAST_FRAMES:
                            if tid in smoothed_boxes and tid in track_class_scores:
                                # Dự đoán vị trí tiếp tục theo vận tốc
                                vel = track_velocities.get(tid, np.zeros(4))
                                smoothed_boxes[tid] = smoothed_boxes[tid] + vel * 0.7
                                x1, y1, x2, y2 = smoothed_boxes[tid].astype(int)
                                x1, y1 = max(0, x1), max(0, y1)
                                x2, y2 = min(app_w - 1, x2), min(app_h - 1, y2)

                                stable_cname = max(track_class_scores[tid].items(), key=lambda x: x[1])[0]
                                detected_counts[stable_cname] = detected_counts.get(stable_cname, 0) + 1
                                last_conf = track_last_conf.get(tid, 0.3)
                                label_str = f"#{tid} {stable_cname} ~{last_conf:.2f}"
                                color = CLASS_COLORS.get(stable_cname, (0, 255, 120))

                                # Vẽ viền nhẹ nhàng (thickness=2)
                                cv2.rectangle(current_frame, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)

                                (tw, th), _ = cv2.getTextSize(label_str, cv2.FONT_HERSHEY_DUPLEX, 0.44, 1)
                                label_y1 = max(y1 - th - 6, 50)
                                cv2.rectangle(current_frame, (x1, label_y1), (x1 + tw + 6, label_y1 + th + 6), (50, 50, 50), -1)
                                cv2.putText(current_frame, label_str, (x1 + 3, label_y1 + th),
                                            cv2.FONT_HERSHEY_DUPLEX, 0.44, (200, 255, 200), 1, cv2.LINE_AA)

                                # Cập nhật vệt di chuyển
                                bot_center = ((x1 + x2) // 2, y2)
                                if tid in track_trails:
                                    track_trails[tid].append(bot_center)
                                    if len(track_trails[tid]) > 20:
                                        track_trails[tid].pop(0)

                    # Vẽ vệt quỹ đạo di chuyển (Trajectory Trail) cho các xe đang theo dõi (kể cả đang coasting)
                    for tid, trail in list(track_trails.items()):
                        if (tid in active_track_ids or (frame_counter - track_last_seen.get(tid, 0) <= MAX_COAST_FRAMES)) and len(trail) > 1:
                            for j in range(1, len(trail)):
                                trail_thick = max(1, int(1 + 2.5 * (j / len(trail))))
                                cv2.line(current_frame, trail[j - 1], trail[j], (0, 255, 255), trail_thick, cv2.LINE_AA)

                    # Dọn dẹp bộ đệm khi track_id biến mất quá 60 frames (~2.0s đồng bộ với track_buffer của ByteTrack)
                    stale_ids = [tid for tid, last_f in track_last_seen.items() if frame_counter - last_f > 60]
                    for tid in stale_ids:
                        smoothed_boxes.pop(tid, None)
                        track_velocities.pop(tid, None)
                        track_trails.pop(tid, None)
                        track_last_seen.pop(tid, None)
                        track_class_scores.pop(tid, None)
                        track_last_conf.pop(tid, None)

            # Giao diện Top Bar
            display_img = current_frame.copy()
            top_bar_h = 46
            cv2.rectangle(display_img, (0, 0), (app_w, top_bar_h), (20, 20, 20), -1)

            vname = Path(current_video_path).name if current_video_path else ""
            disp_fps = avg_fps if avg_fps > 0 else video_fps
            status_txt = "TAM DUNG" if state == "PAUSED" else f"{disp_fps:.1f} FPS"
            status_col = (0, 165, 255) if state == "PAUSED" else (0, 255, 0)
            speed_label = f"{current_speed}x"

            is_compact = (app_w < 860)
            if is_compact:
                short_name = (vname[:8] + "..") if len(vname) > 10 else vname
                cv2.putText(display_img, status_txt, (8, 29), cv2.FONT_HERSHEY_DUPLEX, 0.50, status_col, 1, cv2.LINE_AA)

                btn_close_rect = (app_w - 38, 6, app_w - 8, 40)
                btn_pause_rect = (app_w - 94, 6, app_w - 44, 40)
                btn_speed_rect = (app_w - 150, 6, app_w - 100, 40)
                btn_change_rect = (app_w - 212, 6, app_w - 156, 40)
                btn_track_rect = (app_w - 296, 6, app_w - 218, 40)
                btn_model_rect = (app_w - 396, 6, app_w - 302, 40)

                pause_label = "Tiep" if state == "PAUSED" else "Pause"
                change_label = "Vid"
                track_label = "Track" if use_tracking else "NoTrack"
                model_btn_txt = f"{curr_label[:8]}"
            else:
                cv2.putText(display_img, f"BlindGuard AI | {vname}", (14, 28),
                            cv2.FONT_HERSHEY_DUPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)
                fps_info = f"{status_txt} (Goc: {video_fps:.0f} FPS)" if state != "PAUSED" else status_txt
                cv2.putText(display_img, fps_info, (app_w - 710, 28),
                            cv2.FONT_HERSHEY_DUPLEX, 0.48, status_col, 1, cv2.LINE_AA)

                btn_close_rect = (app_w - 44, 6, app_w - 10, 40)
                btn_pause_rect = (app_w - 134, 6, app_w - 50, 40)
                btn_speed_rect = (app_w - 202, 6, app_w - 140, 40)
                btn_change_rect = (app_w - 298, 6, app_w - 208, 40)
                btn_track_rect = (app_w - 424, 6, app_w - 304, 40)
                btn_model_rect = (app_w - 580, 6, app_w - 430, 40)

                pause_label = "Tiep tuc" if state == "PAUSED" else "Tam dung"
                change_label = "Doi Video"
                track_label = "Tracking: ByteTrack" if use_tracking else "Tracking: OFF"
                model_btn_txt = f"Model: {curr_label}"

            hover_close = is_point_in_rect(mouse_pos, btn_close_rect)
            hover_pause = is_point_in_rect(mouse_pos, btn_pause_rect)
            hover_speed = is_point_in_rect(mouse_pos, btn_speed_rect)
            hover_change = is_point_in_rect(mouse_pos, btn_change_rect)
            hover_track = is_point_in_rect(mouse_pos, btn_track_rect)
            hover_model = is_point_in_rect(mouse_pos, btn_model_rect)

            # Vẽ các nút điều khiển trên Top Bar
            draw_interactive_button(display_img, btn_model_rect, model_btn_txt, hover_model,
                                    bg_color=(95, 35, 140), hover_color=(145, 55, 205), text_color=(255, 255, 255))
            draw_interactive_button(display_img, btn_track_rect, track_label, hover_track,
                                    bg_color=(25, 75, 75) if use_tracking else (50, 50, 50),
                                    hover_color=(35, 115, 115) if use_tracking else (75, 75, 75),
                                    text_color=(0, 255, 220) if use_tracking else (180, 180, 180))
            draw_interactive_button(display_img, btn_change_rect, change_label, hover_change,
                                    bg_color=(35, 75, 140), hover_color=(45, 110, 200))
            draw_interactive_button(display_img, btn_speed_rect, speed_label, hover_speed,
                                    bg_color=(40, 65, 75), hover_color=(55, 105, 125), text_color=(255, 235, 130))
            draw_interactive_button(display_img, btn_pause_rect, pause_label, hover_pause,
                                    bg_color=(50, 50, 50), hover_color=(80, 80, 80))
            draw_interactive_button(display_img, btn_close_rect, "X", hover_close,
                                    bg_color=(80, 30, 30), hover_color=(160, 40, 40), text_color=(255, 255, 255))

            # Toast thông báo khi đổi model hoặc chế độ
            if time.time() < toast_time:
                toast_bar_h = 30
                cv2.rectangle(display_img, (0, top_bar_h), (app_w, top_bar_h + toast_bar_h), (110, 40, 160), -1)
                cv2.putText(display_img, f"[*] {toast_msg}  (Nhan M doi model, T doi tracking)", (16, top_bar_h + 20),
                            cv2.FONT_HERSHEY_DUPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)

            # Sub-bar thống kê các đối tượng nhận diện
            stat_items = []
            for cn, count in sorted(detected_counts.items(), key=lambda x: -x[1]):
                if count > 0:
                    stat_items.append(f"{cn}: {count}")
            if stat_items:
                sub_y = top_bar_h + (30 if time.time() < toast_time else 0)
                sub_h = 28
                cv2.rectangle(display_img, (0, sub_y), (app_w, sub_y + sub_h), (35, 35, 35), -1)
                cv2.putText(display_img, "  |  ".join(stat_items), (14, sub_y + 19),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.46, (220, 240, 255), 1, cv2.LINE_AA)

            # Hướng dẫn phím tắt ở đáy
            bot_h = 24
            cv2.rectangle(display_img, (0, app_h - bot_h), (app_w, app_h), (15, 15, 15), -1)
            if is_compact:
                bot_text = f"[M] Model | [T] Track ON/OFF | [SPACE] Pause | [[]/[]] ({current_speed}x) | [R] Vid | [Q] Thoat"
            else:
                bot_text = f"Phim: [M] Doi Model  |  [T] Tracking BAT/TAT  |  [B] Duyet .pt  |  [SPACE] Tam dung  |  [[]/[]] Toc do ({current_speed}x)  |  [R] Doi Video  |  [S] Chup  |  [Q] Thoat"
            cv2.putText(display_img, bot_text, (12, app_h - 7),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, (180, 180, 180), 1, cv2.LINE_AA)

            cv2.imshow(window_name, display_img)

            # Đồng bộ FPS thời gian thực
            if state == "PLAYING":
                target_frame_time = 1.0 / max(1.0, (video_fps * current_speed))
                elapsed_proc = time.time() - t_frame_start
                wait_sec = target_frame_time - elapsed_proc
                wait_ms = max(1, int(wait_sec * 1000))
            else:
                wait_ms = 40

            key = cv2.waitKey(wait_ms) & 0xFF

            if state == "PLAYING":
                now = time.time()
                dt = now - last_frame_timestamp
                last_frame_timestamp = now
                if dt > 0.001:
                    fps_list.append(1.0 / dt)
                    if len(fps_list) > 20:
                        fps_list.pop(0)
                    avg_fps = sum(fps_list) / len(fps_list)

            # Xử lý click chuột trong lúc chiếu
            if mouse_clicked:
                mouse_clicked = False
                if hover_model:
                    switch_to_next_model()
                elif hover_track:
                    toggle_tracking_mode()
                elif hover_change:
                    vid = choose_video_dialog()
                    if vid:
                        if cap:
                            cap.release()
                        cap, app_w, app_h, video_fps = setup_video_capture(vid, screen_w, screen_h)
                        if cap:
                            current_video_path = vid
                            update_window_geometry(window_name, app_w, app_h, screen_w, screen_h)
                            state = "PLAYING"
                            fps_list = []
                            avg_fps = video_fps
                            detected_counts = {}
                            reset_tracking_state()
                            last_frame_timestamp = time.time()
                elif hover_speed:
                    speed_idx = (speed_idx + 1) % len(SPEED_PRESETS)
                    current_speed = SPEED_PRESETS[speed_idx]
                elif hover_pause:
                    state = "PAUSED" if state == "PLAYING" else "PLAYING"
                    last_frame_timestamp = time.time()
                elif hover_close:
                    cap.release()
                    cv2.destroyAllWindows()
                    return

            # Xử lý phím tắt
            if key in [ord('q'), ord('Q'), 27]:
                cap.release()
                cv2.destroyAllWindows()
                return
            elif key in [ord('m'), ord('M')]:
                switch_to_next_model()
            elif key in [ord('t'), ord('T')]:
                toggle_tracking_mode()
            elif key in [ord('b'), ord('B')]:
                browse_and_add_model()
            elif key in [ord('r'), ord('R'), ord('c'), ord('C')]:
                vid = choose_video_dialog()
                if vid:
                    if cap:
                        cap.release()
                    cap, app_w, app_h, video_fps = setup_video_capture(vid, screen_w, screen_h)
                    if cap:
                        current_video_path = vid
                        update_window_geometry(window_name, app_w, app_h, screen_w, screen_h)
                        state = "PLAYING"
                        fps_list = []
                        avg_fps = video_fps
                        detected_counts = {}
                        reset_tracking_state()
                        last_frame_timestamp = time.time()
            elif key in [ord('['), ord('-')]:
                speed_idx = max(0, speed_idx - 1)
                current_speed = SPEED_PRESETS[speed_idx]
            elif key in [ord(']'), ord('+'), ord('=')]:
                speed_idx = min(len(SPEED_PRESETS) - 1, speed_idx + 1)
                current_speed = SPEED_PRESETS[speed_idx]
            elif key == 32:  # SPACE
                state = "PAUSED" if state == "PLAYING" else "PLAYING"
                last_frame_timestamp = time.time()
            elif key in [ord('s'), ord('S')]:
                save_dir = SCRIPT_DIR / "runs" / "screenshots"
                save_dir.mkdir(parents=True, exist_ok=True)
                snap_path = save_dir / f"snap_{int(time.time())}.jpg"
                cv2.imwrite(str(snap_path), display_img)
                print(f"[+] Đã lưu ảnh chụp màn hình: {snap_path}")
                toast_msg = f"Da luu: {snap_path.name}"
                toast_time = time.time() + 2.0

        # -------------------------------------------------------------
        # 3. TRẠNG THÁI: ENDED (Video đã chiếu xong -> Nút chọn lại & Đổi model)
        # -------------------------------------------------------------
        elif state == "ENDED":
            end_canvas = current_frame.copy() if current_frame is not None else np.zeros((app_h, app_w, 3), dtype=np.uint8)
            overlay = end_canvas.copy()
            cv2.rectangle(overlay, (0, 0), (app_w, app_h), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.65, end_canvas, 0.35, 0, end_canvas)

            card_w, card_h = min(540, app_w - 40), 290
            cx1 = (app_w - card_w) // 2
            cy1 = (app_h - card_h) // 2
            cx2 = cx1 + card_w
            cy2 = cy1 + card_h
            cv2.rectangle(end_canvas, (cx1, cy1), (cx2, cy2), (30, 30, 30), -1)
            cv2.rectangle(end_canvas, (cx1, cy1), (cx2, cy2), (0, 220, 255), 2)

            cv2.putText(end_canvas, "VIDEO DA CHIEU XONG!", (cx1 + 45, cy1 + 38),
                        cv2.FONT_HERSHEY_DUPLEX, 0.85, (0, 255, 255), 2, cv2.LINE_AA)
            mode_desc = "Theo doi: ByteTrack (ON)" if use_tracking else "Nhan dien Tinh (OFF)"
            cv2.putText(end_canvas, f"Model: {curr_label}  |  {mode_desc}", (cx1 + 45, cy1 + 62),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 200), 1, cv2.LINE_AA)

            # Nút 1: [ 📂 CHỌN VIDEO LẠI / ĐỔI VIDEO ]
            btn1_rect = (cx1 + 30, cy1 + 76, cx2 - 30, cy1 + 118)
            hover_btn1 = is_point_in_rect(mouse_pos, btn1_rect)
            draw_interactive_button(end_canvas, btn1_rect, "[ CHON VIDEO LAI / DOI VIDEO ]", hover_btn1,
                                    bg_color=(30, 90, 180), hover_color=(40, 130, 240))

            # Nút 2: [ 🔄 ĐỔI MODEL ]
            next_idx = (current_model_idx + 1) % len(available_models)
            next_label = available_models[next_idx]["label"] if len(available_models) > 1 else "Duyệt .pt"
            btn2_rect = (cx1 + 30, cy1 + 126, cx2 - 30, cy1 + 168)
            hover_btn2 = is_point_in_rect(mouse_pos, btn2_rect)
            draw_interactive_button(end_canvas, btn2_rect, f"[ DOI MODEL: Chuyen sang {next_label} ]", hover_btn2,
                                    bg_color=(90, 35, 130), hover_color=(140, 55, 200), text_color=(255, 255, 255))

            # Nút 3: [ 🛰️ TRACKING BYTETRACK BẬT / TẮT ]
            track_end_txt = "Tracking: [ BAT ] (ByteTrack)" if use_tracking else "Tracking: [ TAT ] (Nhan dien Tinh)"
            btn_track_end = (cx1 + 30, cy1 + 176, cx2 - 30, cy1 + 214)
            hover_track_end = is_point_in_rect(mouse_pos, btn_track_end)
            draw_interactive_button(end_canvas, btn_track_end, track_end_txt, hover_track_end,
                                    bg_color=(25, 75, 75) if use_tracking else (50, 50, 50),
                                    hover_color=(35, 110, 110) if use_tracking else (75, 75, 75),
                                    text_color=(0, 255, 220) if use_tracking else (180, 180, 180))

            # Nút 4: [ 🔁 Phát lại ]
            btn3_rect = (cx1 + 30, cy1 + 222, cx1 + (card_w // 2) - 10, cy1 + 258)
            hover_btn3 = is_point_in_rect(mouse_pos, btn3_rect)
            draw_interactive_button(end_canvas, btn3_rect, f"Phat lai ({current_speed}x)", hover_btn3,
                                    bg_color=(40, 70, 40), hover_color=(50, 110, 50))

            # Nút 5: [ ❌ Thoát ]
            btn5_rect = (cx1 + (card_w // 2) + 10, cy1 + 222, cx2 - 30, cy1 + 258)
            hover_btn5 = is_point_in_rect(mouse_pos, btn5_rect)
            draw_interactive_button(end_canvas, btn5_rect, "Thoat (Exit)", hover_btn5,
                                    bg_color=(60, 30, 30), hover_color=(120, 40, 40))

            cv2.imshow(window_name, end_canvas)
            key = cv2.waitKey(30) & 0xFF

            if mouse_clicked:
                mouse_clicked = False
                if hover_btn1:
                    vid = choose_video_dialog()
                    if vid:
                        if cap:
                            cap.release()
                        cap, app_w, app_h, video_fps = setup_video_capture(vid, screen_w, screen_h)
                        if cap:
                            current_video_path = vid
                            update_window_geometry(window_name, app_w, app_h, screen_w, screen_h)
                            state = "PLAYING"
                            fps_list = []
                            avg_fps = video_fps
                            detected_counts = {}
                            reset_tracking_state()
                            last_frame_timestamp = time.time()
                elif hover_btn2:
                    switch_to_next_model()
                elif hover_track_end:
                    toggle_tracking_mode()
                elif hover_btn3:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    state = "PLAYING"
                    fps_list = []
                    avg_fps = video_fps
                    detected_counts = {}
                    reset_tracking_state()
                    last_frame_timestamp = time.time()
                elif hover_btn5:
                    break

            if key in [ord('m'), ord('M')]:
                switch_to_next_model()
            elif key in [ord('t'), ord('T')]:
                toggle_tracking_mode()
            elif key in [ord('b'), ord('B')]:
                browse_and_add_model()
            elif key in [ord('r'), ord('R'), ord('c'), ord('C')]:
                vid = choose_video_dialog()
                if vid:
                    if cap:
                        cap.release()
                    cap, app_w, app_h, video_fps = setup_video_capture(vid, screen_w, screen_h)
                    if cap:
                        current_video_path = vid
                        update_window_geometry(window_name, app_w, app_h, screen_w, screen_h)
                        state = "PLAYING"
                        fps_list = []
                        avg_fps = video_fps
                        detected_counts = {}
                        last_frame_timestamp = time.time()
            elif key == 32:  # SPACE phát lại
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                state = "PLAYING"
                fps_list = []
                avg_fps = video_fps
                last_frame_timestamp = time.time()
            elif key in [ord('t'), ord('T')]:
                speed_idx = (speed_idx + 1) % len(SPEED_PRESETS)
                current_speed = SPEED_PRESETS[speed_idx]
            elif key in [ord('q'), ord('Q'), 27]:
                break

    if cap:
        cap.release()
    cv2.destroyAllWindows()
    print("\n[+] Đã đóng ứng dụng kiểm thử.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Kiểm thử trực quan Video cho BlindGuardAI")
    parser.add_argument("--model", type=str, default=None, help="Đường dẫn file trọng số model (.pt), mặc định tự tìm v2 rồi tới v1")
    parser.add_argument("--conf", type=float, default=0.35, help="Ngưỡng Confidence (mặc định 0.35)")
    parser.add_argument("--iou", type=float, default=0.45, help="Ngưỡng NMS IoU (mặc định 0.45)")
    args = parser.parse_args()

    main_app(model_path=args.model, conf_thres=args.conf, iou_thres=args.iou)
