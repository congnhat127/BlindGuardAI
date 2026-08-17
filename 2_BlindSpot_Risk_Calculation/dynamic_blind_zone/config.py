# ==============================================================================
# CONFIG.PY - CẤU HÌNH THÔNG SỐ XE ĐẦU KÉO RƠ-MOÓC (DERIVED CONFIG ARCHITECTURE)
# ==============================================================================
import numpy as np

# ==============================================================================
# [BƯỚC 1]: CHỈ CẦN KHAI BÁO 4 THÔNG SỐ CƠ BẢN TỪ SỔ ĐĂNG KIỂM / CATALOG XE
# ==============================================================================
WHEELBASE_TRACTOR = 3.6  # [L_f] Chiều dài cơ sở đầu kéo (trục trước -> trục sau) (m)
CAB_WIDTH = 2.5          # [W_cab] Chiều rộng tổng thể cabin (m)
L_TRAIL = 12.0           # [L_trail] Chiều dài rơ-moóc (chốt kéo -> trục bánh sau) (m)
W_TRAIL = 2.5            # [W_trail] Chiều rộng thùng rơ-moóc (m)

# ==============================================================================
# [BƯỚC 2]: TỰ ĐỘNG SUY RA TOÀN BỘ HÌNH HỌC THEO TỶ LỆ CHUẨN Ô TÔ (SAE/ISO)
# ==============================================================================
# Half-widths
CAB_HALF_W = CAB_WIDTH / 2.0
TRAIL_HALF_W = W_TRAIL / 2.0
CHASSIS_HALF_W = CAB_WIDTH * 0.18 # Khung gầm hẹp bằng 36% cabin (0.45m)

# Cabin Dimensions (Suy ra từ Chiều dài cơ sở L_f)
CAB_FRONT_X = WHEELBASE_TRACTOR + 0.40  # Mũi xe nhô trước trục trước 40cm (4.0m)
CAB_REAR_X = WHEELBASE_TRACTOR * 0.61   # Vách sau cabin cách trục sau 61% (2.2m)
D_HITCH = WHEELBASE_TRACTOR * 0.08      # Mâm xoay chốt kéo lệch 8% trước trục sau (0.3m)
TRAIL_OVERHANG = WHEELBASE_TRACTOR * 0.25 # Nhô rơ-moóc phía trước chốt kéo (0.9m)

# --- VỊ TRÍ MẮT TÀI XẾ (Tự động suy ra từ kích thước Cabin & Chiều cao tài xế) ---
DRIVER_HEIGHT = 1.70                    # Chiều cao tài xế (m) - Mặc định 1.70m (Tiêu chuẩn nam Châu Á)
EYE_X = WHEELBASE_TRACTOR * 0.78        # Mắt tài xế ngồi nhô trước 78% (2.8m)
EYE_Y = CAB_WIDTH * 0.20                # Lệch trái 20% cabin (0.5m)
# Độ cao tầm mắt (EYE_Z): Độ cao sàn cabin (1.4m) + Tầm mắt ngồi (0.8m) + Sai số chiều cao tài xế
EYE_Z = 2.20 + (DRIVER_HEIGHT - 1.70) * 0.5

# --- VỊ TRÍ GƯƠNG CHIẾU HẬU (Tự động suy ra từ mép kính và cabin) ---
MIRROR_R_X = WHEELBASE_TRACTOR * 0.97   # Gương gắn sát kính trước (3.5m)
MIRROR_R_Y = -(CAB_HALF_W + 0.10)       # Gương phụ nhô ra ngoài 10cm (-1.35m)
MIRROR_L_X = WHEELBASE_TRACTOR * 0.97
MIRROR_L_Y = (CAB_HALF_W + 0.10)        # Gương tài xế nhô ra ngoài 10cm (+1.35m)

# --- VỊ TRÍ CỘT A & CỘT B (Tự động suy ra từ khung xe) ---
A_PILLAR_R_X = MIRROR_R_X - 0.10        # Cột A sát chân gương (3.4m)
A_PILLAR_R_Y = -(CAB_HALF_W - 0.05)      # Chắn mép cửa sổ góc nghiêng (-1.20m)
A_PILLAR_L_X = MIRROR_L_X - 0.10
A_PILLAR_L_Y = (CAB_HALF_W - 0.05)       # (+1.20m)
A_PILLAR_WIDTH = 0.28                   # Bề rộng hiệu dụng cụm Cột A + Gương (28cm)
A_PILLAR_BLIND_RANGE = 15.0            # Tầm xa chiếu đường Cột A (15m)

B_PILLAR_R_X = CAB_REAR_X              # Cột B đặt ngay thành sau cabin (2.2m)
B_PILLAR_R_Y = -CAB_HALF_W              # (-1.25m)
B_PILLAR_L_X = CAB_REAR_X
B_PILLAR_L_Y = CAB_HALF_W               # (+1.25m)

# ==============================================================================
# [BƯỚC 3]: THÔNG SỐ VẬT LÝ VÀ ĐỘNG LỰC HỌC CHUẨN
# ==============================================================================
REACTION_TIME = 1.5                     # Thời gian phản ứng phanh (1.5s)
FRICTION_COEFF = 0.7                    # Ma sát đường khô (0.7)
GRAVITY = 9.81
MAX_GAMMA_DEG = 85.0
MECHANICAL_MAX_GAMMA_DEG = 65.0         # Giới hạn va chạm cabin cab-strike
STEER_RATIO = 16.0                      # Tỷ số truyền hệ thống lái

FRONT_BLIND_MIN = 2.0
SIDE_BLIND_MAX = 4.0
REAR_BLIND_DEPTH = 3.0
FRONT_RED_RATIO = 0.3

# ==============================================================================
# [BƯỚC 4]: TỰ ĐỘNG KHÓA VỊ TRÍ VÀ ÁNH XẠ CAMERA (AUTOMATIC CAMERA MAPPING)
# ==============================================================================
GPS_FREQ = 1.0
CAMERA_FREQ = 30.0
GPS_TIMEOUT_SEC = 5.0
DT_CAMERA = 1.0 / 30.0

K_CAMERA = np.array([
    [1000.0,    0.0, 960.0],
    [   0.0, 1000.0, 540.0],
    [   0.0,    0.0,   1.0]
])

# Tự động gán vị trí Camera trùng với vị trí Gương và Mũi xe đã suy ra ở trên!
CAMERAS_EXTRINSICS = {
    "MIRROR_R": {
        "position": [MIRROR_R_X, MIRROR_R_Y, EYE_Z], # Tự động lấy tọa độ gương phải
        "pitch_deg": -15.0,
        "yaw_deg": -165.0,
        "roll_deg": 0.0,
        "monitored_blind_zones": [
            "right_side_occlusion",
            "a_pillar_right",
            "b_pillar_right",
            "swept_path_right"
        ]
    },
    "MIRROR_L": {
        "position": [MIRROR_L_X, MIRROR_L_Y, EYE_Z], # Tự động lấy tọa độ gương trái
        "pitch_deg": -15.0,
        "yaw_deg": 165.0,
        "roll_deg": 0.0,
        "monitored_blind_zones": [
            "left_side_occlusion",
            "a_pillar_left",
            "b_pillar_left",
            "swept_path_left"
        ]
    },
    "FRONT_CAM": {
        "position": [CAB_FRONT_X, 0.0, EYE_Z + 0.3], # Tự động lấy tọa độ mũi xe
        "pitch_deg": -10.0,
        "yaw_deg": 0.0,
        "roll_deg": 0.0,
        "monitored_blind_zones": [
            "front_bonnet",
            "stopping_hazard"
        ]
    }
}
