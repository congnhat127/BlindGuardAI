"""
Module: run_bsri_simulator_gui.py
Vị trí: BlindGuard_App/run_bsri_simulator_gui.py
Mô tả: Ứng dụng Mô phỏng & Thẩm định Trực quan Chỉ số Rủi ro Điểm mù BSRI (Interactive BSRI & DHZ Visual Simulator).
Chức năng chính:
  1. Cấu hình thông số hình học xe chủ (ARTICULATED xe đầu kéo hoặc RIGID xe tải liền thân).
  2. Dựng hình bao thân xe (Vehicle Footprint) và Vùng Nguy Hiểm Động (Dynamic Hazard Zone - DHZ) chuẩn VCS ISO 8855.
  3. Điều khiển linh hoạt vận tốc, góc bẻ lái vô lăng, yaw rate, góc gập rơ-moóc, xi-nhan.
  4. Thêm, sửa, xóa và KÉO THẢ (Drag & Drop) trực tiếp các đối tượng VRU (người, xe máy, xe đạp...) trên bản đồ 2D.
  5. Tính toán Chỉ số BSRI theo thời gian thực và hiển thị Bảng Giải thích Trí tuệ Nhân tạo (Explainable AI - XAI).
"""

import sys
import math
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
from shapely.geometry import Point, Polygon

# Đảm bảo import được module từ core
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

try:
    from core.config_loader import SystemConfigManager
    from core.bsri_calculator import BSRICalculator
    from core.risk_models import (
        RiskLevel, BlindSpotZone, EgoVehicleState,
        TrackedObstacle, BSRIResult, VehicleType
    )
except ImportError:
    from BlindGuard_App.core.config_loader import SystemConfigManager
    from BlindGuard_App.core.bsri_calculator import BSRICalculator
    from BlindGuard_App.core.risk_models import (
        RiskLevel, BlindSpotZone, EgoVehicleState,
        TrackedObstacle, BSRIResult, VehicleType
    )


class BSRISimulatorApp(tk.Tk):
    """Giao diện mô phỏng tương tác toán học BSRI & DHZ"""

    # Bảng màu giao diện High-Tech Cyber Dark
    BG_DARK = "#12121a"
    BG_PANEL = "#1b1b26"
    BG_CARD = "#232334"
    BG_INPUT = "#14141e"
    FG_TEXT = "#ffffff"
    FG_MUTED = "#8e8ea6"
    ACCENT_CYAN = "#00e5ff"
    ACCENT_GREEN = "#00e676"
    ACCENT_YELLOW = "#ffd600"
    ACCENT_ORANGE = "#ff9100"
    ACCENT_RED = "#ff1744"

    # Danh mục các loại đối tượng VRU và phương tiện
    AVAILABLE_CLASSES = [
        ("motorcycle", "🏍️ Xe máy (VRU)"),
        ("person", "🚶 Người đi bộ (VRU)"),
        ("bicycle", "🚲 Xe đạp (VRU)"),
        ("xe_keo", "🛺 Xe đẩy / Xe kéo (VRU)"),
        ("xich_lo", "🚲 Xích lô (VRU)"),
        ("car", "🚗 Ô tô con (Enclosed)"),
        ("truck", "🚚 Xe tải khác (Heavy)")
    ]

    def __init__(self):
        super().__init__()
        self.title("🛡️ BLINDGUARD AI — BSRI & DHZ VISUAL SIMULATOR (ADAS RISK TESTBENCH)")
        
        # Kích thước cửa sổ
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        ww, wh = min(1500, sw - 40), min(920, sh - 60)
        self.geometry(f"{ww}x{wh}+{(sw - ww)//2}+{max(10, (sh - wh - 30)//2)}")
        self.minsize(1200, 750)
        self.configure(bg=self.BG_DARK)

        # Quản lý cấu hình & Tính toán BSRI
        self.config_manager = SystemConfigManager()
        self.v_profile = dict(self.config_manager.vehicle_profile)
        self.bsri_calc = BSRICalculator(**self.v_profile)

        # Trạng thái xe chủ
        self.ego_state = EgoVehicleState(
            speed_mps=4.17,        # ~15 km/h
            yaw_rate_rad_s=0.15,   # đang ôm cua nhẹ
            steering_angle_deg=12.0,
            accel_y_mps2=-0.6,
            trailer_gamma_rad=0.08,
            gear="D"
        )

        # Danh sách đối tượng chướng ngại vật mô phỏng
        self.obstacles: List[TrackedObstacle] = []
        self.selected_obs_id: Optional[int] = None
        self.dragging_obs_id: Optional[int] = None
        self.drag_offset = (0.0, 0.0)

        # Thông số Canvas VCS
        self.scale_pixels_per_meter = 22.0   # 1 mét = 22 pixel
        self.origin_x = 0
        self.origin_y = 0
        self.show_zones = tk.BooleanVar(value=True)
        self.show_dhz = tk.BooleanVar(value=True)
        self.show_grid = tk.BooleanVar(value=True)
        self.is_simulating = False

        # Dựng giao diện trước
        self._build_header()
        self._build_main_layout()

        # Khởi tạo kịch bản mẫu ban đầu
        self._init_default_scenario()

        # Cập nhật tính toán & Vẽ lần đầu
        self.after(100, self._on_profile_or_dynamics_change)

    # =========================================================================
    # DỰNG GIAO DIỆN CHÍNH
    # =========================================================================
    def _build_header(self):
        header = tk.Frame(self, bg=self.BG_DARK, height=52)
        header.pack(side=tk.TOP, fill=tk.X)
        header.pack_propagate(False)

        lbl_logo = tk.Label(header, text="🛡️ BLINDGUARD AI — TRÌNH MÔ PHỎNG & THẨM ĐỊNH RỦI RO BSRI & DHZ",
                            font=("Segoe UI", 13, "bold"), fg=self.ACCENT_CYAN, bg=self.BG_DARK)
        lbl_logo.pack(side=tk.LEFT, padx=18, pady=10)

        lbl_sub = tk.Label(header, text="Hệ tọa độ xe VCS ISO 8855 | Mô hình một vết Ellis 1969 | Đa giác DHZ động",
                           font=("Segoe UI", 9, "italic"), fg=self.FG_MUTED, bg=self.BG_DARK)
        lbl_sub.pack(side=tk.LEFT, padx=10, pady=12)

        # Các tùy chọn hiển thị
        chk_grid = tk.Checkbutton(header, text="Lưới tọa độ", variable=self.show_grid,
                                  font=("Segoe UI", 9), fg=self.FG_TEXT, bg=self.BG_DARK,
                                  selectcolor=self.BG_CARD, activebackground=self.BG_DARK,
                                  command=self.redraw_canvas)
        chk_grid.pack(side=tk.RIGHT, padx=12)

        chk_zone = tk.Checkbutton(header, text="Vùng điểm mù quang học", variable=self.show_zones,
                                  font=("Segoe UI", 9), fg=self.FG_TEXT, bg=self.BG_DARK,
                                  selectcolor=self.BG_CARD, activebackground=self.BG_DARK,
                                  command=self.redraw_canvas)
        chk_zone.pack(side=tk.RIGHT, padx=6)

        chk_dhz = tk.Checkbutton(header, text="Đa giác DHZ động", variable=self.show_dhz,
                                 font=("Segoe UI", 9), fg=self.ACCENT_YELLOW, bg=self.BG_DARK,
                                 selectcolor=self.BG_CARD, activebackground=self.BG_DARK,
                                 command=self.redraw_canvas)
        chk_dhz.pack(side=tk.RIGHT, padx=6)

    def _build_main_layout(self):
        main_box = tk.Frame(self, bg=self.BG_DARK)
        main_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # CỘT TRÁI (340px): Cấu hình Xe & Động học Xe Chủ
        left_panel = tk.Frame(main_box, bg=self.BG_PANEL, width=350)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        left_panel.pack_propagate(False)
        self._build_left_panel(left_panel)

        # CỘT PHẢI (380px): Quản lý Vật thể & Bảng XAI BSRI
        right_panel = tk.Frame(main_box, bg=self.BG_PANEL, width=390)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
        right_panel.pack_propagate(False)
        self._build_right_panel(right_panel)

        # KHU VỰC GIỮA: Canvas hiển thị 2D VCS Map
        center_panel = tk.Frame(main_box, bg=self.BG_CARD, bd=1, relief="solid")
        center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_center_canvas(center_panel)

    # -------------------------------------------------------------------------
    # CỘT TRÁI: CẤU HÌNH XE & ĐIỀU KHIỂN ĐỘNG LỰC HỌC
    # -------------------------------------------------------------------------
    def _build_left_panel(self, parent):
        # 1. Khung cấu hình xe
        box_vehicle = tk.LabelFrame(parent, text=" 🚚 1. CẤU HÌNH HÌNH HỌC THÂN XE ",
                                    font=("Segoe UI", 9, "bold"), fg=self.ACCENT_CYAN,
                                    bg=self.BG_PANEL, padx=10, pady=8)
        box_vehicle.pack(fill=tk.X, padx=8, pady=(8, 4))

        # Chọn loại xe
        f_type = tk.Frame(box_vehicle, bg=self.BG_PANEL)
        f_type.pack(fill=tk.X, pady=(0, 6))
        self.var_vtype = tk.StringVar(value=self.v_profile.get("vehicle_type", "ARTICULATED"))
        tk.Radiobutton(f_type, text="Đầu Kéo Rơ-moóc (ART)", variable=self.var_vtype,
                       value="ARTICULATED", font=("Segoe UI", 9, "bold"), fg=self.FG_TEXT,
                       bg=self.BG_PANEL, selectcolor=self.BG_CARD,
                       command=self._on_vehicle_type_toggle).pack(side=tk.LEFT, padx=(0, 8))
        tk.Radiobutton(f_type, text="Xe Tải Liền Thân (RIGID)", variable=self.var_vtype,
                       value="RIGID", font=("Segoe UI", 9, "bold"), fg=self.FG_TEXT,
                       bg=self.BG_PANEL, selectcolor=self.BG_CARD,
                       command=self._on_vehicle_type_toggle).pack(side=tk.LEFT)

        # Khung thông số xe đầu kéo
        self.f_art_inputs = tk.Frame(box_vehicle, bg=self.BG_PANEL)
        self.f_art_inputs.pack(fill=tk.X)

        self.ent_art_lf = self._create_param_row(self.f_art_inputs, "Wheelbase đầu kéo L_f (m):", "3.6", 0)
        self.ent_art_foh = self._create_param_row(self.f_art_inputs, "Nhô cản trước L_foh (m):", "1.35", 1)
        self.ent_art_hitch = self._create_param_row(self.f_art_inputs, "Vị trí Kingpin d_hitch (m):", "0.30", 2)
        self.ent_art_wb_trail = self._create_param_row(self.f_art_inputs, "Wheelbase rơ-moóc L_wb (m):", "8.2", 3, highlight=True)
        self.ent_art_roh_trail = self._create_param_row(self.f_art_inputs, "Nhô cản sau rơ-moóc L_roh (m):", "2.8", 4, highlight=True)
        self.ent_art_wc = self._create_param_row(self.f_art_inputs, "Chiều rộng Cabin / Thùng (m):", "2.5", 5)

        # Khung thông số xe liền thân
        self.f_rig_inputs = tk.Frame(box_vehicle, bg=self.BG_PANEL)
        self.ent_rig_wb = self._create_param_row(self.f_rig_inputs, "Wheelbase xe tải L_wb (m):", "5.8", 0)
        self.ent_rig_foh = self._create_param_row(self.f_rig_inputs, "Nhô cản trước L_foh (m):", "1.35", 1)
        self.ent_rig_roh = self._create_param_row(self.f_rig_inputs, "Nhô cản sau L_roh (m):", "2.4", 2, highlight=True)
        self.ent_rig_w = self._create_param_row(self.f_rig_inputs, "Chiều rộng xe W_rigid (m):", "2.5", 3)

        # Tóm tắt kích thước tự tính
        self.lbl_v_summary = tk.Label(box_vehicle, text="", font=("Segoe UI", 8),
                                      fg=self.ACCENT_GREEN, bg=self.BG_PANEL, justify="left")
        self.lbl_v_summary.pack(fill=tk.X, pady=(6, 2))

        btn_apply_prof = tk.Button(box_vehicle, text="ÁP DỤNG CẤU HÌNH XE", font=("Segoe UI", 9, "bold"),
                                   bg="#0277bd", fg="#ffffff", relief="flat", padx=10, pady=4,
                                   command=self._on_apply_vehicle_profile)
        btn_apply_prof.pack(fill=tk.X, pady=(4, 0))

        # 2. Khung điều khiển động lực học xe chủ
        box_dynamics = tk.LabelFrame(parent, text=" 🕹️ 2. ĐỘNG LỰC HỌC XE CHỦ (EGO DYNAMICS) ",
                                     font=("Segoe UI", 9, "bold"), fg=self.ACCENT_YELLOW,
                                     bg=self.BG_PANEL, padx=10, pady=8)
        box_dynamics.pack(fill=tk.X, padx=8, pady=4)

        # Vận tốc v
        f_spd = tk.Frame(box_dynamics, bg=self.BG_PANEL)
        f_spd.pack(fill=tk.X, pady=2)
        self.lbl_speed = tk.Label(f_spd, text="Vận tốc: 15.0 km/h (4.2 m/s)", font=("Segoe UI", 9), fg=self.FG_TEXT, bg=self.BG_PANEL)
        self.lbl_speed.pack(anchor="w")
        self.scale_speed = tk.Scale(f_spd, from_=-15, to=60, orient=tk.HORIZONTAL,
                                    bg=self.BG_PANEL, fg=self.FG_TEXT, highlightthickness=0,
                                    troughcolor=self.BG_CARD, command=self._on_speed_slide)
        self.scale_speed.set(15)
        self.scale_speed.pack(fill=tk.X)

        # Góc bẻ lái vô lăng delta
        f_steer = tk.Frame(box_dynamics, bg=self.BG_PANEL)
        f_steer.pack(fill=tk.X, pady=2)
        self.lbl_steer = tk.Label(f_steer, text="Góc lái: 0.0° (ĐI THẲNG) | Yaw: +0.00 rad/s", font=("Segoe UI", 9, "bold"), fg=self.FG_TEXT, bg=self.BG_PANEL)
        self.lbl_steer.pack(anchor="w")
        tk.Label(f_steer, text="⬅️ Kéo Trái: RẼ TRÁI  |  Kéo Phải: RẼ PHẢI ➡️", font=("Segoe UI", 7, "italic"), fg="#90a4ae", bg=self.BG_PANEL).pack(anchor="w")
        self.scale_steer = tk.Scale(f_steer, from_=-35, to=35, orient=tk.HORIZONTAL,
                                    bg=self.BG_PANEL, fg=self.FG_TEXT, highlightthickness=0,
                                    troughcolor=self.BG_CARD, command=self._on_steer_slide)
        self.scale_steer.set(0)
        self.scale_steer.pack(fill=tk.X)

        # Góc gập rơ-moóc gamma (chỉ dành cho ARTICULATED)
        self.f_gamma_box = tk.Frame(box_dynamics, bg=self.BG_PANEL)
        self.f_gamma_box.pack(fill=tk.X, pady=2)
        self.lbl_gamma = tk.Label(self.f_gamma_box, text="Góc gập rơ-moóc gamma: +5.0°", font=("Segoe UI", 9), fg=self.FG_TEXT, bg=self.BG_PANEL)
        self.lbl_gamma.pack(anchor="w")
        self.scale_gamma = tk.Scale(self.f_gamma_box, from_=-45, to=45, orient=tk.HORIZONTAL,
                                    bg=self.BG_PANEL, fg=self.FG_TEXT, highlightthickness=0,
                                    troughcolor=self.BG_CARD, command=self._on_gamma_slide)
        self.scale_gamma.set(5)
        self.scale_gamma.pack(fill=tk.X)

        # Gia tốc ngang a_y từ cảm biến IMU (quyết định khoảng đệm động C_dynamic)
        f_ay = tk.Frame(box_dynamics, bg=self.BG_PANEL)
        f_ay.pack(fill=tk.X, pady=2)
        self.lbl_ay = tk.Label(f_ay, text="Gia tốc ngang IMU a_y: +0.00 m/s² (C_dyn: 0.00m)",
                               font=("Segoe UI", 9), fg=self.FG_TEXT, bg=self.BG_PANEL)
        self.lbl_ay.pack(anchor="w")
        self.scale_ay = tk.Scale(f_ay, from_=-3.0, to=3.0, resolution=0.1, orient=tk.HORIZONTAL,
                                 bg=self.BG_PANEL, fg=self.FG_TEXT, highlightthickness=0,
                                 troughcolor=self.BG_CARD, command=self._on_ay_slide)
        self.scale_ay.set(0.0)
        self.scale_ay.pack(fill=tk.X)

        # Trạng thái hành vi xe nhận diện tự động từ IMU & GPS (KHÔNG DÙNG XI-NHAN)
        f_beh = tk.Frame(box_dynamics, bg="#14141e", padx=6, pady=4)
        f_beh.pack(fill=tk.X, pady=(4, 2))
        self.lbl_imu_behavior = tk.Label(f_beh, text="📡 Trạng thái: [IMU: XE ĐANG ÔM CUA PHẢI ➡️]",
                                         font=("Segoe UI", 9, "bold"), fg=self.ACCENT_YELLOW, bg="#14141e")
        self.lbl_imu_behavior.pack(anchor="w")
        tk.Label(f_beh, text="ℹ️ Nhận biết 100% qua IMU/GPS (Không can thiệp CAN bus/Xi-nhan)",
                 font=("Segoe UI", 7, "italic"), fg="#78909c", bg="#14141e").pack(anchor="w")

        # Nút Chạy mô phỏng / Dừng
        f_sim_btn = tk.Frame(parent, bg=self.BG_PANEL)
        f_sim_btn.pack(fill=tk.X, padx=8, pady=8)
        self.btn_play = tk.Button(f_sim_btn, text="▶️ BẬT MÔ PHỎNG ĐỘNG LỰC HỌC", font=("Segoe UI", 10, "bold"),
                                  bg=self.ACCENT_GREEN, fg="#000000", relief="flat", pady=6,
                                  command=self._toggle_simulation)
        self.btn_play.pack(fill=tk.X)

    def _create_param_row(self, parent, label_text, default_val, row_idx, highlight=False):
        col_lbl = self.ACCENT_YELLOW if highlight else self.FG_TEXT
        tk.Label(parent, text=label_text, font=("Segoe UI", 8, "bold" if highlight else "normal"),
                 fg=col_lbl, bg=self.BG_PANEL).grid(row=row_idx, column=0, sticky="w", pady=2)
        ent = tk.Entry(parent, font=("Segoe UI", 8), width=7, bg=self.BG_INPUT, fg="#ffffff", insertbackground="white")
        ent.insert(0, default_val)
        ent.grid(row=row_idx, column=1, sticky="e", pady=2, padx=(6, 0))
        return ent

    # -------------------------------------------------------------------------
    # KHU VỰC GIỮA: 2D VCS CANVAS MAP
    # -------------------------------------------------------------------------
    def _build_center_canvas(self, parent):
        # Thanh chỉ dẫn thao tác chuột
        info_bar = tk.Frame(parent, bg=self.BG_DARK, height=28)
        info_bar.pack(side=tk.TOP, fill=tk.X)
        info_bar.pack_propagate(False)

        tk.Label(info_bar, text="🖱️ BẤM CHUỘT TRÁI / KÉO THẢ: Di chuyển vật thể | CHUỘT PHẢI: Thêm nhanh vật thể | LĂN CHUỘT: Phóng to/Thu nhỏ",
                 font=("Segoe UI", 8, "bold"), fg=self.ACCENT_CYAN, bg=self.BG_DARK).pack(side=tk.LEFT, padx=12, pady=4)

        self.lbl_cursor_pos = tk.Label(info_bar, text="Tọa độ VCS: X = 0.0m, Y = 0.0m",
                                       font=("Segoe UI", 8), fg="#b0bec5", bg=self.BG_DARK)
        self.lbl_cursor_pos.pack(side=tk.RIGHT, padx=12, pady=4)

        # Canvas vẽ 2D
        self.canvas = tk.Canvas(parent, bg="#0d0d15", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Bắt sự kiện chuột trên Canvas
        self.canvas.bind("<Configure>", lambda e: self.redraw_canvas())
        self.canvas.bind("<Motion>", self._on_canvas_motion)
        self.canvas.bind("<Button-1>", self._on_canvas_left_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Button-3>", self._on_canvas_right_click)
        self.canvas.bind("<MouseWheel>", self._on_canvas_zoom)

    # -------------------------------------------------------------------------
    # CỘT PHẢI: QUẢN LÝ VẬT THỂ & BẢNG XAI BSRI
    # -------------------------------------------------------------------------
    def _build_right_panel(self, parent):
        # 1. Kịch bản mẫu (1-Click Presets)
        box_presets = tk.LabelFrame(parent, text=" 🎯 KỊCH BẢN THỬ NGHIỆM ĐIỂM NÓNG (PRESETS) ",
                                    font=("Segoe UI", 9, "bold"), fg=self.ACCENT_CYAN,
                                    bg=self.BG_PANEL, padx=8, pady=6)
        box_presets.pack(fill=tk.X, padx=8, pady=(8, 4))

        presets = [
            ("1. Xe máy chui bụng cua phải (Inswing Phải)", self._load_scenario_inswing),
            ("2. Xe máy chui bụng cua trái (Inswing Trái)", self._load_scenario_inswing_left),
            ("3. Người đi bộ sát cản trước (MOIS R159)", self._load_scenario_front_mois),
            ("4. Xe máy bị văng đuôi rơ-moóc (Tail-Swing)", self._load_scenario_tailswing),
            ("5. Người đứng sau xe đang lùi (Rear R158)", self._load_scenario_rear_backing),
            ("6. Xe máy chạy song song an toàn (Safe 3m)", self._load_scenario_safe_parallel),
        ]
        for title, func in presets:
            btn = tk.Button(box_presets, text=title, font=("Segoe UI", 8), bg=self.BG_CARD,
                            fg=self.FG_TEXT, activebackground="#2c2c40", relief="flat",
                            anchor="w", padx=6, pady=2, command=func)
            btn.pack(fill=tk.X, pady=1)

        # 2. Thêm vật thể & Điều khiển Vận tốc / Hướng di chuyển
        box_add = tk.LabelFrame(parent, text=" ➕ THÊM & ĐIỀU KHIỂN CHUYỂN ĐỘNG VẬT THỂ ",
                                font=("Segoe UI", 9, "bold"), fg=self.ACCENT_GREEN,
                                bg=self.BG_PANEL, padx=8, pady=6)
        box_add.pack(fill=tk.X, padx=8, pady=4)

        # Hàng 1: Loại & Tọa độ X, Y
        f_inputs = tk.Frame(box_add, bg=self.BG_PANEL)
        f_inputs.pack(fill=tk.X, pady=(0, 4))

        tk.Label(f_inputs, text="Loại:", font=("Segoe UI", 8), fg=self.FG_TEXT, bg=self.BG_PANEL).grid(row=0, column=0, sticky="w", pady=2)
        self.cbo_class = ttk.Combobox(f_inputs, values=[c[0] for c in self.AVAILABLE_CLASSES], width=11, state="readonly")
        self.cbo_class.set("motorcycle")
        self.cbo_class.grid(row=0, column=1, sticky="w", pady=2)

        tk.Label(f_inputs, text="X (m):", font=("Segoe UI", 8), fg=self.FG_TEXT, bg=self.BG_PANEL).grid(row=0, column=2, sticky="e", padx=(6, 2), pady=2)
        self.ent_obs_x = tk.Entry(f_inputs, font=("Segoe UI", 8), width=5, bg=self.BG_INPUT, fg="#ffffff", insertbackground="white")
        self.ent_obs_x.insert(0, "2.0")
        self.ent_obs_x.grid(row=0, column=3, sticky="w", pady=2)

        tk.Label(f_inputs, text="Y (m):", font=("Segoe UI", 8), fg=self.FG_TEXT, bg=self.BG_PANEL).grid(row=1, column=0, sticky="w", pady=2)
        self.ent_obs_y = tk.Entry(f_inputs, font=("Segoe UI", 8), width=11, bg=self.BG_INPUT, fg="#ffffff", insertbackground="white")
        self.ent_obs_y.insert(0, "-2.2")
        self.ent_obs_y.grid(row=1, column=1, sticky="w", pady=2)

        btn_set_xy = tk.Button(f_inputs, text="Đặt XY", font=("Segoe UI", 7, "bold"),
                               bg="#37474f", fg="#ffffff", relief="flat", padx=4, pady=1,
                               command=self._apply_manual_obs_xy)
        btn_set_xy.grid(row=1, column=2, columnspan=2, sticky="ew", padx=(6, 0), pady=2)

        # Hàng 2: Thanh trượt Tốc độ vật thể v_obs
        f_obs_spd = tk.Frame(box_add, bg=self.BG_PANEL)
        f_obs_spd.pack(fill=tk.X, pady=(2, 2))
        self.lbl_obs_spd = tk.Label(f_obs_spd, text="Tốc độ vật thể: 0.0 km/h (0.0 m/s)",
                                    font=("Segoe UI", 8, "bold"), fg=self.ACCENT_CYAN, bg=self.BG_PANEL)
        self.lbl_obs_spd.pack(anchor="w")
        self.scale_obs_spd = tk.Scale(f_obs_spd, from_=0, to=50, orient=tk.HORIZONTAL,
                                      bg=self.BG_PANEL, fg=self.FG_TEXT, highlightthickness=0,
                                      troughcolor=self.BG_CARD, command=self._on_obs_speed_slide)
        self.scale_obs_spd.set(0)
        self.scale_obs_spd.pack(fill=tk.X)

        # Hàng 3: Thanh trượt Hướng di chuyển (Heading Angle θ)
        f_obs_heading = tk.Frame(box_add, bg=self.BG_PANEL)
        f_obs_heading.pack(fill=tk.X, pady=(2, 2))
        self.lbl_obs_heading = tk.Label(f_obs_heading, text="Góc hướng θ: 0° [⬆️ Tiến cùng chiều +X]",
                                        font=("Segoe UI", 8, "bold"), fg=self.ACCENT_YELLOW, bg=self.BG_PANEL)
        self.lbl_obs_heading.pack(anchor="w")
        self.scale_obs_heading = tk.Scale(f_obs_heading, from_=0, to=359, orient=tk.HORIZONTAL,
                                          bg=self.BG_PANEL, fg=self.FG_TEXT, highlightthickness=0,
                                          troughcolor=self.BG_CARD, command=self._on_obs_heading_slide)
        self.scale_obs_heading.set(0)
        self.scale_obs_heading.pack(fill=tk.X)

        # Hàng 4: 4 Nút chọn nhanh hướng di chuyển
        f_quick_dir = tk.Frame(box_add, bg=self.BG_PANEL)
        f_quick_dir.pack(fill=tk.X, pady=(2, 4))
        tk.Button(f_quick_dir, text="⬆️ 0° Tiến", font=("Segoe UI", 7), bg=self.BG_CARD, fg=self.FG_TEXT,
                  relief="flat", pady=2, command=lambda: self._set_obs_quick_heading(0)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        tk.Button(f_quick_dir, text="⬅️ 90° Trái", font=("Segoe UI", 7), bg=self.BG_CARD, fg=self.FG_TEXT,
                  relief="flat", pady=2, command=lambda: self._set_obs_quick_heading(90)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        tk.Button(f_quick_dir, text="⬇️ 180° Ngược", font=("Segoe UI", 7), bg=self.BG_CARD, fg=self.FG_TEXT,
                  relief="flat", pady=2, command=lambda: self._set_obs_quick_heading(180)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        tk.Button(f_quick_dir, text="➡️ 270° Phải", font=("Segoe UI", 7), bg=self.BG_CARD, fg=self.FG_TEXT,
                  relief="flat", pady=2, command=lambda: self._set_obs_quick_heading(270)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        # Hàng 5: Nút thao tác Thêm / Xóa
        f_act_btn = tk.Frame(box_add, bg=self.BG_PANEL)
        f_act_btn.pack(fill=tk.X, pady=(4, 0))
        btn_add = tk.Button(f_act_btn, text="➕ Thêm mới", font=("Segoe UI", 8, "bold"),
                            bg=self.ACCENT_GREEN, fg="#000000", relief="flat", padx=8, pady=3,
                            command=self._add_obstacle_manual)
        btn_add.pack(side=tk.LEFT, padx=(0, 4))

        btn_del = tk.Button(f_act_btn, text="🗑️ Xóa chọn", font=("Segoe UI", 8),
                            bg="#d32f2f", fg="#ffffff", relief="flat", padx=6, pady=3,
                            command=self._delete_selected_obstacle)
        btn_del.pack(side=tk.LEFT, padx=4)

        btn_clear = tk.Button(f_act_btn, text="🧹 Xóa hết", font=("Segoe UI", 8),
                              bg="#455a64", fg="#ffffff", relief="flat", padx=6, pady=3,
                              command=self._clear_all_obstacles)
        btn_clear.pack(side=tk.RIGHT)

        # 3. Bảng phân tích chi tiết BSRI XAI (Explainable AI)
        box_xai = tk.LabelFrame(parent, text=" 📊 GIẢI TRÌNH CÔNG THỨC BSRI (EXPLAINABLE AI) ",
                                font=("Segoe UI", 9, "bold"), fg=self.ACCENT_YELLOW,
                                bg=self.BG_PANEL, padx=8, pady=6)
        box_xai.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))

        self.txt_xai = tk.Text(box_xai, font=("Consolas", 8), bg=self.BG_CARD, fg="#e0e0e0",
                               relief="flat", wrap=tk.WORD, height=14)
        self.txt_xai.pack(fill=tk.BOTH, expand=True)

    # =========================================================================
    # KỊCH BẢN THỰC TẾ PRESET
    # =========================================================================
    def _init_default_scenario(self):
        """Khởi tạo kịch bản mặc định: Xe máy ở góc bụng cua rơ-moóc bên phải"""
        self._load_scenario_inswing()

    def _apply_scenario_dynamics(self, speed_kmh: float, steer_deg: float, ay: float, gamma_deg: Optional[float] = None):
        """Đồng bộ đầy đủ trạng thái động học xe từ thanh trượt khi nạp kịch bản"""
        self.scale_speed.set(speed_kmh)
        self._on_speed_slide(speed_kmh)
        self.scale_steer.set(steer_deg)
        self._on_steer_slide(steer_deg)
        self.scale_ay.set(ay)
        self._on_ay_slide(ay)
        if gamma_deg is not None:
            self.scale_gamma.set(gamma_deg)
            self._on_gamma_slide(gamma_deg)

    def _load_scenario_inswing(self):
        """Kịch bản 1: Bụng cua rơ-moóc bên phải chém vào xe máy khi rẽ phải"""
        self.obstacles = [
            TrackedObstacle(
                track_id=1,
                class_name="motorcycle",
                confidence=0.94,
                bbox_xyxy=(0, 0, 0, 0),
                vcs_x=-2.5,
                vcs_y=-2.3,
                vel_x=0.0,
                vel_y=0.0
            )
        ]
        self.selected_obs_id = 1
        self._apply_scenario_dynamics(speed_kmh=15, steer_deg=16, ay=-0.8)
        self._sync_obs_controls_from_selected(self.obstacles[0])
        self._on_profile_or_dynamics_change()

    def _load_scenario_inswing_left(self):
        """Kịch bản 2: Bụng cua rơ-moóc bên trái chém vào xe máy khi rẽ trái"""
        self.obstacles = [
            TrackedObstacle(
                track_id=1,
                class_name="motorcycle",
                confidence=0.94,
                bbox_xyxy=(0, 0, 0, 0),
                vcs_x=-2.5,
                vcs_y=2.3,
                vel_x=0.0,
                vel_y=0.0
            )
        ]
        self.selected_obs_id = 1
        self._apply_scenario_dynamics(speed_kmh=15, steer_deg=-16, ay=0.8)
        self._sync_obs_controls_from_selected(self.obstacles[0])
        self._on_profile_or_dynamics_change()

    def _load_scenario_front_mois(self):
        """Kịch bản 3: Người đi bộ băng cắt sát cản trước (MOIS R159) khi xe dừng/khởi hành"""
        x_front = 5.2 if self.var_vtype.get() == "ARTICULATED" else 7.4
        self.obstacles = [
            TrackedObstacle(
                track_id=2,
                class_name="person",
                confidence=0.91,
                bbox_xyxy=(0, 0, 0, 0),
                vcs_x=x_front,
                vcs_y=-0.3,
                vel_x=0.0,
                vel_y=0.8
            )
        ]
        self.selected_obs_id = 2
        self._apply_scenario_dynamics(speed_kmh=0, steer_deg=0, ay=0.0, gamma_deg=0.0)
        self._sync_obs_controls_from_selected(self.obstacles[0])
        self._on_profile_or_dynamics_change()

    def _load_scenario_tailswing(self):
        """Kịch bản 4: Đuôi rơ-moóc văng cản sau quét vào xe máy khi rẽ phải"""
        x_rear = -10.5 if self.var_vtype.get() == "ARTICULATED" else -2.3
        self.obstacles = [
            TrackedObstacle(
                track_id=3,
                class_name="motorcycle",
                confidence=0.89,
                bbox_xyxy=(0, 0, 0, 0),
                vcs_x=x_rear,
                vcs_y=2.4,    # Bên trái xe, trong khi xe đang đánh lái mạnh sang phải -> văng đuôi sang trái!
                vel_x=0.0,
                vel_y=0.0
            )
        ]
        self.selected_obs_id = 3
        self._apply_scenario_dynamics(speed_kmh=10, steer_deg=25, ay=-1.2)
        self._sync_obs_controls_from_selected(self.obstacles[0])
        self._on_profile_or_dynamics_change()

    def _load_scenario_rear_backing(self):
        """Kịch bản 5: Người đứng ngay sau đuôi khi xe đang lùi (R158)"""
        x_rear = -12.2 if self.var_vtype.get() == "ARTICULATED" else -3.8
        self.obstacles = [
            TrackedObstacle(
                track_id=4,
                class_name="person",
                confidence=0.96,
                bbox_xyxy=(0, 0, 0, 0),
                vcs_x=x_rear,
                vcs_y=0.2,
                vel_x=0.0,
                vel_y=0.0
            )
        ]
        self.selected_obs_id = 4
        self._apply_scenario_dynamics(speed_kmh=-8, steer_deg=0, ay=0.0, gamma_deg=0.0)
        self._sync_obs_controls_from_selected(self.obstacles[0])
        self._on_profile_or_dynamics_change()

    def _load_scenario_safe_parallel(self):
        """Kịch bản 6: Xe máy chạy song song ở khoảng cách an toàn ngoài vùng đệm"""
        self.obstacles = [
            TrackedObstacle(
                track_id=5,
                class_name="motorcycle",
                confidence=0.92,
                bbox_xyxy=(0, 0, 0, 0),
                vcs_x=1.0,
                vcs_y=-4.5,   # Cách sườn xe 3.25m, ngoài DHZ
                vel_x=5.5,    # Chạy cùng chiều 20 km/h
                vel_y=0.0
            )
        ]
        self.selected_obs_id = 5
        self._apply_scenario_dynamics(speed_kmh=20, steer_deg=0, ay=0.0, gamma_deg=0.0)
        self._sync_obs_controls_from_selected(self.obstacles[0])
        self._on_profile_or_dynamics_change()

    # =========================================================================
    # ĐIỀU KHIỂN & TÍNH TOÁN ĐỘNG LỰC HỌC XE CHỦ
    # =========================================================================
    def _on_vehicle_type_toggle(self):
        vtype = self.var_vtype.get()
        if vtype == "RIGID":
            self.f_art_inputs.pack_forget()
            self.f_gamma_box.pack_forget()
            self.f_rig_inputs.pack(fill=tk.X)
        else:
            self.f_rig_inputs.pack_forget()
            self.f_art_inputs.pack(fill=tk.X)
            self.f_gamma_box.pack(fill=tk.X, pady=2)
        self._on_apply_vehicle_profile()

    def _on_apply_vehicle_profile(self):
        vtype = self.var_vtype.get()
        try:
            if vtype == "RIGID":
                wb = float(self.ent_rig_wb.get() or 5.8)
                foh = float(self.ent_rig_foh.get() or 1.35)
                roh = float(self.ent_rig_roh.get() or 2.4)
                w = float(self.ent_rig_w.get() or 2.5)

                self.v_profile.update({
                    "vehicle_type": "RIGID",
                    "rigid_wheelbase": wb,
                    "rigid_front_overhang": foh,
                    "rigid_front_length": wb + foh,
                    "rigid_rear_overhang": roh,
                    "rigid_rear_length": roh,
                    "rigid_width": w
                })
                self.lbl_v_summary.config(text=f"• Mũi cản trước: +{wb+foh:.2f}m | Cản sau: -{roh:.2f}m | Dài OAL: {wb+foh+roh:.2f}m")
            else:
                lf = float(self.ent_art_lf.get() or 3.6)
                foh = float(self.ent_art_foh.get() or 1.35)
                hitch = float(self.ent_art_hitch.get() or 0.3)
                wb_trail = float(self.ent_art_wb_trail.get() or 8.2)
                roh_trail = float(self.ent_art_roh_trail.get() or 2.8)
                wc = float(self.ent_art_wc.get() or 2.5)

                x_front = lf + foh
                x_rear = hitch - (wb_trail + roh_trail)
                oal = x_front - x_rear

                self.v_profile.update({
                    "vehicle_type": "ARTICULATED",
                    "tractor_wheelbase": lf,
                    "tractor_front_overhang": foh,
                    "tractor_front_length": x_front,
                    "kingpin_distance": hitch,
                    "trailer_wheelbase": wb_trail,
                    "trailer_rear_overhang": roh_trail,
                    "trailer_front_overhang": 1.0,
                    "trailer_width": wc,
                    "trailer_length": 1.0 + wb_trail + roh_trail,
                    "cab_width": wc
                })
                self.lbl_v_summary.config(text=f"• Cản trước: +{x_front:.2f}m | Cản sau: {x_rear:.2f}m | OAL: {oal:.2f}m\n• Inswing ~ L_wb ({wb_trail:.1f}m)² | Tail-Swing ~ L_roh ({roh_trail:.1f}m)")

            # Khởi tạo lại BSRICalculator với profile mới
            self.bsri_calc = BSRICalculator(**self.v_profile)
        except Exception as e:
            messagebox.showerror("Lỗi thông số", f"Sai định dạng số: {e}")

        self._on_profile_or_dynamics_change()

    def _on_speed_slide(self, val):
        spd_kmh = float(val)
        spd_mps = spd_kmh / 3.6
        self.lbl_speed.config(text=f"Vận tốc: {spd_kmh:+.1f} km/h ({spd_mps:+.2f} m/s)")
        self.ego_state.speed_mps = spd_mps
        self.ego_state.gear = "R" if spd_mps < -0.1 else "D"
        self._update_kinematics_from_steering()
        self._on_profile_or_dynamics_change()

    def _on_steer_slide(self, val):
        self._update_kinematics_from_steering()
        self._on_profile_or_dynamics_change()

    def _on_gamma_slide(self, val):
        gamma_deg = float(val)
        self.lbl_gamma.config(text=f"Góc gập rơ-moóc gamma: {gamma_deg:+.1f}°")
        self.ego_state.trailer_gamma_rad = math.radians(gamma_deg)
        self._on_profile_or_dynamics_change()

    def _on_ay_slide(self, val):
        ay = float(val)
        self.ego_state.accel_y_mps2 = ay
        v = self.ego_state.speed_mps
        wz = self.ego_state.yaw_rate_rad_s
        expected_ay = v * wz
        res_ay = ay - expected_ay
        c_dyn = min(0.75, 0.5 * abs(res_ay) * (0.5 ** 2))
        self.lbl_ay.config(text=f"Gia tốc ngang IMU a_y: {ay:+.2f} m/s² (C_dyn: {c_dyn:.2f}m)")
        self._update_imu_behavior_label()
        self.redraw_canvas()
        self._recompute_bsri_and_update_xai()

    def _update_kinematics_from_steering(self):
        """Mô hình động học liên kết giữa Góc lái vô lăng, Tốc độ góc yaw và Gia tốc ngang"""
        steer_input = float(self.scale_steer.get())
        # Quy ước công thái học giao diện trực quan:
        # - Kéo thanh trượt sang TRÁI (steer_input < 0): Xe RẼ TRÁI (Góc lái ISO 8855 delta > 0, Yaw rate omega_z > 0, lệch sang +Y)
        # - Kéo thanh trượt sang PHẢI (steer_input > 0): Xe RẼ PHẢI (Góc lái ISO 8855 delta < 0, Yaw rate omega_z < 0, lệch sang -Y)
        delta_deg = -steer_input
        delta_rad = math.radians(delta_deg)
        speed = self.ego_state.speed_mps

        # Bán kính quay vòng theo mô hình xe đạp Ackermann
        wb = self.v_profile.get("tractor_wheelbase", 3.6) if self.var_vtype.get() == "ARTICULATED" else self.v_profile.get("rigid_wheelbase", 5.8)
        if abs(delta_rad) > 1e-4:
            r_turn = wb / math.tan(delta_rad)
            yaw_rate = speed / r_turn
        else:
            r_turn = float('inf')
            yaw_rate = 0.0

        yaw_rate = float(np.clip(yaw_rate, -0.6, 0.6))
        self.ego_state.steering_angle_deg = delta_deg
        self.ego_state.yaw_rate_rad_s = yaw_rate

        dir_str = "⬅️ RẼ TRÁI" if steer_input < -1 else ("RẼ PHẢI ➡️" if steer_input > 1 else "ĐI THẲNG")
        self.lbl_steer.config(text=f"Góc lái: {abs(steer_input):.1f}° ({dir_str}) | Yaw: {yaw_rate:+.2f} rad/s")

        # Tự động đồng bộ góc gập rơ-moóc gamma theo trạng thái xác lập Ellis 1969 khi người dùng chỉnh góc lái (khi không chạy mô phỏng)
        if self.var_vtype.get() == "ARTICULATED" and not self.is_simulating:
            l_t = float(self.v_profile.get("trailer_wheelbase", 8.2))
            d_hitch = float(self.v_profile.get("kingpin_distance", 0.3))
            if abs(speed) >= 0.2 and abs(yaw_rate) > 1e-4:
                kappa = yaw_rate / speed
                offset = d_hitch * kappa
                scale_val = math.sqrt(1.0 + offset * offset)
                rhs = max(-1.0, min(1.0, (l_t * kappa) / scale_val))
                gamma_rad = math.asin(rhs) - math.atan(offset)
                gamma_deg = round(math.degrees(gamma_rad), 1)
                gamma_deg = max(-45.0, min(45.0, gamma_deg))
            else:
                gamma_deg = 0.0
            self.scale_gamma.set(gamma_deg)
            self.ego_state.trailer_gamma_rad = math.radians(gamma_deg)
            self.lbl_gamma.config(text=f"Góc gập rơ-moóc gamma: {gamma_deg:+.1f}°")

        self._update_imu_behavior_label()

    def _update_imu_behavior_label(self):
        """Tự động phân loại trạng thái hành vi xe thuần túy qua IMU & GPS (KHÔNG DÙNG XI-NHAN)"""
        v = self.ego_state.speed_mps
        wz = self.ego_state.yaw_rate_rad_s
        ay = self.ego_state.accel_y_mps2
        delta = self.ego_state.steering_angle_deg

        if abs(v) < 0.2:
            status = "🅿️ [IMU: XE ĐANG ĐỖ / DỪNG ĐÈN ĐỎ]"
            color = "#b0bec5"
        elif v < -0.2:
            status = "⚠️ [IMU: XE ĐANG VÀO SỐ LÙI (REVERSING)]"
            color = "#ff5252"
        elif wz > 0.035 or delta > 3.0 or ay > 0.3:
            status = "⬅️ [IMU: XE ĐANG ÔM CUA / LƯỢN TRÁI]"
            color = self.ACCENT_CYAN
        elif wz < -0.035 or delta < -3.0 or ay < -0.3:
            status = "➡️ [IMU: XE ĐANG ÔM CUA / LƯỢN PHẢI]"
            color = self.ACCENT_YELLOW
        else:
            status = "⬆️ [IMU: XE ĐANG CHẠY THẲNG]"
            color = self.ACCENT_GREEN

        if hasattr(self, "lbl_imu_behavior"):
            self.lbl_imu_behavior.config(text=f"📡 Trạng thái: {status}", fg=color)

    def _on_profile_or_dynamics_change(self):
        self._update_imu_behavior_label()
        self.redraw_canvas()
        self._recompute_bsri_and_update_xai()

    # =========================================================================
    # ĐIỀU KHIỂN HƯỚNG VÀ VẬN TỐC CỦA ĐỐI TƯỢNG (OBSTACLE DYNAMICS)
    # =========================================================================
    @staticmethod
    def _get_heading_label_text(theta_deg: float) -> str:
        theta = (theta_deg % 360 + 360) % 360
        if 337.5 <= theta or theta < 22.5:
            return f"θ: {int(theta)}° [⬆️ Tiến cùng chiều +X]"
        elif 22.5 <= theta < 67.5:
            return f"θ: {int(theta)}° [↖️ Chéo trước trái]"
        elif 67.5 <= theta < 112.5:
            return f"θ: {int(theta)}° [⬅️ Cắt ngang sang trái +Y]"
        elif 112.5 <= theta < 157.5:
            return f"θ: {int(theta)}° [↙️ Chéo sau trái]"
        elif 157.5 <= theta < 202.5:
            return f"θ: {int(theta)}° [⬇️ Ngược chiều / Đi lùi -X]"
        elif 202.5 <= theta < 247.5:
            return f"θ: {int(theta)}° [↘️ Chéo sau phải]"
        elif 247.5 <= theta < 292.5:
            return f"θ: {int(theta)}° [➡️ Cắt ngang sang phải -Y]"
        else:
            return f"θ: {int(theta)}° [↗️ Chéo trước phải]"

    def _on_obs_speed_slide(self, val):
        spd_kmh = float(val)
        spd_mps = spd_kmh / 3.6
        self.lbl_obs_spd.config(text=f"Tốc độ vật thể: {spd_kmh:.1f} km/h ({spd_mps:.2f} m/s)")
        self._update_selected_obstacle_velocity()

    def _on_obs_heading_slide(self, val):
        heading_deg = float(val)
        self.lbl_obs_heading.config(text=f"Góc hướng {self._get_heading_label_text(heading_deg)}")
        self._update_selected_obstacle_velocity()

    def _set_obs_quick_heading(self, deg: int):
        self.scale_obs_heading.set(deg)
        self.lbl_obs_heading.config(text=f"Góc hướng {self._get_heading_label_text(deg)}")
        self._update_selected_obstacle_velocity()

    def _update_selected_obstacle_velocity(self):
        """Đồng bộ tốc độ & góc hướng từ thanh trượt vào đối tượng đang chọn"""
        if self.selected_obs_id is None:
            return
        target_obs = next((o for o in self.obstacles if o.track_id == self.selected_obs_id), None)
        if target_obs is None:
            return

        spd_kmh = float(self.scale_obs_spd.get())
        spd_mps = spd_kmh / 3.6
        heading_deg = float(self.scale_obs_heading.get())
        rad = math.radians(heading_deg)

        target_obs.vel_x = round(spd_mps * math.cos(rad), 2)
        target_obs.vel_y = round(spd_mps * math.sin(rad), 2)

        self.redraw_canvas()
        self._recompute_bsri_and_update_xai()

    def _apply_manual_obs_xy(self):
        """Áp dụng tọa độ X, Y nhập từ ô Entry vào đối tượng đang chọn"""
        if self.selected_obs_id is None:
            messagebox.showinfo("Thông báo", "Vui lòng click chọn 1 vật thể trên bản đồ trước!")
            return
        target_obs = next((o for o in self.obstacles if o.track_id == self.selected_obs_id), None)
        if target_obs is None:
            return
        try:
            target_obs.vcs_x = float(self.ent_obs_x.get())
            target_obs.vcs_y = float(self.ent_obs_y.get())
            self.redraw_canvas()
            self._recompute_bsri_and_update_xai()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Tọa độ không hợp lệ: {e}")

    def _sync_obs_controls_from_selected(self, obs: TrackedObstacle):
        """Cập nhật giá trị lên các thanh trượt và Entry khi chọn 1 vật thể"""
        self.cbo_class.set(obs.class_name)
        self.ent_obs_x.delete(0, tk.END)
        self.ent_obs_x.insert(0, f"{obs.vcs_x:.2f}")
        self.ent_obs_y.delete(0, tk.END)
        self.ent_obs_y.insert(0, f"{obs.vcs_y:.2f}")

        # Tính tốc độ & góc hướng từ (vel_x, vel_y)
        v_mps = math.hypot(obs.vel_x, obs.vel_y)
        v_kmh = v_mps * 3.6
        self.scale_obs_spd.set(round(v_kmh, 1))
        self.lbl_obs_spd.config(text=f"Tốc độ vật thể: {v_kmh:.1f} km/h ({v_mps:.2f} m/s)")

        if v_mps > 0.05:
            theta_deg = (math.degrees(math.atan2(obs.vel_y, obs.vel_x)) + 360) % 360
            self.scale_obs_heading.set(round(theta_deg))
            self.lbl_obs_heading.config(text=f"Góc hướng {self._get_heading_label_text(theta_deg)}")
        else:
            self.lbl_obs_heading.config(text=f"Góc hướng {self._get_heading_label_text(float(self.scale_obs_heading.get()))}")

    def _toggle_simulation(self):
        self.is_simulating = not self.is_simulating
        if self.is_simulating:
            self.btn_play.config(text="⏸️ TẠM DỪNG MÔ PHỎNG", bg="#ff9100")
            self._simulation_step()
        else:
            self.btn_play.config(text="▶️ BẬT MÔ PHỎNG ĐỘNG LỰC HỌC", bg=self.ACCENT_GREEN)

    def _simulation_step(self):
        if not self.is_simulating:
            return

        dt = 0.05
        # 1. Cập nhật góc gập rơ-moóc gamma theo phương trình vi phân Ellis 1969
        if self.var_vtype.get() == "ARTICULATED":
            v = self.ego_state.speed_mps
            wz = self.ego_state.yaw_rate_rad_s
            gamma = self.ego_state.trailer_gamma_rad
            l_wb_trail = float(self.v_profile.get("trailer_wheelbase", 8.2))
            d_hitch = float(self.v_profile.get("kingpin_distance", 0.3))

            # d(gamma)/dt = wz - (v*sin(gamma) + d_hitch*wz*cos(gamma)) / l_wb_trail
            d_gamma = wz - (v * math.sin(gamma) + d_hitch * wz * math.cos(gamma)) / max(0.5, l_wb_trail)
            new_gamma = gamma + d_gamma * dt
            new_gamma_deg = math.degrees(new_gamma)
            if -45 <= new_gamma_deg <= 45:
                self.scale_gamma.set(round(new_gamma_deg, 1))

        # 2. Cập nhật vị trí các vật thể theo vận tốc tương đối
        for obs in self.obstacles:
            obs.vcs_x += obs.vel_x * dt
            obs.vcs_y += obs.vel_y * dt

        self.redraw_canvas()
        self._recompute_bsri_and_update_xai()
        self.after(50, self._simulation_step)

    # =========================================================================
    # TÍNH TOÁN BSRI & HIỂN THỊ XAI
    # =========================================================================
    def _recompute_bsri_and_update_xai(self):
        """Tính toán BSRI cho tất cả đối tượng và cập nhật cửa sổ XAI"""
        if not self.obstacles:
            self.txt_xai.delete("1.0", tk.END)
            self.txt_xai.insert(tk.END, "Chưa có đối tượng chướng ngại vật nào trong phân cảnh.\nBấm các nút kịch bản mẫu ở trên hoặc click chuột phải trên bản đồ để thêm vật thể.")
            return

        # Gọi lõi BSRICalculator
        all_results, highest_threat = self.bsri_calc.evaluate_scene(self.ego_state, self.obstacles)

        # Tìm đối tượng để hiển thị chi tiết (đối tượng được chọn hoặc đối tượng nguy hiểm nhất)
        target_res: Optional[BSRIResult] = None
        if self.selected_obs_id is not None:
            for r in all_results:
                if r.track_id == self.selected_obs_id:
                    target_res = r
                    break
        if target_res is None and highest_threat is not None:
            target_res = highest_threat

        # Xây dựng nội dung Explainable AI
        self.txt_xai.delete("1.0", tk.END)

        header_str = "╔══════════════════════════════════════════════════════════════╗\n"
        header_str += f"║ KẾT QUẢ ĐÁNH GIÁ RỦI RO BSRI | TỔNG SỐ ĐỐI TƯỢNG: {len(all_results):02d}        ║\n"
        header_str += "╚══════════════════════════════════════════════════════════════╝\n\n"
        self.txt_xai.insert(tk.END, header_str)

        if target_res is not None:
            # Tìm obstacle tương ứng
            t_obs = next((o for o in self.obstacles if o.track_id == target_res.track_id), None)
            pos_str = f"({t_obs.vcs_x:+.2f}m, {t_obs.vcs_y:+.2f}m)" if t_obs else "N/A"
            if t_obs:
                spd_obs = math.hypot(t_obs.vel_x, t_obs.vel_y)
                heading_obs = (math.degrees(math.atan2(t_obs.vel_y, t_obs.vel_x)) + 360) % 360 if spd_obs > 0.05 else 0.0
                v_str = f"({t_obs.vel_x:+.1f}, {t_obs.vel_y:+.1f}) m/s | {spd_obs*3.6:.1f} km/h (Hướng θ={int(heading_obs)}°)"
            else:
                v_str = "N/A"

            lvl_name = target_res.risk_level.name
            lvl_vi = target_res.risk_level.label_vi

            detail = []
            detail.append(f"📌 ĐỐI TƯỢNG ĐANG CHỌN: ID #{target_res.track_id} [{target_res.class_name.upper()}]")
            detail.append(f" • Tọa độ mặt đất VCS : {pos_str}")
            detail.append(f" • Vận tốc & Hướng di chuyển: {v_str}")
            detail.append(f" • Phân vùng điểm mù  : {target_res.zone.value}")
            detail.append("────────────────────────────────────────────────────────")
            detail.append("📐 BẢNG THÀNH PHẦN TOÁN HỌC TRUNG GIAN:")
            detail.append(f" 1. Xâm nhập DHZ      : {'CÓ (Đang trong vùng xe quét qua)' if target_res.is_in_dhz else f'KHÔNG (Cách DHZ {target_res.dist_to_dhz:.2f}m)'}")
            detail.append(f" 2. Rủi ro Không gian : S_spatial = {target_res.spatial_risk:.3f} (Trọng số ws=0.45)")
            ttc_str = f"{target_res.ttc_seconds:.2f} s" if target_res.ttc_seconds is not None else "Không tiếp cận"
            detail.append(f" 3. Thời gian va chạm : TTC = {ttc_str}")
            detail.append(f" 4. Rủi ro Thời gian  : S_temporal = {target_res.temporal_risk:.3f} (Trọng số wt=0.55)")
            detail.append(f" 5. Hệ số đối tượng   : C_vru = {target_res.vru_weight:.2f} ({'Tối đa sinh mạng VRU' if target_res.vru_weight == 1.0 else 'Có khung vỏ'})")
            detail.append(f" 6. Hệ số rủi ro che khuất: V_blind = {target_res.blind_factor:.2f} (Trọng số nội bộ BSRI)")
            detail.append(f" 7. Hệ số thao tác xe : M_ego = {target_res.maneuver_factor:.2f} (IMU Yaw Rate & Đánh lái)")
            detail.append("────────────────────────────────────────────────────────")
            detail.append(f"🧮 CÔNG THỨC: BSRI = min(1.0, (0.45*S_s + 0.55*S_t) * C_vru * V_blind * M_ego)")
            detail.append(f"🎯 ĐIỂM CHỈ SỐ BSRI   : {target_res.bsri_score:.3f} / 1.000")
            detail.append(f"🚨 CẤP ĐỘ CẢNH BÁO    : [{lvl_name}] — {lvl_vi}")
            detail.append("────────────────────────────────────────────────────────")
            detail.append(f"💡 GIẢI THÍCH (XAI)   : {target_res.explanation}")
            detail.append(f"📢 KHUYẾN CÁO LÁI XE  : {target_res.recommendation}")

            self.txt_xai.insert(tk.END, "\n".join(detail) + "\n\n")

        # Bảng tóm tắt tất cả các đối tượng
        self.txt_xai.insert(tk.END, "📋 DANH SÁCH TẤT CẢ ĐỐI TƯỢNG:\n")
        for r in all_results:
            tag = "➡️ [CHỌN]" if (target_res and r.track_id == target_res.track_id) else "  "
            self.txt_xai.insert(tk.END, f"{tag} ID #{r.track_id:02d} | {r.class_name:<10} | BSRI: {r.bsri_score:.3f} | {r.risk_level.label_vi}\n")

    # =========================================================================
    # VẼ 2D CANVAS BẢN ĐỒ VCS
    # =========================================================================
    def _vcs_to_canvas(self, x_vcs: float, y_vcs: float) -> Tuple[float, float]:
        """
        Chuyển tọa độ thế giới thực VCS (mét) sang tọa độ Canvas (pixel):
        - X_vcs hướng tiến mũi xe -> hướng LÊN trên màn hình (trục Y canvas giảm).
        - Y_vcs hướng sang trái xe -> hướng SANG TRÁI trên màn hình (trục X canvas giảm).
        """
        u = self.origin_x - y_vcs * self.scale_pixels_per_meter
        v = self.origin_y - x_vcs * self.scale_pixels_per_meter
        return u, v

    def _canvas_to_vcs(self, u: float, v: float) -> Tuple[float, float]:
        """Chuyển ngược từ Canvas pixel sang VCS mét"""
        x_vcs = (self.origin_y - v) / self.scale_pixels_per_meter
        y_vcs = (self.origin_x - u) / self.scale_pixels_per_meter
        return x_vcs, y_vcs

    def redraw_canvas(self):
        """Vẽ lại toàn bộ bản đồ 2D"""
        self.canvas.delete("all")
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 50 or ch < 50:
            return

        # Điểm gốc O(0,0) VCS (Tâm trục sau đầu kéo/xe tải)
        self.origin_x = cw // 2
        self.origin_y = int(ch * 0.58)  # Để phần đầu xe vươn lên trên, phần rơ-moóc lui xuống dưới

        # 1. Vẽ lưới tọa độ mét
        if self.show_grid.get():
            self._draw_grid(cw, ch)

        # 2. Vẽ các vùng điểm mù quang học (nếu bật)
        if self.show_zones.get():
            self._draw_blind_spot_zones()

        # 3. Vẽ Đa giác Vùng Nguy Hiểm Động (Dynamic Hazard Zone - DHZ)
        if self.show_dhz.get():
            self._draw_dhz_polygon()

        # 4. Vẽ Hình bao thân xe (Vehicle Footprint)
        self._draw_vehicle_footprint()

        # 5. Vẽ các đối tượng chướng ngại vật
        self._draw_obstacles()

    def _draw_grid(self, cw, ch):
        """Vẽ lưới tọa độ chuẩn mét và trục chính"""
        scale = self.scale_pixels_per_meter

        # Lưới mờ mỗi 1 mét
        for m in range(-30, 31):
            # Đường ngang (theo X_vcs)
            _, v = self._vcs_to_canvas(m, 0)
            if 0 <= v <= ch:
                col = "#1c1c2a" if m % 5 != 0 else "#2e2e42"
                self.canvas.create_line(0, v, cw, v, fill=col, width=1)
                if m % 5 == 0 and m != 0:
                    self.canvas.create_text(self.origin_x + 12, v, text=f"X={m:+d}m", fill="#62627a", font=("Segoe UI", 7), anchor="w")

            # Đường dọc (theo Y_vcs)
            u, _ = self._vcs_to_canvas(0, m)
            if 0 <= u <= cw:
                col = "#1c1c2a" if m % 5 != 0 else "#2e2e42"
                self.canvas.create_line(u, 0, u, ch, fill=col, width=1)
                if m % 5 == 0 and m != 0:
                    self.canvas.create_text(u, self.origin_y + 12, text=f"Y={m:+d}m", fill="#62627a", font=("Segoe UI", 7), anchor="n")

        # Trục chính X và Y
        self.canvas.create_line(self.origin_x, 0, self.origin_x, ch, fill="#00e5ff", width=1, dash=(4, 4))
        self.canvas.create_line(0, self.origin_y, cw, self.origin_y, fill="#00e5ff", width=1, dash=(4, 4))

        # Đánh dấu tâm trục sau O(0,0)
        self.canvas.create_oval(self.origin_x - 5, self.origin_y - 5, self.origin_x + 5, self.origin_y + 5, fill="#00e5ff", outline="#ffffff")
        self.canvas.create_text(self.origin_x + 8, self.origin_y - 8, text="O (Trục sau)", fill="#00e5ff", font=("Segoe UI", 8, "bold"), anchor="w")

        # Mũi tên chỉ hướng tiến +X
        self.canvas.create_text(self.origin_x, 15, text="▲ HƯỚNG TIẾN MŨI XE (+X)", fill="#00e5ff", font=("Segoe UI", 9, "bold"))
        self.canvas.create_text(40, self.origin_y - 12, text="◀ BÊN TRÁI (+Y)", fill="#8888aa", font=("Segoe UI", 8))
        self.canvas.create_text(cw - 40, self.origin_y - 12, text="BÊN PHẢI (-Y) ▶", fill="#8888aa", font=("Segoe UI", 8))

    def _draw_blind_spot_zones(self):
        """Vẽ ranh giới các vùng điểm mù quang học"""
        vtype = self.var_vtype.get()
        if vtype == "RIGID":
            x_front = float(self.v_profile.get("rigid_front_length", 7.15))
            x_rear = -float(self.v_profile.get("rigid_rear_length", 2.4))
            w = float(self.v_profile.get("rigid_width", 2.5))
            d_hitch = 0.0
        else:
            x_front = float(self.v_profile.get("tractor_front_length", 4.95))
            d_hitch = float(self.v_profile.get("kingpin_distance", 0.3))
            wb_trail = float(self.v_profile.get("trailer_wheelbase", 8.2))
            roh_trail = float(self.v_profile.get("trailer_rear_overhang", 2.8))
            x_rear = d_hitch - (wb_trail + roh_trail)
            w = float(self.v_profile.get("cab_width", 2.5))

        hw = w / 2.0

        zones_data = [
            # Zone 1: CAB_FRONT (Tham chiếu MOIS)
            ([ (x_front, -hw - 0.8), (x_front + 2.0, -hw - 0.8), (x_front + 2.0, hw + 0.8), (x_front, hw + 0.8) ],
             "#ffb300", "CAB_FRONT (MOIS cản trước)"),
            # Zone 2: MIRROR_RIGHT (Gương phụ)
            ([ (d_hitch, -3.5), (x_front, -3.5), (x_front, -hw), (d_hitch, -hw) ],
             "#ab47bc", "MIRROR_RIGHT (Gương phụ)"),
            # Zone 3: MIRROR_LEFT (Gương lái)
            ([ (d_hitch, hw), (x_front, hw), (x_front, 3.5), (d_hitch, 3.5) ],
             "#26a69a", "MIRROR_LEFT (Gương lái)"),
            # Zone 4: SWEPT_PATH_RIGHT (Bụng cua rơ-moóc phải)
            ([ (x_rear, -4.5), (d_hitch, -4.5), (d_hitch, -hw), (x_rear, -hw) ],
             "#e53935", "SWEPT_PATH_RIGHT (Bụng cua phải)"),
            # Zone 5: SWEPT_PATH_LEFT (Bụng cua rơ-moóc trái)
            ([ (x_rear, hw), (d_hitch, hw), (d_hitch, 4.5), (x_rear, 4.5) ],
             "#3949ab", "SWEPT_PATH_LEFT (Bụng cua trái)"),
            # Zone 6: REAR_TRAILER (Lùi đuôi xe)
            ([ (x_rear - 3.5, -hw - 1.0), (x_rear, -hw - 1.0), (x_rear, hw + 1.0), (x_rear - 3.5, hw + 1.0) ],
             "#d81b60", "REAR_TRAILER (Lùi đuôi xe)")
        ]

        for pts, color, label in zones_data:
            c_pts = [self._vcs_to_canvas(px, py) for px, py in pts]
            flat_pts = [coord for pt in c_pts for coord in pt]
            self.canvas.create_polygon(flat_pts, outline=color, fill="", width=1, dash=(3, 3))
            # Nhãn vùng
            mid_u = sum(pt[0] for pt in c_pts) / len(c_pts)
            mid_v = sum(pt[1] for pt in c_pts) / len(c_pts)
            self.canvas.create_text(mid_u, mid_v, text=label, fill=color, font=("Segoe UI", 7, "italic"))

    def _draw_dhz_polygon(self):
        """Vẽ Đa giác Vùng Nguy Hiểm Động (Dynamic Hazard Zone - DHZ) chuẩn Module 2"""
        try:
            dhz_poly = self.bsri_calc.compute_dynamic_hazard_zone(self.ego_state, horizon_sec=0.50, dt_nominal=0.05)
            if dhz_poly is None or dhz_poly.is_empty:
                return

            polys = [dhz_poly] if dhz_poly.geom_type == 'Polygon' else list(dhz_poly.geoms)

            for p in polys:
                ext_coords = list(p.exterior.coords)
                c_pts = [self._vcs_to_canvas(x, y) for x, y in ext_coords]
                flat_pts = [coord for pt in c_pts for coord in pt]
                self.canvas.create_polygon(flat_pts, outline="#ffd600", fill="#2d2200", width=2, stipple="gray25")
            
            # Ghi nhãn DHZ
            bounds = dhz_poly.bounds
            lbl_u, lbl_v = self._vcs_to_canvas(bounds[3] + 0.3, bounds[0] - 0.2)
            self.canvas.create_text(lbl_u, lbl_v, text="⚡ VÙNG NGUY HIỂM ĐỘNG (DHZ - MODULE 2)", fill="#ffd600",
                                    font=("Segoe UI", 8, "bold"), anchor="w")
        except Exception as e:
            print(f"[Error drawing DHZ] {e}")

    def _draw_vehicle_footprint(self):
        """Vẽ hình học thân xe chi tiết"""
        vtype = self.var_vtype.get()
        gamma = self.ego_state.trailer_gamma_rad

        if vtype == "RIGID":
            x_front = float(self.v_profile.get("rigid_front_length", 7.15))
            x_rear = -float(self.v_profile.get("rigid_rear_length", 2.4))
            wb = float(self.v_profile.get("rigid_wheelbase", 5.8))
            w = float(self.v_profile.get("rigid_width", 2.5))
            hw = w / 2.0

            # Thân xe tải
            pts = [(x_front, hw), (x_front, -hw), (x_rear, -hw), (x_rear, hw)]
            c_pts = [self._vcs_to_canvas(x, y) for x, y in pts]
            flat = [coord for pt in c_pts for coord in pt]
            self.canvas.create_polygon(flat, outline="#00e5ff", fill="#16222f", width=2)

            # Cabin phía trước
            cab_pts = [(x_front, hw), (x_front, -hw), (wb - 0.5, -hw), (wb - 0.5, hw)]
            c_cab = [self._vcs_to_canvas(x, y) for x, y in cab_pts]
            self.canvas.create_polygon([c for p in c_cab for c in p], outline="#00e5ff", fill="#1e3448", width=1)
            
            # Kính chắn gió
            ws_pts = [(x_front - 0.3, hw - 0.2), (x_front - 0.3, -hw + 0.2), (x_front - 0.9, -hw + 0.2), (x_front - 0.9, hw - 0.2)]
            c_ws = [self._vcs_to_canvas(x, y) for x, y in ws_pts]
            self.canvas.create_polygon([c for p in c_ws for c in p], fill="#4fc3f7", outline="")

            # Trục bánh trước (có bẻ lái) & Trục bánh sau
            self._draw_wheel(wb, hw + 0.1, self.ego_state.steering_angle_deg)
            self._draw_wheel(wb, -hw - 0.1, self.ego_state.steering_angle_deg)
            self._draw_wheel(0.0, hw + 0.1, 0.0)
            self._draw_wheel(0.0, -hw - 0.1, 0.0)

            # Nhãn xe
            u_center, v_center = self._vcs_to_canvas(wb / 2, 0)
            self.canvas.create_text(u_center, v_center, text="XE TẢI LIỀN THÂN\n(RIGID 5.8m)", fill="#e0f7fa", font=("Segoe UI", 8, "bold"), justify="center")

        else:
            # XE ĐẦU KÉO SƠ-MI RƠ-MOÓC (ARTICULATED)
            lf = float(self.v_profile.get("tractor_wheelbase", 3.6))
            foh = float(self.v_profile.get("tractor_front_overhang", 1.35))
            x_front = lf + foh
            wc = float(self.v_profile.get("cab_width", 2.5))
            hwc = wc / 2.0
            hitch = float(self.v_profile.get("kingpin_distance", 0.3))

            # 1. Cabin đầu kéo
            cab_pts = [(x_front, hwc), (x_front, -hwc), (lf - 1.4, -hwc), (lf - 1.4, hwc)]
            c_cab = [self._vcs_to_canvas(x, y) for x, y in cab_pts]
            self.canvas.create_polygon([c for p in c_cab for c in p], outline="#00e5ff", fill="#1e3448", width=2)

            # Kính chắn gió đầu kéo
            ws_pts = [(x_front - 0.3, hwc - 0.2), (x_front - 0.3, -hwc + 0.2), (x_front - 0.9, -hwc + 0.2), (x_front - 0.9, hwc - 0.2)]
            c_ws = [self._vcs_to_canvas(x, y) for x, y in ws_pts]
            self.canvas.create_polygon([c for p in c_ws for c in p], fill="#4fc3f7", outline="")

            # Khung gầm đầu kéo phía sau
            chassis_pts = [(lf - 1.4, hwc * 0.35), (lf - 1.4, -hwc * 0.35), (-0.8, -hwc * 0.35), (-0.8, hwc * 0.35)]
            c_chass = [self._vcs_to_canvas(x, y) for x, y in chassis_pts]
            self.canvas.create_polygon([c for p in c_chass for c in p], outline="#37474f", fill="#263238")

            # Bánh xe đầu kéo
            self._draw_wheel(lf, hwc + 0.08, self.ego_state.steering_angle_deg)
            self._draw_wheel(lf, -hwc - 0.08, self.ego_state.steering_angle_deg)
            self._draw_wheel(0.0, hwc + 0.08, 0.0)
            self._draw_wheel(0.0, -hwc - 0.08, 0.0)

            # Khớp mâm xoay Kingpin
            u_hitch, v_hitch = self._vcs_to_canvas(hitch, 0)
            self.canvas.create_oval(u_hitch - 6, v_hitch - 6, u_hitch + 6, v_hitch + 6, fill="#ffd600", outline="#ffffff", width=2)

            # 2. Thùng rơ-moóc xoay quanh Kingpin (góc -gamma)
            wb_trail = float(self.v_profile.get("trailer_wheelbase", 8.2))
            roh_trail = float(self.v_profile.get("trailer_rear_overhang", 2.8))
            foh_trail = float(self.v_profile.get("trailer_front_overhang", 1.0))
            w_trail = float(self.v_profile.get("trailer_width", 2.5))
            hwt = w_trail / 2.0

            front_t = hitch + foh_trail
            rear_t = hitch - (wb_trail + roh_trail)
            axle_t = hitch - wb_trail

            raw_trail_pts = [
                (front_t, hwt),
                (front_t, -hwt),
                (rear_t, -hwt),
                (rear_t, hwt)
            ]

            # Xoay quanh khớp hitch
            cos_g = math.cos(-gamma)
            sin_g = math.sin(-gamma)
            rot_trail_pts = []
            for px, py in raw_trail_pts:
                rx = (px - hitch) * cos_g - py * sin_g + hitch
                ry = (px - hitch) * sin_g + py * cos_g
                rot_trail_pts.append((rx, ry))

            c_trail = [self._vcs_to_canvas(rx, ry) for rx, ry in rot_trail_pts]
            self.canvas.create_polygon([c for p in c_trail for c in p], outline="#80d8ff", fill="#132330", width=2)

            # Bánh xe rơ-moóc (cách hitch 8.2m)
            for side in [hwt + 0.08, -hwt - 0.08]:
                wx = (axle_t - hitch) * cos_g - side * sin_g + hitch
                wy = (axle_t - hitch) * sin_g + side * cos_g
                self._draw_wheel(wx, wy, -math.degrees(gamma))

            # Nhãn rơ-moóc
            mid_tx = (axle_t - hitch) * 0.5 * cos_g + hitch
            mid_ty = (axle_t - hitch) * 0.5 * sin_g
            u_tmid, v_tmid = self._vcs_to_canvas(mid_tx, mid_ty)
            self.canvas.create_text(u_tmid, v_tmid, text=f"THÙNG RƠ-MOÓC\n(WB: {wb_trail:.1f}m | γ: {math.degrees(gamma):+.1f}°)",
                                    fill="#b0bec5", font=("Segoe UI", 8, "bold"), justify="center")

    def _draw_wheel(self, x_m: float, y_m: float, steer_deg: float):
        """Vẽ một bánh xe có góc bẻ lái theo chuẩn tọa độ xe VCS"""
        u, v = self._vcs_to_canvas(x_m, y_m)
        angle_rad = math.radians(steer_deg)  # Góc lái chuẩn VCS (>0 quay trái, <0 quay phải)
        l = 10
        w = 4
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        pts = [
            (u - l*sin_a - w*cos_a, v - l*cos_a + w*sin_a),
            (u - l*sin_a + w*cos_a, v - l*cos_a - w*sin_a),
            (u + l*sin_a + w*cos_a, v + l*cos_a - w*sin_a),
            (u + l*sin_a - w*cos_a, v + l*cos_a + w*sin_a),
        ]
        flat = [coord for pt in pts for coord in pt]
        self.canvas.create_polygon(flat, fill="#212121", outline="#90a4ae", width=1)

    def _draw_obstacles(self):
        """Vẽ các chướng ngại vật cùng vector vận tốc xoay theo hướng di chuyển và nhãn BSRI"""
        for obs in self.obstacles:
            u, v = self._vcs_to_canvas(obs.vcs_x, obs.vcs_y)
            is_selected = (obs.track_id == self.selected_obs_id)

            # Lấy thông tin BSRI của đối tượng này
            bsri_res = self.bsri_calc.evaluate_obstacle(obs, self.ego_state)
            color_hex = bsri_res.risk_level.color_hex

            # Kích thước icon
            r = 11 if is_selected else 8

            # Vòng hào quang nếu được chọn
            if is_selected:
                self.canvas.create_oval(u - r - 5, v - r - 5, u + r + 5, v + r + 5, outline="#00e5ff", width=2, dash=(3, 3))

            # Hình khối đối tượng theo loại
            if obs.class_name in ["motorcycle", "bicycle"]:
                self.canvas.create_oval(u - r, v - r, u + r, v + r, fill=color_hex, outline="#ffffff", width=1.5)
                self.canvas.create_text(u, v, text="🏍️" if obs.class_name == "motorcycle" else "🚲", font=("Segoe UI", 9))
            elif obs.class_name == "person":
                self.canvas.create_oval(u - r, v - r, u + r, v + r, fill=color_hex, outline="#ffffff", width=1.5)
                self.canvas.create_text(u, v, text="🚶", font=("Segoe UI", 9))
            else:
                self.canvas.create_rectangle(u - r, v - r, u + r, v + r, fill=color_hex, outline="#ffffff", width=1.5)
                self.canvas.create_text(u, v, text="🚗", font=("Segoe UI", 9))

            # Vector vận tốc xoay theo góc hướng di chuyển
            spd_mps = math.hypot(obs.vel_x, obs.vel_y)
            if spd_mps > 0.05:
                # Độ dài hiển thị tối thiểu 22px, tối đa 65px để nhìn rõ hướng di chuyển
                arrow_len = min(65.0, max(22.0, spd_mps * self.scale_pixels_per_meter * 0.5))
                # vcs_x hướng tiến (màn hình -V), vcs_y hướng trái (màn hình -U)
                norm_vx = obs.vel_x / spd_mps
                norm_vy = obs.vel_y / spd_mps
                tip_u = u - norm_vy * arrow_len
                tip_v = v - norm_vx * arrow_len

                # Vẽ mũi tên vận tốc màu vàng neon
                self.canvas.create_line(u, v, tip_u, tip_v, fill="#ffea00", width=2.5, arrow=tk.LAST, arrowshape=(10, 12, 5))

                # Góc hướng để hiển thị
                heading_deg = (math.degrees(math.atan2(obs.vel_y, obs.vel_x)) + 360) % 360
                vel_info = f" {spd_mps*3.6:.0f}km/h {int(heading_deg)}°"
            else:
                vel_info = " 0km/h"

            # Tag thông tin nổi
            tag_text = f"#{obs.track_id} {obs.class_name}{vel_info} | BSRI={bsri_res.bsri_score:.2f} ({bsri_res.risk_level.label_vi})"
            tag_w = len(tag_text) * 6 + 18
            self.canvas.create_rectangle(u + 12, v - 16, u + tag_w, v + 3, fill="#12121a", outline=color_hex)
            self.canvas.create_text(u + 16, v - 7, text=tag_text, fill=color_hex, font=("Segoe UI", 8, "bold"), anchor="w")

    # =========================================================================
    # TƯƠNG TÁC CHUỘT TRÊN BẢN ĐỒ VCS (MOUSE EVENTS)
    # =========================================================================
    def _on_canvas_motion(self, event):
        x_vcs, y_vcs = self._canvas_to_vcs(event.x, event.y)
        self.lbl_cursor_pos.config(text=f"Tọa độ VCS: X = {x_vcs:+.2f}m, Y = {y_vcs:+.2f}m")

    def _on_canvas_left_click(self, event):
        """Bấm chuột trái: Chọn đối tượng hoặc bắt đầu Kéo Thả (Drag)"""
        click_u, click_v = event.x, event.y
        x_m, y_m = self._canvas_to_vcs(click_u, click_v)

        # Kiểm tra xem có bấm trúng vật thể nào không (bán kính 1.2 mét)
        clicked_obs = None
        for obs in self.obstacles:
            dist = math.hypot(obs.vcs_x - x_m, obs.vcs_y - y_m)
            if dist < 1.2:
                clicked_obs = obs
                break

        if clicked_obs:
            self.selected_obs_id = clicked_obs.track_id
            self.dragging_obs_id = clicked_obs.track_id
            self.drag_offset = (clicked_obs.vcs_x - x_m, clicked_obs.vcs_y - y_m)
            # Đồng bộ toàn bộ controls bên phải (Class, X, Y, Tốc độ, Góc hướng)
            self._sync_obs_controls_from_selected(clicked_obs)
        else:
            self.selected_obs_id = None
            self.dragging_obs_id = None

        self.redraw_canvas()
        self._recompute_bsri_and_update_xai()

    def _on_canvas_drag(self, event):
        """Kéo chuột: Di chuyển vị trí của vật thể đang chọn theo thời gian thực!"""
        if self.dragging_obs_id is None:
            return

        x_m, y_m = self._canvas_to_vcs(event.x, event.y)
        for obs in self.obstacles:
            if obs.track_id == self.dragging_obs_id:
                obs.vcs_x = round(x_m + self.drag_offset[0], 2)
                obs.vcs_y = round(y_m + self.drag_offset[1], 2)
                # Cập nhật ô text
                self.ent_obs_x.delete(0, tk.END)
                self.ent_obs_x.insert(0, f"{obs.vcs_x:.2f}")
                self.ent_obs_y.delete(0, tk.END)
                self.ent_obs_y.insert(0, f"{obs.vcs_y:.2f}")
                break

        self.redraw_canvas()
        self._recompute_bsri_and_update_xai()

    def _on_canvas_release(self, event):
        self.dragging_obs_id = None

    def _on_canvas_right_click(self, event):
        """Bấm chuột phải: Thêm nhanh một vật thể mới tại vị trí chuột với tốc độ & hướng hiện tại"""
        x_m, y_m = self._canvas_to_vcs(event.x, event.y)
        new_id = max([o.track_id for o in self.obstacles], default=0) + 1
        cls_name = self.cbo_class.get() or "motorcycle"

        spd_kmh = float(self.scale_obs_spd.get())
        spd_mps = spd_kmh / 3.6
        heading_deg = float(self.scale_obs_heading.get())
        rad = math.radians(heading_deg)
        vx = round(spd_mps * math.cos(rad), 2)
        vy = round(spd_mps * math.sin(rad), 2)

        new_obs = TrackedObstacle(
            track_id=new_id,
            class_name=cls_name,
            confidence=0.92,
            bbox_xyxy=(0, 0, 0, 0),
            vcs_x=round(x_m, 2),
            vcs_y=round(y_m, 2),
            vel_x=vx,
            vel_y=vy
        )
        self.obstacles.append(new_obs)
        self.selected_obs_id = new_id
        self._sync_obs_controls_from_selected(new_obs)

        self.redraw_canvas()
        self._recompute_bsri_and_update_xai()

    def _on_canvas_zoom(self, event):
        """Lăn chuột: Phóng to / Thu nhỏ bản đồ"""
        if event.delta > 0:
            self.scale_pixels_per_meter = min(45.0, self.scale_pixels_per_meter * 1.15)
        else:
            self.scale_pixels_per_meter = max(10.0, self.scale_pixels_per_meter * 0.85)
        self.redraw_canvas()

    # =========================================================================
    # QUẢN LÝ THÊM / XÓA VẬT THỂ
    # =========================================================================
    def _add_obstacle_manual(self):
        try:
            cls_name = self.cbo_class.get() or "motorcycle"
            x = float(self.ent_obs_x.get() or 2.0)
            y = float(self.ent_obs_y.get() or -2.2)
            spd_kmh = float(self.scale_obs_spd.get())
            spd_mps = spd_kmh / 3.6
            heading_deg = float(self.scale_obs_heading.get())
            rad = math.radians(heading_deg)
            vx = round(spd_mps * math.cos(rad), 2)
            vy = round(spd_mps * math.sin(rad), 2)
            new_id = max([o.track_id for o in self.obstacles], default=0) + 1

            obs = TrackedObstacle(
                track_id=new_id,
                class_name=cls_name,
                confidence=0.90,
                bbox_xyxy=(0, 0, 0, 0),
                vcs_x=x,
                vcs_y=y,
                vel_x=vx,
                vel_y=vy
            )
            self.obstacles.append(obs)
            self.selected_obs_id = new_id
            self._sync_obs_controls_from_selected(obs)
            self.redraw_canvas()
            self._recompute_bsri_and_update_xai()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Vui lòng kiểm tra lại tọa độ số: {e}")

    def _delete_selected_obstacle(self):
        if self.selected_obs_id is None:
            messagebox.showinfo("Thông báo", "Vui lòng click chọn 1 vật thể trên bản đồ trước!")
            return
        self.obstacles = [o for o in self.obstacles if o.track_id != self.selected_obs_id]
        self.selected_obs_id = None
        self.redraw_canvas()
        self._recompute_bsri_and_update_xai()

    def _clear_all_obstacles(self):
        self.obstacles.clear()
        self.selected_obs_id = None
        self.redraw_canvas()
        self._recompute_bsri_and_update_xai()


if __name__ == "__main__":
    app = BSRISimulatorApp()
    app.mainloop()
