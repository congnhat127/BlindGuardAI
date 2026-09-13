"""
Script: calibrate_homography_gui.py
Mô tả: Công cụ giao diện đồ họa trực quan (GUI) hiệu chuẩn ma trận Homography chuyển đổi 2D (Pixel) sang 3D (Mét).

Tính năng:
1. Ban đầu KHÔNG tự động hiện bất kỳ ảnh nào. Bắt đầu bằng việc bấm [📂 Chọn Ảnh Camera / Video].
2. Cho phép TỰ NHẬP cả tọa độ mét (X, Y) lẫn tọa độ pixel (u, v) của 4 điểm mốc vào các ô nhập liệu:
   - Có thể gõ số trực tiếp bằng bàn phím.
   - Hoặc click chuột lên ảnh để tự động điền tọa độ pixel (u, v).
3. Bấm [🚀 TÍNH MA TRẬN HOMOGRAPHY] để tính ra ma trận H (3x3) và lưu cấu hình vào homography_config.json.
4. KHÔNG hiển thị lưới phối cảnh 3D gây rối mắt.
5. Sau khi tính xong ma trận H: Click vào BẤT KỲ ĐIỂM NÀO trên ảnh, chương trình sẽ tự động nhân với ma trận H
   và xuất ra ngay tọa độ thực tế (X, Y) tính bằng mét cùng khoảng cách D tính từ camera!
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

# Màu sắc điểm mốc
POINT_COLORS_HEX = ["#3498db", "#f1c40f", "#2ecc71", "#e74c3c"]
POINT_COLORS_BGR = [(219, 152, 52), (15, 196, 241), (113, 204, 46), (60, 76, 231)]


class HomographyCalibratorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BlindGuard AI - Công Cụ Hiệu Chuẩn Homography 2D -> 3D (Mét)")
        self.geometry("1420x860")
        self.minsize(1100, 700)
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

        # Danh sách điểm test đo đạc khi click vào ảnh: [(u, v, x_m, y_m, dist_m)]
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

        # Nếu có cấu hình cũ, nạp vào calibrator
        if saved_config:
            try:
                self.calibrator.load_from_json(CONFIG_FILE)
                self._update_matrix_display()
            except Exception:
                pass

    def _build_ui(self, saved_config):
        # Khung chính chia làm 2 cột: Trái (Bảng điều khiển & Nhập liệu), Phải (Vùng hiển thị ảnh)
        self.main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg="#1e1e24", sashwidth=6)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # =========================================================================
        # 1. CỘT TRÁI: PANEL ĐIỀU KHIỂN & NHẬP LIỆU
        # =========================================================================
        left_container = tk.Frame(self.main_paned, bg="#2b2b36", width=460)
        left_container.pack_propagate(False)
        self.main_paned.add(left_container)

        # Cuộn thanh trượt cho cột trái nếu màn hình nhỏ
        canvas_left = tk.Canvas(left_container, bg="#2b2b36", highlightthickness=0)
        scrollbar_left = ttk.Scrollbar(left_container, orient="vertical", command=canvas_left.yview)
        self.scrollable_left = tk.Frame(canvas_left, bg="#2b2b36")

        self.scrollable_left.bind(
            "<Configure>",
            lambda e: canvas_left.configure(scrollregion=canvas_left.bbox("all"))
        )
        canvas_left.create_window((0, 0), window=self.scrollable_left, anchor="nw", width=440)
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
            text="Chuyển đổi 2D (Pixel) sang 3D Mặt đất (Mét)",
            font=("Segoe UI", 9),
            fg="#b0bec5",
            bg="#2b2b36"
        )
        lbl_sub.pack(anchor="w", padx=14, pady=(0, 10))

        # -------------------------------------------------------------
        # PHẦN 1: CHỌN ẢNH
        # -------------------------------------------------------------
        frame_img_sec = tk.LabelFrame(
            self.scrollable_left,
            text=" 1. Nạp Ảnh Camera ",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg="#23232c",
            padx=10,
            pady=8
        )
        frame_img_sec.pack(fill="x", padx=12, pady=6)

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
            wraplength=400,
            justify="left"
        )
        self.lbl_img_info.pack(anchor="w", pady=(4, 0))

        # -------------------------------------------------------------
        # PHẦN 2: BẢNG TỰ NHẬP 4 ĐIỂM MỐC (TỌA ĐỘ MÉT & TỌA ĐỘ PIXEL)
        # -------------------------------------------------------------
        frame_pts_sec = tk.LabelFrame(
            self.scrollable_left,
            text=" 2. Bảng Tọa Độ 4 Điểm Mốc (Mét & Pixel) ",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg="#23232c",
            padx=10,
            pady=8
        )
        frame_pts_sec.pack(fill="x", padx=12, pady=6)

        lbl_instruct = tk.Label(
            frame_pts_sec,
            text="Nhập trực tiếp số vào ô hoặc Click lên ảnh để tự điền Pixel:",
            font=("Segoe UI", 8, "italic"),
            fg="#cfd8dc",
            bg="#23232c",
            justify="left"
        )
        lbl_instruct.pack(anchor="w", pady=(0, 6))

        # Tiêu đề cột
        header_frame = tk.Frame(frame_pts_sec, bg="#23232c")
        header_frame.pack(fill="x", pady=2)
        tk.Label(header_frame, text="Mốc", width=5, font=("Segoe UI", 8, "bold"), fg="#90a4ae", bg="#23232c").pack(side="left")
        tk.Label(header_frame, text="Tọa độ Mét (m)", width=17, font=("Segoe UI", 8, "bold"), fg="#00e676", bg="#23232c").pack(side="left", padx=4)
        tk.Label(header_frame, text="Tọa độ Pixel (px)", width=17, font=("Segoe UI", 8, "bold"), fg="#ffeb3b", bg="#23232c").pack(side="left", padx=4)

        # Mặc định tọa độ mét (thảm chữ nhật 2m x 4m)
        default_world = [
            (-1.0, 2.0),
            ( 1.0, 2.0),
            ( 1.0, 6.0),
            (-1.0, 6.0)
        ]
        if saved_config and "points_world_meter" in saved_config:
            default_world = saved_config["points_world_meter"]

        default_pixels = [("", ""), ("", ""), ("", ""), ("", "")]
        if saved_config and "points_image_pixel" in saved_config:
            default_pixels = saved_config["points_image_pixel"]

        self.entries_world = []   # [(entry_x, entry_y)]
        self.entries_pixel = []   # [(entry_u, entry_v)]

        point_names = ["#1", "#2", "#3", "#4"]
        point_descs = ["Trái Gần", "Phải Gần", "Phải Xa", "Trái Xa"]

        for i in range(4):
            row = tk.Frame(frame_pts_sec, bg="#2b2b36", padx=4, pady=3, highlightbackground="#37474f", highlightthickness=1)
            row.pack(fill="x", pady=2)

            # Nhãn mốc
            lbl_tag = tk.Label(
                row,
                text=f"{point_names[i]}",
                font=("Segoe UI", 9, "bold"),
                fg=POINT_COLORS_HEX[i],
                bg="#2b2b36",
                width=3
            )
            lbl_tag.pack(side="left")

            # Ô nhập X, Y (mét)
            tk.Label(row, text="X:", font=("Segoe UI", 8), fg="#b0bec5", bg="#2b2b36").pack(side="left")
            e_x = tk.Entry(row, width=5, font=("Segoe UI", 9), bg="#1e1e24", fg="#00e676", insertbackground="white", justify="center")
            e_x.insert(0, str(default_world[i][0]))
            e_x.pack(side="left", padx=1)

            tk.Label(row, text="Y:", font=("Segoe UI", 8), fg="#b0bec5", bg="#2b2b36").pack(side="left")
            e_y = tk.Entry(row, width=5, font=("Segoe UI", 9), bg="#1e1e24", fg="#00e676", insertbackground="white", justify="center")
            e_y.insert(0, str(default_world[i][1]))
            e_y.pack(side="left", padx=1)

            # Ô nhập u, v (pixel)
            tk.Label(row, text=" | u:", font=("Segoe UI", 8), fg="#b0bec5", bg="#2b2b36").pack(side="left")
            e_u = tk.Entry(row, width=5, font=("Segoe UI", 9), bg="#1e1e24", fg="#ffeb3b", insertbackground="white", justify="center")
            if default_pixels[i][0] != "":
                e_u.insert(0, f"{float(default_pixels[i][0]):.0f}")
            e_u.pack(side="left", padx=1)

            tk.Label(row, text="v:", font=("Segoe UI", 8), fg="#b0bec5", bg="#2b2b36").pack(side="left")
            e_v = tk.Entry(row, width=5, font=("Segoe UI", 9), bg="#1e1e24", fg="#ffeb3b", insertbackground="white", justify="center")
            if default_pixels[i][1] != "":
                e_v.insert(0, f"{float(default_pixels[i][1]):.0f}")
            e_v.pack(side="left", padx=1)

            # Nút điền điểm này
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

        # Hàng nút thao tác nhanh cho bảng điểm
        row_actions = tk.Frame(frame_pts_sec, bg="#23232c")
        row_actions.pack(fill="x", pady=(6, 2))

        btn_preset = tk.Button(
            row_actions,
            text="⚡ Mẫu 2mx4m",
            font=("Segoe UI", 8),
            bg="#37474f",
            fg="#eceff1",
            relief="flat",
            command=self._apply_preset_2x4
        )
        btn_preset.pack(side="left", padx=2)

        btn_preset_lane = tk.Button(
            row_actions,
            text="⚡ Làn 3mx6m",
            font=("Segoe UI", 8),
            bg="#37474f",
            fg="#eceff1",
            relief="flat",
            command=self._apply_preset_3x6
        )
        btn_preset_lane.pack(side="left", padx=2)

        btn_clear_px = tk.Button(
            row_actions,
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
            text="🚀 TÍNH MA TRẬN HOMOGRAPHY",
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
        # PHẦN 4: KẾT QUẢ ĐO ĐẠC TỨC THÌ KHI CLICK VÀO ẢNH
        # -------------------------------------------------------------
        frame_res_sec = tk.LabelFrame(
            self.scrollable_left,
            text=" 4. Kết Quả Đo Đạc Khi Click Lên Ảnh ",
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
            text="👉 TỌA ĐỘ MÉT:  X = --- m  |  Y = --- m",
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
            text="👉 KHOẢNG CÁCH TỚI CAMERA:  D = --- m",
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
            text="Khoảng cách 2 điểm click gần nhất: --- m",
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

        # Thanh trạng thái phía trên ảnh
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

        # Canvas hiển thị ảnh
        self.canvas = tk.Canvas(right_container, bg="#121216", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Ràng buộc sự kiện Canvas
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Motion>", self._on_canvas_motion)

        # Vẽ thông báo chưa có ảnh lên canvas
        self.after(100, self._draw_placeholder)

    def _draw_placeholder(self):
        """Vẽ màn hình chờ khi chưa chọn ảnh"""
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
            text="Sau đó, bạn có thể tự gõ tọa độ Pixel / Mét hoặc click trực tiếp lên ảnh.",
            font=("Segoe UI", 9, "italic"),
            fill="#455a64"
        )

    def choose_image_action(self):
        """Hộp thoại chọn ảnh từ máy tính"""
        filetypes = [
            ("Ảnh hoặc Video", "*.jpg *.jpeg *.png *.bmp *.webp *.mp4 *.avi *.mkv *.mov"),
            ("Tập tin Hình ảnh", "*.jpg *.jpeg *.png *.bmp *.webp"),
            ("Tập tin Video", "*.mp4 *.avi *.mkv *.mov"),
            ("Tất cả tập tin", "*.*")
        ]
        chosen = filedialog.askopenfilename(
            title="Chọn ảnh hoặc video camera để hiệu chuẩn Homography",
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
            messagebox.showerror("Lỗi", f"Không thể đọc ảnh từ tập tin: {chosen}")
            return

        self.orig_cv_img = img
        self.orig_h, self.orig_w = img.shape[:2]
        self.image_path = chosen

        self.lbl_img_info.config(
            text=f"Ảnh: {Path(chosen).name} ({self.orig_w} x {self.orig_h} px)",
            fg="#00e676"
        )
        self.lbl_top_status.config(
            text="Đã nạp ảnh thành công! Bạn có thể tự nhập hoặc click chấm 4 mốc.",
            fg="#00e5ff"
        )

        self.measured_points.clear()
        self._redraw_image()

    def _apply_preset_2x4(self):
        """Mẫu thảm mốc 2m x 4m"""
        vals = [(-1.0, 2.0), (1.0, 2.0), (1.0, 6.0), (-1.0, 6.0)]
        for i, (x, y) in enumerate(vals):
            self.entries_world[i][0].delete(0, tk.END)
            self.entries_world[i][0].insert(0, str(x))
            self.entries_world[i][1].delete(0, tk.END)
            self.entries_world[i][1].insert(0, str(y))

    def _apply_preset_3x6(self):
        """Mẫu làn đường 3m x 6m"""
        vals = [(-1.5, 3.0), (1.5, 3.0), (1.5, 9.0), (-1.5, 9.0)]
        for i, (x, y) in enumerate(vals):
            self.entries_world[i][0].delete(0, tk.END)
            self.entries_world[i][0].insert(0, str(x))
            self.entries_world[i][1].delete(0, tk.END)
            self.entries_world[i][1].insert(0, str(y))

    def _clear_pixel_entries(self):
        """Xóa sạch các ô nhập Pixel"""
        for eu, ev in self.entries_pixel:
            eu.delete(0, tk.END)
            ev.delete(0, tk.END)
        self._redraw_image()

    def _set_active_pick_point(self, idx):
        """Chọn nhanh điểm cần chấm tiếp theo"""
        self.lbl_top_status.config(
            text=f"Hãy click lên ảnh để điền tọa độ Pixel cho Mốc #{idx+1}!",
            fg=POINT_COLORS_HEX[idx]
        )
        self.active_manual_pick_idx = idx

    def _get_pixel_points_from_entries(self):
        """Đọc danh sách 4 điểm pixel từ các ô nhập liệu"""
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
        """Đọc danh sách 4 điểm mét từ các ô nhập liệu"""
        pts = []
        for i, (ex, ey) in enumerate(self.entries_world):
            x_str = ex.get().strip()
            y_str = ey.get().strip()
            try:
                pts.append((float(x_str), float(y_str)))
            except ValueError:
                return None, f"Tọa độ Mét mốc #{i+1} không phải là số hợp lệ!"
        return pts, None

    def compute_homography_action(self):
        """Tính toán ma trận Homography từ các giá trị người dùng đã nhập"""
        w_pts, w_err = self._get_world_points_from_entries()
        if w_err:
            messagebox.showerror("Lỗi Nhập Liệu", w_err)
            return

        px_pts, px_err = self._get_pixel_points_from_entries()
        if px_err:
            messagebox.showerror("Lỗi Nhập Liệu", px_err)
            return

        # Kiểm tra đủ 4 điểm pixel
        missing = [i + 1 for i, p in enumerate(px_pts) if p is None]
        if missing:
            messagebox.showwarning(
                "Thiếu Tọa Độ Pixel",
                f"Vui lòng nhập hoặc click chấm tọa độ Pixel cho mốc: {missing}!"
            )
            return

        try:
            shape = (self.orig_h, self.orig_w) if self.orig_h > 0 else (1080, 1920)
            H, rep_err = self.calibrator.compute_homography(px_pts, w_pts, shape)
            self._update_matrix_display()

            self.lbl_top_status.config(
                text=f"✅ ĐÃ TÍNH XONG MA TRẬN H (Sai số: {rep_err:.3f}m) - CLICK VÀO BẤT KỲ ĐIỂM NÀO ĐỂ ĐO MÉT!",
                fg="#00e676"
            )

            # Tự động lưu vào config
            self.calibrator.save_to_json(CONFIG_FILE, metadata={"image_path": self.image_path})

            messagebox.showinfo(
                "Thành Công",
                f"Đã tính toán thành công ma trận Homography!\nSai số tái chiếu: {rep_err:.4f} mét.\n\nBây giờ bạn có thể click vào bất kỳ điểm nào trên ảnh để xem tọa độ mét!"
            )
            self._redraw_image()

        except Exception as e:
            messagebox.showerror("Lỗi Tính Toán", f"Không thể tính ma trận Homography:\n{e}")

    def save_homography_action(self):
        """Lưu cấu hình ra file JSON"""
        if not self.calibrator.is_calibrated:
            messagebox.showwarning("Cảnh Báo", "Chưa có ma trận Homography để lưu. Vui lòng bấm [TÍNH MA TRẬN] trước!")
            return
        try:
            saved_path = self.calibrator.save_to_json(CONFIG_FILE, metadata={"image_path": self.image_path})
            messagebox.showinfo("Đã Lưu", f"Đã lưu ma trận thành công tại:\n{saved_path}")
        except Exception as e:
            messagebox.showerror("Lỗi Lưu File", f"Không thể lưu file cấu hình: {e}")

    def _update_matrix_display(self):
        """Hiển thị ma trận H lên Textbox"""
        if self.calibrator.is_calibrated:
            self.txt_matrix_info.config(state="normal")
            self.txt_matrix_info.delete("1.0", tk.END)
            h = self.calibrator.H
            txt = f"Ma trận H (Pixel -> Mét):\n"
            for row in h:
                txt += "  [" + "  ".join([f"{val:11.4e}" for val in row]) + "]\n"
            txt += f"Sai số trung bình: {self.calibrator.reprojection_error:.4f} m"
            self.txt_matrix_info.insert(tk.END, txt)
            self.txt_matrix_info.config(state="disabled")

    def clear_measurements_action(self):
        """Xóa danh sách các điểm đo kiểm thử"""
        self.measured_points.clear()
        self.lbl_click_pixel.config(text="Tọa độ Pixel vừa click: Đã xóa")
        self.lbl_res_meters.config(text="👉 TỌA ĐỘ MÉT:  X = --- m  |  Y = --- m")
        self.lbl_res_dist.config(text="👉 KHOẢNG CÁCH TỚI CAMERA:  D = --- m")
        self.lbl_delta_dist.config(text="Khoảng cách 2 điểm click gần nhất: --- m")
        self._redraw_image()

    def _on_canvas_resize(self, event):
        """Khi kích thước Canvas thay đổi (người dùng phóng to/thu nhỏ cửa sổ)"""
        if self.orig_cv_img is not None:
            self._redraw_image()
        else:
            self._draw_placeholder()

    def _on_canvas_motion(self, event):
        """Theo dõi tọa độ chuột trên ảnh"""
        if self.orig_cv_img is None or self.scale <= 0:
            return

        cx, cy = event.x, event.y
        # Kiểm tra chuột có nằm trong vùng ảnh không
        if (self.offset_x <= cx <= self.offset_x + self.disp_w and
            self.offset_y <= cy <= self.offset_y + self.disp_h):
            orig_u = (cx - self.offset_x) / self.scale
            orig_v = (cy - self.offset_y) / self.scale
            self.lbl_mouse_coord.config(text=f"Pixel: (u={orig_u:.0f}, v={orig_v:.0f})")
        else:
            self.lbl_mouse_coord.config(text="Pixel: (---, ---)")

    def _on_canvas_click(self, event):
        """Xử lý sự kiện click chuột lên ảnh"""
        if self.orig_cv_img is None or self.scale <= 0:
            return

        cx, cy = event.x, event.y
        # Kiểm tra click có nằm trong ảnh không
        if not (self.offset_x <= cx <= self.offset_x + self.disp_w and
                self.offset_y <= cy <= self.offset_y + self.disp_h):
            return

        orig_u = (cx - self.offset_x) / self.scale
        orig_v = (cy - self.offset_y) / self.scale

        # -----------------------------------------------------------------
        # TÌNH HUỐNG 1: ĐIỀN ĐIỂM MỐC PIXEL NẾU CÒN Ô TRỐNG HOẶC ĐANG CHẤM
        # -----------------------------------------------------------------
        # Kiểm tra xem ô pixel nào đang trống
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

            # Nếu vừa điền xong mốc thứ 4 -> Gợi ý bấm tính toán
            all_filled = all(eu.get().strip() != "" and ev.get().strip() != "" for eu, ev in self.entries_pixel)
            if all_filled and not self.calibrator.is_calibrated:
                self.compute_homography_action()
            return

        # -----------------------------------------------------------------
        # TÌNH HUỐNG 2: ĐÃ CÓ MA TRẬN H -> ĐO ĐẠC TỨC THÌ TỌA ĐỘ MÉT!
        # -----------------------------------------------------------------
        if self.calibrator.is_calibrated:
            try:
                x_m, y_m, dist_m = self.calibrator.pixel_to_world(orig_u, orig_v)
                point_char = chr(65 + len(self.measured_points) % 26)
                self.measured_points.append((orig_u, orig_v, x_m, y_m, dist_m))

                # Cập nhật kết quả lên các Label
                self.lbl_click_pixel.config(
                    text=f"Tọa độ Pixel [{point_char}]: u = {orig_u:.1f} px , v = {orig_v:.1f} px"
                )
                self.lbl_res_meters.config(
                    text=f"👉 TỌA ĐỘ MÉT:  X = {x_m:+.2f} m  |  Y = {y_m:.2f} m"
                )
                self.lbl_res_dist.config(
                    text=f"👉 KHOẢNG CÁCH TỚI CAMERA:  D = {dist_m:.2f} m"
                )

                if len(self.measured_points) >= 2:
                    p1 = self.measured_points[-2]
                    p2 = self.measured_points[-1]
                    delta_d = np.sqrt((p1[2] - p2[2])**2 + (p1[3] - p2[3])**2)
                    self.lbl_delta_dist.config(
                        text=f"Khoảng cách 2 điểm click gần nhất: Δd = {delta_d:.2f} m"
                    )

                self.lbl_top_status.config(
                    text=f"[{point_char}] Pixel({orig_u:.0f}, {orig_v:.0f}) -> X={x_m:+.2f}m, Y={y_m:.2f}m (Cách Cam: {dist_m:.2f}m)",
                    fg="#00e676"
                )

                print(f"[+] CLICK ĐO ĐẠC [{point_char}]: Pixel({orig_u:.1f}, {orig_v:.1f}) -> X = {x_m:+.2f} m, Y = {y_m:.2f} m | Khoảng cách = {dist_m:.2f} m")

                self._redraw_image()

            except Exception as e:
                messagebox.showerror("Lỗi Đo Đạc", f"Lỗi tính toán tọa độ:\n{e}")
        else:
            self.lbl_top_status.config(
                text="Chưa tính ma trận Homography! Vui lòng bấm [🚀 TÍNH MA TRẬN HOMOGRAPHY] bên trái.",
                fg="#ff9800"
            )

    def _redraw_image(self):
        """Vẽ lại ảnh kèm các điểm mốc và điểm đo đạc lên Canvas"""
        if self.orig_cv_img is None:
            self._draw_placeholder()
            return

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 50 or ch < 50:
            return

        # Tính toán tỷ lệ co giãn ảnh sao cho vừa khít Canvas (giữ nguyên tỷ lệ)
        scale_w = cw / float(self.orig_w)
        scale_h = ch / float(self.orig_h)
        self.scale = min(scale_w, scale_h)

        self.disp_w = max(1, int(self.orig_w * self.scale))
        self.disp_h = max(1, int(self.orig_h * self.scale))
        self.offset_x = (cw - self.disp_w) // 2
        self.offset_y = (ch - self.disp_h) // 2

        # Tạo bản copy ảnh để vẽ
        display_img = self.orig_cv_img.copy()

        # -------------------------------------------------------------
        # 1. VẼ 4 ĐIỂM MỐC (NẾU CÓ TRONG Ô NHẬP LIỆU)
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

        # Nối các điểm mốc
        if len(valid_pixel_pts) >= 2:
            poly_pts = np.array([[pt[1], pt[2]] for pt in valid_pixel_pts], dtype=np.int32).reshape((-1, 1, 2))
            is_closed = (len(valid_pixel_pts) == 4)
            cv2.polylines(display_img, [poly_pts], is_closed, (0, 255, 255), 2, cv2.LINE_AA)
            if is_closed:
                overlay = display_img.copy()
                cv2.fillPoly(overlay, [poly_pts], (0, 100, 140))
                cv2.addWeighted(overlay, 0.25, display_img, 0.75, 0, display_img)

        # Vẽ từng điểm tròn mốc
        for idx, u_pt, v_pt in valid_pixel_pts:
            col = POINT_COLORS_BGR[idx % len(POINT_COLORS_BGR)]
            cv2.circle(display_img, (u_pt, v_pt), 8, col, -1)
            cv2.circle(display_img, (u_pt, v_pt), 10, (255, 255, 255), 2)

            # Đọc tọa độ mét tương ứng
            try:
                wx = float(self.entries_world[idx][0].get().strip())
                wy = float(self.entries_world[idx][1].get().strip())
                lbl_m = f"#{idx+1}: ({wx:+.1f}m, {wy:.1f}m)"
            except Exception:
                lbl_m = f"#{idx+1}"

            (tw, th), _ = cv2.getTextSize(lbl_m, cv2.FONT_HERSHEY_DUPLEX, 0.55, 1)
            cv2.rectangle(display_img, (u_pt + 12, v_pt - th - 6), (u_pt + 16 + tw, v_pt + 4), (20, 20, 20), -1)
            cv2.putText(display_img, lbl_m, (u_pt + 14, v_pt - 2), cv2.FONT_HERSHEY_DUPLEX, 0.55, col, 1, cv2.LINE_AA)

        # -------------------------------------------------------------
        # 2. VẼ CÁC ĐIỂM ĐO ĐẠC KIỂM THỬ (CLICK BẤT KỲ ĐỂ ĐO MÉT)
        # -------------------------------------------------------------
        for idx, (pu, pv, xm, ym, dm) in enumerate(self.measured_points):
            iu, iv = int(pu), int(pv)
            point_char = chr(65 + idx % 26)

            cv2.drawMarker(display_img, (iu, iv), (0, 255, 0), cv2.MARKER_CROSS, 20, 2)
            cv2.circle(display_img, (iu, iv), 6, (0, 255, 255), -1)

            meas_tag = f"[{point_char}] X:{xm:+.2f}m | Y:{ym:.2f}m | D:{dm:.2f}m"
            (tw, th), _ = cv2.getTextSize(meas_tag, cv2.FONT_HERSHEY_DUPLEX, 0.52, 1)
            tx = min(self.orig_w - tw - 15, max(10, iu + 14))
            ty = max(30, iv - 10)
            cv2.rectangle(display_img, (tx - 4, ty - th - 4), (tx + tw + 4, ty + 4), (15, 35, 15), -1)
            cv2.rectangle(display_img, (tx - 4, ty - th - 4), (tx + tw + 4, ty + 4), (0, 255, 0), 1)
            cv2.putText(display_img, meas_tag, (tx, ty), cv2.FONT_HERSHEY_DUPLEX, 0.52, (0, 255, 200), 1, cv2.LINE_AA)

        # Đường nối 2 điểm đo gần nhất
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

        # Resize ảnh để hiển thị lên Canvas
        resized_bgr = cv2.resize(display_img, (self.disp_w, self.disp_h), interpolation=cv2.INTER_LINEAR)
        resized_rgb = cv2.cvtColor(resized_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(resized_rgb)
        self.current_tk_img = ImageTk.PhotoImage(pil_img)

        # Xóa canvas và vẽ ảnh căn giữa
        self.canvas.delete("all")
        self.canvas.create_image(self.offset_x, self.offset_y, anchor="nw", image=self.current_tk_img)


if __name__ == "__main__":
    app = HomographyCalibratorApp()
    app.mainloop()
