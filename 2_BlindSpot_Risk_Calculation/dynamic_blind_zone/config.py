# ==============================================================================
# CONFIG.PY - CẤU HÌNH HỆ THỐNG CẢNH BÁO VA CHẠM (SURROUND HAZARD ZONE)
# ==============================================================================
import numpy as np

# ==============================================================================
# [BƯỚC 1]: THÔNG SỐ SỔ ĐĂNG KIỂM (CƠ BẢN)
# ==============================================================================
WHEELBASE_TRACTOR = 3.6  # [L_f] Chiều dài cơ sở đầu kéo (m)
CAB_WIDTH = 2.5          # [W_cab] Chiều rộng tổng thể cabin (m)
L_TRAIL = 12.0           # [L_trail] Chiều dài rơ-moóc (m) (0 nếu là xe thân liền)
W_TRAIL = 2.5            # [W_trail] Chiều rộng thùng rơ-moóc (m)

# ==============================================================================
# [BƯỚC 2]: TỰ ĐỘNG SUY RA HÌNH HỌC THÂN XE
# ==============================================================================
CAB_HALF_W = CAB_WIDTH / 2.0
TRAIL_HALF_W = W_TRAIL / 2.0
CHASSIS_HALF_W = CAB_WIDTH * 0.18 # Khung gầm

CAB_FRONT_X = WHEELBASE_TRACTOR + 0.40  # Mũi xe nhô trước trục trước 40cm
CAB_REAR_X = WHEELBASE_TRACTOR * 0.61   # Vách sau cabin
D_HITCH = WHEELBASE_TRACTOR * 0.08      # Chốt kéo rơ-moóc
TRAIL_OVERHANG = WHEELBASE_TRACTOR * 0.25 # Phần nhô trước rơ-moóc

# ==============================================================================
# [BƯỚC 3]: THÔNG SỐ ĐỘNG LỰC HỌC VÀ CẢNH BÁO NGUY HIỂM
# ==============================================================================
REACTION_TIME = 1.5
FRICTION_COEFF = 0.7
GRAVITY = 9.81
MECHANICAL_MAX_GAMMA_DEG = 65.0
STEER_RATIO = 16.0

# Các hệ số cho Vùng Đệm Nguy Hiểm (Surround Hazard Zone Buffer)
HAZARD_BUFFER_BASE = 1.0         # Mặc định phình ra 1.0m bao quanh thân xe (Tiêu chuẩn ISO 15622)
HAZARD_BUFFER_SPEED_FACTOR = 0.1 # Phình thêm 0.1m cho mỗi 1m/s tốc độ (Thời gian dự phòng)

# Hệ số phân tán ngang khi phanh (Lateral Dispersion Angle)
LATERAL_DISPERSION_DEG = 3.5     # Góc loe ngang 3.5 độ do sai số thước lái và láng xe khi phanh gấp

# ==============================================================================
# [BƯỚC 4]: CAMERA MAPPING (ĐƠN GIẢN HÓA CHO HAZARD ZONE)
# ==============================================================================
DT_CAMERA = 1.0 / 30.0

K_CAMERA = np.array([
    [1000.0,    0.0, 960.0],
    [   0.0, 1000.0, 540.0],
    [   0.0,    0.0,   1.0]
])

CAMERAS_EXTRINSICS = {
    "MIRROR_R": {
        "position": [WHEELBASE_TRACTOR * 0.97, -(CAB_HALF_W + 0.10), 2.2],
        "pitch_deg": -15.0,
        "yaw_deg": -165.0,
        "roll_deg": 0.0,
        "monitored_blind_zones": ["surround_hazard"]
    },
    "MIRROR_L": {
        "position": [WHEELBASE_TRACTOR * 0.97, (CAB_HALF_W + 0.10), 2.2],
        "pitch_deg": -15.0,
        "yaw_deg": 165.0,
        "roll_deg": 0.0,
        "monitored_blind_zones": ["surround_hazard"]
    },
    "FRONT_CAM": {
        "position": [CAB_FRONT_X, 0.0, 2.5],
        "pitch_deg": -10.0,
        "yaw_deg": 0.0,
        "roll_deg": 0.0,
        "monitored_blind_zones": ["surround_hazard", "stopping_hazard"]
    }
}
