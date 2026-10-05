#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================================
                      DỰ ÁN BLINDGUARD AI — TRÌNH TRÌNH DIỄN DEMO CHÍNH
========================================================================================
Tính năng:
1. Giao diện Launcher trực quan: Cho phép chọn video, chọn 1 trong 4 góc camera,
   hoặc mở nhanh Trình cấu hình xe & Homography.
2. Tự động đồng bộ ma trận Homography và thông số xe từ file config/system_config.json.
3. Triết lý thiết kế PHI XÂM LẤN (Non-invasive): Hoàn toàn không can thiệp CAN-bus xe.
4. Phím tắt tiện ích trong lúc phát:
   - [SPACE]: Tạm dừng / Tiếp tục video
   - [C]    : Đổi tuần hoàn qua lại giữa 4 góc Camera
   - [V]    : Mở hộp thoại chọn video khác
   - [D]    : Bật / Tắt hiển thị lưới đa giác nguy hiểm DHZ
   - [+/-/0], [J/L/K], [R]: Giả lập tốc độ, đánh lái, số lùi (kiểm thử 5 kịch bản)
   - [Q/ESC]: Thoát
========================================================================================
"""

import os
import sys
import time
import argparse
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
import numpy as np

# Thiết lập đường dẫn import nội bộ
APP_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = APP_ROOT.parent

sys.path.insert(0, str(APP_ROOT))
sys.path.insert(0, str(APP_ROOT / "core"))

from core.config_loader import SystemConfigManager
from core.homography_manager import MultiCameraHomographyManager
from core.hud_renderer import MultiCamCabinHUDRenderer
from core.motion_analyzer import NonInvasiveMotionAnalyzer
from core.bsri_calculator import BSRICalculator
from core.risk_models import (
    EgoVehicleState,
    TrackedObstacle,
    BSRIResult,
    RiskLevel,
    BlindSpotZone,
    VehicleType
)
from ultralytics import YOLO


class DemoLauncherGUI:
    """Cửa sổ Launcher trực quan chọn video và góc camera trước khi chiếu"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BlindGuard AI — Khởi Động Trình Diễn Demo")
        self.root.geometry("560x420")
        self.root.configure(bg="#1a1a24")
        self.root.resizable(False, False)

        # Căn giữa màn hình
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"560x420+{(sw - 560)//2}+{(sh - 420)//2}")

        self.video_path = ""
        self.camera_angle = "MIRROR_RIGHT"
        self.show_dhz = True
        self.is_confirmed = False

        self._build_ui()

    def _build_ui(self):
        # Tiêu đề
        tk.Label(self.root, text="🛡️ BLINDGUARD AI — DEMO LAUNCHER", font=("Segoe UI", 13, "bold"),
                 fg="#00e5ff", bg="#1a1a24").pack(pady=(16, 4))
        tk.Label(self.root, text="Hệ thống hỗ trợ an toàn & cảnh báo điểm mù phi xâm lấn",
                 font=("Segoe UI", 9), fg="#9fa8da", bg="#1a1a24").pack(pady=(0, 14))

        # Khung 1: Chọn Video
        f_vid = tk.LabelFrame(self.root, text=" 1. CHỌN VIDEO KIỂM THỬ ", font=("Segoe UI", 9, "bold"),
                              fg="#ffffff", bg="#242432", padx=12, pady=10)
        f_vid.pack(fill=tk.X, padx=20, pady=6)

        self.lbl_vid_path = tk.Label(f_vid, text="Chưa chọn video (Vui lòng bấm Duyệt file)",
                                     font=("Segoe UI", 9, "italic"), fg="#ffb74d", bg="#242432",
                                     anchor="w", width=42)
        self.lbl_vid_path.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_browse = tk.Button(f_vid, text="📂 Duyệt File...", font=("Segoe UI", 9, "bold"),
                               bg="#3949ab", fg="#ffffff", relief="flat", padx=10, pady=4,
                               command=self._browse_video)
        btn_browse.pack(side=tk.RIGHT)

        # Khung 2: Chọn Góc Camera
        f_cam = tk.LabelFrame(self.root, text=" 2. CHỌN GÓC CAMERA HIỆN TẠI ", font=("Segoe UI", 9, "bold"),
                              fg="#ffffff", bg="#242432", padx=12, pady=8)
        f_cam.pack(fill=tk.X, padx=20, pady=8)

        self.var_cam = tk.StringVar(value="MIRROR_RIGHT")
        cams = [
            ("MIRROR_RIGHT", "📷 1. Gương Phụ (Hông phải - Góc nguy hiểm nhất)"),
            ("MIRROR_LEFT",  "📷 2. Gương Lái (Hông trái - Quan sát chuyển làn)"),
            ("CAB_FRONT",    "📷 3. Mũi Xe (Cản trước - Đèn đỏ & khởi hành)"),
            ("REAR_TRAILER", "📷 4. Đuôi Xe (Điểm mù lùi bến bãi)")
        ]
        for val, text in cams:
            tk.Radiobutton(f_cam, text=text, variable=self.var_cam, value=val,
                           font=("Segoe UI", 9), fg="#ffffff", bg="#242432",
                           selectcolor="#121218", activebackground="#242432",
                           activeforeground="#00e5ff").pack(anchor="w", pady=2)

        # Khung 3: Nút điều khiển
        f_btn = tk.Frame(self.root, bg="#1a1a24")
        f_btn.pack(fill=tk.X, padx=20, pady=14)

        btn_config = tk.Button(f_btn, text="⚙️ Cấu Hình Xe & Cam", font=("Segoe UI", 9, "bold"),
                               bg="#455a64", fg="#ffffff", relief="flat", padx=14, pady=8,
                               command=self._open_configurator)
        btn_config.pack(side=tk.LEFT)

        btn_run = tk.Button(f_btn, text="🚀 BẮT ĐẦU CHẠY DEMO", font=("Segoe UI", 10, "bold"),
                            bg="#00c853", fg="#ffffff", relief="flat", padx=22, pady=8,
                            command=self._confirm_and_run)
        btn_run.pack(side=tk.RIGHT)

    def _browse_video(self):
        f = filedialog.askopenfilename(
            parent=self.root,
            title="BlindGuard AI — Chọn Video Kiểm Thử Điểm Mù",
            filetypes=[("Video Files", "*.mp4 *.avi *.mkv *.mov *.wmv *.flv"), ("Tất cả tập tin", "*.*")]
        )
        if f:
            self.video_path = f
            short_name = Path(f).name
            if len(short_name) > 36:
                short_name = short_name[:33] + "..."
            self.lbl_vid_path.config(text=f"✅ {short_name}", fg="#00e676")

    def _open_configurator(self):
        cfg_script = APP_ROOT / "system_configurator" / "run_configurator_gui.py"
        try:
            subprocess.Popen([sys.executable, str(cfg_script)])
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể khởi động trình cấu hình: {e}")

    def _confirm_and_run(self):
        if not self.video_path or not Path(self.video_path).is_file():
            # Tự động mở duyệt file nếu chưa chọn
            self._browse_video()
            if not self.video_path or not Path(self.video_path).is_file():
                messagebox.showwarning("Thông báo", "Vui lòng chọn 1 file video kiểm thử!")
                return

        self.camera_angle = self.var_cam.get()
        self.is_confirmed = True
        self.root.destroy()

    def run(self):
        self.root.mainloop()
        return self.is_confirmed, self.video_path, self.camera_angle


def discover_best_model_path() -> str:
    """Tự động tìm kiếm file trọng số tối ưu nhất trong dự án"""
    candidates = [
        PROJECT_ROOT / "1_AI_Processing_Edge" / "object_detection" / "runs" / "yolo11n_blindguard_v4" / "weights" / "best.engine",
        PROJECT_ROOT / "1_AI_Processing_Edge" / "object_detection" / "runs" / "yolo11n_blindguard_v4" / "weights" / "best.pt",
        PROJECT_ROOT / "1_AI_Processing_Edge" / "object_detection" / "runs" / "yolo11n_blindguard_v3" / "weights" / "best.pt",
        PROJECT_ROOT / "1_AI_Processing_Edge" / "object_detection" / "weights" / "best.pt",
        PROJECT_ROOT / "1_AI_Processing_Edge" / "yolo11n.pt"
    ]
    for c in candidates:
        if c.is_file():
            return str(c.resolve())
    return "yolo11n.pt"


def run_blindguard_demo(video_path: str = None, camera_angle: str = None):
    # Nếu không có video truyền qua CLI -> Mở cửa sổ Launcher
    if not video_path or not Path(video_path).is_file():
        launcher = DemoLauncherGUI()
        confirmed, chosen_video, chosen_cam = launcher.run()
        if not confirmed or not chosen_video:
            print("[*] Đã đóng Launcher. Thoát chương trình.")
            return
        video_path = chosen_video
        camera_angle = chosen_cam
    elif not camera_angle:
        camera_angle = "MIRROR_RIGHT"

    print("=" * 80)
    print(f"{'BLINDGUARD AI — HỆ THỐNG AN TOÀN ĐIỂM MÙ PHI XÂM LẤN':^80}")
    print("=" * 80)
    print(f"[+] Video đã chọn : {Path(video_path).name}")
    print(f"[+] Góc Camera    : {camera_angle}")

    # 1. Nạp cấu hình từ system_config.json
    cfg_mgr = SystemConfigManager(APP_ROOT / "config" / "system_config.json")
    v_prof = cfg_mgr.vehicle_profile
    print(f"[+] Hồ sơ xe tải  : {v_prof.get('name', 'N/A')} ({v_prof.get('vehicle_type', 'ARTICULATED')})")

    # 2. Khởi tạo Multi-camera Homography Manager
    homo_mgr = MultiCameraHomographyManager(cfg_mgr, default_camera=camera_angle)
    homo_mgr.set_active_camera(camera_angle)

    # 3. Khởi tạo BSRI Calculator & Motion Analyzer phi xâm lấn (CAN-Bus Free)
    bsri_calc = BSRICalculator(
        vehicle_type=v_prof.get("vehicle_type", "ARTICULATED"),
        wheelbase_tractor=float(v_prof.get("tractor_wheelbase", 3.6)),
        tractor_front_overhang=float(v_prof.get("tractor_front_overhang", 1.35)),
        cab_width=float(v_prof.get("cab_width", 2.5)),
        kingpin_distance=float(v_prof.get("kingpin_distance", 0.30)),
        trailer_wheelbase=float(v_prof.get("trailer_wheelbase", 8.2)),
        trailer_rear_overhang=float(v_prof.get("trailer_rear_overhang", 2.8)),
        trailer_front_overhang=float(v_prof.get("trailer_front_overhang", 1.0)),
        trailer_width=float(v_prof.get("trailer_width", 2.5)),
        trailer_length=float(v_prof.get("trailer_length", 12.0)),
        rigid_front_length=float(v_prof.get("rigid_front_length", 7.15)),
        rigid_front_overhang=float(v_prof.get("rigid_front_overhang", 1.35)),
        rigid_rear_length=float(v_prof.get("rigid_rear_length", 2.4)),
        rigid_width=float(v_prof.get("rigid_width", 2.5)),
        rigid_wheelbase=float(v_prof.get("rigid_wheelbase", 5.8)),
        base_clearance=float(v_prof.get("base_clearance", 1.5))
    )
    motion_analyzer = NonInvasiveMotionAnalyzer(default_speed_mps=5.0)
    motion_analyzer.set_camera_context(camera_angle)

    # 4. Nạp mô hình YOLO & Tracker
    model_path = discover_best_model_path()
    print(f"[*] Nạp mô hình AI: {Path(model_path).name}")
    model = YOLO(model_path)

    tracker_cfg = str(APP_ROOT / "config" / "bytetrack_fisheye.yaml")
    if not Path(tracker_cfg).is_file():
        tracker_cfg = "bytetrack.yaml"

    # 5. Khởi tạo HUD Renderer
    hud_renderer = MultiCamCabinHUDRenderer(show_dhz=True)

    # 6. Mở VideoCapture
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[Error] Không thể mở file video: {video_path}")
        return

    def _video_fps(c) -> float:
        f = c.get(cv2.CAP_PROP_FPS)
        return f if f and 1.0 <= f <= 240.0 else 30.0

    fps = _video_fps(cap)
    win_name = "BlindGuard AI — Cabin HUD (Interactive Demo)"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, 1100, 700)

    print("\n" + "=" * 80)
    print("  ĐANG CHẠY DEMO — HƯỚNG DẪN ĐIỀU KHIỂN:")
    print("    [SPACE]   : Tạm dừng / Tiếp tục video")
    print("    [C]       : Đổi góc Camera (Mirror Right -> Mirror Left -> Front -> Rear)")
    print("    [V]       : Chọn video khác")
    print("    [D]       : Bật / Tắt hiển thị lưới đa giác nguy hiểm DHZ")
    print("    [+ / -]   : Tăng / Giảm tốc độ xe chủ (1 m/s)    [0]: Dừng xe (0 km/h)")
    print("    [J / L]   : Đánh lái trái / phải (yaw ±0.03 rad/s) [K]: Trả lái thẳng")
    print("    [R]       : Bật / Tắt số lùi (R)")
    print("    [Q / ESC] : Thoát chương trình")
    print("=" * 80 + "\n")

    cam_cycle = ["MIRROR_RIGHT", "MIRROR_LEFT", "CAB_FRONT", "REAR_TRAILER"]
    cam_idx = cam_cycle.index(camera_angle) if camera_angle in cam_cycle else 0

    paused = False
    prev_positions = {}
    frame_idx = 0
    display_frame = None
    reset_tracker = True          # persist=False ở lần gọi kế tiếp -> khởi tạo lại ByteTrack
    size_checked = False
    consecutive_read_fail = 0
    last_frame_t = None
    avg_fps = 0.0
    frame_interval = 1.0 / fps

    def _reset_tracking_state():
        nonlocal reset_tracker
        prev_positions.clear()
        reset_tracker = True

    while True:
        loop_start = time.perf_counter()

        if not paused:
            ret, frame = cap.read()
            if not ret:
                consecutive_read_fail += 1
                if consecutive_read_fail >= 2:
                    print("[Error] Video không đọc được khung hình nào. Thoát.")
                    break
                # Hết video -> tua lại từ đầu
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                frame_idx = 0
                _reset_tracking_state()
                continue
            consecutive_read_fail = 0

            frame_idx += 1
            h, w = frame.shape[:2]
            curr_time = frame_idx / fps

            if not size_checked:
                homo_mgr.set_frame_size(w, h)
                if homo_mgr.resolution_mismatch():
                    print(f"[!] Độ phân giải video {w}x{h} khác độ phân giải hiệu chuẩn -> tự quy đổi tỉ lệ.")
                    if homo_mgr.aspect_mismatch():
                        print("[!] CẢNH BÁO: Tỉ lệ khung hình khác lúc hiệu chuẩn, tọa độ mét có thể sai. "
                              "Hãy hiệu chuẩn lại camera bằng video này.")
                size_checked = True

            # Trạng thái xe chủ phi xâm lấn (IMU/GPS hoặc điều khiển thủ công trong demo)
            spd, yaw_r, turn_dir, gear = motion_analyzer.get_motion_state()
            ego_state = EgoVehicleState(
                speed_mps=spd,
                yaw_rate_rad_s=yaw_r,
                turn_signal=turn_dir,
                gear=gear
            )

            # Suy luận YOLO + ByteTrack
            results = model.track(
                source=frame,
                tracker=tracker_cfg,
                conf=0.20,
                iou=0.45,
                persist=not reset_tracker,
                verbose=False
            )
            reset_tracker = False

            obstacles = []
            boxes = results[0].boxes if results else None
            if boxes is not None and boxes.id is not None and len(boxes) > 0:
                # Chuyển GPU -> CPU MỘT LẦN cho cả khung hình (tránh đồng bộ từng box)
                xyxy_all = boxes.xyxy.cpu().numpy()
                cls_all = boxes.cls.cpu().numpy().astype(int)
                conf_all = boxes.conf.cpu().numpy()
                id_all = boxes.id.cpu().numpy().astype(int)
                frame_area = float(w * h)

                for xyxy, cls_id, conf, tid in zip(xyxy_all, cls_all, conf_all, id_all):
                    x1, y1, x2, y2 = (float(v) for v in xyxy)
                    if (x2 - x1) * (y2 - y1) > 0.85 * frame_area:
                        continue

                    # Điểm chạm đất chân vật thể (Ground Anchor) -> tọa độ xe VCS
                    world = homo_mgr.pixel_to_world((x1 + x2) / 2.0, y2)
                    if world is None:
                        continue  # trên đường chân trời / quá xa -> không tin cậy
                    vcs_x, vcs_y, dist_m = world

                    # Làm mượt vận tốc tương đối
                    vel_x, vel_y = 0.0, 0.0
                    if tid in prev_positions:
                        ox, oy, ot, ovx, ovy = prev_positions[tid]
                        dt = max(0.02, curr_time - ot)
                        raw_vx = float(np.clip((vcs_x - ox) / dt, -15.0, 15.0))
                        raw_vy = float(np.clip((vcs_y - oy) / dt, -8.0, 8.0))
                        vel_x = 0.4 * raw_vx + 0.6 * ovx
                        vel_y = 0.4 * raw_vy + 0.6 * ovy
                    prev_positions[int(tid)] = (vcs_x, vcs_y, curr_time, vel_x, vel_y)

                    obstacles.append(TrackedObstacle(
                        track_id=int(tid),
                        class_name=model.names.get(int(cls_id), f"cls_{cls_id}"),
                        confidence=float(conf),
                        bbox_xyxy=(x1, y1, x2, y2),
                        vcs_x=vcs_x,
                        vcs_y=vcs_y,
                        vel_x=vel_x,
                        vel_y=vel_y,
                        distance_m=dist_m
                    ))

            # Đánh giá rủi ro BSRI
            all_bsri, highest_threat = bsri_calc.evaluate_scene(ego_state, obstacles)

            # FPS thực tế = khoảng thời gian giữa 2 khung hình đã xử lý (gồm cả vẽ & chờ phím)
            now = time.perf_counter()
            if last_frame_t is not None:
                inst = 1.0 / max(1e-3, now - last_frame_t)
                avg_fps = inst if avg_fps == 0.0 else 0.9 * avg_fps + 0.1 * inst
            last_frame_t = now

            # Dựng hình Cabin HUD
            display_frame = hud_renderer.render(
                frame=frame,
                camera_key=homo_mgr.active_camera,
                obstacles=obstacles,
                bsri_results=all_bsri,
                highest_threat=highest_threat,
                ego_state=ego_state,
                fps=avg_fps,
                homo_manager=homo_mgr,
                dhz_poly=bsri_calc.last_dhz
            )

        if display_frame is not None:
            cv2.imshow(win_name, display_frame)

        # Chỉ chờ phần thời gian còn lại của khung hình để phát đúng tốc độ thực
        elapsed = time.perf_counter() - loop_start
        wait_ms = 30 if paused else max(1, int((frame_interval - elapsed) * 1000))
        key = cv2.waitKey(wait_ms) & 0xFF

        if key in [ord('q'), ord('Q'), 27]:
            break
        elif key in [ord(' '), ord('p'), ord('P')]:
            paused = not paused
            last_frame_t = None
        elif key in [ord('c'), ord('C')]:
            cam_idx = (cam_idx + 1) % len(cam_cycle)
            new_cam = cam_cycle[cam_idx]
            homo_mgr.set_active_camera(new_cam)
            motion_analyzer.set_camera_context(new_cam)
            size_checked = False
            _reset_tracking_state()  # tọa độ VCS cũ thuộc camera khác -> bỏ để tránh vận tốc ảo
            print(f"[*] Đã chuyển sang góc camera: {new_cam}")
        elif key in [ord('d'), ord('D')]:
            hud_renderer.show_dhz = not hud_renderer.show_dhz
            print(f"[*] Hiển thị vùng DHZ: {'BẬT' if hud_renderer.show_dhz else 'TẮT'}")
        elif key in [ord('+'), ord('=')]:
            motion_analyzer.manual_adjust_speed(+1.0)
        elif key in [ord('-'), ord('_')]:
            motion_analyzer.manual_adjust_speed(-1.0)
        elif key == ord('0'):
            motion_analyzer.manual_stop()
        elif key in [ord('j'), ord('J')]:
            motion_analyzer.manual_adjust_yaw(+0.03)
        elif key in [ord('l'), ord('L')]:
            motion_analyzer.manual_adjust_yaw(-0.03)
        elif key in [ord('k'), ord('K')]:
            motion_analyzer.manual_reset_yaw()
        elif key in [ord('r'), ord('R')]:
            motion_analyzer.manual_toggle_reverse()
            print(f"[*] Số hiện tại: {motion_analyzer.gear}")
        elif key in [ord('v'), ord('V')]:
            launcher = DemoLauncherGUI()
            confirmed, new_v, new_cam = launcher.run()
            if confirmed and new_v and Path(new_v).is_file():
                new_cap = cv2.VideoCapture(new_v)
                if not new_cap.isOpened():
                    print(f"[Error] Không thể mở file video: {new_v}")
                else:
                    cap.release()
                    cap = new_cap
                    fps = _video_fps(cap)
                    frame_interval = 1.0 / fps
                    frame_idx = 0
                    size_checked = False
                    last_frame_t = None
                    consecutive_read_fail = 0
                    if new_cam in cam_cycle:
                        cam_idx = cam_cycle.index(new_cam)
                        homo_mgr.set_active_camera(new_cam)
                        motion_analyzer.set_camera_context(new_cam)
                    _reset_tracking_state()
                    print(f"[+] Đã đổi sang video: {Path(new_v).name} ({homo_mgr.active_camera})")

    cap.release()
    cv2.destroyAllWindows()
    print("[+] Đã kết thúc chương trình demo BlindGuard AI an toàn.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BlindGuard AI - Interactive Demo App")
    parser.add_argument("--video", type=str, default=None, help="Đường dẫn file video (Nếu để trống sẽ hiện Launcher)")
    parser.add_argument("--camera", type=str, default=None, choices=["MIRROR_RIGHT", "MIRROR_LEFT", "CAB_FRONT", "REAR_TRAILER"],
                        help="Góc Camera: MIRROR_RIGHT, MIRROR_LEFT, CAB_FRONT, REAR_TRAILER")
    args = parser.parse_args()

    run_blindguard_demo(video_path=args.video, camera_angle=args.camera)
