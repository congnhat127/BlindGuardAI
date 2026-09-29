"""
Module: risk_models.py
Phân hệ: 2_BlindSpot_Risk_Calculation / bsri_engine
Mô tả: Định nghĩa các kiểu dữ liệu, Enum và cấu trúc trạng thái phục vụ tính toán
       Chỉ số Rủi ro Điểm mù (Blind-Spot Risk Index - BSRI) cho xe tải hạng nặng.
Tiêu chuẩn:
- Hệ tọa độ xe (Vehicle Coordinate System - VCS): ISO 8855 / SAE J670
- Phân cấp cảnh báo ADAS theo ISO 15622 / UNECE R151 (Blind Spot Information System - BSIS)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple, List


class RiskLevel(Enum):
    """
    Cấp độ rủi ro va chạm tổng thể (BSRI Level).
    Mỗi cấp độ định nghĩa mã màu (BGR cho OpenCV, HEX cho Web/HUD) và hướng dẫn xử lý.
    """
    SAFE = (0, "AN TOÀN", (0, 220, 0), "#00DC00", "Không có nguy cơ va chạm trong tầm hoạt động.")
    CAUTION = (1, "CHÚ Ý", (0, 230, 255), "#FFE600", "Đối tượng tiếp cận gần vùng đệm an toàn, cần theo dõi.")
    WARNING = (2, "CẢNH BÁO", (0, 140, 255), "#FF8C00", "Nguy cơ va chạm cao trong 2-3 giây tới, chuẩn bị phanh/đánh lái.")
    CRITICAL = (3, "NGUY HIỂM KHẨN CẤP", (0, 0, 255), "#FF0000", "Va chạm cận kề (< 1.5 giây) hoặc đã xâm nhập vùng xe quét qua! Kích hoạt phanh/còi khẩn cấp.")

    def __init__(self, code: int, label_vi: str, color_bgr: Tuple[int, int, int], color_hex: str, description: str):
        self.code = code
        self.label_vi = label_vi
        self.color_bgr = color_bgr
        self.color_hex = color_hex
        self.description = description


class BlindSpotZone(Enum):
    """
    Phân vùng điểm mù hình học quanh xe đầu kéo & rơ-moóc theo tiêu chuẩn UNECE R46 / R151.
    """
    CAB_FRONT = "Mũi xe (Gầm cabin trước - Class VI)"
    MIRROR_RIGHT = "Hông phụ (Điểm mù gương phải - Class IV/V)"
    MIRROR_LEFT = "Hông lái (Điểm mù gương trái - Class IV/V)"
    SWEPT_PATH_RIGHT = "Bụng cua rơ-moóc phải (Swept Path lấn lề)"
    SWEPT_PATH_LEFT = "Bụng cua rơ-moóc trái (Swept Path lấn lề)"
    REAR_TRAILER = "Đuôi rơ-moóc (Điểm mù sau)"
    CLEAR_ZONE = "Vùng thoáng (Ngoài điểm mù)"


@dataclass
class EgoVehicleState:
    """
    Trạng thái động học của xe chủ (Ego Vehicle) từ cảm biến GPS/GNSS, IMU và Vô-lăng.
    Hệ tọa độ VCS: Gốc tại tâm trục sau đầu kéo, X+ hướng tiến, Y+ hướng sang trái.
    """
    speed_mps: float = 0.0              # Vận tốc dọc có dấu (m/s): > 0 tiến, < 0 lùi
    yaw_rate_rad_s: float = 0.0         # Tốc độ quay góc yaw r (rad/s): > 0 rẽ trái, < 0 rẽ phải
    steering_angle_deg: float = 0.0     # Góc bẻ lái vô lăng (độ): > 0 rẽ trái, < 0 rẽ phải
    accel_x_mps2: float = 0.0           # Gia tốc dọc (m/s2): > 0 tăng tốc, < 0 giảm tốc/phanh
    accel_y_mps2: float = 0.0           # Gia tốc ngang (m/s2): > 0 lạng trái, < 0 lạng phải
    turn_signal: str = "OFF"            # Trạng thái xi-nhan: "OFF", "LEFT", "RIGHT", "HAZARD"
    trailer_gamma_rad: float = 0.0      # Góc gập rơ-moóc thực tế hoặc ước tính (rad)
    gear: str = "D"                     # Số hiện tại: "D" (Tiến), "R" (Lùi), "N", "P"


@dataclass
class TrackedObstacle:
    """
    Thông tin đối tượng chướng ngại vật được nhận diện và theo dõi bởi Module 1 (YOLO + ByteTrack)
    sau khi đã được chiếu sang Hệ tọa độ xe VCS (mét) bằng ma trận Homography.
    """
    track_id: int                                   # ID định danh duy nhất từ ByteTrack
    class_name: str                                 # Tên class: 'person', 'bicycle', 'motorcycle', 'car', 'truck', 'bus', 'xe_keo', 'xich_lo'
    confidence: float                               # Độ tin cậy AI (0.0 -> 1.0)
    bbox_xyxy: Tuple[float, float, float, float]    # Tọa độ pixel (x1, y1, x2, y2) trên ảnh camera
    vcs_x: float                                    # Tọa độ X trên mặt đất (mét, trục dọc: tiến > 0, lùi < 0)
    vcs_y: float                                    # Tọa độ Y trên mặt đất (mét, trục ngang: trái > 0, phải < 0)
    vel_x: float = 0.0                              # Vận tốc tương đối dọc trục X (m/s)
    vel_y: float = 0.0                              # Vận tốc tương đối dọc trục Y (m/s)
    distance_m: float = 0.0                         # Khoảng cách Euclid thẳng tới gốc xe sqrt(x^2 + y^2)

    def __post_init__(self):
        if self.distance_m <= 0.0:
            self.distance_m = float((self.vcs_x ** 2 + self.vcs_y ** 2) ** 0.5)


@dataclass
class BSRIResult:
    """
    Kết quả đánh giá rủi ro BSRI chi tiết cho từng đối tượng chướng ngại vật.
    """
    track_id: int
    class_name: str
    bsri_score: float                           # Điểm rủi ro tổng hợp chuẩn hóa (0.00 -> 1.00)
    risk_level: RiskLevel                       # Cấp độ cảnh báo (SAFE, CAUTION, WARNING, CRITICAL)
    zone: BlindSpotZone                         # Phân vùng không gian đang hiện diện
    is_in_dhz: bool                             # Có nằm trực tiếp bên trong Vùng Nguy Hiểm Động (DHZ) không
    dist_to_dhz: float                          # Khoảng cách mét tới đường biên viền của DHZ (0.0 nếu nằm trong)
    ttc_seconds: Optional[float]                # Thời gian ước tính tới va chạm Time-To-Collision (giây)
    vru_weight: float                           # Trọng số tổn thương của loại đối tượng (VRU Severity)
    spatial_risk: float                         # Điểm rủi ro không gian (Spatial Proximity Risk)
    temporal_risk: float                        # Điểm rủi ro thời gian (Kinematic TTC Risk)
    maneuver_factor: float                      # Hệ số rủi ro do thao tác của xe chủ (Ego turning/accelerating)
    blind_factor: float                         # Hệ số khuếch đại do nằm trong điểm mù quang học
    explanation: str                            # Giải thích ngữ cảnh ngắn gọn hiển thị trên màn hình Cabin/HUD
    recommendation: str                         # Khuyến nghị hành động tức thời cho tài xế xe tải

