"""
Script: calibrate_homography_gui.py
Mô tả: Công cụ giao diện đồ họa trực quan (GUI) hiệu chuẩn ma trận Homography chuyển đổi 2D (Pixel) sang 3D (Mét)
       theo chuẩn Hệ tọa độ xe (Vehicle Coordinate System - VCS) ISO 8855 / SAE J670 của BlindGuard AI.

QUY ƯỚC HỆ TỌA ĐỘ XE (VCS):
- Gốc (0, 0, 0): Tâm trục bánh sau xe đầu kéo (Rear Axle Center).
- Trục X (Longitudinal): Dọc thân xe về PHÍA TRƯỚC (X > 0: Phía trước đầu xe, X < 0: Phía sau đuôi xe/rơ-moóc).
- Trục Y (Lateral): Ngang thân xe sang BÊN TRÁI (Y > 0: Bên Trái xe, Y < 0: Bên Phải xe).
- Trục Z (Vertical): Đứng hướng lên trời (Z = 0: Mặt đường phẳng).

TÍNH NĂNG:
1. Ban đầu KHÔNG tự động hiện bất kỳ ảnh nào. Bắt đầu bằng việc bấm [📂 Chọn Ảnh Camera / Video].
2. Cho phép TỰ NHẬP cả tọa độ mét VCS (X, Y) lẫn tọa độ pixel (u, v) của 4 điểm mốc vào các ô nhập liệu:
   - Tự gõ số trực tiếp bằng bàn phím.
   - Hoặc click chuột lên ảnh để tự động điền tọa độ pixel (u, v).
3. Cung cấp Preset mẫu chuẩn theo đúng cấu hình hệ thống:
   - Camera Mũi Xe (FRONT_CAM): Mốc phía trước đầu xe (X > 4.0m, Y quanh trục giữa).
   - Camera Gương Phải (MIRROR_R): Vùng điểm mù hông phải (Y âm, X từ cabin lùi về rơ-moóc).
   - Mốc tương đối trước camera: Khung 2m x 4m.
4. Bấm [🚀 TÍNH MA TRẬN HOMOGRAPHY] để tính ra ma trận H (3x3) và lưu cấu hình vào homography_config.json.
5. KHÔNG hiển thị lưới phối cảnh 3D gây rối mắt.
6. Sau khi tính xong ma trận H: Click vào BẤT KỲ ĐIỂM NÀO trên ảnh, chương trình sẽ tự động nhân với ma trận H
   và xuất ra ngay tọa độ chuẩn VCS (X_vcs dọc, Y_vcs ngang) cùng khoảng cách D ngay lập tức!
"""

import os
import sys
import json
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk

# Thiết lập đường dẫn module
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from homography_calibrator import HomographyCalibrator

CONFIG_FILE = SCRIPT_DIR / "homography_config.json"

# Màu sắc các điểm mốc
POINT_COLORS_HEX = ["#3498db", "#f1c40f", "#2ecc71", "#e74c3c"]
POINT_COLORS_BGR = [(219, 152, 52), (15, 196, 241), (113, 204, 46), (60, 76, 231)]


class HomographyCalibratorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BlindGuard AI - Hiệu Chuẩn Homography 2D -> 3D Chuẩn Hệ Tọa Độ Xe (VCS)")
        self.geometry("1440x880")
        self.minsize(1100, 720)
        self.configure(bg="#1e1e24")

        # Căn giữa màn hình
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w, win_h = min(1440, screen_w - 60), min(880, screen_h - 60)
        x = (screen_w - win_w) // 2
        y = max(10, (screen_h - win_h - 40) // 2)
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")

        # Dữ liệu ảnh & calibrator
        self.calibrator = HomographyCalibrator()
        self.orig_cv_img = None
        self.orig_h = 0
        self.orig_w = 0
        self.image_path = None

        # Tỷ lệ hiển thị trên canvas
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.disp_w = 0
        self.disp_h = 0
        self.current_tk_img = None

        # Danh sách điểm test đo đạc khi click vào ảnh: [(u, v, x_vcs, y_vcs, dist_m)]
        self.measured_points = []

        # Tự động nạp cấu hình nếu đã tồn tại
        saved_config = None
        if CONFIG_FILE.is_file():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved_config = json.load(f)
            except Exception:
                saved_config = None

        self._build_ui(saved_config)

        if saved_config:
            try:
                self.calibrator.load_from_json(CONFIG_FILE)
                self._update_matrix_display()
            except Exception:
                pass

    def _build_ui(self, saved_config):
        self.main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg="#1e1e24", sashwidth=6)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # =========================================================================
        # 1. CỘT TRÁI: PANEL ĐIỀU KHIỂN & NHẬP LIỆU
        # =========================================================================
        left_container = tk.Frame(self.main_paned, bg="#2b2b36", width=480)
        left_container.pack_propagate(False)
        self.main_paned.add(left_container)

        canvas_left = tk.Canvas(left_container, bg="#2b2b36", highlightthickness=0)
        scrollbar_left = ttk.Scrollbar(left_container, orient="vertical", command=canvas_left.yview)
        self.scrollable_left = tk.Frame(canvas_left, bg="#2b2b36")

        self.scrollable_left.bind(
            "<Configure>",
            lambda e: canvas_left.configure(scrollregion=canvas_left.bbox("all"))
        )
        canvas_left.create_window((0, 0), window=self.scrollable_left, anchor="nw", width=460)
        canvas_left.configure(yscrollcommand=scrollbar_left.set)

        canvas_left.pack(side="left", fill="both", expand=True)
        scrollbar_left.pack(side="right", fill="y")

        # Tiêu đề
        lbl_title = tk.Label(
            self.scrollable_left,
            text="BLINDGUARD AI - CALIBRATOR",
            font=("Segoe UI", 13, "bold"),
            fg="#00e5ff",
            bg="#2b2b36"
        )
        lbl_title.pack(anchor="w", padx=14, pady=(12, 2))

        lbl_sub = tk.Label(
            self.scrollable_left,
            text="2D Pixel -> 3D Hệ Tọa Độ Xe (VCS: X-Dọc, Y-Ngang)",
            font=("Segoe UI", 9),
            fg="#b0bec5",
            bg="#2b2b36"
        )
        lbl_sub.pack(anchor="w", padx=14, pady=(0, 10))

        # -------------------------------------------------------------
        # PHẦN 1: CHỌN ẢNH & LOẠI CAMERA
        # -------------------------------------------------------------
        frame_img_sec = tk.LabelFrame(
            self.scrollable_left,
            text=" 1. Nạp Ảnh & Khai Báo Camera ",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg="#23232c",
            padx=10,
            pady=8
        )
        frame_img_sec.pack(fill="x", padx=12, pady=6)

        # Chọn loại Camera
        row_cam = tk.Frame(frame_img_sec, bg="#23232c")
        row_cam.pack(fill="x", pady=(0, 6))
        tk.Label(row_cam, text="Vị trí Camera:", font=("Segoe UI", 9, "bold"), fg="#eceff1", bg="#23232c").pack(side="left")

        self.cam_var = tk.StringVar(value="FRONT_CAM")
        cam_menu = ttk.Combobox(
            row_cam,
            textvariable=self.cam_var,
            values=["FRONT_CAM (Mũi xe)", "MIRROR_R (Gương phụ phải)", "MIRROR_L (Gương tài trái)"],
            state="readonly",
            width=26
        )
        cam_menu.pack(side="left", padx=8)
        cam_menu.bind("<<ComboboxSelected>>", self._on_camera_changed)

        btn_choose_img = tk.Button(
            frame_img_sec,
            text="📂 Chọn Ảnh Camera / Video",
            font=("Segoe UI", 10, "bold"),
            bg="#1976d2",
            fg="white",
            activebackground="#2196f3",
            activeforeground="white",
            relief="flat",
            padx=10,
            pady=6,
            command=self.choose_image_action
        )
        btn_choose_img.pack(fill="x", pady=2)

        self.lbl_img_info = tk.Label(
            frame_img_sec,
            text="Trạng thái: Chưa chọn ảnh",
            font=("Segoe UI", 9),
            fg="#ffb74d",
            bg="#23232c",
            wraplength=420,
            justify="left"
        )
        self.lbl_img_info.pack(anchor="w", pady=(4, 0))

        # -------------------------------------------------------------
        # PHẦN 2: BẢNG TỰ NHẬP 4 ĐIỂM MỐC (MÉT VCS & PIXEL)
        # -------------------------------------------------------------
        frame_pts_sec = tk.LabelFrame(
            self.scrollable_left,
            text=" 2. Bảng Tọa Độ 4 Điểm Mốc (VCS Mét & Pixel) ",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg="#23232c",
            padx=10,
            pady=8
        )
        frame_pts_sec.pack(fill="x", padx=12, pady=6)

        lbl_instruct = tk.Label(
            frame_pts_sec,
            text="Quy ước VCS: X=Dọc (Tiến > 0), Y=Ngang (Trái > 0, Phải < 0)\nNhập trực tiếp số hoặc click lên ảnh để tự điền Pixel:",
            font=("Segoe UI", 8, "italic"),
            fg="#cfd8dc",
            bg="#23232c",
            justify="left"
        )
        lbl_instruct.pack(anchor="w", pady=(0, 6))

        header_frame = tk.Frame(frame_pts_sec, bg="#23232c")
        header_frame.pack(fill="x", pady=2)
        tk.Label(header_frame, text="Mốc", width=4, font=("Segoe UI", 8, "bold"), fg="#90a4ae", bg="#23232c").pack(side="left")
        tk.Label(header_frame, text="X_vcs (Dọc m)", width=12, font=("Segoe UI", 8, "bold"), fg="#00e676", bg="#23232c").pack(side="left")
        tk.Label(header_frame, text="Y_vcs (Ngang m)", width=12, font=("Segoe UI", 8, "bold"), fg="#00e676", bg="#23232c").pack(side="left")
        tk.Label(header_frame, text="u, v (Pixel)", width=14, font=("Segoe UI", 8, "bold"), fg="#ffeb3b", bg="#23232c").pack(side="left")

        # Tọa độ mặc định theo chuẩn VCS (Mũi xe X=5m -> 9m, Y=-1m -> +1m)
        default_world = [
            (5.0,  1.0),   # Mốc 1: Trái gần (X=+5m, Y=+1m)
            (5.0, -1.0),   # Mốc 2: Phải gần (X=+5m, Y=-1m)
            (9.0, -1.0),   # Mốc 3: Phải xa  (X=+9m, Y=-1m)
            (9.0,  1.0)    # Mốc 4: Trái xa  (X=+9m, Y=+1m)
        ]
        if saved_config and "points_world_vcs_meter" in saved_config:
            default_world = saved_config["points_world_vcs_meter"]
        elif saved_config and "points_world_meter" in saved_config:
            default_world = saved_config["points_world_meter"]

        default_pixels = [("", ""), ("", ""), ("", ""), ("", "")]
        if saved_config and "points_image_pixel" in saved_config:
            default_pixels = saved_config["points_image_pixel"]

        self.entries_world = []
        self.entries_pixel = []
        point_names = ["#1", "#2", "#3", "#4"]

        for i in range(4):
            row = tk.Frame(frame_pts_sec, bg="#2b2b36", padx=4, pady=3, highlightbackground="#37474f", highlightthickness=1)
            row.pack(fill="x", pady=2)

            lbl_tag = tk.Label(
                row,
                text=f"{point_names[i]}",
                font=("Segoe UI", 9, "bold"),
                fg=POINT_COLORS_HEX[i],
                bg="#2b2b36",
                width=3
            )
            lbl_tag.pack(side="left")

            # Ô nhập X, Y (VCS mét)
            e_x = tk.Entry(row, width=6, font=("Segoe UI", 9), bg="#1e1e24", fg="#00e676", insertbackground="white", justify="center")
            e_x.insert(0, f"{float(default_world[i][0]):.2f}")
            e_x.pack(side="left", padx=2)

            e_y = tk.Entry(row, width=6, font=("Segoe UI", 9), bg="#1e1e24", fg="#00e676", insertbackground="white", justify="center")
            e_y.insert(0, f"{float(default_world[i][1]):.2f}")
            e_y.pack(side="left", padx=2)

            # Ô nhập u, v (pixel)
            e_u = tk.Entry(row, width=6, font=("Segoe UI", 9), bg="#1e1e24", fg="#ffeb3b", insertbackground="white", justify="center")
            if default_pixels[i][0] != "":
                e_u.insert(0, f"{float(default_pixels[i][0]):.0f}")
            e_u.pack(side="left", padx=2)

            e_v = tk.Entry(row, width=6, font=("Segoe UI", 9), bg="#1e1e24", fg="#ffeb3b", insertbackground="white", justify="center")
            if default_pixels[i][1] != "":
                e_v.insert(0, f"{float(default_pixels[i][1]):.0f}")
            e_v.pack(side="left", padx=2)

            btn_pick_this = tk.Button(
                row,
                text="Chấm",
                font=("Segoe UI", 7),
                bg="#455a64",
                fg="white",
                relief="flat",
                command=lambda idx=i: self._set_active_pick_point(idx)
            )
            btn_pick_this.pack(side="right", padx=2)

            self.entries_world.append((e_x, e_y))
            self.entries_pixel.append((e_u, e_v))

        # Hàng nút Preset theo cấu hình xe BlindGuard AI
        row_presets = tk.Frame(frame_pts_sec, bg="#23232c")
        row_presets.pack(fill="x", pady=(6, 2))

        btn_pre_front = tk.Button(
            row_presets,
            text="⚡ Mũi Xe (+5->9m)",
            font=("Segoe UI", 8),
            bg="#37474f",
            fg="#eceff1",
            relief="flat",
            command=self._apply_preset_front
        )
        btn_pre_front.pack(side="left", padx=2)

        btn_pre_right = tk.Button(
            row_presets,
            text="⚡ Hông Phải (Y âm)",
            font=("Segoe UI", 8),
            bg="#37474f",
            fg="#eceff1",
            relief="flat",
            command=self._apply_preset_right_mirror
        )
        btn_pre_right.pack(side="left", padx=2)

        btn_clear_px = tk.Button(
            row_presets,
            text="🧹 Xóa Pixel",
            font=("Segoe UI", 8),
            bg="#4e342e",
            fg="#ffccbc",
            relief="flat",
            command=self._clear_pixel_entries
        )
        btn_clear_px.pack(side="right", padx=2)

        # -------------------------------------------------------------
        # PHẦN 3: TÍNH TOÁN & LƯU MA TRẬN
        # -------------------------------------------------------------
        frame_calc_sec = tk.LabelFrame(
            self.scrollable_left,
            text=" 3. Tính Toán & Lưu Ma Trận ",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg="#23232c",
            padx=10,
            pady=8
        )
        frame_calc_sec.pack(fill="x", padx=12, pady=6)

        btn_compute = tk.Button(
            frame_calc_sec,
            text="🚀 TÍNH MA TRẬN HOMOGRAPHY (VCS)",
            font=("Segoe UI", 10, "bold"),
            bg="#2e7d32",
            fg="white",
            activebackground="#388e3c",
            activeforeground="white",
            relief="flat",
            pady=6,
            command=self.compute_homography_action
        )
        btn_compute.pack(fill="x", pady=2)

        btn_save = tk.Button(
            frame_calc_sec,
            text="💾 Lưu Ma Trận vào config.json",
            font=("Segoe UI", 9),
            bg="#00695c",
            fg="white",
            activebackground="#00897b",
            activeforeground="white",
            relief="flat",
            pady=4,
            command=self.save_homography_action
        )
        btn_save.pack(fill="x", pady=3)

        self.txt_matrix_info = tk.Text(
            frame_calc_sec,
            height=5,
            font=("Consolas", 8),
            bg="#18181f",
            fg="#80cbc4",
            relief="flat",
            wrap="none"
        )
        self.txt_matrix_info.pack(fill="x", pady=3)
        self.txt_matrix_info.insert(tk.END, "Chưa tính toán ma trận H.")
        self.txt_matrix_info.config(state="disabled")

        # -------------------------------------------------------------
        # PHẦN 4: KẾT QUẢ ĐO ĐẠC TỨC THÌ (INSPECTION RESULT)
        # -------------------------------------------------------------
        frame_res_sec = tk.LabelFrame(
            self.scrollable_left,
            text=" 4. Kết Quả Đo Đạc Điểm Bất Kỳ (VCS Mét) ",
            font=("Segoe UI", 10, "bold"),
            fg="#00e5ff",
            bg="#23232c",
            padx=10,
            pady=8
        )
        frame_res_sec.pack(fill="x", padx=12, pady=6)

        self.lbl_click_pixel = tk.Label(
            frame_res_sec,
            text="Tọa độ Pixel vừa click: Chưa click",
            font=("Segoe UI", 9),
            fg="#cfd8dc",
            bg="#23232c",
            anchor="w"
        )
        self.lbl_click_pixel.pack(fill="x", pady=1)

        self.lbl_res_meters = tk.Label(
            frame_res_sec,
            text="👉 TỌA ĐỘ VCS:  X = --- m  |  Y = --- m",
            font=("Segoe UI", 10, "bold"),
            fg="#00e676",
            bg="#1b2e23",
            padx=6,
            pady=5,
            anchor="w"
        )
        self.lbl_res_meters.pack(fill="x", pady=3)

        self.lbl_res_dist = tk.Label(
            frame_res_sec,
            text="👉 KHOẢNG CÁCH EUCLID:  D = --- m",
            font=("Segoe UI", 9, "bold"),
            fg="#ffeb3b",
            bg="#2e2e1b",
            padx=6,
            pady=4,
            anchor="w"
        )
        self.lbl_res_dist.pack(fill="x", pady=2)

        self.lbl_delta_dist = tk.Label(
            frame_res_sec,
            text="Khoảng cách giữa 2 điểm click gần nhất: --- m",
            font=("Segoe UI", 8),
            fg="#b0bec5",
            bg="#23232c",
            anchor="w"
        )
        self.lbl_delta_dist.pack(fill="x", pady=2)

        btn_clear_meas = tk.Button(
            frame_res_sec,
            text="🧹 Xóa Các Điểm Đo Trên Ảnh",
            font=("Segoe UI", 8),
            bg="#37474f",
            fg="#eceff1",
            relief="flat",
            command=self.clear_measurements_action
        )
        btn_clear_meas.pack(anchor="e", pady=(4, 0))

        # =========================================================================
        # 2. CỘT PHẢI: VÙNG CANVAS HIỂN THỊ ẢNH TƯƠNG TÁC
        # =========================================================================
        right_container = tk.Frame(self.main_paned, bg="#121216")
        self.main_paned.add(right_container)

        top_status_frame = tk.Frame(right_container, bg="#1a1a22", height=32)
        top_status_frame.pack(fill="x", side="top")

        self.lbl_top_status = tk.Label(
            top_status_frame,
            text="Vui lòng bấm [📂 Chọn Ảnh Camera / Video] bên trái để tải ảnh lên!",
            font=("Segoe UI", 9, "bold"),
            fg="#00e5ff",
            bg="#1a1a22",
            padx=10
        )
        self.lbl_top_status.pack(side="left", fill="y")

        self.lbl_mouse_coord = tk.Label(
            top_status_frame,
            text="Pixel: (---, ---)",
            font=("Consolas", 9),
            fg="#90a4ae",
            bg="#1a1a22",
            padx=10
        )
        self.lbl_mouse_coord.pack(side="right", fill="y")

        self.canvas = tk.Canvas(right_container, bg="#121216", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Motion>", self._on_canvas_motion)

        self.after(100, self._draw_placeholder)

    def _draw_placeholder(self):
        """Vẽ màn hình chờ sạch sẽ khi chưa chọn ảnh"""
        self.canvas.delete("all")
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 50 or ch < 50:
            return

        self.canvas.create_text(
            cw // 2, ch // 2 - 30,
            text="📷 CHƯA CHỌN ẢNH CAMERA",
            font=("Segoe UI", 16, "bold"),
            fill="#546e7a"
        )
        self.canvas.create_text(
            cw // 2, ch // 2 + 15,
            text="Nhấn nút [📂 Chọn Ảnh Camera / Video] ở cột bên trái để nạp ảnh.",
            font=("Segoe UI", 11),
            fill="#78909c"
        )
        self.canvas.create_text(
            cw // 2, ch // 2 + 45,
            text="Hệ tọa độ xe (VCS): X là trục dọc (Tiến/Lùi), Y là trục ngang (Trái/Phải).",
            font=("Segoe UI", 9, "italic"),
            fill="#455a64"
        )

    def _on_camera_changed(self, event=None):
        raw_val = self.cam_var.get()
        if "FRONT_CAM" in raw_val:
            self._apply_preset_front()
        elif "MIRROR_R" in raw_val:
            self._apply_preset_right_mirror()

    def _apply_preset_front(self):
        """Preset Camera Mũi Xe (Mốc cách đầu xe X = 5m -> 9m, Y = ±1m)"""
        vals = [(5.0, 1.0), (5.0, -1.0), (9.0, -1.0), (9.0, 1.0)]
        for i, (x, y) in enumerate(vals):
            self.entries_world[i][0].delete(0, tk.END)
            self.entries_world[i][0].insert(0, f"{x:.2f}")
            self.entries_world[i][1].delete(0, tk.END)
            self.entries_world[i][1].insert(0, f"{y:.2f}")
        self.lbl_top_status.config(text="Đã nạp Preset Mũi Xe FRONT_CAM (X: +5m->+9m, Y: ±1m)", fg="#00e5ff")

    def _apply_preset_right_mirror(self):
        """Preset Camera Gương Phụ Phải MIRROR_R (Y âm: bên phải xe)"""
        vals = [(2.0, -2.0), (2.0, -4.0), (-6.0, -4.0), (-6.0, -2.0)]
        for i, (x, y) in enumerate(vals):
            self.entries_world[i][0].delete(0, tk.END)
            self.entries_world[i][0].insert(0, f"{x:.2f}")
            self.entries_world[i][1].delete(0, tk.END)
            self.entries_world[i][1].insert(0, f"{y:.2f}")
        self.lbl_top_status.config(text="Đã nạp Preset Gương Phải MIRROR_R (Hông phải: Y âm, X lùi về rơ-moóc)", fg="#00e5ff")

    def _clear_pixel_entries(self):
        for eu, ev in self.entries_pixel:
            eu.delete(0, tk.END)
            ev.delete(0, tk.END)
        self._redraw_image()

    def _set_active_pick_point(self, idx):
        self.lbl_top_status.config(
            text=f"Hãy click lên ảnh để điền tọa độ Pixel cho Mốc #{idx+1}!",
            fg=POINT_COLORS_HEX[idx]
        )
        self.active_manual_pick_idx = idx

    def choose_image_action(self):
        filetypes = [
            ("Ảnh hoặc Video", "*.jpg *.jpeg *.png *.bmp *.webp *.mp4 *.avi *.mkv *.mov"),
            ("Tập tin Hình ảnh", "*.jpg *.jpeg *.png *.bmp *.webp"),
            ("Tập tin Video", "*.mp4 *.avi *.mkv *.mov"),
            ("Tất cả tập tin", "*.*")
        ]
        chosen = filedialog.askopenfilename(
            title="Chọn ảnh hoặc video camera để hiệu chuẩn Homography VCS",
            filetypes=filetypes
        )
        if not chosen:
            return

        ext = Path(chosen).suffix.lower()
        img = None
        if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.webp']:
            img = cv2.imread(chosen)
        elif ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv']:
            cap = cv2.VideoCapture(chosen)
            if cap.isOpened():
                for _ in range(5):
                    cap.read()
                ret, frame = cap.read()
                cap.release()
                if ret:
                    img = frame

        if img is None:
            messagebox.showerror("Lỗi", f"Không thể đọc ảnh từ: {chosen}")
            return

        self.orig_cv_img = img
        self.orig_h, self.orig_w = img.shape[:2]
        self.image_path = chosen

        self.lbl_img_info.config(
            text=f"Ảnh: {Path(chosen).name} ({self.orig_w} x {self.orig_h} px)",
            fg="#00e676"
        )
        self.lbl_top_status.config(
            text="Đã nạp ảnh thành công! Bạn có thể tự gõ số hoặc click chấm 4 mốc.",
            fg="#00e5ff"
        )

        self.measured_points.clear()
        self._redraw_image()

    def _get_pixel_points_from_entries(self):
        pts = []
        for i, (eu, ev) in enumerate(self.entries_pixel):
            u_str = eu.get().strip()
            v_str = ev.get().strip()
            if u_str != "" and v_str != "":
                try:
                    pts.append((float(u_str), float(v_str)))
                except ValueError:
                    return None, f"Tọa độ Pixel mốc #{i+1} không phải là số hợp lệ!"
            else:
                pts.append(None)
        return pts, None

    def _get_world_points_from_entries(self):
        pts = []
        for i, (ex, ey) in enumerate(self.entries_world):
            x_str = ex.get().strip()
            y_str = ey.get().strip()
            try:
                pts.append((float(x_str), float(y_str)))
            except ValueError:
                return None, f"Tọa độ Mét VCS mốc #{i+1} không phải là số hợp lệ!"
        return pts, None

    def compute_homography_action(self):
        w_pts, w_err = self._get_world_points_from_entries()
        if w_err:
            messagebox.showerror("Lỗi Nhập Liệu", w_err)
            return

        px_pts, px_err = self._get_pixel_points_from_entries()
        if px_err:
            messagebox.showerror("Lỗi Nhập Liệu", px_err)
            return

        missing = [i + 1 for i, p in enumerate(px_pts) if p is None]
        if missing:
            messagebox.showwarning(
                "Thiếu Tọa Độ Pixel",
                f"Vui lòng nhập hoặc click chấm tọa độ Pixel cho mốc: {missing}!"
            )
            return

        try:
            cam_name = self.cam_var.get().split()[0]
            shape = (self.orig_h, self.orig_w) if self.orig_h > 0 else (1080, 1920)
            H, rep_err = self.calibrator.compute_homography(px_pts, w_pts, shape, camera_name=cam_name)
            self._update_matrix_display()

            self.lbl_top_status.config(
                text=f"✅ ĐÃ TÍNH XONG MA TRẬN H VCS (Sai số: {rep_err:.3f}m) - CLICK VÀO ẢNH ĐỂ ĐO MÉT!",
                fg="#00e676"
            )

            self.calibrator.save_to_json(CONFIG_FILE, metadata={"image_path": self.image_path})

            messagebox.showinfo(
                "Thành Công",
                f"Đã tính toán thành công ma trận Homography theo chuẩn VCS!\n"
                f"Sai số tái chiếu: {rep_err:.4f} mét.\n\n"
                f"Bây giờ bạn có thể click vào bất kỳ điểm nào trên ảnh để đo tọa độ mét thực tế!"
            )
            self._redraw_image()

        except Exception as e:
            messagebox.showerror("Lỗi Tính Toán", f"Không thể tính ma trận Homography:\n{e}")

    def save_homography_action(self):
        if not self.calibrator.is_calibrated:
            messagebox.showwarning("Cảnh Báo", "Chưa có ma trận Homography để lưu. Vui lòng bấm [TÍNH MA TRẬN] trước!")
            return
        try:
            saved_path = self.calibrator.save_to_json(CONFIG_FILE, metadata={"image_path": self.image_path})
            messagebox.showinfo("Đã Lưu", f"Đã lưu ma trận thành công tại:\n{saved_path}")
        except Exception as e:
            messagebox.showerror("Lỗi Lưu File", f"Không thể lưu file cấu hình: {e}")

    def _update_matrix_display(self):
        if self.calibrator.is_calibrated:
            self.txt_matrix_info.config(state="normal")
            self.txt_matrix_info.delete("1.0", tk.END)
            h = self.calibrator.H
            txt = f"Ma trận H (Pixel -> VCS Mét):\n"
            for row in h:
                txt += "  [" + "  ".join([f"{val:11.4e}" for val in row]) + "]\n"
            txt += f"Sai số trung bình: {self.calibrator.reprojection_error:.4f} m"
            self.txt_matrix_info.insert(tk.END, txt)
            self.txt_matrix_info.config(state="disabled")

    def clear_measurements_action(self):
        self.measured_points.clear()
        self.lbl_click_pixel.config(text="Tọa độ Pixel vừa click: Đã xóa")
        self.lbl_res_meters.config(text="👉 TỌA ĐỘ VCS:  X = --- m  |  Y = --- m")
        self.lbl_res_dist.config(text="👉 KHOẢNG CÁCH EUCLID:  D = --- m")
        self.lbl_delta_dist.config(text="Khoảng cách giữa 2 điểm click gần nhất: --- m")
        self._redraw_image()

    def _on_canvas_resize(self, event):
        if self.orig_cv_img is not None:
            self._redraw_image()
        else:
            self._draw_placeholder()

    def _on_canvas_motion(self, event):
        if self.orig_cv_img is None or self.scale <= 0:
            return

        cx, cy = event.x, event.y
        if (self.offset_x <= cx <= self.offset_x + self.disp_w and
            self.offset_y <= cy <= self.offset_y + self.disp_h):
            orig_u = (cx - self.offset_x) / self.scale
            orig_v = (cy - self.offset_y) / self.scale
            self.lbl_mouse_coord.config(text=f"Pixel: (u={orig_u:.0f}, v={orig_v:.0f})")
        else:
            self.lbl_mouse_coord.config(text="Pixel: (---, ---)")

    def _on_canvas_click(self, event):
        if self.orig_cv_img is None or self.scale <= 0:
            return

        cx, cy = event.x, event.y
        if not (self.offset_x <= cx <= self.offset_x + self.disp_w and
                self.offset_y <= cy <= self.offset_y + self.disp_h):
            return

        orig_u = (cx - self.offset_x) / self.scale
        orig_v = (cy - self.offset_y) / self.scale

        # Điền vào ô pixel còn trống nếu đang ở giai đoạn chấm mốc
        empty_idx = None
        if hasattr(self, 'active_manual_pick_idx') and self.active_manual_pick_idx is not None:
            empty_idx = self.active_manual_pick_idx
            self.active_manual_pick_idx = None
        else:
            for i, (eu, ev) in enumerate(self.entries_pixel):
                if eu.get().strip() == "" or ev.get().strip() == "":
                    empty_idx = i
                    break

        if empty_idx is not None:
            self.entries_pixel[empty_idx][0].delete(0, tk.END)
            self.entries_pixel[empty_idx][0].insert(0, f"{orig_u:.0f}")
            self.entries_pixel[empty_idx][1].delete(0, tk.END)
            self.entries_pixel[empty_idx][1].insert(0, f"{orig_v:.0f}")

            self.lbl_top_status.config(
                text=f"Đã điền Mốc #{empty_idx+1}: Pixel (u={orig_u:.0f}, v={orig_v:.0f})",
                fg=POINT_COLORS_HEX[empty_idx]
            )
            self._redraw_image()

            all_filled = all(eu.get().strip() != "" and ev.get().strip() != "" for eu, ev in self.entries_pixel)
            if all_filled and not self.calibrator.is_calibrated:
                self.compute_homography_action()
            return

        # Đo đạc tức thì khi click vào ảnh
        if self.calibrator.is_calibrated:
            try:
                x_vcs, y_vcs, dist_m = self.calibrator.pixel_to_world(orig_u, orig_v)
                point_char = chr(65 + len(self.measured_points) % 26)
                self.measured_points.append((orig_u, orig_v, x_vcs, y_vcs, dist_m))

                # Ghi chú hướng vị trí theo chuẩn VCS
                fwd_note = f"Phía trước {x_vcs:.2f}m" if x_vcs >= 0 else f"Phía sau {abs(x_vcs):.2f}m"
                lat_note = f"Bên Trái {y_vcs:.2f}m" if y_vcs >= 0 else f"Bên Phải {abs(y_vcs):.2f}m"

                self.lbl_click_pixel.config(
                    text=f"Tọa độ Pixel [{point_char}]: u = {orig_u:.1f} px , v = {orig_v:.1f} px"
                )
                self.lbl_res_meters.config(
                    text=f"👉 VCS: X_dọc = {x_vcs:+.2f}m ({fwd_note}) | Y_ngang = {y_vcs:+.2f}m ({lat_note})"
                )
                self.lbl_res_dist.config(
                    text=f"👉 KHOẢNG CÁCH EUCLID: D = {dist_m:.2f} m"
                )

                if len(self.measured_points) >= 2:
                    p1 = self.measured_points[-2]
                    p2 = self.measured_points[-1]
                    delta_d = np.sqrt((p1[2] - p2[2])**2 + (p1[3] - p2[3])**2)
                    self.lbl_delta_dist.config(
                        text=f"Khoảng cách 2 điểm click gần nhất: Δd = {delta_d:.2f} m"
                    )

                self.lbl_top_status.config(
                    text=f"[{point_char}] Pixel({orig_u:.0f}, {orig_v:.0f}) -> VCS(X={x_vcs:+.2f}m, Y={y_vcs:+.2f}m) | D={dist_m:.2f}m",
                    fg="#00e676"
                )

                print(f"[+] CLICK ĐO ĐẠC [{point_char}]: Pixel({orig_u:.1f}, {orig_v:.1f}) -> X_vcs = {x_vcs:+.2f} m, Y_vcs = {y_vcs:+.2f} m | D = {dist_m:.2f} m")

                self._redraw_image()

            except Exception as e:
                messagebox.showerror("Lỗi Đo Đạc", f"Lỗi tính toán tọa độ:\n{e}")
        else:
            self.lbl_top_status.config(
                text="Chưa tính ma trận Homography! Vui lòng bấm [🚀 TÍNH MA TRẬN HOMOGRAPHY] bên trái.",
                fg="#ff9800"
            )

    def _redraw_image(self):
        """Vẽ lại ảnh kèm các điểm mốc và các điểm đo đạc (KHÔNG VẼ LƯỚI)"""
        if self.orig_cv_img is None:
            self._draw_placeholder()
            return

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 50 or ch < 50:
            return

        scale_w = cw / float(self.orig_w)
        scale_h = ch / float(self.orig_h)
        self.scale = min(scale_w, scale_h)

        self.disp_w = max(1, int(self.orig_w * self.scale))
        self.disp_h = max(1, int(self.orig_h * self.scale))
        self.offset_x = (cw - self.disp_w) // 2
        self.offset_y = (ch - self.disp_h) // 2

        display_img = self.orig_cv_img.copy()

        # -------------------------------------------------------------
        # 1. VẼ 4 ĐIỂM MỐC
        # -------------------------------------------------------------
        valid_pixel_pts = []
        for i, (eu, ev) in enumerate(self.entries_pixel):
            u_str = eu.get().strip()
            v_str = ev.get().strip()
            if u_str != "" and v_str != "":
                try:
                    u_val = float(u_str)
                    v_val = float(v_str)
                    valid_pixel_pts.append((i, int(u_val), int(v_val)))
                except ValueError:
                    pass

        if len(valid_pixel_pts) >= 2:
            poly_pts = np.array([[pt[1], pt[2]] for pt in valid_pixel_pts], dtype=np.int32).reshape((-1, 1, 2))
            is_closed = (len(valid_pixel_pts) == 4)
            cv2.polylines(display_img, [poly_pts], is_closed, (0, 255, 255), 2, cv2.LINE_AA)
            if is_closed:
                overlay = display_img.copy()
                cv2.fillPoly(overlay, [poly_pts], (0, 100, 140))
                cv2.addWeighted(overlay, 0.25, display_img, 0.75, 0, display_img)

        for idx, u_pt, v_pt in valid_pixel_pts:
            col = POINT_COLORS_BGR[idx % len(POINT_COLORS_BGR)]
            cv2.circle(display_img, (u_pt, v_pt), 8, col, -1)
            cv2.circle(display_img, (u_pt, v_pt), 10, (255, 255, 255), 2)

            try:
                wx = float(self.entries_world[idx][0].get().strip())
                wy = float(self.entries_world[idx][1].get().strip())
                lbl_m = f"#{idx+1}: ({wx:+.1f}m, {wy:+.1f}m)"
            except Exception:
                lbl_m = f"#{idx+1}"

            (tw, th), _ = cv2.getTextSize(lbl_m, cv2.FONT_HERSHEY_DUPLEX, 0.55, 1)
            cv2.rectangle(display_img, (u_pt + 12, v_pt - th - 6), (u_pt + 16 + tw, v_pt + 4), (20, 20, 20), -1)
            cv2.putText(display_img, lbl_m, (u_pt + 14, v_pt - 2), cv2.FONT_HERSHEY_DUPLEX, 0.55, col, 1, cv2.LINE_AA)

        # -------------------------------------------------------------
        # 2. VẼ CÁC ĐIỂM ĐO ĐẠC KIỂM THỬ (CLICK ĐO MÉT)
        # -------------------------------------------------------------
        for idx, (pu, pv, xm, ym, dm) in enumerate(self.measured_points):
            iu, iv = int(pu), int(pv)
            point_char = chr(65 + idx % 26)

            cv2.drawMarker(display_img, (iu, iv), (0, 255, 0), cv2.MARKER_CROSS, 20, 2)
            cv2.circle(display_img, (iu, iv), 6, (0, 255, 255), -1)

            meas_tag = f"[{point_char}] X:{xm:+.2f}m | Y:{ym:+.2f}m | D:{dm:.2f}m"
            (tw, th), _ = cv2.getTextSize(meas_tag, cv2.FONT_HERSHEY_DUPLEX, 0.52, 1)
            tx = min(self.orig_w - tw - 15, max(10, iu + 14))
            ty = max(30, iv - 10)
            cv2.rectangle(display_img, (tx - 4, ty - th - 4), (tx + tw + 4, ty + 4), (15, 35, 15), -1)
            cv2.rectangle(display_img, (tx - 4, ty - th - 4), (tx + tw + 4, ty + 4), (0, 255, 0), 1)
            cv2.putText(display_img, meas_tag, (tx, ty), cv2.FONT_HERSHEY_DUPLEX, 0.52, (0, 255, 200), 1, cv2.LINE_AA)

        if len(self.measured_points) >= 2:
            p1 = self.measured_points[-2]
            p2 = self.measured_points[-1]
            u1, v1 = int(p1[0]), int(p1[1])
            u2, v2 = int(p2[0]), int(p2[1])
            cv2.line(display_img, (u1, v1), (u2, v2), (0, 255, 255), 2, cv2.LINE_AA)
            delta_d = np.sqrt((p1[2] - p2[2])**2 + (p1[3] - p2[3])**2)
            mid_u = (u1 + u2) // 2
            mid_v = (v1 + v2) // 2
            d_tag = f"d = {delta_d:.2f}m"
            (mw, mh), _ = cv2.getTextSize(d_tag, cv2.FONT_HERSHEY_DUPLEX, 0.55, 1)
            cv2.rectangle(display_img, (mid_u - mw//2 - 4, mid_v - mh - 4), (mid_u + mw//2 + 4, mid_v + 4), (20, 20, 20), -1)
            cv2.putText(display_img, d_tag, (mid_u - mw//2, mid_v), cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 255, 255), 1, cv2.LINE_AA)

        # Chuyển đổi sang PhotoImage cho Tkinter
        resized_bgr = cv2.resize(display_img, (self.disp_w, self.disp_h), interpolation=cv2.INTER_LINEAR)
        resized_rgb = cv2.cvtColor(resized_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(resized_rgb)
        self.current_tk_img = ImageTk.PhotoImage(pil_img)

        self.canvas.delete("all")
        self.canvas.create_image(self.offset_x, self.offset_y, anchor="nw", image=self.current_tk_img)


if __name__ == "__main__":
    app = HomographyCalibratorApp()
    app.mainloop()
