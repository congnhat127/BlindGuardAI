#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Công cụ GUI: run_configurator_gui.py
Vị trí: BlindGuard_App/system_configurator/run_configurator_gui.py
Mô tả: Trình hướng dẫn thiết lập hệ thống BlindGuard AI (Configuration Wizard):
       - Bước 1: Cấu hình thông số hình học xe tải (Xe đầu kéo hoặc Xe liền thân).
       - Bước 2: Hiệu chuẩn ma trận Homography cho 4 góc Camera điểm mù.
       - Lưu toàn bộ cấu hình vào file system_config.json.
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

# Thiết lập đường dẫn import
CURRENT_DIR = Path(__file__).resolve().parent
APP_ROOT = CURRENT_DIR.parent
sys.path.insert(0, str(APP_ROOT))
sys.path.insert(0, str(APP_ROOT / "core"))

from core.config_loader import SystemConfigManager
from core.homography_manager import MultiCameraHomographyManager

POINT_COLORS_HEX = ["#3498db", "#f1c40f", "#2ecc71", "#e74c3c"]
POINT_COLORS_BGR = [(219, 152, 52), (15, 196, 241), (113, 204, 46), (60, 76, 231)]


class BlindGuardSystemConfiguratorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BlindGuard AI — Trình Thiết Lập Hệ Thống & Căn Chỉnh 4 Camera")
        self.geometry("1400x880")
        self.minsize(1100, 720)
        self.configure(bg="#1a1a24")

        # Căn giữa màn hình
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        ww, wh = min(1400, sw - 60), min(880, sh - 60)
        self.geometry(f"{ww}x{wh}+{(sw - ww)//2}+{max(10, (sh - wh - 40)//2)}")

        self.config_manager = SystemConfigManager()
        self.homo_manager = MultiCameraHomographyManager(self.config_manager)

        self.current_step = 1  # 1: Xe Profile, 2: Camera Homography
        self.active_camera = "MIRROR_RIGHT"

        # Dữ liệu ảnh camera
        self.orig_cv_img = None
        self.orig_h, self.orig_w = 0, 0
        self.scale = 1.0
        self.offset_x, self.offset_y = 0, 0
        self.current_tk_img = None
        self.measured_points = []

        self._build_header()
        self._build_body()
        self._load_vehicle_profile_to_ui()
        self._load_camera_to_ui(self.active_camera)

    def _build_header(self):
        header_frame = tk.Frame(self, bg="#12121a", height=60)
        header_frame.pack(side=tk.TOP, fill=tk.X)
        header_frame.pack_propagate(False)

        logo_lbl = tk.Label(header_frame, text="🛡️ BLINDGUARD AI — SYSTEM CONFIGURATOR",
                            font=("Segoe UI", 14, "bold"), fg="#00e5ff", bg="#12121a")
        logo_lbl.pack(side=tk.LEFT, padx=20, pady=12)

        # Tab điều hướng
        nav_frame = tk.Frame(header_frame, bg="#12121a")
        nav_frame.pack(side=tk.RIGHT, padx=20)

        self.btn_nav_step1 = tk.Button(nav_frame, text="1. Thông số Xe", font=("Segoe UI", 10, "bold"),
                                       bg="#00b0ff", fg="#ffffff", relief="flat", padx=14, pady=6,
                                       command=lambda: self.switch_step(1))
        self.btn_nav_step1.pack(side=tk.LEFT, padx=6)

        self.btn_nav_step2 = tk.Button(nav_frame, text="2. Hiệu chuẩn 4 Camera", font=("Segoe UI", 10, "bold"),
                                       bg="#2d2d3d", fg="#b0b0c0", relief="flat", padx=14, pady=6,
                                       command=lambda: self.switch_step(2))
        self.btn_nav_step2.pack(side=tk.LEFT, padx=6)

        btn_save_all = tk.Button(nav_frame, text="💾 Lưu Cấu Hình", font=("Segoe UI", 10, "bold"),
                                 bg="#00c853", fg="#ffffff", relief="flat", padx=16, pady=6,
                                 command=self.save_all_and_notify)
        btn_save_all.pack(side=tk.LEFT, padx=12)

    def _build_body(self):
        self.body_container = tk.Frame(self, bg="#1a1a24")
        self.body_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # Frame Bước 1
        self.frame_step1 = tk.Frame(self.body_container, bg="#1a1a24")

        # Frame Bước 2
        self.frame_step2 = tk.Frame(self.body_container, bg="#1a1a24")

        self._build_step1_vehicle_ui()
        self._build_step2_homography_ui()

        # Hiển thị ban đầu bước 1
        self.switch_step(1)

    # =========================================================================
    # BƯỚC 1: CẤU HÌNH THÔNG SỐ XE
    # =========================================================================
    def _build_step1_vehicle_ui(self):
        main_box = tk.Frame(self.frame_step1, bg="#242432", bd=1, relief="solid")
        main_box.pack(fill=tk.BOTH, expand=True, padx=40, pady=20)

        title = tk.Label(main_box, text="CẤU HÌNH HÌNH HỌC & ĐỘNG LỰC HỌC XE CHỦ (EGO VEHICLE PROFILE)",
                         font=("Segoe UI", 13, "bold"), fg="#ffffff", bg="#242432")
        title.pack(anchor="w", padx=25, pady=(20, 6))

        desc = tk.Label(main_box, text="Các thông số này xác định vị trí cản trước, cản sau, kích thước vùng nguy hiểm động (DHZ), độ lấn cua (Inswing) và văng đuôi (Tail-Swing).",
                        font=("Segoe UI", 10), fg="#a0a0b5", bg="#242432")
        desc.pack(anchor="w", padx=25, pady=(0, 14))

        # --- Khung chung (General Profile) ---
        f_gen = tk.Frame(main_box, bg="#242432")
        f_gen.pack(fill=tk.X, padx=25, pady=(0, 10))

        # 1. Chọn kiểu loại xe
        tk.Label(f_gen, text="Kiểu loại thân xe:", font=("Segoe UI", 10, "bold"), fg="#00e5ff", bg="#242432").grid(row=0, column=0, sticky="w", pady=4)
        self.var_vtype = tk.StringVar(value="ARTICULATED")
        vtype_box = tk.Frame(f_gen, bg="#242432")
        vtype_box.grid(row=0, column=1, sticky="w", pady=4)
        tk.Radiobutton(vtype_box, text="Xe Đầu Kéo Sơ-mi Rơ-moóc (ARTICULATED)", variable=self.var_vtype,
                       value="ARTICULATED", font=("Segoe UI", 10, "bold"), fg="#ffffff", bg="#242432", selectcolor="#12121a",
                       command=self._on_vtype_change).pack(side=tk.LEFT, padx=(0, 20))
        tk.Radiobutton(vtype_box, text="Xe Tải Liền Thân / Thùng Cố Định (RIGID)", variable=self.var_vtype,
                       value="RIGID", font=("Segoe UI", 10, "bold"), fg="#ffffff", bg="#242432", selectcolor="#12121a",
                       command=self._on_vtype_change).pack(side=tk.LEFT)

        # 2. Tên cấu hình & Khoảng đệm an toàn
        tk.Label(f_gen, text="Tên gọi cấu hình:", font=("Segoe UI", 10), fg="#ffffff", bg="#242432").grid(row=1, column=0, sticky="w", pady=4)
        f_name_row = tk.Frame(f_gen, bg="#242432")
        f_name_row.grid(row=1, column=1, sticky="w", pady=4)

        self.ent_vname = tk.Entry(f_name_row, font=("Segoe UI", 10), width=34, bg="#181822", fg="#ffffff", insertbackground="white")
        self.ent_vname.pack(side=tk.LEFT, padx=(0, 25))

        tk.Label(f_name_row, text="Khoảng đệm an toàn cơ sở d_clearance (m):", font=("Segoe UI", 10), fg="#ffffff", bg="#242432").pack(side=tk.LEFT, padx=(0, 8))
        self.ent_clearance = tk.Entry(f_name_row, font=("Segoe UI", 10), width=8, bg="#181822", fg="#ffffff", insertbackground="white")
        self.ent_clearance.pack(side=tk.LEFT)

        # =====================================================================
        # KHUNG THÔNG SỐ XE ĐẦU KÉO SƠ-MI RƠ-MOÓC (ARTICULATED)
        # =====================================================================
        self.form_art = tk.LabelFrame(main_box, text=" 🚚 THÔNG SỐ XE ĐẦU KÉO SƠ-MI RƠ-MOÓC (ARTICULATED) ",
                                      font=("Segoe UI", 10, "bold"), fg="#00e5ff", bg="#242432", padx=12, pady=10)

        # Chia 2 cột: Trái (Nhập tay) - Phải (Tự tính toán)
        col_art_box = tk.Frame(self.form_art, bg="#242432")
        col_art_box.pack(fill=tk.BOTH, expand=True)

        # --- CỘT TRÁI: NHẬP TAY (ARTICULATED) ---
        f_art_left = tk.LabelFrame(col_art_box, text=" ✍️ 1. THÔNG SỐ NHẬP TAY (TỪ ĐĂNG KIỂM / CATALOGUE) ",
                                   font=("Segoe UI", 9, "bold"), fg="#ffd600", bg="#1e1e2a", padx=12, pady=8)
        f_art_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        row = 0
        tk.Label(f_art_left, text="Chiều rộng Cabin đầu kéo W_cab (m):", font=("Segoe UI", 9), fg="#ffffff", bg="#1e1e2a").grid(row=row, column=0, sticky="w", pady=3)
        self.ent_art_cab_w = tk.Entry(f_art_left, font=("Segoe UI", 9), width=8, bg="#12121a", fg="#ffffff", insertbackground="white")
        self.ent_art_cab_w.grid(row=row, column=1, sticky="w", pady=3)
        tk.Label(f_art_left, text="[Chuẩn 2.5m]", font=("Segoe UI", 8), fg="#888899", bg="#1e1e2a").grid(row=row, column=2, sticky="w", padx=6)

        row += 1
        tk.Label(f_art_left, text="Chiều rộng Thùng rơ-moóc W_trail (m):", font=("Segoe UI", 9), fg="#ffffff", bg="#1e1e2a").grid(row=row, column=0, sticky="w", pady=3)
        self.ent_art_trail_w = tk.Entry(f_art_left, font=("Segoe UI", 9), width=8, bg="#12121a", fg="#ffffff", insertbackground="white")
        self.ent_art_trail_w.grid(row=row, column=1, sticky="w", pady=3)
        tk.Label(f_art_left, text="[Chuẩn 2.5m]", font=("Segoe UI", 8), fg="#888899", bg="#1e1e2a").grid(row=row, column=2, sticky="w", padx=6)

        row += 1
        tk.Label(f_art_left, text="Chiều dài cơ sở đầu kéo L_f (m):", font=("Segoe UI", 9), fg="#ffffff", bg="#1e1e2a").grid(row=row, column=0, sticky="w", pady=3)
        self.ent_art_wb = tk.Entry(f_art_left, font=("Segoe UI", 9), width=8, bg="#12121a", fg="#ffffff", insertbackground="white")
        self.ent_art_wb.grid(row=row, column=1, sticky="w", pady=3)
        tk.Label(f_art_left, text="[Tâm trục sau -> Trục trước, ~3.6m]", font=("Segoe UI", 8), fg="#888899", bg="#1e1e2a").grid(row=row, column=2, sticky="w", padx=6)

        row += 1
        tk.Label(f_art_left, text="Độ nhô cản trước đầu kéo L_foh (m):", font=("Segoe UI", 9), fg="#ffffff", bg="#1e1e2a").grid(row=row, column=0, sticky="w", pady=3)
        self.ent_art_foh = tk.Entry(f_art_left, font=("Segoe UI", 9), width=8, bg="#12121a", fg="#ffffff", insertbackground="white")
        self.ent_art_foh.grid(row=row, column=1, sticky="w", pady=3)
        tk.Label(f_art_left, text="[Trục trước -> Mép cản trước, ~1.35m]", font=("Segoe UI", 8), fg="#888899", bg="#1e1e2a").grid(row=row, column=2, sticky="w", padx=6)

        row += 1
        tk.Label(f_art_left, text="Vị trí chốt Kingpin trước trục sau d_hitch (m):", font=("Segoe UI", 9), fg="#ffffff", bg="#1e1e2a").grid(row=row, column=0, sticky="w", pady=3)
        self.ent_art_hitch = tk.Entry(f_art_left, font=("Segoe UI", 9), width=8, bg="#12121a", fg="#ffffff", insertbackground="white")
        self.ent_art_hitch.grid(row=row, column=1, sticky="w", pady=3)
        tk.Label(f_art_left, text="[Mâm xoay cách trục sau, ~0.30m]", font=("Segoe UI", 8), fg="#888899", bg="#1e1e2a").grid(row=row, column=2, sticky="w", padx=6)

        row += 1
        tk.Label(f_art_left, text="Chiều dài cơ sở rơ-moóc L_wb_trail (m):", font=("Segoe UI", 9, "bold"), fg="#ff80ab", bg="#1e1e2a").grid(row=row, column=0, sticky="w", pady=3)
        self.ent_art_trail_wb = tk.Entry(f_art_left, font=("Segoe UI", 9, "bold"), width=8, bg="#12121a", fg="#ff80ab", insertbackground="white")
        self.ent_art_trail_wb.grid(row=row, column=1, sticky="w", pady=3)
        tk.Label(f_art_left, text="[Kingpin -> Trục rơ-moóc: quyết định Inswing!]", font=("Segoe UI", 8), fg="#ff80ab", bg="#1e1e2a").grid(row=row, column=2, sticky="w", padx=6)

        row += 1
        tk.Label(f_art_left, text="Độ nhô cản sau rơ-moóc L_roh_trail (m):", font=("Segoe UI", 9, "bold"), fg="#ffab40", bg="#1e1e2a").grid(row=row, column=0, sticky="w", pady=3)
        self.ent_art_trail_roh = tk.Entry(f_art_left, font=("Segoe UI", 9, "bold"), width=8, bg="#12121a", fg="#ffab40", insertbackground="white")
        self.ent_art_trail_roh.grid(row=row, column=1, sticky="w", pady=3)
        tk.Label(f_art_left, text="[Trục rơ-moóc -> Cản sau: quyết định Tail-Swing!]", font=("Segoe UI", 8), fg="#ffab40", bg="#1e1e2a").grid(row=row, column=2, sticky="w", padx=6)

        row += 1
        tk.Label(f_art_left, text="Độ nhô đầu rơ-moóc L_foh_trail (m):", font=("Segoe UI", 9), fg="#ffffff", bg="#1e1e2a").grid(row=row, column=0, sticky="w", pady=3)
        self.ent_art_trail_foh = tk.Entry(f_art_left, font=("Segoe UI", 9), width=8, bg="#12121a", fg="#ffffff", insertbackground="white")
        self.ent_art_trail_foh.grid(row=row, column=1, sticky="w", pady=3)
        tk.Label(f_art_left, text="[Kingpin -> Mép trước thùng rơ-moóc, ~1.0m]", font=("Segoe UI", 8), fg="#888899", bg="#1e1e2a").grid(row=row, column=2, sticky="w", padx=6)

        # --- CỘT PHẢI: TỰ ĐỘNG TÍNH TOÁN (ARTICULATED) ---
        f_art_right = tk.LabelFrame(col_art_box, text=" ⚡ 2. BẢNG THÔNG SỐ TỰ ĐỘNG TÍNH TOÁN (LIVE PREVIEW) ",
                                    font=("Segoe UI", 9, "bold"), fg="#00e676", bg="#1a2420", padx=14, pady=8)
        f_art_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))

        self.lbl_art_calc_xfront = tk.Label(f_art_right, text="🔹 Mũi cản trước đầu kéo (X_front): +4.95 m",
                                            font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#1a2420", anchor="w")
        self.lbl_art_calc_xfront.pack(fill=tk.X, pady=3)

        self.lbl_art_calc_axle = tk.Label(f_art_right, text="🔹 Vị trí cụm trục rơ-moóc (X_axle_trail): -7.90 m",
                                          font=("Segoe UI", 9, "bold"), fg="#80d8ff", bg="#1a2420", anchor="w")
        self.lbl_art_calc_axle.pack(fill=tk.X, pady=3)

        self.lbl_art_calc_xrear = tk.Label(f_art_right, text="🔹 Mép cản sau rơ-moóc (X_rear): -10.70 m",
                                           font=("Segoe UI", 9, "bold"), fg="#ff80ab", bg="#1a2420", anchor="w")
        self.lbl_art_calc_xrear.pack(fill=tk.X, pady=3)

        self.lbl_art_calc_traillen = tk.Label(f_art_right, text="🔹 Tổng chiều dài thùng rơ-moóc (L_trail): 12.00 m",
                                              font=("Segoe UI", 9, "bold"), fg="#ffd600", bg="#1a2420", anchor="w")
        self.lbl_art_calc_traillen.pack(fill=tk.X, pady=3)

        self.lbl_art_calc_oal = tk.Label(f_art_right, text="🏁 TỔNG CHIỀU DÀI ĐOÀN XE (OAL): 15.65 m",
                                         font=("Segoe UI", 10, "bold"), fg="#00e676", bg="#1a2420", anchor="w")
        self.lbl_art_calc_oal.pack(fill=tk.X, pady=6)

        lbl_art_note = tk.Label(f_art_right,
                                text="ℹ️ Cơ sở vật lý động lực học:\n"
                                     " • Độ lấn cua Inswing phụ thuộc L_wb_trailer (8.2m): Thùng càng dài cua càng hẹp.\n"
                                     " • Độ văng đuôi Tail-Swing phụ thuộc L_roh_trailer (2.8m): Đuôi quét nghịch chiều lái.\n"
                                     " • Chuẩn VCS: Gốc (0,0) đặt tại tâm trục sau đầu kéo, trục X hướng tới trước.",
                                font=("Segoe UI", 8), fg="#b0bec5", bg="#1a2420", justify="left")
        lbl_art_note.pack(fill=tk.X, pady=(4, 0))

        # =====================================================================
        # KHUNG THÔNG SỐ XE TẢI LIỀN THÂN (RIGID)
        # =====================================================================
        self.form_rigid = tk.LabelFrame(main_box, text=" 🚛 THÔNG SỐ XE TẢI LIỀN THÂN / THÙNG CỐ ĐỊNH (RIGID) ",
                                        font=("Segoe UI", 10, "bold"), fg="#00e5ff", bg="#242432", padx=12, pady=10)

        col_rig_box = tk.Frame(self.form_rigid, bg="#242432")
        col_rig_box.pack(fill=tk.BOTH, expand=True)

        # --- CỘT TRÁI: NHẬP TAY (RIGID) ---
        f_rig_left = tk.LabelFrame(col_rig_box, text=" ✍️ 1. THÔNG SỐ NHẬP TAY (TỪ ĐĂNG KIỂM / CATALOGUE) ",
                                   font=("Segoe UI", 9, "bold"), fg="#ffd600", bg="#1e1e2a", padx=12, pady=8)
        f_rig_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        r_row = 0
        tk.Label(f_rig_left, text="Chiều rộng xe W_rigid (m):", font=("Segoe UI", 9), fg="#ffffff", bg="#1e1e2a").grid(row=r_row, column=0, sticky="w", pady=4)
        self.ent_rig_w = tk.Entry(f_rig_left, font=("Segoe UI", 9), width=8, bg="#12121a", fg="#ffffff", insertbackground="white")
        self.ent_rig_w.grid(row=r_row, column=1, sticky="w", pady=4)
        tk.Label(f_rig_left, text="[Chuẩn 2.5m]", font=("Segoe UI", 8), fg="#888899", bg="#1e1e2a").grid(row=r_row, column=2, sticky="w", padx=6)

        r_row += 1
        tk.Label(f_rig_left, text="Chiều dài cơ sở L_wb (m):", font=("Segoe UI", 9), fg="#ffffff", bg="#1e1e2a").grid(row=r_row, column=0, sticky="w", pady=4)
        self.ent_rig_wb = tk.Entry(f_rig_left, font=("Segoe UI", 9), width=8, bg="#12121a", fg="#ffffff", insertbackground="white")
        self.ent_rig_wb.grid(row=r_row, column=1, sticky="w", pady=4)
        tk.Label(f_rig_left, text="[Tâm trục trước -> Tâm trục sau, ~5.8m]", font=("Segoe UI", 8), fg="#888899", bg="#1e1e2a").grid(row=r_row, column=2, sticky="w", padx=6)

        r_row += 1
        tk.Label(f_rig_left, text="Độ nhô cản trước L_foh (m):", font=("Segoe UI", 9), fg="#ffffff", bg="#1e1e2a").grid(row=r_row, column=0, sticky="w", pady=4)
        self.ent_rig_foh = tk.Entry(f_rig_left, font=("Segoe UI", 9), width=8, bg="#12121a", fg="#ffffff", insertbackground="white")
        self.ent_rig_foh.grid(row=r_row, column=1, sticky="w", pady=4)
        tk.Label(f_rig_left, text="[Trục trước -> Mép cản trước xe, ~1.35m]", font=("Segoe UI", 8), fg="#888899", bg="#1e1e2a").grid(row=r_row, column=2, sticky="w", padx=6)

        r_row += 1
        tk.Label(f_rig_left, text="Độ nhô cản sau L_roh (m):", font=("Segoe UI", 9, "bold"), fg="#ffab40", bg="#1e1e2a").grid(row=r_row, column=0, sticky="w", pady=4)
        self.ent_rig_roh = tk.Entry(f_rig_left, font=("Segoe UI", 9, "bold"), width=8, bg="#12121a", fg="#ffab40", insertbackground="white")
        self.ent_rig_roh.grid(row=r_row, column=1, sticky="w", pady=4)
        tk.Label(f_rig_left, text="[Trục sau -> Cản sau: quyết định Tail-Swing, ~2.4m]", font=("Segoe UI", 8), fg="#ffab40", bg="#1e1e2a").grid(row=r_row, column=2, sticky="w", padx=6)

        # --- CỘT PHẢI: TỰ ĐỘNG TÍNH TOÁN (RIGID) ---
        f_rig_right = tk.LabelFrame(col_rig_box, text=" ⚡ 2. BẢNG THÔNG SỐ TỰ ĐỘNG TÍNH TOÁN (LIVE PREVIEW) ",
                                    font=("Segoe UI", 9, "bold"), fg="#00e676", bg="#1a2420", padx=14, pady=8)
        f_rig_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))

        self.lbl_rig_calc_xfront = tk.Label(f_rig_right, text="🔹 Mũi cản trước xe (X_front): +7.15 m",
                                            font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#1a2420", anchor="w")
        self.lbl_rig_calc_xfront.pack(fill=tk.X, pady=4)

        self.lbl_rig_calc_xrear = tk.Label(f_rig_right, text="🔹 Mép cản sau xe (X_rear): -2.40 m",
                                           font=("Segoe UI", 9, "bold"), fg="#ff80ab", bg="#1a2420", anchor="w")
        self.lbl_rig_calc_xrear.pack(fill=tk.X, pady=4)

        self.lbl_rig_calc_oal = tk.Label(f_rig_right, text="🏁 TỔNG CHIỀU DÀI XE (OAL): 9.55 m",
                                         font=("Segoe UI", 10, "bold"), fg="#00e676", bg="#1a2420", anchor="w")
        self.lbl_rig_calc_oal.pack(fill=tk.X, pady=8)

        lbl_rig_note = tk.Label(f_rig_right,
                                text="ℹ️ Giải thích tọa độ VCS chuẩn ISO 8855:\n"
                                     " • Gốc tọa độ (0,0) đặt tại tâm trục cầu sau xe tải.\n"
                                     " • Mũi cản trước = L_wb (5.8m) + L_foh (1.35m) = +7.15m trước trục sau.\n"
                                     " • Cản sau = -L_roh = -2.40m sau trục sau.\n"
                                     " • Tổng chiều dài = 7.15m - (-2.40m) = 9.55m.",
                                font=("Segoe UI", 8), fg="#b0bec5", bg="#1a2420", justify="left")
        lbl_rig_note.pack(fill=tk.X, pady=(4, 0))

        # --- BẮT SỰ KIỆN TỰ TÍNH TOÁN TỨC THÌ KHI GÕ PHÍM ---
        for ent in [self.ent_art_cab_w, self.ent_art_trail_w, self.ent_art_wb, self.ent_art_foh,
                    self.ent_art_hitch, self.ent_art_trail_wb, self.ent_art_trail_roh, self.ent_art_trail_foh,
                    self.ent_rig_w, self.ent_rig_wb, self.ent_rig_foh, self.ent_rig_roh]:
            ent.bind("<KeyRelease>", lambda e: self._recalc_live_geometry())

        # Nút chuyển bước
        btn_next = tk.Button(main_box, text="TIẾP TỤC: CẤU HÌNH HOMOGRAPHY 4 CAMERA ➡️", font=("Segoe UI", 11, "bold"),
                             bg="#00b0ff", fg="#ffffff", relief="flat", padx=24, pady=10,
                             command=lambda: self.switch_step(2))
        btn_next.pack(side=tk.BOTTOM, anchor="e", padx=30, pady=15)

    def _recalc_live_geometry(self):
        """Tính toán tức thì các kích thước dẫn xuất khi người dùng thay đổi thông số nhập tay."""
        # 1. Xe đầu kéo Articulated
        try:
            art_wb = float(self.ent_art_wb.get() or 3.6)
            art_foh = float(self.ent_art_foh.get() or 1.35)
            art_hitch = float(self.ent_art_hitch.get() or 0.30)
            trail_wb = float(self.ent_art_trail_wb.get() or 8.2)
            trail_roh = float(self.ent_art_trail_roh.get() or 2.8)
            trail_foh = float(self.ent_art_trail_foh.get() or 1.0)

            x_front = art_wb + art_foh
            x_axle = art_hitch - trail_wb
            x_rear = art_hitch - (trail_wb + trail_roh)
            l_trail = trail_foh + trail_wb + trail_roh
            oal = x_front - x_rear

            self.lbl_art_calc_xfront.config(text=f"🔹 Mũi cản trước đầu kéo (X_front): +{x_front:.2f} m  (L_f {art_wb:.1f}m + Nhô {art_foh:.2f}m)")
            self.lbl_art_calc_axle.config(text=f"🔹 Vị trí cụm trục rơ-moóc (X_axle_trail): {x_axle:.2f} m  (Kingpin {art_hitch:.2f}m - Trục {trail_wb:.1f}m)")
            self.lbl_art_calc_xrear.config(text=f"🔹 Mép cản sau rơ-moóc (X_rear): {x_rear:.2f} m  (Đuôi xa nhất)")
            self.lbl_art_calc_traillen.config(text=f"🔹 Tổng chiều dài thùng rơ-moóc (L_trail): {l_trail:.2f} m  (Nhô trước {trail_foh:.1f}m + Trục {trail_wb:.1f}m + Nhô sau {trail_roh:.1f}m)")
            self.lbl_art_calc_oal.config(text=f"🏁 TỔNG CHIỀU DÀI ĐOÀN XE (OAL): {oal:.2f} m")
        except Exception:
            pass

        # 2. Xe tải liền thân Rigid
        try:
            rig_wb = float(self.ent_rig_wb.get() or 5.8)
            rig_foh = float(self.ent_rig_foh.get() or 1.35)
            rig_roh = float(self.ent_rig_roh.get() or 2.4)

            x_front_rig = rig_wb + rig_foh
            x_rear_rig = -rig_roh
            oal_rig = x_front_rig - x_rear_rig

            self.lbl_rig_calc_xfront.config(text=f"🔹 Mũi cản trước xe (X_front): +{x_front_rig:.2f} m  (L_wb {rig_wb:.1f}m + Nhô trước {rig_foh:.2f}m)")
            self.lbl_rig_calc_xrear.config(text=f"🔹 Mép cản sau xe (X_rear): {x_rear_rig:.2f} m  (Nhô cản sau sau trục bánh {rig_roh:.2f}m)")
            self.lbl_rig_calc_oal.config(text=f"🏁 TỔNG CHIỀU DÀI XE (OAL): {oal_rig:.2f} m")
        except Exception:
            pass

    def _on_vtype_change(self):
        vtype = self.var_vtype.get()
        curr_name = self.ent_vname.get().strip()

        if vtype == "RIGID":
            self.form_art.pack_forget()
            self.form_rigid.pack(fill=tk.X, padx=25, pady=8)
            if not curr_name or curr_name == "Xe đầu kéo sơ-mi rơ-moóc chuẩn":
                self.ent_vname.delete(0, tk.END)
                self.ent_vname.insert(0, "Xe tải liền thân / thùng cố định")
        else:
            self.form_rigid.pack_forget()
            self.form_art.pack(fill=tk.X, padx=25, pady=8)
            if not curr_name or curr_name == "Xe tải liền thân / thùng cố định":
                self.ent_vname.delete(0, tk.END)
                self.ent_vname.insert(0, "Xe đầu kéo sơ-mi rơ-moóc chuẩn")

        self._recalc_live_geometry()

    def _load_vehicle_profile_to_ui(self):
        prof = self.config_manager.vehicle_profile
        vtype = prof.get("vehicle_type", "ARTICULATED")
        self.var_vtype.set(vtype)

        self.ent_vname.delete(0, tk.END)
        self.ent_vname.insert(0, prof.get("name", "Xe đầu kéo sơ-mi rơ-moóc chuẩn" if vtype == "ARTICULATED" else "Xe tải liền thân / thùng cố định"))
        self.ent_clearance.delete(0, tk.END)
        self.ent_clearance.insert(0, str(prof.get("base_clearance", 1.5)))

        # Nạp thông số xe đầu kéo
        self.ent_art_cab_w.delete(0, tk.END)
        self.ent_art_cab_w.insert(0, str(prof.get("cab_width", 2.5)))
        self.ent_art_trail_w.delete(0, tk.END)
        self.ent_art_trail_w.insert(0, str(prof.get("trailer_width", 2.5)))
        self.ent_art_wb.delete(0, tk.END)
        self.ent_art_wb.insert(0, str(prof.get("tractor_wheelbase", 3.6)))
        self.ent_art_foh.delete(0, tk.END)
        self.ent_art_foh.insert(0, str(prof.get("tractor_front_overhang", 1.35)))
        self.ent_art_hitch.delete(0, tk.END)
        self.ent_art_hitch.insert(0, str(prof.get("kingpin_distance", 0.30)))
        self.ent_art_trail_wb.delete(0, tk.END)
        self.ent_art_trail_wb.insert(0, str(prof.get("trailer_wheelbase", 8.2)))
        self.ent_art_trail_roh.delete(0, tk.END)
        self.ent_art_trail_roh.insert(0, str(prof.get("trailer_rear_overhang", 2.8)))
        self.ent_art_trail_foh.delete(0, tk.END)
        self.ent_art_trail_foh.insert(0, str(prof.get("trailer_front_overhang", 1.0)))

        # Nạp thông số xe liền thân
        self.ent_rig_w.delete(0, tk.END)
        self.ent_rig_w.insert(0, str(prof.get("rigid_width", 2.5)))
        self.ent_rig_wb.delete(0, tk.END)
        self.ent_rig_wb.insert(0, str(prof.get("rigid_wheelbase", 5.8)))
        self.ent_rig_foh.delete(0, tk.END)
        self.ent_rig_foh.insert(0, str(prof.get("rigid_front_overhang", 1.35)))
        self.ent_rig_roh.delete(0, tk.END)
        self.ent_rig_roh.insert(0, str(prof.get("rigid_rear_overhang", prof.get("rigid_rear_length", 2.4))))

        self._on_vtype_change()

    def _save_vehicle_profile_from_ui(self):
        vtype = self.var_vtype.get()
        prof = dict(self.config_manager.vehicle_profile)

        try:
            cl = float(self.ent_clearance.get() or 1.5)
            # Articulated
            art_cab_w = float(self.ent_art_cab_w.get() or 2.5)
            art_trail_w = float(self.ent_art_trail_w.get() or 2.5)
            art_wb = float(self.ent_art_wb.get() or 3.6)
            art_foh = float(self.ent_art_foh.get() or 1.35)
            art_hitch = float(self.ent_art_hitch.get() or 0.30)
            trail_wb = float(self.ent_art_trail_wb.get() or 8.2)
            trail_roh = float(self.ent_art_trail_roh.get() or 2.8)
            trail_foh = float(self.ent_art_trail_foh.get() or 1.0)
            # Rigid
            rig_w = float(self.ent_rig_w.get() or 2.5)
            rig_wb = float(self.ent_rig_wb.get() or 5.8)
            rig_foh = float(self.ent_rig_foh.get() or 1.35)
            rig_roh = float(self.ent_rig_roh.get() or 2.4)
        except Exception:
            cl = 1.5
            art_cab_w, art_trail_w = 2.5, 2.5
            art_wb, art_foh, art_hitch = 3.6, 1.35, 0.30
            trail_wb, trail_roh, trail_foh = 8.2, 2.8, 1.0
            rig_w, rig_wb, rig_foh, rig_roh = 2.5, 5.8, 1.35, 2.4

        prof["vehicle_type"] = vtype
        prof["name"] = self.ent_vname.get().strip() or ("Xe tải liền thân / thùng cố định" if vtype == "RIGID" else "Xe đầu kéo sơ-mi rơ-moóc chuẩn")
        prof["base_clearance"] = cl

        # Lưu thông số đầu kéo
        prof["cab_width"] = art_cab_w
        prof["trailer_width"] = art_trail_w
        prof["tractor_wheelbase"] = art_wb
        prof["tractor_front_overhang"] = art_foh
        prof["tractor_front_length"] = round(art_wb + art_foh, 2)
        prof["kingpin_distance"] = art_hitch
        prof["trailer_wheelbase"] = trail_wb
        prof["trailer_rear_overhang"] = trail_roh
        prof["trailer_front_overhang"] = trail_foh
        prof["trailer_length"] = round(trail_foh + trail_wb + trail_roh, 2)

        # Lưu thông số xe liền thân
        prof["rigid_width"] = rig_w
        prof["rigid_wheelbase"] = rig_wb
        prof["rigid_front_overhang"] = rig_foh
        prof["rigid_front_length"] = round(rig_wb + rig_foh, 2)
        prof["rigid_rear_overhang"] = rig_roh
        prof["rigid_rear_length"] = rig_roh

        self.config_manager.update_vehicle_profile(prof)

    # =========================================================================
    # BƯỚC 2: HIỆU CHUẨN HOMOGRAPHY 4 CAMERA
    # =========================================================================
    def _build_step2_homography_ui(self):
        top_cam_bar = tk.Frame(self.frame_step2, bg="#242432", height=50)
        top_cam_bar.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
        top_cam_bar.pack_propagate(False)

        tk.Label(top_cam_bar, text="CHỌN GÓC CAMERA HIỆU CHUẨN:", font=("Segoe UI", 10, "bold"),
                 fg="#00e5ff", bg="#242432").pack(side=tk.LEFT, padx=15)

        self.cam_buttons = {}
        cam_info_list = [
            ("MIRROR_RIGHT", "📷 1. Hông phụ (Gương phải)"),
            ("MIRROR_LEFT", "📷 2. Hông lái (Gương trái)"),
            ("CAB_FRONT", "📷 3. Mũi xe (Cản trước)"),
            ("REAR_TRAILER", "📷 4. Đuôi xe (Lùi sau)")
        ]
        for key, text in cam_info_list:
            btn = tk.Button(top_cam_bar, text=text, font=("Segoe UI", 9, "bold"),
                            bg="#2e2e40", fg="#c0c0d0", relief="flat", padx=10, pady=5,
                            command=lambda k=key: self.select_camera(k))
            btn.pack(side=tk.LEFT, padx=6)
            self.cam_buttons[key] = btn

        paned = tk.PanedWindow(self.frame_step2, orient=tk.HORIZONTAL, bg="#1a1a24", sashwidth=6)
        paned.pack(fill=tk.BOTH, expand=True)

        left_col = tk.Frame(paned, bg="#242432", width=480)
        left_col.pack_propagate(False)
        paned.add(left_col)

        self.lbl_curr_cam_title = tk.Label(left_col, text="Camera Gương Phụ (Hông phải)",
                                           font=("Segoe UI", 12, "bold"), fg="#ffffff", bg="#242432")
        self.lbl_curr_cam_title.pack(anchor="w", padx=15, pady=(15, 2))

        self.lbl_curr_cam_desc = tk.Label(left_col, text="Mô tả góc mù...", font=("Segoe UI", 9),
                                          fg="#a0a0b0", bg="#242432", wraplength=440, justify="left")
        self.lbl_curr_cam_desc.pack(anchor="w", padx=15, pady=(0, 10))

        btn_box = tk.Frame(left_col, bg="#242432")
        btn_box.pack(fill=tk.X, padx=15, pady=5)
        tk.Button(btn_box, text="📂 Chọn Ảnh / Video", font=("Segoe UI", 9, "bold"),
                  bg="#3949ab", fg="#ffffff", relief="flat", padx=10, pady=5,
                  command=self.choose_image_dialog).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(btn_box, text="🎯 Preset Chuẩn", font=("Segoe UI", 9, "bold"),
                  bg="#00838f", fg="#ffffff", relief="flat", padx=10, pady=5,
                  command=self.load_preset_for_active_camera).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_box, text="🧹 Xóa Pixel (Chọn lại)", font=("Segoe UI", 9, "bold"),
                  bg="#e65100", fg="#ffffff", relief="flat", padx=10, pady=5,
                  command=self.clear_pixel_points).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_box, text="🔄 Reset", font=("Segoe UI", 9),
                  bg="#37474f", fg="#ffffff", relief="flat", padx=8, pady=5,
                  command=self.reset_to_default_camera).pack(side=tk.LEFT, padx=4)

        pts_frame = tk.LabelFrame(left_col, text="4 ĐIỂM TIẾP ĐẤT MỐC (PIXEL & MÉT VCS)",
                                  font=("Segoe UI", 9, "bold"), fg="#00e5ff", bg="#242432", padx=8, pady=8)
        pts_frame.pack(fill=tk.X, padx=15, pady=10)

        self.point_entries = []
        headers = ["Điểm", "u (px)", "v (px)", "X_vcs (m)", "Y_vcs (m)"]
        for c_idx, h in enumerate(headers):
            tk.Label(pts_frame, text=h, font=("Segoe UI", 8, "bold"), fg="#b0b0c0", bg="#242432").grid(row=0, column=c_idx, padx=4, pady=3)

        for i in range(4):
            lbl_p = tk.Label(pts_frame, text=f"P{i+1}", font=("Segoe UI", 9, "bold"), fg=POINT_COLORS_HEX[i], bg="#242432")
            lbl_p.grid(row=i+1, column=0, padx=4, pady=4)
            ent_u = tk.Entry(pts_frame, width=7, font=("Segoe UI", 9), bg="#181822", fg="#ffffff", insertbackground="white")
            ent_v = tk.Entry(pts_frame, width=7, font=("Segoe UI", 9), bg="#181822", fg="#ffffff", insertbackground="white")
            ent_x = tk.Entry(pts_frame, width=8, font=("Segoe UI", 9), bg="#181822", fg="#ffffff", insertbackground="white")
            ent_y = tk.Entry(pts_frame, width=8, font=("Segoe UI", 9), bg="#181822", fg="#ffffff", insertbackground="white")

            ent_u.grid(row=i+1, column=1, padx=3, pady=4)
            ent_v.grid(row=i+1, column=2, padx=3, pady=4)
            ent_x.grid(row=i+1, column=3, padx=3, pady=4)
            ent_y.grid(row=i+1, column=4, padx=3, pady=4)

            self.point_entries.append((ent_u, ent_v, ent_x, ent_y))

        self.lbl_click_status = tk.Label(left_col, text="💡 Hướng dẫn: Click lên ảnh để chọn tọa độ P1..P4",
                                         font=("Segoe UI", 9, "italic"), fg="#80d8ff", bg="#242432",
                                         wraplength=440, justify="left")
        self.lbl_click_status.pack(anchor="w", padx=15, pady=(2, 6))

        tk.Button(left_col, text="🚀 TÍNH TOÁN MA TRẬN HOMOGRAPHY", font=("Segoe UI", 11, "bold"),
                  bg="#00c853", fg="#ffffff", relief="flat", pady=8,
                  command=self.compute_homography_active_camera).pack(fill=tk.X, padx=15, pady=8)

        self.lbl_matrix_res = tk.Label(left_col, text="Chưa tính ma trận.", font=("Segoe UI", 9),
                                       fg="#ffb74d", bg="#242432", justify="left")
        self.lbl_matrix_res.pack(anchor="w", padx=15, pady=5)

        tk.Button(left_col, text="⬅️ QUAY LẠI BƯỚC 1: THÔNG SỐ XE", font=("Segoe UI", 9),
                  bg="#37474f", fg="#ffffff", relief="flat", pady=6,
                  command=lambda: self.switch_step(1)).pack(fill=tk.X, padx=15, pady=(15, 5))

        right_col = tk.Frame(paned, bg="#181820")
        paned.add(right_col)

        self.canvas = tk.Canvas(right_col, bg="#121218", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<Button-1>", self._on_canvas_click)

    def switch_step(self, step: int):
        self.current_step = step
        if step == 1:
            self.frame_step2.pack_forget()
            self.frame_step1.pack(fill=tk.BOTH, expand=True)
            self.btn_nav_step1.config(bg="#00b0ff", fg="#ffffff")
            self.btn_nav_step2.config(bg="#2d2d3d", fg="#b0b0c0")
        else:
            self._save_vehicle_profile_from_ui()
            self.frame_step1.pack_forget()
            self.frame_step2.pack(fill=tk.BOTH, expand=True)
            self.btn_nav_step1.config(bg="#2d2d3d", fg="#b0b0c0")
            self.btn_nav_step2.config(bg="#00b0ff", fg="#ffffff")
            self.select_camera(self.active_camera)

    def select_camera(self, cam_key: str):
        self.active_camera = cam_key
        for k, btn in self.cam_buttons.items():
            if k == cam_key:
                btn.config(bg="#00e5ff", fg="#000000")
            else:
                btn.config(bg="#2e2e40", fg="#c0c0d0")
        self._load_camera_to_ui(cam_key)

    def _load_camera_to_ui(self, cam_key: str):
        c_info = self.config_manager.get_camera_config(cam_key)
        self.lbl_curr_cam_title.config(text=c_info.get("name", cam_key))
        self.lbl_curr_cam_desc.config(text=c_info.get("description", ""))

        pts_px = c_info.get("points_pixel", [])
        pts_vcs = c_info.get("points_vcs_meter", [])

        for i in range(4):
            ent_u, ent_v, ent_x, ent_y = self.point_entries[i]
            ent_u.delete(0, tk.END)
            ent_v.delete(0, tk.END)
            ent_x.delete(0, tk.END)
            ent_y.delete(0, tk.END)

            if i < len(pts_px):
                ent_u.insert(0, str(pts_px[i][0]))
                ent_v.insert(0, str(pts_px[i][1]))
            if i < len(pts_vcs):
                ent_x.insert(0, str(pts_vcs[i][0]))
                ent_y.insert(0, str(pts_vcs[i][1]))

        err_m = c_info.get("reprojection_error_m", None)
        if err_m is not None:
            self.lbl_matrix_res.config(text=f"✅ Đã hiệu chuẩn! Sai số tái chiếu: {err_m:.3f} mét", fg="#00e676")
        else:
            self.lbl_matrix_res.config(text="⚠️ Chưa tính toán ma trận Homography cho camera này.", fg="#ffb74d")

        self._update_click_status()
        self.redraw_canvas()

    def _update_click_status(self):
        first_empty = -1
        for i in range(4):
            ent_u, ent_v, _, _ = self.point_entries[i]
            if not ent_u.get().strip() or not ent_v.get().strip():
                first_empty = i
                break

        if first_empty >= 0:
            self.lbl_click_status.config(
                text=f"👉 Click lên ảnh để chọn vị trí điểm P{first_empty+1} ({POINT_COLORS_HEX[first_empty]})...",
                fg="#ffea00"
            )
        else:
            self.lbl_click_status.config(
                text="✅ Đã đủ 4 điểm mốc! Bấm nút xanh để tính Homography, hoặc click lên ảnh để đo khoảng cách kiểm tra.",
                fg="#00e676"
            )

    def clear_pixel_points(self):
        """Xóa sạch tọa độ pixel để người dùng click chọn lại từ đầu mà không vướng giá trị cũ"""
        for i in range(4):
            self.point_entries[i][0].delete(0, tk.END)
            self.point_entries[i][1].delete(0, tk.END)
        self.measured_points.clear()
        self._update_click_status()
        self.redraw_canvas()

    def reset_to_default_camera(self):
        self.load_preset_for_active_camera()

    def load_preset_for_active_camera(self):
        presets = {
            "MIRROR_RIGHT": {
                "px": [[850.0, 680.0], [1200.0, 680.0], [750.0, 420.0], [1050.0, 420.0]],
                "vcs": [[1.0, -1.6], [1.0, -3.8], [-4.5, -1.6], [-4.5, -3.8]]
            },
            "MIRROR_LEFT": {
                "px": [[430.0, 680.0], [80.0, 680.0], [530.0, 420.0], [230.0, 420.0]],
                "vcs": [[1.0, 1.6], [1.0, 3.8], [-4.5, 1.6], [-4.5, 3.8]]
            },
            "CAB_FRONT": {
                "px": [[400.0, 680.0], [880.0, 680.0], [480.0, 400.0], [800.0, 400.0]],
                "vcs": [[4.5, 1.2], [4.5, -1.2], [9.0, 1.2], [9.0, -1.2]]
            },
            "REAR_TRAILER": {
                "px": [[400.0, 680.0], [880.0, 680.0], [480.0, 400.0], [800.0, 400.0]],
                "vcs": [[-12.5, 1.2], [-12.5, -1.2], [-18.0, 1.2], [-18.0, -1.2]]
            }
        }
        p = presets.get(self.active_camera)
        if p:
            for i in range(4):
                ent_u, ent_v, ent_x, ent_y = self.point_entries[i]
                ent_u.delete(0, tk.END)
                ent_v.delete(0, tk.END)
                ent_x.delete(0, tk.END)
                ent_y.delete(0, tk.END)
                ent_u.insert(0, str(p["px"][i][0]))
                ent_v.insert(0, str(p["px"][i][1]))
                ent_x.insert(0, str(p["vcs"][i][0]))
                ent_y.insert(0, str(p["vcs"][i][1]))
            self.measured_points.clear()
            self._update_click_status()
            self.redraw_canvas()

    def choose_image_dialog(self):
        f = filedialog.askopenfilename(parent=self, title="Chọn ảnh hoặc video mốc căn chỉnh",
                                       filetypes=[("Hình ảnh / Video", "*.png *.jpg *.jpeg *.mp4 *.avi *.mkv")])
        if not f:
            return

        if f.lower().endswith(('.mp4', '.avi', '.mkv')):
            cap = cv2.VideoCapture(f)
            ret, frame = cap.read()
            cap.release()
            if not ret or frame is None:
                messagebox.showerror("Lỗi", "Không thể trích xuất khung hình từ video!")
                return
            self.orig_cv_img = frame
        else:
            self.orig_cv_img = cv2.imread(f)

        if self.orig_cv_img is None:
            messagebox.showerror("Lỗi", "Không thể đọc file ảnh!")
            return

        self.orig_h, self.orig_w = self.orig_cv_img.shape[:2]
        self.redraw_canvas()

    def compute_homography_active_camera(self):
        pts_px = []
        pts_vcs = []
        try:
            for i in range(4):
                u = float(self.point_entries[i][0].get())
                v = float(self.point_entries[i][1].get())
                x = float(self.point_entries[i][2].get())
                y = float(self.point_entries[i][3].get())
                pts_px.append([u, v])
                pts_vcs.append([x, y])
        except Exception:
            messagebox.showerror("Lỗi nhập liệu", "Vui lòng nhập đầy đủ giá trị số cho cả 4 điểm!")
            return

        H, err = MultiCameraHomographyManager.compute_homography_from_points(pts_px, pts_vcs)
        if H is None:
            messagebox.showerror("Lỗi tính toán", "Không thể tìm ma trận Homography (các điểm có thể bị thẳng hàng/suy biến)!")
            return

        H_inv = np.linalg.inv(H)

        c_info = self.config_manager.get_camera_config(self.active_camera)
        c_info["is_calibrated"] = True
        c_info["reprojection_error_m"] = err
        c_info["points_pixel"] = pts_px
        c_info["points_vcs_meter"] = pts_vcs
        c_info["homography_matrix_pixel_to_vcs"] = H.tolist()
        c_info["homography_matrix_vcs_to_pixel"] = H_inv.tolist()
        self.config_manager.update_camera_config(self.active_camera, c_info)

        self.homo_manager.H_matrices[self.active_camera] = H
        self.homo_manager.H_inv_matrices[self.active_camera] = H_inv

        self.lbl_matrix_res.config(text=f"✅ Tính thành công! Sai số tái chiếu: {err:.3f} mét", fg="#00e676")
        messagebox.showinfo("Thành công", f"Đã tính ma trận Homography cho {self.active_camera} thành công!\nSai số tái chiếu: {err:.3f} mét")
        self.redraw_canvas()

    def save_all_and_notify(self):
        self._save_vehicle_profile_from_ui()
        self.config_manager.save()
        messagebox.showinfo("BlindGuard AI", "ĐÃ LƯU TOÀN BỘ CẤU HÌNH XE VÀ 4 CAMERA VÀO SYSTEM_CONFIG.JSON THÀNH CÔNG!")

    def _on_canvas_resize(self, event):
        self.redraw_canvas()

    def _on_canvas_click(self, event):
        if self.orig_cv_img is None:
            return

        u = (event.x - self.offset_x) / max(0.001, self.scale)
        v = (event.y - self.offset_y) / max(0.001, self.scale)

        if not (0 <= u < self.orig_w and 0 <= v < self.orig_h):
            return

        filled = False
        for i in range(4):
            ent_u, ent_v, _, _ = self.point_entries[i]
            if not ent_u.get().strip() or not ent_v.get().strip():
                ent_u.delete(0, tk.END)
                ent_v.delete(0, tk.END)
                ent_u.insert(0, f"{u:.1f}")
                ent_v.insert(0, f"{v:.1f}")
                filled = True
                break

        if not filled:
            self.homo_manager.set_active_camera(self.active_camera)
            world = self.homo_manager.pixel_to_world(u, v)
            if world is not None:
                x_vcs, y_vcs, d = world
                self.measured_points.append((u, v, x_vcs, y_vcs, d))
                if len(self.measured_points) > 5:
                    self.measured_points.pop(0)

        self._update_click_status()
        self.redraw_canvas()

    def redraw_canvas(self):
        self.canvas.delete("all")
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 50 or ch < 50:
            return

        if self.orig_cv_img is None:
            self.canvas.create_text(cw // 2, ch // 2, text="Chưa có ảnh. Vui lòng bấm [📂 Chọn Ảnh Camera / Chụp Frame Video].",
                                    fill="#707085", font=("Segoe UI", 12))
            return

        scale = min(cw / self.orig_w, ch / self.orig_h)
        disp_w = int(self.orig_w * scale)
        disp_h = int(self.orig_h * scale)
        off_x = (cw - disp_w) // 2
        off_y = (ch - disp_h) // 2

        self.scale = scale
        self.offset_x = off_x
        self.offset_y = off_y

        img_bgr = self.orig_cv_img.copy()

        for i in range(4):
            try:
                u = float(self.point_entries[i][0].get())
                v = float(self.point_entries[i][1].get())
                pt = (int(u), int(v))
                col = POINT_COLORS_BGR[i]
                cv2.circle(img_bgr, pt, 6, col, -1)
                cv2.circle(img_bgr, pt, 8, (255, 255, 255), 2)
                cv2.putText(img_bgr, f"P{i+1}", (pt[0] + 10, pt[1] - 5), cv2.FONT_HERSHEY_DUPLEX, 0.7, col, 2)
            except Exception:
                pass

        for (u, v, x, y, d) in self.measured_points:
            pt = (int(u), int(v))
            cv2.circle(img_bgr, pt, 5, (0, 255, 255), -1)
            cv2.putText(img_bgr, f"({x:+.1f}m, {y:+.1f}m)", (pt[0] + 8, pt[1] + 15),
                        cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 255, 255), 1)

        img_rgb = cv2.cvtColor(cv2.resize(img_bgr, (disp_w, disp_h)), cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        self.current_tk_img = ImageTk.PhotoImage(pil_img)
        self.canvas.create_image(off_x, off_y, anchor=tk.NW, image=self.current_tk_img)


if __name__ == "__main__":
    app = BlindGuardSystemConfiguratorApp()
    app.mainloop()
