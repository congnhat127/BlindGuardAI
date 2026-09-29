"""
Module: bsri_calculator.py
Phân hệ: 2_BlindSpot_Risk_Calculation / bsri_engine
Mô tả: Bộ tính toán Chỉ số Rủi ro Điểm mù (Blind-Spot Risk Index - BSRI) thời gian thực
       kết hợp Động lực học xe (DHZ), Dự đoán va chạm (TTC), Phân loại đối tượng dễ tổn thương (VRU),
       và Điểm mù quang học (Blind Spot Geometry) theo chuẩn UNECE R151 / ISO 15622.
"""

import math
from typing import List, Optional, Tuple, Dict, Any
import numpy as np
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

try:
    from .risk_models import RiskLevel, BlindSpotZone, EgoVehicleState, TrackedObstacle, BSRIResult
except ImportError:
    from risk_models import RiskLevel, BlindSpotZone, EgoVehicleState, TrackedObstacle, BSRIResult


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

    # Trọng số tính tổn thương của từng loại phương tiện / đối tượng (VRU Severity Weight)
    # Tham chiếu chuẩn đánh giá va chạm Euro NCAP / UNECE R151 cho xe tải nặng
    VRU_WEIGHTS: Dict[str, float] = {
        "person": 1.00,        # Người đi bộ: Khả năng tử vong cao nhất, quỹ đạo khó lường
        "bicycle": 0.95,       # Xe đạp: Rất dễ ngã, tốc độ chậm trong điểm mù
        "xe_keo": 0.92,        # Xe kéo hàng: Cồng kềnh, không phanh cơ khí, người kéo đi bộ
        "xich_lo": 0.90,       # Xích lô: Thân xe dài, tầm quan sát thấp
        "motorcycle": 0.85,    # Xe máy: Tốc độ cơ động cao, hay vượt phải trong điểm mù
        "car": 0.65,           # Ô tô con: Có khung vỏ kim loại bảo vệ
        "truck": 0.60,         # Xe tải khác: Tương đương kích thước
        "bus": 0.65            # Xe buýt
    }

    # Ngưỡng phân loại cấp độ rủi ro (Risk Thresholds)
    THRESH_CRITICAL = 0.80     # BSRI >= 0.80 -> NGUY HIỂM KHẨN CẤP (Phanh/Còi)
    THRESH_WARNING = 0.55      # 0.55 <= BSRI < 0.80 -> CẢNH BÁO (Rung vô lăng / Chuông)
    THRESH_CAUTION = 0.30      # 0.30 <= BSRI < 0.55 -> CHÚ Ý (Đèn vàng HUD)

    def __init__(self,
                 wheelbase_tractor: float = 3.6,
                 cab_width: float = 2.5,
                 trailer_length: float = 12.0,
                 trailer_width: float = 2.5,
                 base_clearance: float = 1.5,
                 spatial_weight: float = 0.45,
                 temporal_weight: float = 0.55):
        """
        Khởi tạo bộ tính toán BSRI với các thông số kích thước xe đầu kéo & rơ-moóc.
        :param wheelbase_tractor: Chiều dài cơ sở đầu kéo (m, mặc định 3.6m)
        :param cab_width: Chiều rộng cabin (m, mặc định 2.5m)
        :param trailer_length: Chiều dài thùng rơ-moóc (m, mặc định 12.0m)
        :param trailer_width: Chiều rộng thùng rơ-moóc (m, mặc định 2.5m)
        :param base_clearance: Khoảng đệm an toàn vật lý cơ sở (m, mặc định 1.5m)
        """
        self.L_f = float(wheelbase_tractor)
        self.W_c = float(cab_width)
        self.L_trail = float(trailer_length)
        self.W_trail = float(trailer_width)
        self.base_clearance = float(base_clearance)

        # Trọng số kết hợp giữa Rủi ro Không gian và Rủi ro Thời gian
        self.w_spatial = float(spatial_weight)
        self.w_temporal = float(temporal_weight)

        # Kích thước hình học thân xe trong hệ VCS (Gốc tại tâm trục sau đầu kéo)
        self.cab_half_w = self.W_c / 2.0
        self.trail_half_w = self.W_trail / 2.0
        self.cab_front_x = self.L_f + 0.40      # Mũi xe nhô trước trục trước 40cm
        self.cab_rear_x = self.L_f * 0.61       # Vách sau cabin
        self.d_hitch = self.L_f * 0.08          # Vị trí chốt kéo (hitch)
        self.trail_rear_x = self.d_hitch - self.L_trail # Đuôi rơ-moóc

    def build_vehicle_footprint(self, gamma: float = 0.0) -> Polygon:
        """
        Dựng đa giác hình chiếu thân xe (Vehicle Footprint) theo góc gập rơ-moóc gamma trong hệ VCS.
        """
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
        Bao gồm: Vùng quét tương lai (Swept Occupancy) + Khoảng đệm vật lý an toàn (Physical Buffer).
        """
        footprints = []
        gamma = ego.trailer_gamma_rad
        dt = horizon_sec / max(1, steps)

        for step in range(steps + 1):
            t = step * dt
            # Dự đoán góc gập rơ-moóc ở các bước thời gian tới
            if self.L_trail > 0 and abs(ego.speed_mps) > 0.1:
                d_gamma = ego.yaw_rate_rad_s - (ego.speed_mps / self.L_trail) * math.sin(gamma)
                gamma += d_gamma * dt
            
            fp = self.build_vehicle_footprint(gamma)
            footprints.append(fp)

        # Hợp nhất tất cả footprint trong khoảng dự đoán
        swept_poly = unary_union(footprints)

        # Tính khoảng đệm động (Clearance)
        # Tăng nhẹ đệm khi xe có gia tốc ngang lớn hoặc đang quay đầu
        dyn_clearance = min(0.75, 0.5 * abs(ego.accel_y_mps2) * (0.5 ** 2))
        total_buffer = self.base_clearance + dyn_clearance

        # Mở rộng đa giác bằng Minkowski Buffer
        dhz_poly = swept_poly.buffer(total_buffer, resolution=16)
        return dhz_poly

    def classify_blind_spot_zone(self, x: float, y: float, ego: EgoVehicleState) -> BlindSpotZone:
        """
        Phân loại đối tượng tại tọa độ (x, y) thuộc vào vùng điểm mù hình học nào của xe tải.
        """
        # 1. Điểm mù trực diện gầm Cabin (Mũi xe - Class VI)
        if (self.L_f <= x <= self.cab_front_x + 2.0) and (abs(y) <= self.cab_half_w + 0.8):
            return BlindSpotZone.CAB_FRONT

        # 2. Hông phụ (Gương phải - Class IV/V) - Vùng tử thần kinh điển của xe tải
        if (self.cab_rear_x - 1.0 <= x <= self.cab_front_x) and (-3.5 <= y <= -self.cab_half_w):
            return BlindSpotZone.MIRROR_RIGHT

        # 3. Hông lái (Gương trái - Class IV/V)
        if (self.cab_rear_x - 1.0 <= x <= self.cab_front_x) and (self.cab_half_w <= y <= 3.5):
            return BlindSpotZone.MIRROR_LEFT

        # 4. Bụng cua rơ-moóc bên phải (Swept path nguy hiểm khi xe rẽ phải)
        if (self.trail_rear_x <= x < self.cab_rear_x - 1.0) and (-4.5 <= y <= -self.trail_half_w):
            return BlindSpotZone.SWEPT_PATH_RIGHT

        # 5. Bụng cua rơ-moóc bên trái (Swept path nguy hiểm khi xe rẽ trái)
        if (self.trail_rear_x <= x < self.cab_rear_x - 1.0) and (self.trail_half_w <= y <= 4.5):
            return BlindSpotZone.SWEPT_PATH_LEFT

        # 6. Đuôi rơ-moóc (Điểm mù lùi)
        if (self.trail_rear_x - 3.5 <= x < self.trail_rear_x) and (abs(y) <= self.trail_half_w + 1.0):
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
        # v_closing > 0 nghĩa là khoảng cách đang thu hẹp lại (đối tượng đang lao về phía xe)
        v_closing = - (obs.vcs_x * obs.vel_x + obs.vcs_y * obs.vel_y) / r

        # Nếu có vận tốc xe chủ, cộng thêm vận tốc dọc của xe chủ nếu đối tượng ở trước/sau
        if obs.vcs_x > 0 and ego.speed_mps > 0:
            # Xe đang tiến về đối tượng phía trước
            v_closing += ego.speed_mps * (obs.vcs_x / r)
        elif obs.vcs_x < 0 and ego.speed_mps < 0:
            # Xe đang lùi về đối tượng phía sau
            v_closing += abs(ego.speed_mps) * (abs(obs.vcs_x) / r)

        if v_closing > 0.15:
            ttc = r / v_closing
            # Mô hình hóa đường cong suy giảm TTC theo tiêu chuẩn ISO 15622 (LCDAS)
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

        # 4. Xe đang phanh gấp (giảm bớt rủi ro vì xe đang chủ động dừng lại)
        if ego.accel_x_mps2 < -1.5:
            factor *= 0.85

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

    def evaluate_obstacle(self, obs: TrackedObstacle, ego: EgoVehicleState, dhz_poly: Polygon) -> BSRIResult:
        """
        Tính toán chỉ số BSRI đầy đủ cho 1 đối tượng chướng ngại vật.
        """
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

