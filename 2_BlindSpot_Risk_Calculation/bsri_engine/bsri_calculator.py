"""
Module: bsri_calculator.py
Phân hệ: 2_BlindSpot_Risk_Calculation / bsri_engine
Mô tả: Bộ tính toán Chỉ số Rủi ro Điểm mù (Blind-Spot Risk Index - BSRI) thời gian thực
       kết hợp Động lực học xe (DHZ), Dự đoán va chạm (TTC), Hệ số ưu tiên nhóm đối tượng (C_vru),
       và Điểm mù quang học (Blind Spot Geometry).
Cơ sở lý thuyết & Chuẩn tham chiếu:
- Quy ước hệ tọa độ xe VCS: ISO 8855 / SAE J670 (Gốc tại tâm trục sau là lựa chọn thiết kế).
- Khái niệm điểm mù gián tiếp: Tham chiếu UNECE R46 (các phân vùng gương Class IV, V, VI).
- Khái niệm cảnh báo điểm mù & chuyển làn: Lấy cảm hứng từ UNECE R151, ISO 15623, ISO 22839 và mở rộng cho giao thông hỗn hợp tại Việt Nam.
- Các tham số tính toán nội bộ (weights, thresholds) thuộc nhóm Engineering Calibration Parameters.
"""

import math
from typing import List, Optional, Tuple, Dict, Any
import numpy as np
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

try:
    from .risk_models import RiskLevel, BlindSpotZone, EgoVehicleState, TrackedObstacle, BSRIResult, VehicleType
except ImportError:
    from risk_models import RiskLevel, BlindSpotZone, EgoVehicleState, TrackedObstacle, BSRIResult, VehicleType


class BSRICalculator:
    """
    Bộ xử lý tính toán Chỉ số Nguy cơ Điểm mù BSRI (Blind-Spot Risk Index Engine).
    
    Đầu vào:
    1. Trạng thái động học xe chủ (vận tốc dọc v, tốc độ quay góc yaw r, xi-nhan, gia tốc a_x).
    2. Danh sách đối tượng chướng ngại vật theo dõi từ Module 1 (tọa độ VCS X, Y mét, vận tốc tương đối vx, vy).
    
    Đầu ra:
    - BSRI Score (0.00 -> 1.00) cho từng đối tượng và toàn bộ phân cảnh.
    - Cấp độ cảnh báo (SAFE, CAUTION, WARNING, CRITICAL) sẵn sàng chuyển xuống ESP32 kích hoạt còi/LED.
    - Chuỗi giải thích ngữ cảnh phục vụ màn hình Cabin HUD (Explainable AI).
    """

    # Hệ số ưu tiên nhóm đối tượng C_vru (Class Vulnerability Factor)
    # Phân loại chuẩn hóa theo định nghĩa an toàn giao thông quốc tế (WHO / UNECE / Euro NCAP):
    # 1. Nhóm VRU (Vulnerable Road Users - KHÔNG CÓ KHUNG VỎ BẢO VỆ):
    #    Tất cả person, motorcycle, bicycle, xe_keo, xich_lo đều có C_vru = 1.00
    #    (Đồng hạng rủi ro sinh mạng tối đa: khi va chạm với xe tải nặng 15-40 tấn,
    #     người đi xe máy và người đi bộ đều không có khung kim loại hay túi khí bảo vệ,
    #     khả năng tử vong / thương tật nghiêm trọng là tương đương).
    # 2. Nhóm có khung vỏ bảo vệ (Enclosed Vehicles): car = 0.70 (cabin thép, đai an toàn, túi khí).
    # 3. Nhóm xe lớn (Heavy Vehicles): truck = 0.60, bus = 0.65 (đối trọng kích thước & khối lượng).
    VRU_WEIGHTS: Dict[str, float] = {
        "person": 1.00,        # Người đi bộ (VRU): Không có khung vỏ bảo vệ
        "motorcycle": 1.00,    # Xe máy (VRU): Không có khung vỏ bảo vệ, rủi ro sinh mạng tương đương người đi bộ
        "bicycle": 1.00,       # Xe đạp (VRU): Không có khung vỏ bảo vệ
        "xe_keo": 1.00,        # Xe kéo hàng (VRU): Không có khung vỏ bảo vệ, người kéo đi bộ
        "xich_lo": 1.00,       # Xích lô (VRU): Không có khung vỏ bảo vệ
        "car": 0.70,           # Ô tô con: Có cabin thép, đai an toàn và túi khí bảo vệ
        "truck": 0.60,         # Xe tải khác: Tương đương kích thước và khối lượng
        "bus": 0.65            # Xe buýt: Khối lượng lớn
    }

    # Ngưỡng phân loại cấp độ rủi ro (Risk Thresholds)
    THRESH_CRITICAL = 0.80     # BSRI >= 0.80 -> NGUY HIỂM KHẨN CẤP (Phanh/Còi)
    THRESH_WARNING = 0.55      # 0.55 <= BSRI < 0.80 -> CẢNH BÁO (Rung vô lăng / Chuông)
    THRESH_CAUTION = 0.30      # 0.30 <= BSRI < 0.55 -> CHÚ Ý (Đèn vàng HUD)

    def __init__(self,
                 vehicle_type: str = "ARTICULATED",
                 wheelbase_tractor: float = 3.6,
                 cab_width: float = 2.5,
                 trailer_length: float = 12.0,
                 trailer_width: float = 2.5,
                 rigid_front_length: float = 7.8,
                 rigid_rear_length: float = 2.4,
                 rigid_width: float = 2.5,
                 rigid_wheelbase: float = 5.8,
                 base_clearance: float = 1.5,
                 spatial_weight: float = 0.45,
                 temporal_weight: float = 0.55):
        """
        Khởi tạo bộ tính toán BSRI hỗ trợ cả xe đầu kéo rơ-moóc (ARTICULATED) và xe tải liền thân (RIGID).
        :param vehicle_type: "ARTICULATED" (đầu kéo rơ-moóc) hoặc "RIGID" (xe tải liền thân)
        :param wheelbase_tractor: Chiều dài cơ sở đầu kéo (m, mặc định 3.6m)
        :param cab_width: Chiều rộng cabin (m, mặc định 2.5m)
        :param trailer_length: Chiều dài thùng rơ-moóc (m, mặc định 12.0m)
        :param trailer_width: Chiều rộng thùng rơ-moóc (m, mặc định 2.5m)
        :param rigid_front_length: Khoảng cách từ tâm trục sau tới cản trước xe liền thân (m, mặc định 7.8m)
        :param rigid_rear_length: Khoảng cách từ tâm trục sau tới cản sau xe liền thân (m, mặc định 2.4m)
        :param rigid_width: Chiều rộng thùng xe liền thân (m, mặc định 2.5m)
        :param rigid_wheelbase: Chiều dài cơ sở xe liền thân (m, mặc định 5.8m)
        :param base_clearance: Khoảng đệm an toàn vật lý cơ sở (m, mặc định 1.5m)
        """
        if isinstance(vehicle_type, str):
            try:
                self.vehicle_type = VehicleType(vehicle_type.upper())
            except ValueError:
                self.vehicle_type = VehicleType(vehicle_type.lower())
        elif isinstance(vehicle_type, VehicleType):
            self.vehicle_type = vehicle_type
        else:
            self.vehicle_type = VehicleType.ARTICULATED

        # Thông số xe đầu kéo rơ-moóc
        self.L_f = float(wheelbase_tractor)
        self.W_c = float(cab_width)
        self.L_trail = float(trailer_length)
        self.W_trail = float(trailer_width)

        # Thông số xe tải liền thân (Rigid Truck)
        self.rigid_front_length = float(rigid_front_length)
        self.rigid_rear_length = float(rigid_rear_length)
        self.rigid_width = float(rigid_width)
        self.rigid_wheelbase = float(rigid_wheelbase)
        self.rigid_half_w = self.rigid_width / 2.0

        self.base_clearance = float(base_clearance)
        self.w_spatial = float(spatial_weight)
        self.w_temporal = float(temporal_weight)

        # Kích thước hình học thân xe đầu kéo trong hệ VCS (Gốc tại tâm trục sau đầu kéo)
        self.cab_half_w = self.W_c / 2.0
        self.trail_half_w = self.W_trail / 2.0
        self.cab_front_x = self.L_f + 0.40      # Mũi xe nhô trước trục trước 40cm
        self.cab_rear_x = self.L_f * 0.61       # Vách sau cabin
        self.d_hitch = self.L_f * 0.08          # Vị trí chốt kéo (hitch)
        self.trail_rear_x = self.d_hitch - self.L_trail # Đuôi rơ-moóc

    def build_vehicle_footprint(self, gamma: float = 0.0, vehicle_type: Optional[VehicleType] = None) -> Polygon:
        """
        Dựng đa giác hình chiếu thân xe (Vehicle Footprint) trong hệ VCS.
        - RIGID: Khối chữ nhật phẳng nguyên khối duy nhất.
        - ARTICULATED: 2 khối (Cabin + Rơ-moóc) gập góc gamma quanh khớp hitch.
        """
        vtype = vehicle_type or self.vehicle_type
        if isinstance(vtype, str):
            vtype = VehicleType(vtype.upper())

        if vtype == VehicleType.RIGID:
            return Polygon([
                (self.rigid_front_length, self.rigid_half_w),
                (self.rigid_front_length, -self.rigid_half_w),
                (-self.rigid_rear_length, -self.rigid_half_w),
                (-self.rigid_rear_length, self.rigid_half_w),
            ])

        # 1. Đa giác Cabin đầu kéo
        cab_poly = Polygon([
            (self.cab_front_x, self.cab_half_w),
            (self.cab_front_x, -self.cab_half_w),
            (self.cab_rear_x, -self.cab_half_w),
            (self.cab_rear_x, self.cab_half_w),
        ])

        # 2. Đa giác Khung gầm trục sau
        chassis_poly = Polygon([
            (self.cab_rear_x, self.W_c * 0.18),
            (self.cab_rear_x, -self.W_c * 0.18),
            (-0.30, -self.W_c * 0.18),
            (-0.30, self.W_c * 0.18),
        ])

        # 3. Đa giác Thùng rơ-moóc xoay quanh chốt kéo hitch (góc -gamma)
        hitch_x, hitch_y = self.d_hitch, 0.0
        front_trail = self.d_hitch + self.L_f * 0.25
        rear_trail = self.trail_rear_x
        
        base_trail_pts = [
            (front_trail, self.trail_half_w),
            (front_trail, -self.trail_half_w),
            (rear_trail, -self.trail_half_w),
            (rear_trail, self.trail_half_w),
        ]
        
        # Biến đổi xoay quanh khớp nối hitch
        c, s = math.cos(-gamma), math.sin(-gamma)
        rotated_trail_pts = []
        for px, py in base_trail_pts:
            rx = (px - hitch_x) * c - (py - hitch_y) * s + hitch_x
            ry = (px - hitch_x) * s + (py - hitch_y) * c + hitch_y
            rotated_trail_pts.append((rx, ry))
        trail_poly = Polygon(rotated_trail_pts)

        return unary_union([cab_poly, chassis_poly, trail_poly])

    def compute_dynamic_hazard_zone(self, ego: EgoVehicleState, horizon_sec: float = 0.50, steps: int = 5) -> Polygon:
        """
        Tính toán Đa giác Vùng Nguy Hiểm Động (Dynamic Hazard Zone - DHZ).
        - Đối với xe tải liền thân (RIGID): Áp dụng công thức lấn cua (inswing/off-tracking) theo chuẩn UNECE R151.
        - Đối với xe đầu kéo (ARTICULATED): Hợp nhất swept occupancy theo động học xoay khớp hitch.
        """
        vtype = getattr(ego, "vehicle_type", self.vehicle_type)
        if isinstance(vtype, str):
            vtype = VehicleType(vtype.upper())

        dyn_clearance = min(0.75, 0.5 * abs(ego.accel_y_mps2) * (0.5 ** 2))
        total_buffer = self.base_clearance + dyn_clearance

        if vtype == VehicleType.RIGID:
            base_fp = self.build_vehicle_footprint(vehicle_type=VehicleType.RIGID)

            # 1. Độ lấn cua bánh sau / sườn xe vào lòng cua (Inswing / Off-tracking)
            yaw_abs = abs(ego.yaw_rate_rad_s)
            spd = max(1.0, abs(ego.speed_mps))
            off_tracking = (self.rigid_wheelbase ** 2 * yaw_abs) / (2.0 * spd)

            # 2. Độ văng đuôi cản sau ra hướng ngược lại (Tail-Swing)
            # Khi xe rẽ, phần nhô sau trục bánh (rigid_rear_length) văng ngược sang làn đối diện
            tail_swing = self.rigid_rear_length * yaw_abs * horizon_sec

            lead_dist = max(0.0, ego.speed_mps) * horizon_sec
            is_turning_right = (ego.yaw_rate_rad_s < -0.03) or (ego.turn_signal == "RIGHT")
            is_turning_left = (ego.yaw_rate_rad_s > 0.03) or (ego.turn_signal == "LEFT")

            front_x = self.rigid_front_length + lead_dist
            rear_x = -self.rigid_rear_length

            # Mép bên sườn trước/giữa xe: lấn vào trong góc cua (Inswing)
            front_left_y = self.rigid_half_w + (off_tracking if is_turning_left else 0.0)
            front_right_y = -self.rigid_half_w - (off_tracking if is_turning_right else 0.0)

            # Mép cản sau xe: văng ngược chiều đánh lái (Tail-Swing)
            rear_left_y = self.rigid_half_w + (tail_swing if is_turning_right else 0.0)
            rear_right_y = -self.rigid_half_w - (tail_swing if is_turning_left else 0.0)

            # Đa giác quét tổng hợp bao gồm cả chém cua phía trước và văng đuôi phía sau
            swept_poly_pts = [
                (front_x, front_left_y),
                (front_x, front_right_y),
                (0.0, front_right_y),
                (rear_x, rear_right_y),
                (rear_x, rear_left_y),
                (0.0, front_left_y),
            ]
            swept_box = Polygon(swept_poly_pts)
            swept_poly = unary_union([base_fp, swept_box])
            return swept_poly.buffer(total_buffer, resolution=16)

        # ARTICULATED
        footprints = []
        gamma = ego.trailer_gamma_rad
        dt = horizon_sec / max(1, steps)

        for step in range(steps + 1):
            if self.L_trail > 0 and abs(ego.speed_mps) > 0.1:
                d_gamma = ego.yaw_rate_rad_s - (ego.speed_mps / self.L_trail) * math.sin(gamma)
                gamma += d_gamma * dt
            
            fp = self.build_vehicle_footprint(gamma, vehicle_type=VehicleType.ARTICULATED)
            footprints.append(fp)

        swept_poly = unary_union(footprints)
        return swept_poly.buffer(total_buffer, resolution=16)

    def classify_blind_spot_zone(self, x: float, y: float, ego: Optional[EgoVehicleState] = None) -> BlindSpotZone:
        """
        Phân loại đối tượng tại tọa độ (x, y) thuộc vào vùng điểm mù hình học nào của xe tải.
        Đối với xe đầu kéo (ARTICULATED), các vùng rơ-moóc (SWEPT_PATH, REAR_TRAILER) tự động
        được xoay quanh chốt mâm kéo (Kingpin) theo góc gập gamma thực tế của rơ-moóc.
        """
        vtype = getattr(ego, "vehicle_type", self.vehicle_type) if ego is not None else self.vehicle_type
        if isinstance(vtype, str):
            vtype = VehicleType(vtype.upper())

        gamma = float(getattr(ego, "trailer_gamma_rad", 0.0)) if ego is not None else 0.0

        if vtype == VehicleType.RIGID:
            # 1. Gầm cabin mũi xe (Class VI)
            if (self.rigid_wheelbase <= x <= self.rigid_front_length + 2.0) and (abs(y) <= self.rigid_half_w + 0.8):
                return BlindSpotZone.CAB_FRONT
            # 2. Hông phụ (Gương phải - Class IV/V)
            if (self.rigid_wheelbase * 0.4 <= x <= self.rigid_front_length) and (-3.5 <= y <= -self.rigid_half_w):
                return BlindSpotZone.MIRROR_RIGHT
            # 3. Hông lái (Gương trái - Class IV/V)
            if (self.rigid_wheelbase * 0.4 <= x <= self.rigid_front_length) and (self.rigid_half_w <= y <= 3.5):
                return BlindSpotZone.MIRROR_LEFT
            # 4. Sườn phải thùng xe (Vùng lấn cua khi xe rẽ phải)
            if (-self.rigid_rear_length <= x < self.rigid_wheelbase * 0.4) and (-4.5 <= y <= -self.rigid_half_w):
                return BlindSpotZone.SWEPT_PATH_RIGHT
            # 5. Sườn trái thùng xe (Vùng lấn cua khi xe rẽ trái)
            if (-self.rigid_rear_length <= x < self.rigid_wheelbase * 0.4) and (self.rigid_half_w <= y <= 4.5):
                return BlindSpotZone.SWEPT_PATH_LEFT
            # 6. Đuôi xe (Điểm mù lùi)
            if (-self.rigid_rear_length - 3.5 <= x < -self.rigid_rear_length) and (abs(y) <= self.rigid_half_w + 1.0):
                return BlindSpotZone.REAR_TRAILER
            return BlindSpotZone.CLEAR_ZONE

        # === ARTICULATED (XE ĐẦU KÉO SƠ-MI RƠ-MOÓC) ===
        # A. CÁC VÙNG GẮN VỚI CABIN & ĐẦU KÉO (Hệ tọa độ đầu kéo X, Y)
        # 1. Điểm mù trực diện gầm Cabin (Mũi xe - Class VI)
        if (self.L_f <= x <= self.cab_front_x + 2.0) and (abs(y) <= self.cab_half_w + 0.8):
            return BlindSpotZone.CAB_FRONT

        # 2. Hông phụ Cabin (Gương phải - Class IV/V) - Từ chốt kéo mâm xoay lên cản trước (Không chồng lấn)
        if (self.d_hitch <= x <= self.cab_front_x) and (-3.5 <= y <= -self.cab_half_w):
            return BlindSpotZone.MIRROR_RIGHT

        # 3. Hông lái Cabin (Gương trái - Class IV/V) - Từ chốt kéo mâm xoay lên cản trước (Không chồng lấn)
        if (self.d_hitch <= x <= self.cab_front_x) and (self.cab_half_w <= y <= 3.5):
            return BlindSpotZone.MIRROR_LEFT

        # B. CÁC VÙNG GẮN VỚI THÙNG RƠ-MOÓC (Xoay theo góc gập gamma quanh chốt mâm kéo Kingpin)
        # Chuyển đổi tọa độ (x, y) sang hệ tọa độ cục bộ của rơ-moóc:
        c_g = math.cos(gamma)
        s_g = math.sin(gamma)
        dx = x - self.d_hitch
        dy = y - 0.0
        x_tr = dx * c_g - dy * s_g + self.d_hitch
        y_tr = dx * s_g + dy * c_g

        # 4. Bụng cua rơ-moóc bên phải (Swept path bám theo sườn rơ-moóc xoay)
        if (self.trail_rear_x <= x_tr < self.d_hitch) and (-4.5 <= y_tr <= -self.trail_half_w):
            return BlindSpotZone.SWEPT_PATH_RIGHT

        # 5. Bụng cua rơ-moóc bên trái (Swept path bám theo sườn rơ-moóc xoay)
        if (self.trail_rear_x <= x_tr < self.d_hitch) and (self.trail_half_w <= y_tr <= 4.5):
            return BlindSpotZone.SWEPT_PATH_LEFT

        # 6. Đuôi rơ-moóc (Điểm mù lùi bám theo hướng đuôi rơ-moóc xoay)
        if (self.trail_rear_x - 3.5 <= x_tr < self.trail_rear_x) and (abs(y_tr) <= self.trail_half_w + 1.0):
            return BlindSpotZone.REAR_TRAILER

        return BlindSpotZone.CLEAR_ZONE


    def calculate_temporal_risk(self, obs: TrackedObstacle, ego: EgoVehicleState) -> Tuple[float, Optional[float]]:
        """
        Tính toán rủi ro thời gian dựa trên Vận tốc tiếp cận (Closing Velocity) và Thời gian tới va chạm (TTC).
        :return: (temporal_risk_score [0.0..1.0], ttc_seconds hoặc None)
        """
        r = obs.distance_m
        if r <= 0.2:
            return 1.0, 0.1

        # Vận tốc tiếp cận tương đối hướng tâm (Closing Velocity)
        # obs.vel_x và obs.vel_y từ Camera AI (sai phân tọa độ VCS) vốn dĩ ĐÃ LÀ VẬN TỐC TƯƠNG ĐỐI.
        # v_closing > 0 nghĩa là khoảng cách đang thu hẹp lại (đối tượng đang lao về phía xe).
        v_closing = - (obs.vcs_x * obs.vel_x + obs.vcs_y * obs.vel_y) / r

        if v_closing > 0.15:
            ttc = r / v_closing
            # Đường cong suy giảm rủi ro thời gian dựa trên các ngưỡng khởi tạo kỹ thuật:
            # - TTC_critical = 1.2s: Ngưỡng khẩn cấp (tương ứng tổng thời gian phản xạ người lái ~0.8s + độ trễ phanh khí nén xe tải ~0.4s).
            # - TTC_warning = 3.5s: Ngưỡng cảnh báo sớm phục vụ người lái chuẩn bị rà phanh/chuyển làn.
            # Lưu ý: Các ngưỡng này là Engineering Calibration Parameters, sẽ được hiệu chỉnh trên bãi thử.
            if ttc <= 1.2:
                s_temporal = 1.0
            elif ttc <= 3.5:
                # Tuyến tính từ 1.0 giảm xuống 0.30 khi TTC từ 1.2s -> 3.5s
                s_temporal = 1.0 - 0.70 * ((ttc - 1.2) / (3.5 - 1.2))
            else:
                # Sau 3.5s rủi ro giảm hàm mũ
                s_temporal = 0.30 * math.exp(- (ttc - 3.5) / 3.0)
            return float(np.clip(s_temporal, 0.0, 1.0)), round(float(ttc), 2)
        else:
            # Đối tượng đứng yên hoặc đang đi xa dần -> Không có nguy cơ va chạm khẩn về thời gian
            # Rủi ro thời gian phụ thuộc thuần túy vào khoảng cách cận kề (Proximity baseline)
            s_temporal = 0.20 * math.exp(- r / 4.0)
            return float(np.clip(s_temporal, 0.0, 0.40)), None

    def calculate_ego_maneuver_factor(self, obs: TrackedObstacle, ego: EgoVehicleState) -> float:
        """
        Tính hệ số khuếch đại rủi ro dựa trên thao tác lái của xe chủ (Ego Maneuver).
        Ví dụ: Xe đang xi-nhan phải và đánh lái sang phải trong khi có xe máy bên hông phải -> Rủi ro tăng vọt.
        """
        factor = 1.0

        is_turning_right = (ego.yaw_rate_rad_s < -0.03) or (ego.turn_signal == "RIGHT") or (ego.steering_angle_deg < -5.0)
        is_turning_left = (ego.yaw_rate_rad_s > 0.03) or (ego.turn_signal == "LEFT") or (ego.steering_angle_deg > 5.0)
        is_reversing = (ego.gear == "R") or (ego.speed_mps < -0.2)

        # 1. Xe rẽ phải và đối tượng ở bên phải (Y < 0)
        if is_turning_right and obs.vcs_y < 0.0:
            factor *= 1.35

        # 2. Xe rẽ trái và đối tượng ở bên trái (Y > 0)
        elif is_turning_left and obs.vcs_y > 0.0:
            factor *= 1.35

        # 3. Xe đang lùi và đối tượng ở phía sau (X < 0)
        if is_reversing and obs.vcs_x < 0.0:
            factor *= 1.40

        # 4. Phân biệt tác động của PHANH GẤP theo vị trí trước / sau (ISO 22839 / UNECE R158):
        if ego.accel_x_mps2 < -1.5:
            if obs.vcs_x >= 0.0:
                # Vật cản phía TRƯỚC/BÊN HÔNG: Phanh giúp giảm nguy cơ va chạm
                factor *= 0.85
            else:
                # Vật cản phía SAU ĐUÔI: Phanh gấp làm TĂNG nguy cơ bị đâm đuôi (Rear-end collision)
                factor *= 1.25

        return factor

    def calculate_blind_spot_factor(self, zone: BlindSpotZone) -> float:
        """
        Tính hệ số khuếch đại do đối tượng nằm trong các góc mù nguy hiểm của tài xế.
        """
        if zone in [BlindSpotZone.MIRROR_RIGHT, BlindSpotZone.SWEPT_PATH_RIGHT]:
            return 1.25  # Góc mù bên phụ nguy hiểm nhất
        elif zone == BlindSpotZone.CAB_FRONT:
            return 1.20  # Mũi xe gầm cao tài xế hoàn toàn không thấy
        elif zone == BlindSpotZone.REAR_TRAILER:
            return 1.20  # Sau thùng rơ-moóc
        elif zone in [BlindSpotZone.MIRROR_LEFT, BlindSpotZone.SWEPT_PATH_LEFT]:
            return 1.10  # Góc mù bên lái
        else:
            return 0.85  # Ngoài góc mù (tài xế nhìn thấy trực tiếp qua kính chắn gió/cửa sổ)

    def check_special_scenarios(self, obs: TrackedObstacle, ego: EgoVehicleState) -> Optional[Tuple[float, RiskLevel, str, str]]:
        """
        Kiểm tra và xử lý ưu tiên 5 kịch bản giao thông đặc biệt (Fast-Path Safety Gatekeeper).
        Được thiết kế dựa trên các tình huống va chạm nguy cấp lấy cảm hứng từ UNECE R159 (MOIS),
        UNECE R151 (BSIS), UNECE R158 (Reversing) và mở rộng cho giao thông hỗn hợp tại Việt Nam.

        5 Kịch bản:
            1. Moving-off front hazard (Lấy cảm hứng từ UNECE R159 MOIS) - Dừng đèn đỏ, VRU sát cản trước.
            2. Turning-side pinch hazard (Lấy cảm hứng từ UNECE R151 BSIS) - Dừng/bò chuẩn bị rẽ, VRU ở sườn phụ.
            3. Reverse hazard (Lấy cảm hứng từ UNECE R158) - Lùi xe có vật cản sau đuôi.
            4. Parallel close-proximity hazard - Chạy song song tốc độ cao cự ly cực hẹp.
            5. Trailer cornering scissors occlusion - Cua gắt rơ-moóc che khuất tầm nhìn gương chiếu hậu.

        :return: (bsri_score, risk_level, explanation, recommendation) nếu thỏa mãn; None nếu bình thường.
        """
        vtype = getattr(ego, "vehicle_type", self.vehicle_type)
        if isinstance(vtype, str):
            vtype = VehicleType(vtype.upper())

        if vtype == VehicleType.RIGID:
            ego_front_x = self.rigid_front_length
            ego_rear_x = -self.rigid_rear_length
            cab_half_w = self.rigid_half_w
        else:
            ego_front_x = self.cab_front_x
            ego_rear_x = self.trail_rear_x
            cab_half_w = self.cab_half_w

        is_standstill = abs(ego.speed_mps) < 0.20
        is_vru = obs.class_name.lower() in ["person", "motorcycle", "bicycle", "xe_keo", "xich_lo"]

        # ƯU TIÊN 1: KỊCH BẢN 3 - UNECE R158 REVERSING (LÙI BẾN BÃI)
        is_reversing = (ego.speed_mps < -0.10) or (ego.gear == "R")
        if is_reversing and (obs.vcs_x < ego_rear_x):
            d_rear = abs(obs.vcs_x - ego_rear_x)
            if d_rear <= 2.50 and abs(obs.vcs_y) <= (cab_half_w + 0.60):
                bsri = 0.950
                exp = (
                    f"NGUY HIỂM TỐI CẤP! [ĐIỂM MÙ LÙI R158] Có {obs.class_name} #{obs.track_id} "
                    f"đứng ngay sau đuôi xe ({d_rear:.1f}m)! Tầm nhìn sau bằng 0!"
                )
                rec = "ĐẠP PHANH DỪNG XE NGAY LẬP TỨC! KHÔNG ĐƯỢC TIẾP TỤC LÙI!"
                return bsri, RiskLevel.CRITICAL, exp, rec

        # ƯU TIÊN 2: KỊCH BẢN 1 - UNECE R159 MOIS (DỪNG ĐÈN ĐỎ & SÁT CẢN TRƯỚC)
        in_front_bumper = (ego_front_x <= obs.vcs_x <= ego_front_x + 1.80) and (abs(obs.vcs_y) <= cab_half_w + 0.30)
        if is_standstill and in_front_bumper and is_vru:
            d_front = max(0.10, obs.vcs_x - ego_front_x)
            ttc_takeoff = math.sqrt((2.0 * d_front) / 1.20)
            vru_w = self.VRU_WEIGHTS.get(obs.class_name.lower(), 0.85)
            raw_score = 1.00 * vru_w * 1.20 * 1.25
            bsri = round(float(min(1.0, max(0.85, raw_score))), 3)
            exp = (
                f"KHẨN CẤP! [MOIS R159] {obs.class_name} #{obs.track_id} ĐỖ SÁT CẢN TRƯỚC ({d_front:.1f}m, "
                f"TTC đề-pa: {ttc_takeoff:.1f}s)! Mũi xe che khuất hoàn toàn!"
            )
            rec = "GIỮ CHẶT CHÂN PHANH! KHÔNG ĐƯỢC XUẤT PHÁT! BẤM CÒI CẢNH BÁO CHO ĐỐI TƯỢNG TRÁNH ĐƯỜNG!"
            return bsri, RiskLevel.CRITICAL, exp, rec

        # ƯU TIÊN 3: KỊCH BẢN 2 - UNECE R151 BSIS (BẪY KẸP CUA SƯỜN PHẢI)
        is_turning_right = (ego.yaw_rate_rad_s < -0.03) or (ego.turn_signal == "RIGHT")
        in_pinch_x = (ego_rear_x <= obs.vcs_x <= ego_front_x * 0.70)
        in_pinch_y = (-2.50 <= obs.vcs_y <= -cab_half_w)
        if (is_turning_right or (is_standstill and obs.distance_m < 2.0)) and in_pinch_x and in_pinch_y and is_vru:
            bsri = 0.850
            lateral_gap = abs(obs.vcs_y) - cab_half_w
            exp = (
                f"CẢNH BÁO KHẨN! [BẪY KẸP CUA R151] {obs.class_name} #{obs.track_id} dừng sát sườn phụ "
                f"(cách hông {lateral_gap:.1f}m)! Bánh sau sẽ chém trúng khi ôm cua!"
            )
            rec = "GIỮ PHANH CHỜ XE MÁY ĐI HẾT HOẶC MỞ RỘNG GÓC CUA! BẤM CÒI CẢNH BÁO!"
            return bsri, RiskLevel.CRITICAL, exp, rec

        # ƯU TIÊN 4: KỊCH BẢN 4 - NGUY HIỂM CHẠY ÁP SÁT SONG SONG CỰ LY CỰC HẸP TỐC ĐỘ CAO
        # Khi hai phương tiện chạy song song cùng chiều ở tốc độ cao, v_closing ~ 0 khiến TTC vô hiệu.
        # Khoảng cách ngang d_lat cực nhỏ (< 0.8m) là tình huống nguy cơ cao do nhiễu động khí động học và biên độ lạng lái hẹp.
        r = obs.distance_m
        v_clos = - (obs.vcs_x * obs.vel_x + obs.vcs_y * obs.vel_y) / max(0.1, r)
        d_lat = abs(obs.vcs_y) - cab_half_w
        in_flank_x = (ego_rear_x <= obs.vcs_x <= ego_front_x)
        if (ego.speed_mps >= 8.0) and (0.0 <= d_lat <= 0.80) and in_flank_x and is_vru and (abs(v_clos) <= 0.50):
            s_lateral = math.exp(-max(0.0, d_lat) / 0.40)
            bsri = round(float(min(1.0, 0.65 + 0.35 * s_lateral)), 3)
            r_level = RiskLevel.CRITICAL if bsri >= 0.80 else RiskLevel.WARNING
            exp = (
                f"CẢNH BÁO! [KẸP SƯỜN TỐC ĐỘ CAO] {obs.class_name} #{obs.track_id} chạy áp sát sườn "
                f"({d_lat:.1f}m)! Nguy cơ mất an toàn do cự ly ngang quá hẹp và nhiễu động gió!"
            )
            rec = "GIỮ VÔ-LĂNG THẲNG! TUYỆT ĐỐI KHÔNG ĐÁNH LÁI GẤP SANG PHẢI! GIẢM TỐC TỪ TỪ!"
            return bsri, r_level, exp, rec

        # ƯU TIÊN 5: KỊCH BẢN 5 - CHE KHUẤT TẦM NHÌN GƯƠNG KHI VÀO CUA GẮT
        is_sharp_turn = abs(ego.yaw_rate_rad_s) > 0.08
        if is_sharp_turn and (-2.50 <= obs.vcs_y <= -cab_half_w) and in_flank_x:
            bsri = 0.820
            exp = (
                f"CẢNH BÁO KHẨN! [MẤT GÓC GƯƠNG] Xe đang ôm cua gắt (tốc độ góc {abs(ego.yaw_rate_rad_s):.2f} rad/s) "
                f"che khuất gương phụ! Có {obs.class_name} #{obs.track_id} trong khe mù!"
            )
            rec = "CHÚ Ý QUAN SÁT! TRẢ BỚT LÁI ĐỂ MỞ RỘNG TẦM NHÌN!"
            return bsri, RiskLevel.CRITICAL, exp, rec

        return None

    def evaluate_obstacle(self,
                          arg1: Any,
                          arg2: Optional[Any] = None,
                          dhz_poly: Optional[Polygon] = None) -> BSRIResult:
        """
        Tính toán chỉ số BSRI đầy đủ cho 1 đối tượng chướng ngại vật.
        Hỗ trợ gọi linh hoạt:
          - evaluate_obstacle(obs, ego, dhz_poly)
          - evaluate_obstacle(obs, ego)
          - evaluate_obstacle(ego, obs)
        """
        if isinstance(arg1, TrackedObstacle):
            obs = arg1
            ego = arg2
        elif isinstance(arg1, EgoVehicleState):
            ego = arg1
            obs = arg2
        else:
            obs = arg1
            ego = arg2

        # =========================================================================
        # BƯỚC 0: KIỂM TRA LỚP LỌC ƯU TIÊN 5 KỊCH BẢN ĐẶC BIỆT (FAST-PATH GATEKEEPER)
        # =========================================================================
        special_result = self.check_special_scenarios(obs, ego)
        if special_result is not None:
            bsri_score, risk_level, explanation, recommendation = special_result
            zone = self.classify_blind_spot_zone(obs.vcs_x, obs.vcs_y, ego)
            vru_w = self.VRU_WEIGHTS.get(obs.class_name.lower(), 0.70)
            return BSRIResult(
                track_id=obs.track_id,
                class_name=obs.class_name,
                bsri_score=bsri_score,
                risk_level=risk_level,
                zone=zone,
                is_in_dhz=True if risk_level == RiskLevel.CRITICAL else False,
                dist_to_dhz=0.0 if risk_level == RiskLevel.CRITICAL else 0.5,
                ttc_seconds=0.5 if risk_level == RiskLevel.CRITICAL else None,
                vru_weight=vru_w,
                spatial_risk=1.00 if risk_level == RiskLevel.CRITICAL else 0.70,
                temporal_risk=1.00 if risk_level == RiskLevel.CRITICAL else 0.70,
                maneuver_factor=1.35,
                blind_factor=self.calculate_blind_spot_factor(zone),
                explanation=explanation,
                recommendation=recommendation
            )

        if dhz_poly is None:
            dhz_poly = self.compute_dynamic_hazard_zone(ego)

        pt = Point(obs.vcs_x, obs.vcs_y)

        # 1. Rủi ro Không gian (Spatial Risk) & Kiểm tra xâm nhập DHZ
        is_in_dhz = bool(dhz_poly.contains(pt))

        if is_in_dhz:
            dist_to_dhz = 0.0
            spatial_risk = 1.0
        else:
            dist_to_dhz = float(dhz_poly.distance(pt))
            # Suy giảm hàm mũ theo khoảng cách tới biên DHZ (d0 = 1.8m)
            spatial_risk = math.exp(- dist_to_dhz / 1.80)

        # 2. Rủi ro Thời gian (Temporal Risk & TTC)
        temporal_risk, ttc = self.calculate_temporal_risk(obs, ego)

        # 3. Trọng số đối tượng dễ tổn thương (VRU Severity)
        vru_w = self.VRU_WEIGHTS.get(obs.class_name.lower(), 0.70)

        # 4. Phân vùng điểm mù & Hệ số góc mù
        zone = self.classify_blind_spot_zone(obs.vcs_x, obs.vcs_y, ego)
        blind_factor = self.calculate_blind_spot_factor(zone)

        # 5. Hệ số hành vi xe chủ (Maneuver factor)
        maneuver_factor = self.calculate_ego_maneuver_factor(obs, ego)

        # 6. TỔNG HỢP CHỈ SỐ BSRI
        # Kết hợp lồi giữa Không gian và Thời gian
        base_score = self.w_spatial * spatial_risk + self.w_temporal * temporal_risk

        # Nhân với các hệ số điều kiện môi trường & ngữ cảnh
        raw_bsri = base_score * vru_w * blind_factor * maneuver_factor
        bsri_score = round(float(np.clip(raw_bsri, 0.0, 1.0)), 3)

        # 7. Phân cấp mức độ cảnh báo (Risk Level)
        if bsri_score >= self.THRESH_CRITICAL:
            risk_level = RiskLevel.CRITICAL
        elif bsri_score >= self.THRESH_WARNING:
            risk_level = RiskLevel.WARNING
        elif bsri_score >= self.THRESH_CAUTION:
            risk_level = RiskLevel.CAUTION
        else:
            risk_level = RiskLevel.SAFE

        # 8. Sinh diễn giải ngôn ngữ tự nhiên (Explainable AI) & Khuyến nghị hành động
        explanation, recommendation = self._generate_explanation(obs, ego, zone, is_in_dhz, dist_to_dhz, ttc, risk_level)

        return BSRIResult(
            track_id=obs.track_id,
            class_name=obs.class_name,
            bsri_score=bsri_score,
            risk_level=risk_level,
            zone=zone,
            is_in_dhz=is_in_dhz,
            dist_to_dhz=round(dist_to_dhz, 2),
            ttc_seconds=ttc,
            vru_weight=vru_w,
            spatial_risk=round(spatial_risk, 3),
            temporal_risk=round(temporal_risk, 3),
            maneuver_factor=round(maneuver_factor, 2),
            blind_factor=round(blind_factor, 2),
            explanation=explanation,
            recommendation=recommendation
        )

    def evaluate_scene(self, ego: EgoVehicleState, obstacles: List[TrackedObstacle]) -> Tuple[List[BSRIResult], BSRIResult]:
        """
        Đánh giá BSRI cho toàn bộ hiện trường và tìm đối tượng có mức nguy cơ cao nhất.
        :return: (danh_sách_kết_quả, đối_tượng_nguy_hiểm_nhất)
        """
        # Dựng đa giác DHZ cho toàn bộ khung hình hiện tại
        dhz_poly = self.compute_dynamic_hazard_zone(ego)

        results = []
        highest_risk = None
        max_score = -1.0

        for obs in obstacles:
            res = self.evaluate_obstacle(obs, ego, dhz_poly)
            results.append(res)
            if res.bsri_score > max_score:
                max_score = res.bsri_score
                highest_risk = res

        # Nếu không có đối tượng nào quanh xe, trả về kết quả an toàn mặc định
        if highest_risk is None:
            highest_risk = BSRIResult(
                track_id=0,
                class_name="none",
                bsri_score=0.0,
                risk_level=RiskLevel.SAFE,
                zone=BlindSpotZone.CLEAR_ZONE,
                is_in_dhz=False,
                dist_to_dhz=99.0,
                ttc_seconds=None,
                vru_weight=0.0,
                spatial_risk=0.0,
                temporal_risk=0.0,
                maneuver_factor=1.0,
                blind_factor=1.0,
                explanation="Khu vực xung quanh xe an toàn, không phát hiện chướng ngại vật.",
                recommendation="Duy trì tốc độ và chú ý quan sát."
            )

        return results, highest_risk

    def _generate_explanation(self, obs: TrackedObstacle, ego: EgoVehicleState,
                              zone: BlindSpotZone, is_in_dhz: bool, dist_to_dhz: float,
                              ttc: Optional[float], level: RiskLevel) -> Tuple[str, str]:
        """
        Tạo thông điệp giải thích ngắn gọn, xúc tích bằng Tiếng Việt phục vụ HUD và hệ thống âm thanh.
        """
        cname_vi = {
            "person": "Người đi bộ",
            "bicycle": "Xe đạp",
            "xe_keo": "Xe kéo",
            "xich_lo": "Xích lô",
            "motorcycle": "Xe máy",
            "car": "Ô tô",
            "truck": "Xe tải",
            "bus": "Xe buýt"
        }.get(obs.class_name.lower(), obs.class_name)

        pos_str = f"cách {obs.distance_m:.1f}m tại {zone.value}"
        ttc_str = f", TTC: {ttc:.1f}s" if ttc is not None else ""

        if level == RiskLevel.CRITICAL:
            if is_in_dhz:
                exp = f"KHẨN CẤP! {cname_vi} #{obs.track_id} đã XÂM NHẬP VÙNG QUÉT NGUY HIỂM ({pos_str}{ttc_str})!"
            else:
                exp = f"KHẨN CẤP! Nguy cơ va chạm {cname_vi} #{obs.track_id} cận kề ({pos_str}{ttc_str})!"
            rec = "PHANH GẤP NGAY LẬP TỨC! BẤM CÒI CẢNH BÁO!"
        elif level == RiskLevel.WARNING:
            exp = f"CẢNH BÁO! {cname_vi} #{obs.track_id} đang tiếp cận nhanh ({pos_str}{ttc_str})."
            rec = "Rà phanh giảm tốc độ, không chuyển làn hoặc ép lái về phía này."
        elif level == RiskLevel.CAUTION:
            exp = f"CHÚ Ý: Phát hiện {cname_vi} #{obs.track_id} ở vùng lân cận ({pos_str})."
            rec = "Quan sát qua gương và duy trì khoảng cách an toàn."
        else:
            exp = f"{cname_vi} #{obs.track_id} ở cự ly an toàn ({pos_str})."
            rec = "Tiếp tục lộ trình bình thường."

        return exp, rec

