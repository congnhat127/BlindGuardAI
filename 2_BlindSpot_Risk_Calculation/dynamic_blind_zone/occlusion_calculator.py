# ==============================================================================
# OCCLUSION_CALCULATOR.PY - MÔ HÌNH VÙNG NGUY HIỂM XUNG QUANH (SURROUND HAZARD)
# ==============================================================================
import math
import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union
import config

class PureOcclusionCalculator:
    """
    Mô hình Vùng Nguy Hiểm Xung Quanh (Proximity Surround Hazard Model)
    Thiết kế lại hoàn toàn: Tập trung vào một Vùng Đệm An Toàn (Safety Buffer) bao bọc quanh xe.
    Bất kỳ đối tượng nào vi phạm vào vùng này đều bị coi là nguy hiểm chết người, 
    bất kể tài xế có nhìn thấy qua gương hay không!
    """

    def __init__(self):
        self.gamma = 0.0          # Góc gập rơ-moóc (rad)
        self.yaw_rate = 0.0        # Tốc độ quay góc đầu kéo omega (rad/s)
        self.steering_angle = 0.0  # Góc bẻ lái bánh trước delta (rad)

    def reset(self):
        self.gamma = 0.0
        self.yaw_rate = 0.0
        self.steering_angle = 0.0

    @staticmethod
    def rotate_point(pt, angle, pivot=(0.0, 0.0)):
        """Phép xoay ma trận Euler 2D của một điểm quanh gốc pivot"""
        c, s = math.cos(angle), math.sin(angle)
        px, py = pivot
        x, y = pt
        return ((x - px) * c - (y - py) * s + px, (x - px) * s + (y - py) * c + py)

    @staticmethod
    def rotate_polygon(poly, angle, pivot=(0.0, 0.0)):
        """Phép xoay toàn bộ đa giác"""
        return [PureOcclusionCalculator.rotate_point(pt, angle, pivot) for pt in poly]

    def update_kinematics(self, v, input_val, dt=0.0333, is_steering_angle=False):
        """
        Cập nhật vi phân động học rơ-moóc: d_gamma/dt = omega - (v / L_TRAIL) * sin(gamma)
        """
        if is_steering_angle:
            self.steering_angle = input_val
            steer_ratio = getattr(config, 'STEER_RATIO', 16.0)
            front_wheel_angle = self.steering_angle / steer_ratio
            self.yaw_rate = (v / config.WHEELBASE_TRACTOR) * math.tan(front_wheel_angle)
        else:
            self.yaw_rate = input_val

        # Safety Check cho Xe Thân Liền
        if config.L_TRAIL > 0:
            d_gamma = self.yaw_rate - (v / config.L_TRAIL) * math.sin(self.gamma)
            self.gamma += d_gamma * dt
        else:
            self.gamma = 0.0

        mech_max = math.radians(config.MECHANICAL_MAX_GAMMA_DEG)
        self.gamma = np.clip(self.gamma, -mech_max, mech_max)

        return self.gamma

    def get_vehicle_polygons(self):
        """Trả về đa giác các thành phần hình học của xe"""
        cab = [
            (config.CAB_FRONT_X, config.CAB_HALF_W),
            (config.CAB_FRONT_X, -config.CAB_HALF_W),
            (config.CAB_REAR_X, -config.CAB_HALF_W),
            (config.CAB_REAR_X, config.CAB_HALF_W)
        ]
        
        chassis = [
            (config.CAB_REAR_X, config.CHASSIS_HALF_W),
            (config.CAB_REAR_X, -config.CHASSIS_HALF_W),
            (-0.3, -config.CHASSIS_HALF_W),
            (-0.3, config.CHASSIS_HALF_W)
        ]
        
        pivot = (config.D_HITCH, 0.0)
        trail_front = config.D_HITCH + config.TRAIL_OVERHANG
        trail_rear = config.D_HITCH - config.L_TRAIL
        
        base_trailer = [
            (trail_front, config.TRAIL_HALF_W),
            (trail_front, -config.TRAIL_HALF_W),
            (trail_rear, -config.TRAIL_HALF_W),
            (trail_rear, config.TRAIL_HALF_W)
        ]
        trailer = self.rotate_polygon(base_trailer, -self.gamma, pivot)

        return {"cab": cab, "chassis": chassis, "trailer": trailer, "pivot": pivot}

    def compute_stopping_hazard(self, v):
        """
        PHONG BÌ DỪNG XE PHÍA TRƯỚC — KHÔNG PHẢI VÙNG ĐIỂM MÙ.

        Công thức hiện tại d = v*T + v^2/(2*mu*g) chỉ là baseline vật lý trên đường
        bằng, khô, dùng gia tốc hãm lý tưởng mu*g. Không được union đa giác này với
        near_field_hazard thành một "vùng điểm mù tổng". Đối với cảnh báo va chạm trước
        thực tế nên dùng khoảng cách tương đối/TTC tới từng đối tượng và mô hình phanh
        xe tải đã hiệu chuẩn (tải trọng, độ trễ khí nén, độ dốc, mặt đường).
        """
        d_react = v * config.REACTION_TIME
        d_brake = (v**2) / (2 * config.FRICTION_COEFF * config.GRAVITY)
        d_total = d_react + d_brake

        # Độ loe ngang (Lateral Dispersion) dựa vào góc phân tán động học
        lateral_dispersion = d_total * math.tan(math.radians(config.LATERAL_DISPERSION_DEG))
        hazard_half_w = config.CAB_HALF_W + lateral_dispersion

        front_hazard = [
            (config.CAB_FRONT_X, config.CAB_HALF_W),
            (config.CAB_FRONT_X + d_total, hazard_half_w),
            (config.CAB_FRONT_X + d_total, -hazard_half_w),
            (config.CAB_FRONT_X, -config.CAB_HALF_W)
        ]

        return {
            "d_reaction": d_react,
            "d_braking": d_brake,
            "d_total": d_total,
            "front_hazard_polygon": front_hazard
        }

    def path_curvature(self, v):
        """Độ cong quỹ đạo đầu kéo kappa = 1/R (rad/m)."""
        if abs(v) > 1e-5:
            return self.yaw_rate / v
        front_wheel_angle = self.steering_angle / config.STEER_RATIO
        return math.tan(front_wheel_angle) / config.WHEELBASE_TRACTOR

    @staticmethod
    def _to_current_vcs(points, x, y, theta):
        """Đưa đa giác ở tư thế tương lai về hệ VCS của xe tại thời điểm hiện tại."""
        c, s = math.cos(theta), math.sin(theta)
        return [(px * c - py * s + x, px * s + py * c + y) for px, py in points]

    def compute_base_near_field_hazard(self):
        """Biên cận kề cố định quanh thân xe ở tư thế hiện tại."""
        veh = self.get_vehicle_polygons()
        body = unary_union([
            Polygon(veh["cab"]), Polygon(veh["chassis"]), Polygon(veh["trailer"])
        ])
        return list(body.buffer(config.NEAR_FIELD_BUFFER_BASE, join_style=2).exterior.coords)

    def compute_near_field_hazard(self, v):
        """
        Vùng cận kề động = hợp của các tư thế thân xe trên đoạn đường ngắn s phía trước,
        sau đó buffer cố định 1 m. Horizon tính theo QUÃNG ĐƯỜNG (m), không theo thời
        gian, nên không phình theo tốc độ và không trùng với vùng phanh.

        Mô hình theo tọa độ cung đường:
            dx/ds = cos(theta), dy/ds = sin(theta), dtheta/ds = kappa
            dgamma/ds = kappa - sin(gamma)/L_trail
        Khi kappa != 0, rơ-moóc cắt vào phía trong đường cong (low-speed off-tracking),
        vì vậy hợp các tư thế tạo ra phần vùng quét mở rộng bất đối xứng đúng hướng rẽ.
        """
        saved_gamma = float(self.gamma)
        curvature = self.path_curvature(v)
        distance = min(abs(v) * config.HAZARD_PREVIEW_TIME_SEC,
                       config.HAZARD_PREVIEW_DISTANCE_MAX_M)
        steps = max(1, config.HAZARD_SWEEP_STEPS)
        ds = distance / steps

        sim_x = sim_y = sim_theta = 0.0
        sim_gamma = saved_gamma
        polys_to_union = []

        for step in range(steps + 1):
            self.gamma = sim_gamma
            veh = self.get_vehicle_polygons()
            for part in ("cab", "chassis", "trailer"):
                pts = self._to_current_vcs(veh[part], sim_x, sim_y, sim_theta)
                polys_to_union.append(Polygon(pts))

            if step == steps:
                break

            # Tích phân chính xác cung tròn cho tư thế đầu kéo trên đoạn ds.
            next_theta = sim_theta + curvature * ds
            if abs(curvature) > 1e-8:
                sim_x += (math.sin(next_theta) - math.sin(sim_theta)) / curvature
                sim_y += (math.cos(sim_theta) - math.cos(next_theta)) / curvature
            else:
                sim_x += math.cos(sim_theta) * ds
                sim_y += math.sin(sim_theta) * ds
            sim_theta = next_theta

            if config.L_TRAIL > 0:
                d_gamma_ds = curvature - math.sin(sim_gamma) / config.L_TRAIL
                sim_gamma += d_gamma_ds * ds
                max_gamma = math.radians(config.MECHANICAL_MAX_GAMMA_DEG)
                sim_gamma = float(np.clip(sim_gamma, -max_gamma, max_gamma))

        self.gamma = saved_gamma
        swept_body = unary_union(polys_to_union)
        hazard = swept_body.buffer(config.NEAR_FIELD_BUFFER_BASE, join_style=2)
        return list(hazard.exterior.coords)

    def compute_hazard_zone(self, v):
        """
        Kết quả cuối cùng của hệ thống: MỘT vùng nguy hiểm duy nhất.

        Các thành phần vật lý (quỹ đạo quét cận kề và khoảng dừng phía trước) chỉ là
        dữ liệu trung gian; chúng được hợp bằng phép union trước khi trả ra ngoài.
        """
        near_field = Polygon(self.compute_near_field_hazard(v))
        stopping_data = self.compute_stopping_hazard(v)
        stopping = Polygon(stopping_data["front_hazard_polygon"])

        geometries = [near_field]
        if stopping.is_valid and stopping.area > 1e-8:
            geometries.append(stopping)

        combined = unary_union(geometries).buffer(0)
        if combined.geom_type == "MultiPolygon":
            combined = max(combined.geoms, key=lambda geom: geom.area)
        return list(combined.exterior.coords)

    def compute_all(self, v, input_val, dt=0.0333, is_steering_angle=False):
        """Tổng hợp kết quả"""
        gamma = self.update_kinematics(v, input_val, dt, is_steering_angle)
        veh = self.get_vehicle_polygons()

        # API chính thức chỉ trả MỘT polygon cảnh báo cuối cùng. Các phép tính
        # near-field/stopping là chi tiết nội bộ, không phải hai vùng cảnh báo riêng.
        hazard_zone = self.compute_hazard_zone(v)
        stopping = self.compute_stopping_hazard(v)

        return {
            "gamma_rad": gamma,
            "gamma_deg": math.degrees(gamma),
            "yaw_rate": self.yaw_rate,
            "vehicle": veh,
            "hazard_zone": hazard_zone,
            "metrics": {
                "d_reaction": stopping["d_reaction"],
                "d_braking": stopping["d_braking"],
                "d_total": stopping["d_total"]
            }
        }

    @staticmethod
    def is_point_in_polygon(point: tuple, polygon: list) -> bool:
        """Kiểm tra Point-in-Polygon (Ray-Casting Crossing Number)"""
        if not polygon or len(polygon) < 3:
            return False

        x, y = point[0], point[1]
        n = len(polygon)
        inside = False

        p1x, p1y = polygon[0]
        for i in range(n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    @staticmethod
    def calculate_polygon_area(polygon: list) -> float:
        """Tính diện tích thực tế m2 (Shoelace Formula)"""
        if not polygon or len(polygon) < 3:
            return 0.0

        n = len(polygon)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += polygon[i][0] * polygon[j][1]
            area -= polygon[j][0] * polygon[i][1]

        return abs(area) / 2.0
