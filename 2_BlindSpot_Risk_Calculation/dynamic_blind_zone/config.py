# ==============================================================================
# CONFIG.PY - CẤU HÌNH DYNAMIC HAZARD ZONE (DHZ)
# ==============================================================================
import numpy as np

# ==============================================================================
# [BƯỚC 1]: THÔNG SỐ SỔ ĐĂNG KIỂM (CƠ BẢN)
# ==============================================================================
WHEELBASE_TRACTOR = 3.6  # [L_f] Chiều dài cơ sở đầu kéo (m)
CAB_WIDTH = 2.5          # [W_cab] Chiều rộng tổng thể cabin (m)
L_TRAIL = 12.0           # Chiều dài thân rơ-moóc dùng để dựng polygon (m)
W_TRAIL = 2.5            # Chiều rộng thùng rơ-moóc (m)
TRAILER_KINGPIN_TO_AXLE = 8.0  # Chiều dài động học: kingpin -> tâm cụm trục trailer (m)
                                # Giá trị demo; PHẢI thay bằng số đo xe thực tế.

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
# [BƯỚC 3]: THÔNG SỐ LEGACY CHỈ DÙNG CHO DEMO QUÃNG DỪNG CŨ
# Không được dùng các hằng số này để dựng DHZ.
# ==============================================================================
REACTION_TIME = 1.5
FRICTION_COEFF = 0.7
GRAVITY = 9.81
MECHANICAL_MAX_GAMMA_DEG = 65.0
STEER_RATIO = 16.0

# ============================================================================
# DYNAMIC HAZARD ZONE (DHZ)
# ============================================================================
# DHZ = predicted swept occupancy + dynamic physical clearance.
# Không phải điểm mù quang học, stopping distance hay object-level risk.
DHZ_PREDICTION_HORIZON_SEC = 0.5
DHZ_INTEGRATION_DT_SEC = 0.05
DHZ_MIN_MOVING_SPEED_MPS = 0.5

# Clearance cơ sở và phần tăng động. Phần tăng được tính từ:
# 0.5 * |a_y(measured) - v*yaw_rate| * T_clearance^2, rồi giới hạn.
DHZ_BASE_CLEARANCE_M = 1.50
DHZ_CLEARANCE_RESPONSE_SEC = 0.50
DHZ_MAX_DYNAMIC_CLEARANCE_M = 0.75

# Chỉ dùng để gắn cờ chất lượng trạng thái, không âm thầm sửa số đo.
DHZ_MAX_LATERAL_ACCEL_MPS2 = 3.0
DHZ_MAX_STATIONARY_YAW_RATE_RAD_S = 0.05

# Legacy: chỉ phục vụ visualizer cũ, không tham gia dhz_calculator.py.
LATERAL_DISPERSION_DEG = 3.5

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
        "monitored_blind_zones": ["near_field_hazard"]
    },
    "MIRROR_L": {
        "position": [WHEELBASE_TRACTOR * 0.97, (CAB_HALF_W + 0.10), 2.2],
        "pitch_deg": -15.0,
        "yaw_deg": 165.0,
        "roll_deg": 0.0,
        "monitored_blind_zones": ["near_field_hazard"]
    },
    "FRONT_CAM": {
        "position": [CAB_FRONT_X, 0.0, 2.5],
        "pitch_deg": -10.0,
        "yaw_deg": 0.0,
        "roll_deg": 0.0,
        "monitored_blind_zones": ["near_field_hazard", "stopping_hazard"]
    }
}
