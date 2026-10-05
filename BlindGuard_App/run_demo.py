#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================================
                      DỰ ÁN BLINDGUARD AI — TRÌNH TRÌNH DIỄN & KIỂM THỬ THỰC TẾ
========================================================================================
Tính năng:
1. Hỗ trợ Camera Thực Tế (Live Webcam, USB Camera, Jetson CSI Camera, IP RTSP Stream)
   lẫn File Video kiểm thử offline.
2. Giao diện Launcher trực quan: Cho phép chọn nhanh Camera 0 / 1 / 2, quét tìm camera
   đang cắm, hoặc chọn video từ máy tính.
3. Tự động đồng bộ ma trận Homography và thông số xe từ file config/system_config.json.
4. Triết lý thiết kế PHI XÂM LẤN (Non-invasive): Hoàn toàn không can thiệp CAN-bus xe.
5. Phím tắt tiện ích trong lúc phát:
   - [SPACE]: Tạm dừng / Tiếp tục
   - [C]    : Đổi tuần hoàn qua lại giữa 4 góc Camera (Mirror Right -> Left -> Front -> Rear)
   - [V]    : Mở hộp thoại đổi nguồn (đổi sang Camera khác hoặc đổi file Video khác)
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
from typing import Optional, Union, Tuple, List
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


def scan_available_cameras(max_tested: int = 3) -> List[Tuple[int, str]]:
    """Quét nhanh các cổng camera đang kết nối tới máy"""
    found = []
    for idx in range(max_tested):
        cap = None
        try:
            if sys.platform.startswith("win"):
                cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            else:
                cap = cv2.VideoCapture(idx)
            if cap and cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    h, w = frame.shape[:2]
                    found.append((idx, f"Camera {idx} ({w}x{h})"))
                else:
                    found.append((idx, f"Camera {idx} (Sẵn sàng)"))
        except Exception:
            pass
        finally:
            if cap is not None:
                cap.release()
    return found


def open_capture_source(source: Union[str, int], req_w: int = 1280, req_h: int = 720, req_fps: int = 30):
    """
    Chuẩn hóa và khởi tạo VideoCapture cho mọi loại nguồn:
    1. Số nguyên hoặc '0', '1', '2': Camera USB / Webcam máy tính
    2. 'csi://0': Camera CSI phần cứng trên NVIDIA Jetson (IMX219 / IMX477)
    3. 'rtsp://...': Camera IP mạng / Camera xe tải
    4. Đường dẫn file video: 'video.mp4'
    Trả về: (cap, is_live, display_name)
    """
    src_str = str(source).strip() if source is not None else "0"

    # 1. LIVE WEBCAM / USB CAMERA THEO CHỈ SỐ INDEX
    if src_str.isdigit() or (isinstance(source, int) and source >= 0):
        cam_idx = int(src_str)
        cap = None
        # Trên Windows: Ưu tiên DirectShow (DSHOW) để mở ngay lập tức và hỗ trợ MJPG HD
        if sys.platform.startswith("win"):
            try:
                cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
            except Exception:
                cap = None
        if cap is None or not cap.isOpened():
            cap = cv2.VideoCapture(cam_idx)

        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, req_w)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, req_h)
            cap.set(cv2.CAP_PROP_FPS, req_fps)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Giảm tối đa độ trễ hình buffer
            ret, test_f = cap.read()
            actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if ret and test_f is not None:
                actual_h, actual_w = test_f.shape[:2]
            return cap, True, f"🔴 LIVE CAMERA #{cam_idx} ({actual_w}x{actual_h})"
        return cap, True, f"🔴 CAMERA #{cam_idx} (Lỗi mở thiết bị)"

    # 2. CSI CAMERA TRÊN JETSON
    if src_str.lower().startswith("csi://"):
        sensor_id = int(src_str.lower().replace("csi://", "").strip() or 0)
        pipeline = (
            f"nvarguscamerasrc sensor-id={sensor_id} ! "
            f"video/x-raw(memory:NVMM), width=(int){req_w}, height=(int){req_h}, format=(string)NV12, framerate=(fraction){req_fps}/1 ! "
            f"nvvidconv ! "
            f"video/x-raw, width=(int){req_w}, height=(int){req_h}, format=(string)BGRx ! "
            f"videoconvert ! "
            f"video/x-raw, format=(string)BGR ! appsink drop=1"
        )
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        return cap, True, f"🔴 CSI CAMERA #{sensor_id} (Jetson NVMM)"

    # 3. RTSP / IP STREAM
    if src_str.lower().startswith("rtsp://") or src_str.lower().startswith("http://"):
        cap = cv2.VideoCapture(src_str, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap, True, f"🌐 RTSP: {src_str[:32]}..."

    # 4. FILE VIDEO CỤC BỘ
    cap = cv2.VideoCapture(src_str)
    return cap, False, f"📁 VIDEO: {Path(src_str).name}"


class DemoLauncherGUI:
    """Cửa sổ Launcher trực quan chọn Live Camera hoặc Video trước khi chạy"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BlindGuard AI — Khởi Động Trình Diễn & Kiểm Thử")
        self.root.geometry("620x540")
        self.root.configure(bg="#161622")
        self.root.resizable(False, False)

        # Căn giữa màn hình
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"620x540+{(sw - 620)//2}+{(sh - 540)//2}")

        self.chosen_source: Union[str, int] = "0"
        self.camera_angle = "MIRROR_RIGHT"
        self.is_confirmed = False

        self._build_ui()

    def _build_ui(self):
        # Header
        f_head = tk.Frame(self.root, bg="#161622")
        f_head.pack(fill=tk.X, pady=(14, 8))
        tk.Label(f_head, text="🛡️ BLINDGUARD AI — BỘ KIỂM THỬ THỰC TẾ", font=("Segoe UI", 13, "bold"),
                 fg="#00e5ff", bg="#161622").pack()
        tk.Label(f_head, text="Hỗ trợ Camera Trực Tiếp (Live Webcam / USB / CSI / RTSP) hoặc File Video",
                 font=("Segoe UI", 9), fg="#9fa8da", bg="#161622").pack(pady=(2, 0))

        # Khung 1: Chọn Nguồn Đầu Vào
        f_src_box = tk.LabelFrame(self.root, text=" 1. CHỌN NGUỒN ĐẦU VÀO (INPUT SOURCE) ", font=("Segoe UI", 9, "bold"),
                                  fg="#ffd600", bg="#20202e", padx=12, pady=10)
        f_src_box.pack(fill=tk.X, padx=18, pady=6)

        self.var_source_type = tk.StringVar(value="LIVE")

        # Hàng chọn Loại Nguồn: LIVE vs FILE
        f_type_row = tk.Frame(f_src_box, bg="#20202e")
        f_type_row.pack(fill=tk.X, pady=(0, 8))

        rb_live = tk.Radiobutton(f_type_row, text="🔴 CAMERA THỰC TẾ (Live Webcam / USB / CSI / RTSP)",
                                 variable=self.var_source_type, value="LIVE",
                                 font=("Segoe UI", 9, "bold"), fg="#00e676", bg="#20202e",
                                 selectcolor="#121218", activebackground="#20202e",
                                 command=self._on_source_type_toggle)
        rb_live.pack(anchor="w")

        rb_file = tk.Radiobutton(f_type_row, text="📁 FILE VIDEO KIỂM THỬ (Offline Video Demo)",
                                 variable=self.var_source_type, value="FILE",
                                 font=("Segoe UI", 9, "bold"), fg="#4fc3f7", bg="#20202e",
                                 selectcolor="#121218", activebackground="#20202e",
                                 command=self._on_source_type_toggle)
        rb_file.pack(anchor="w", pady=(2, 0))

        # Khung con dành cho Live Camera
        self.f_live_panel = tk.Frame(f_src_box, bg="#1a1a26", padx=10, pady=8, highlightbackground="#2e2e42", highlightthickness=1)
        self.f_live_panel.pack(fill=tk.X, pady=4)

        f_cam_select = tk.Frame(self.f_live_panel, bg="#1a1a26")
        f_cam_select.pack(fill=tk.X)

        self.var_cam_idx = tk.StringVar(value="0")
        cam_radios = [
            ("0", "Camera 0 (Chính)"),
            ("1", "Camera 1"),
            ("2", "Camera 2"),
            ("CUSTOM", "Tùy chỉnh (CSI/RTSP)")
        ]
        for val, txt in cam_radios:
            tk.Radiobutton(f_cam_select, text=txt, variable=self.var_cam_idx, value=val,
                           font=("Segoe UI", 9), fg="#ffffff", bg="#1a1a26",
                           selectcolor="#101018", activebackground="#1a1a26",
                           command=self._on_cam_idx_change).pack(side=tk.LEFT, padx=(0, 8))

        # Ô nhập URL tùy chỉnh
        f_custom = tk.Frame(self.f_live_panel, bg="#1a1a26")
        f_custom.pack(fill=tk.X, pady=(6, 2))
        tk.Label(f_custom, text="Link CSI/RTSP:", font=("Segoe UI", 8), fg="#b0bec5", bg="#1a1a26").pack(side=tk.LEFT, padx=(0, 4))
        self.ent_custom = tk.Entry(f_custom, font=("Segoe UI", 9), bg="#101018", fg="#00e5ff", insertbackground="#ffffff")
        self.ent_custom.insert(0, "csi://0")
        self.ent_custom.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        btn_scan = tk.Button(f_custom, text="🔍 Quét Cam", font=("Segoe UI", 8, "bold"),
                             bg="#37474f", fg="#ffffff", relief="flat", padx=8, pady=2,
                             command=self._scan_cameras_action)
        btn_scan.pack(side=tk.RIGHT)

        self.lbl_scan_status = tk.Label(self.f_live_panel, text="• Mặc định sử dụng Camera 0 (Webcam laptop hoặc USB cam đầu tiên)",
                                        font=("Segoe UI", 8, "italic"), fg="#81c784", bg="#1a1a26", anchor="w")
        self.lbl_scan_status.pack(fill=tk.X, pady=(4, 0))

        # Khung con dành cho File Video
        self.f_file_panel = tk.Frame(f_src_box, bg="#1a1a26", padx=10, pady=8, highlightbackground="#2e2e42", highlightthickness=1)
        self.lbl_file_path = tk.Label(self.f_file_panel, text="Chưa chọn file video...",
                                      font=("Segoe UI", 9, "italic"), fg="#ffb74d", bg="#1a1a26", anchor="w")
        self.lbl_file_path.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_browse = tk.Button(self.f_file_panel, text="📂 Duyệt File...", font=("Segoe UI", 9, "bold"),
                               bg="#3949ab", fg="#ffffff", relief="flat", padx=10, pady=3,
                               command=self._browse_video)
        btn_browse.pack(side=tk.RIGHT)

        # Mặc định mở Live panel
        self._on_source_type_toggle()

        # Khung 2: Chọn Góc Camera (VCS Angle)
        f_cam_box = tk.LabelFrame(self.root, text=" 2. CHỌN GÓC CAMERA HIỆN TẠI (VCS ANGLE) ", font=("Segoe UI", 9, "bold"),
                                  fg="#00e5ff", bg="#20202e", padx=12, pady=6)
        f_cam_box.pack(fill=tk.X, padx=18, pady=6)

        self.var_cam_angle = tk.StringVar(value="MIRROR_RIGHT")
        cams = [
            ("MIRROR_RIGHT", "📷 1. Gương Phụ (Hông phải - Góc mù chém cua xe kéo)"),
            ("MIRROR_LEFT",  "📷 2. Gương Lái (Hông trái - Chuyển làn & vượt xe)"),
            ("CAB_FRONT",    "📷 3. Mũi Xe (Cản trước - R159 | Khuyên dùng khi test Webcam)"),
            ("REAR_TRAILER", "📷 4. Đuôi Xe (Điểm mù lùi bến bãi R158)")
        ]
        for val, text in cams:
            tk.Radiobutton(f_cam_box, text=text, variable=self.var_cam_angle, value=val,
                           font=("Segoe UI", 9), fg="#ffffff", bg="#20202e",
                           selectcolor="#121218", activebackground="#20202e",
                           activeforeground="#00e5ff").pack(anchor="w", pady=1)

        # Khung 3: Nút điều khiển
        f_btn = tk.Frame(self.root, bg="#161622")
        f_btn.pack(fill=tk.X, padx=18, pady=(10, 10))

        btn_config = tk.Button(f_btn, text="⚙️ Cấu Hình Xe & Cam", font=("Segoe UI", 9, "bold"),
                               bg="#37474f", fg="#ffffff", relief="flat", padx=14, pady=8,
                               command=self._open_configurator)
        btn_config.pack(side=tk.LEFT)

        btn_run = tk.Button(f_btn, text="🚀 BẮT ĐẦU CHẠY KIỂM THỬ", font=("Segoe UI", 10, "bold"),
                            bg="#00c853", fg="#ffffff", relief="flat", padx=22, pady=8,
                            activebackground="#00e676", activeforeground="#000000",
                            command=self._confirm_and_run)
        btn_run.pack(side=tk.RIGHT)

    def _on_source_type_toggle(self):
        m = self.var_source_type.get()
        if m == "LIVE":
            self.f_file_panel.pack_forget()
            self.f_live_panel.pack(fill=tk.X, pady=4)
        else:
            self.f_live_panel.pack_forget()
            self.f_file_panel.pack(fill=tk.X, pady=4)

    def _on_cam_idx_change(self):
        choice = self.var_cam_idx.get()
        if choice != "CUSTOM":
            self.lbl_scan_status.config(text=f"• Đã chọn Camera chỉ số #{choice}", fg="#81c784")

    def _scan_cameras_action(self):
        self.lbl_scan_status.config(text="• Đang quét tìm các camera cắm sẵn...", fg="#ffd54f")
        self.root.update_idletasks()
        found = scan_available_cameras(max_tested=3)
        if found:
            info = " | ".join([txt for _, txt in found])
            self.lbl_scan_status.config(text=f"✅ Tìm thấy: {info}", fg="#69f0ae")
            # Tự động chọn camera đầu tiên tìm thấy
            first_idx = str(found[0][0])
            self.var_cam_idx.set(first_idx)
        else:
            self.lbl_scan_status.config(text="⚠️ Không phát hiện webcam nào (Kiểm tra lại cáp cắm USB)", fg="#ff8a80")

    def _browse_video(self):
        f = filedialog.askopenfilename(
            parent=self.root,
            title="BlindGuard AI — Chọn Video Kiểm Thử Điểm Mù",
            filetypes=[("Video Files", "*.mp4 *.avi *.mkv *.mov *.wmv *.flv"), ("Tất cả tập tin", "*.*")]
        )
        if f:
            self.chosen_source = f
            short_name = Path(f).name
            if len(short_name) > 36:
                short_name = short_name[:33] + "..."
            self.lbl_file_path.config(text=f"✅ {short_name}", fg="#00e676")

    def _open_configurator(self):
        cfg_script = APP_ROOT / "system_configurator" / "run_configurator_gui.py"
        try:
            subprocess.Popen([sys.executable, str(cfg_script)])
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể khởi động trình cấu hình: {e}")

    def _confirm_and_run(self):
        m = self.var_source_type.get()
        if m == "LIVE":
            cam_choice = self.var_cam_idx.get()
            if cam_choice == "CUSTOM":
                custom_val = self.ent_custom.get().strip()
                if not custom_val:
                    messagebox.showwarning("Thông báo", "Vui lòng nhập link CSI (csi://0) hoặc RTSP!")
                    return
                self.chosen_source = custom_val
            else:
                self.chosen_source = int(cam_choice)
        else:
            if not self.chosen_source or not Path(str(self.chosen_source)).is_file():
                self._browse_video()
                if not self.chosen_source or not Path(str(self.chosen_source)).is_file():
                    messagebox.showwarning("Thông báo", "Vui lòng chọn 1 file video kiểm thử!")
                    return

        self.camera_angle = self.var_cam_angle.get()
        self.is_confirmed = True
        self.root.destroy()

    def run(self):
        self.root.mainloop()
        return self.is_confirmed, self.chosen_source, self.camera_angle


def discover_best_model_path() -> str:
    """Tự động tìm kiếm file trọng số tối ưu nhất trong dự án"""
    candidates = [
        PROJECT_ROOT / "1_AI_Processing_Edge" / "object_detection" / "runs" / "yolo11n_blindguard_v4" / "weights" / "best.engine",
        APP_ROOT / "weights" / "yolo11n_v4.engine",
        PROJECT_ROOT / "1_AI_Processing_Edge" / "object_detection" / "runs" / "yolo11n_blindguard_v4" / "weights" / "best.pt",
        PROJECT_ROOT / "1_AI_Processing_Edge" / "object_detection" / "runs" / "yolo11n_blindguard_v3" / "weights" / "best.pt",
        PROJECT_ROOT / "1_AI_Processing_Edge" / "object_detection" / "weights" / "best.pt",
        APP_ROOT / "weights" / "yolo11n_v4.onnx",
        APP_ROOT / "weights" / "yolo11n_v3.onnx",
        PROJECT_ROOT / "1_AI_Processing_Edge" / "yolo11n.pt"
    ]
    for c in candidates:
        if isinstance(c, Path) and c.is_file():
            return str(c.resolve())
    return "yolo11n.pt"


def run_blindguard_demo(source: Optional[Union[str, int]] = None, camera_angle: Optional[str] = None,
                         width: int = 1280, height: int = 720, fps: int = 30):
    # Nếu không có nguồn truyền qua CLI -> Mở cửa sổ Launcher
    if source is None:
        launcher = DemoLauncherGUI()
        confirmed, chosen_src, chosen_cam = launcher.run()
        if not confirmed or chosen_src is None:
            print("[*] Đã đóng Launcher. Thoát chương trình.")
            return
        source = chosen_src
        camera_angle = chosen_cam
    elif not camera_angle:
        camera_angle = "MIRROR_RIGHT"

    print("=" * 80)
    print(f"{'BLINDGUARD AI — TRÌNH KIỂM THỬ AN TOÀN ĐIỂM MÙ XE TẢI':^80}")
    print("=" * 80)

    # 1. Khởi tạo nguồn Camera / Video
    cap, is_live, source_title = open_capture_source(source, req_w=width, req_h=height, req_fps=fps)
    if not cap or not cap.isOpened():
        print(f"[Error] Không thể mở nguồn dữ liệu: {source}")
        return

    print(f"[+] Nguồn đầu vào : {source_title}")
    print(f"[+] Chế độ hoạt động : {'🔴 LIVE REAL-TIME CAMERA' if is_live else '📁 OFFLINE VIDEO FILE'}")
    print(f"[+] Góc quan sát : {camera_angle}")

    # 2. Nạp cấu hình từ system_config.json
    cfg_mgr = SystemConfigManager(APP_ROOT / "config" / "system_config.json")
    v_prof = cfg_mgr.vehicle_profile
    print(f"[+] Hồ sơ xe tải : {v_prof.get('name', 'N/A')} ({v_prof.get('vehicle_type', 'ARTICULATED')})")

    # 3. Khởi tạo Multi-camera Homography Manager
    homo_mgr = MultiCameraHomographyManager(cfg_mgr, default_camera=camera_angle)
    homo_mgr.set_active_camera(camera_angle)

    # 4. Khởi tạo BSRI Calculator & Motion Analyzer phi xâm lấn (CAN-Bus Free)
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

    # 5. Nạp mô hình YOLO & Tracker
    model_path = discover_best_model_path()
    print(f"[*] Nạp mô hình AI: {Path(model_path).name}")
    model = YOLO(model_path)

    tracker_cfg = str(APP_ROOT / "config" / "bytetrack_fisheye.yaml")
    if not Path(tracker_cfg).is_file():
        tracker_cfg = "bytetrack.yaml"

    # 6. Khởi tạo HUD Renderer
    hud_renderer = MultiCamCabinHUDRenderer(show_dhz=True)

    def _get_fps(c) -> float:
        f = c.get(cv2.CAP_PROP_FPS)
        return f if f and 1.0 <= f <= 240.0 else 30.0

    fps_val = _get_fps(cap)
    frame_interval = 1.0 / fps_val
    win_name = f"BlindGuard AI — Cabin HUD ({source_title})"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, 1100, 700)

    print("\n" + "=" * 80)
    print("  ĐANG CHẠY KIỂM THỬ — HƯỚNG DẪN ĐIỀU KHIỂN:")
    print("    [SPACE]   : Tạm dừng / Tiếp tục luồng")
    print("    [C]       : Đổi góc Camera (Mirror Right -> Mirror Left -> Front -> Rear)")
    print("    [V]       : Đổi nguồn dữ liệu (Đổi sang Camera khác hoặc đổi file Video)")
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
                if is_live:
                    if consecutive_read_fail >= 30:
                        print("[Error] Mất kết nối camera thực tế liên tục. Đang dừng...")
                        break
                    time.sleep(0.015)
                    continue
                else:
                    if consecutive_read_fail >= 2:
                        print("[Error] Video không đọc được khung hình nào. Thoát.")
                        break
                    # Hết file video -> tua lại từ đầu
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    frame_idx = 0
                    _reset_tracking_state()
                    continue

            consecutive_read_fail = 0
            frame_idx += 1
            h, w = frame.shape[:2]
            curr_time = time.perf_counter() if is_live else (frame_idx / fps_val)

            if not size_checked:
                homo_mgr.set_frame_size(w, h)
                if homo_mgr.resolution_mismatch():
                    print(f"[!] Độ phân giải đầu vào {w}x{h} khác độ phân giải hiệu chuẩn -> tự quy đổi tỉ lệ.")
                    if homo_mgr.aspect_mismatch():
                        print("[!] CẢNH BÁO: Tỉ lệ khung hình khác lúc hiệu chuẩn, tọa độ mét có thể lệch. "
                              "Khuyến nghị hiệu chuẩn Homography cho camera này.")
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
                # Chuyển GPU -> CPU MỘT LẦN cho cả khung hình
                xyxy_all = boxes.xyxy.cpu().numpy()
                cls_all = boxes.cls.cpu().numpy().astype(int)
                conf_all = boxes.conf.cpu().numpy()
                id_all = boxes.id.cpu().numpy().astype(int)
                frame_area = float(w * h)

                for xyxy, cls_id, conf, tid in zip(xyxy_all, cls_all, conf_all, id_all):
                    x1, y1, x2, y2 = (float(v) for v in xyxy)
                    if (x2 - x1) * (y2 - y1) > 0.85 * frame_area:
                        continue

                    # Điểm chạm đất chân vật thể (Ground Anchor) -> tọa độ xe VCS mét
                    world = homo_mgr.pixel_to_world((x1 + x2) / 2.0, y2)
                    if world is None:
                        continue  # trên đường chân trời / quá xa -> bỏ qua
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

            # Đo FPS thực tế giữa các khung hình
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

        # Điều tiết nhịp phát:
        # - Với Live camera: chạy real-time theo luồng phần cứng, waitKey 1ms
        # - Với Video file: pacing delay theo frame_interval để phát đúng tốc độ thực
        elapsed = time.perf_counter() - loop_start
        if paused:
            wait_ms = 30
        elif is_live:
            wait_ms = 1
        else:
            wait_ms = max(1, int((frame_interval - elapsed) * 1000))

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
            _reset_tracking_state()
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
            confirmed, new_src, new_cam = launcher.run()
            if confirmed and new_src is not None:
                new_cap, new_live, new_title = open_capture_source(new_src, req_w=width, req_h=height, req_fps=fps)
                if not new_cap or not new_cap.isOpened():
                    print(f"[Error] Không thể mở nguồn mới: {new_src}")
                else:
                    cap.release()
                    cap = new_cap
                    is_live = new_live
                    source_title = new_title
                    fps_val = _get_fps(cap)
                    frame_interval = 1.0 / fps_val
                    frame_idx = 0
                    size_checked = False
                    last_frame_t = None
                    consecutive_read_fail = 0
                    if new_cam in cam_cycle:
                        cam_idx = cam_cycle.index(new_cam)
                        homo_mgr.set_active_camera(new_cam)
                        motion_analyzer.set_camera_context(new_cam)
                    _reset_tracking_state()
                    cv2.setWindowTitle(win_name, f"BlindGuard AI — Cabin HUD ({source_title})")
                    print(f"[+] Đã đổi nguồn thành công sang: {source_title} ({homo_mgr.active_camera})")

    cap.release()
    cv2.destroyAllWindows()
    print("[+] Đã kết thúc chương trình kiểm thử BlindGuard AI an toàn.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BlindGuard AI - Real Camera & Video Testing")
    parser.add_argument("--source", "--cam", type=str, default=None,
                        help="Nguồn dữ liệu: Chỉ số camera (0, 1), CSI (csi://0), RTSP (rtsp://...) hoặc file video (.mp4). Để trống sẽ mở Launcher GUI.")
    parser.add_argument("--video", type=str, default=None, help="Bí danh của --source chỉ định file video")
    parser.add_argument("--camera", type=str, default=None, choices=["MIRROR_RIGHT", "MIRROR_LEFT", "CAB_FRONT", "REAR_TRAILER"],
                        help="Góc Camera: MIRROR_RIGHT, MIRROR_LEFT, CAB_FRONT, REAR_TRAILER")
    parser.add_argument("--width", type=int, default=1280, help="Chiều rộng khung hình camera (mặc định 1280)")
    parser.add_argument("--height", type=int, default=720, help="Chiều cao khung hình camera (mặc định 720)")
    parser.add_argument("--fps", type=int, default=30, help="Tốc độ khung hình (mặc định 30)")
    args = parser.parse_args()

    target_src = args.source if args.source is not None else args.video
    run_blindguard_demo(source=target_src, camera_angle=args.camera, width=args.width, height=args.height, fps=args.fps)
