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
        """Vùng nguy hiểm phanh phía trước mũi xe (Dựa vào thời gian phản ứng & Ma sát)"""
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

    def compute_dynamic_surround_hazard(self, v, time_horizon=2.0, num_steps=6):
        """
        [LỚP BẢO VỆ CHÍNH]: DYNAMIC SURROUND HAZARD ZONE
        Dự đoán quỹ đạo lấn lề (Swept Path) trong tương lai và hợp nhất.
        Tạo ra một Vùng Nguy Hiểm Động bao trọn hoàn toàn quỹ đạo rẽ của rơ-moóc.
        """
        dynamic_buffer = config.HAZARD_BUFFER_BASE + (v * config.HAZARD_BUFFER_SPEED_FACTOR)
        
        # Lưu trạng thái hiện tại
        saved_gamma = self.gamma
        
        polys_to_union = []
        sim_x, sim_y, sim_theta = 0.0, 0.0, 0.0
        dt_sim = time_horizon / num_steps if num_steps > 0 else 0
        
        for _ in range(num_steps + 1):
            veh = self.get_vehicle_polygons()
            
            # Đưa về World Coords tương đối
            cab_world = self.rotate_polygon(veh["cab"], sim_theta)
            cab_world = [(px + sim_x, py + sim_y) for px, py in cab_world]
            
            trail_world = self.rotate_polygon(veh["trailer"], sim_theta)
            trail_world = [(px + sim_x, py + sim_y) for px, py in trail_world]
            
            polys_to_union.append(Polygon(cab_world))
            polys_to_union.append(Polygon(trail_world))
            
            if v > 0.1:
                sim_x += v * math.cos(sim_theta) * dt_sim
                sim_y += v * math.sin(sim_theta) * dt_sim
                sim_theta += self.yaw_rate * dt_sim
                
                if config.L_TRAIL > 0:
                    d_gamma = self.yaw_rate - (v / config.L_TRAIL) * math.sin(self.gamma)
                    self.gamma += d_gamma * dt_sim
                    mech_max = math.radians(config.MECHANICAL_MAX_GAMMA_DEG)
                    self.gamma = np.clip(self.gamma, -mech_max, mech_max)
        
        self.gamma = saved_gamma
        
        combined_path = unary_union(polys_to_union)
        hazard_bubble = combined_path.buffer(dynamic_buffer, join_style=2)
        
        return list(hazard_bubble.exterior.coords)

    def compute_all(self, v, input_val, dt=0.0333, is_steering_angle=False):
        """Tổng hợp kết quả"""
        gamma = self.update_kinematics(v, input_val, dt, is_steering_angle)
        veh = self.get_vehicle_polygons()
        
        # Tự động phình to rẽ dựa trên tốc độ và góc lái
        surround_hazard = self.compute_dynamic_surround_hazard(v, time_horizon=1.5, num_steps=5)
        stopping = self.compute_stopping_hazard(v)

        return {
            "gamma_rad": gamma,
            "gamma_deg": math.degrees(gamma),
            "yaw_rate": self.yaw_rate,
            "vehicle": veh,
            "surround_hazard": surround_hazard,
            "stopping_hazard": stopping
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
