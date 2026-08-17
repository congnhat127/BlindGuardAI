# ==============================================================================
# OCCLUSION_CALCULATOR.PY - MÔ HÌNH TOÁN HỌC QUANG HỌC VÀ ĐỘNG HỌC THUẦN TÚY
# (PURE OPTICAL RAY-CASTING OCCLUSION & KINEMATIC SWEPT PATH MODEL)
# ==============================================================================
import math
import numpy as np
import config

class PureOcclusionCalculator:
    """
    Mô hình toán học độc lập dựa trên lý thuyết Quang hình học (Ray-Casting Occlusion)
    và Động học phương tiện thuần túy.
    
    Phân tách minh bạch 3 khái niệm:
      1. Physical Blind Zone (Vùng mù quang học): B(t) = {P | ray(E, P) ∩ Vehicle != ∅}
      2. Swept Path (Diện tích quét bánh xe): S(t) = f(gamma, L_trail)
      3. Hazard Stopping Zone (Vùng nguy hiểm phanh): H(v) = f(v, reaction, friction)
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

    def update_kinematics(self, v, input_val, dt=config.DT_CAMERA, is_steering_angle=False):
        """
        Cập nhật vi phân động học rơ-moóc theo mô hình Leng & Minor (2010):
        d_gamma/dt = omega - (v / L_TRAIL) * sin(gamma)
        
        Nếu input_val là góc bẻ lái vô-lăng delta_wheel (is_steering_angle=True):
           Góc bánh trước thật: delta_front = delta_wheel / STEER_RATIO
           omega = (v / WHEELBASE_TRACTOR) * tan(delta_front)
        """
        if is_steering_angle:
            self.steering_angle = input_val
            steer_ratio = getattr(config, 'STEER_RATIO', 16.0)
            front_wheel_angle = self.steering_angle / steer_ratio
            self.yaw_rate = (v / config.WHEELBASE_TRACTOR) * math.tan(front_wheel_angle)
        else:
            self.yaw_rate = input_val

        # Phương trình vi phân góc gập rơ-moóc
        d_gamma = self.yaw_rate - (v / config.L_TRAIL) * math.sin(self.gamma)
        self.gamma += d_gamma * dt

        # Giới hạn cơ khí thực tế (Mechanical Max) vs Giới hạn mô hình số
        mech_max = math.radians(config.MECHANICAL_MAX_GAMMA_DEG)
        self.gamma = np.clip(self.gamma, -mech_max, mech_max)

        return self.gamma

    def get_vehicle_polygons(self):
        """Trả về đa giác các thành phần hình học của xe"""
        # Cabin đầu kéo
        cab = [
            (config.CAB_FRONT_X, config.CAB_HALF_W),
            (config.CAB_FRONT_X, -config.CAB_HALF_W),
            (config.CAB_REAR_X, -config.CAB_HALF_W),
            (config.CAB_REAR_X, config.CAB_HALF_W)
        ]
        # Khung gầm
        chassis = [
            (config.CAB_REAR_X, config.CHASSIS_HALF_W),
            (config.CAB_REAR_X, -config.CHASSIS_HALF_W),
            (-0.3, -config.CHASSIS_HALF_W),
            (-0.3, config.CHASSIS_HALF_W)
        ]
        # Rơ-moóc (đã xoay theo góc -gamma)
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

    def cast_shadow_ray(self, origin, target_point, max_range=20.0):
        """
        Bắn một tia từ nguồn (Mắt/Gương) đi qua một điểm cản và kéo dài ra khoảng xa max_range.
        Phương trình tia: P(t) = Origin + t * Normalized(Target - Origin)
        """
        dx = target_point[0] - origin[0]
        dy = target_point[1] - origin[1]
        dist = math.sqrt(dx**2 + dy**2)
        if dist < 1e-5:
            return target_point
        ux, uy = dx / dist, dy / dist
        return (origin[0] + ux * max_range, origin[1] + uy * max_range)

    def compute_a_pillar_occlusion(self):
        """
        1. VÙNG MÙ QUANG HỌC CỘT A & CỘT B (A-Pillar & B-Pillar Ray-Casting Shadow):
        Xuất phát thuần túy từ Mắt tài xế E = (EYE_X, EYE_Y).
        - Cột A: Bề rộng hiệu dụng cụm Cột A + Khung cửa + Chân gương (28cm).
        - Cột B / Thành cabin: Che khuất tầm nhìn trực tiếp qua vai tài xế (Direct Shoulder Blind Spot).
        """
        eye = (config.EYE_X, config.EYE_Y)
        w = config.A_PILLAR_WIDTH / 2.0
        R = config.A_PILLAR_BLIND_RANGE

        def get_pillar_wedge(center):
            cx, cy = center
            p1 = (cx, cy - w)
            p2 = (cx, cy + w)
            f1 = self.cast_shadow_ray(eye, p1, R)
            f2 = self.cast_shadow_ray(eye, p2, R)
            return [p1, p2, f2, f1]

        def get_b_pillar_wedge(side_sign):
            # Thành cabin kín phía sau cửa sổ (từ X=2.6m đến X=2.2m)
            p1 = (2.6, side_sign * config.CAB_HALF_W)
            p2 = (2.2, side_sign * config.CAB_HALF_W)
            f1 = self.cast_shadow_ray(eye, p1, R)
            f2 = self.cast_shadow_ray(eye, p2, R)
            return [p1, p2, f2, f1]

        right_pillar = (config.A_PILLAR_R_X, config.A_PILLAR_R_Y)
        left_pillar = (config.A_PILLAR_L_X, config.A_PILLAR_L_Y)

        return {
            "a_pillar_right": get_pillar_wedge(right_pillar),
            "a_pillar_left": get_pillar_wedge(left_pillar),
            "b_pillar_right": get_b_pillar_wedge(-1),
            "b_pillar_left": get_b_pillar_wedge(1)
        }

    def compute_front_bonnet_occlusion(self):
        """
        VÙNG MÙ QUANG HỌC PHÍA TRƯỚC CABIN (Front Bonnet / Windshield Occlusion):
        Chiếu tia 3D từ Mắt tài xế (EYE_X, EYE_Y, EYE_Z = 2.2m) đi qua mép dưới kính chắn gió / nắp capo
        (CAB_FRONT_X, Z_bonnet = 1.4m) xuống mặt đất Z = 0.
        
        Khoảng cách mù trước cản xe:
        d_front = Z_bonnet * (CAB_FRONT_X - EYE_X) / (EYE_Z - Z_bonnet)
        """
        z_eye = getattr(config, 'EYE_Z', 2.2)
        z_bonnet = 1.4  # Chiều cao mép dưới kính chắn gió/mũi xe
        dx_cab = config.CAB_FRONT_X - config.EYE_X

        d_front_ground = z_bonnet * dx_cab / max(1e-3, (z_eye - z_bonnet))
        front_x_end = config.CAB_FRONT_X + d_front_ground
        hw_c = config.CAB_HALF_W

        front_occlusion = [
            (config.CAB_FRONT_X, hw_c),
            (front_x_end, hw_c * 1.2),
            (front_x_end, -hw_c * 1.2),
            (config.CAB_FRONT_X, -hw_c)
        ]
        return front_occlusion

    def compute_generalized_silhouette_shadow(self, observer_pt, target_vertices, R_max=25.0):
        """
        THUẬT TOÁN RAY-CASTING 2D TỔNG QUÁT TÌM BÓNG CHE KHUẤT TỪ ĐỈNH NỔI (SILHOUETTE):
        Hoàn toàn KHÔNG dùng bất kỳ nhánh lệnh if gamma > 0 / gamma < 0 thủ công nào!
        
        Chuẩn hóa góc cực xung quanh hướng nhìn lùi (-X) để triệt tiêu lỗi gián đoạn 360 độ (atan2 Branch Cut at ±pi).
        """
        ox, oy = observer_pt
        angles = []
        for pt in target_vertices:
            dx = pt[0] - ox
            dy = pt[1] - oy
            ang = math.atan2(dy, dx)
            # Chuẩn hóa góc cực theo hướng lùi (-X) để không bị đứt đoạn ở 180 độ
            if ang <= 0:
                ang_norm = ang + math.pi
            else:
                ang_norm = ang - math.pi
            angles.append((ang_norm, pt))

        # Sắp xếp các đỉnh theo góc cực chuẩn hóa từ phải qua trái
        angles.sort(key=lambda item: item[0])
        
        pt_right_bound = angles[0][1]
        pt_left_bound = angles[-1][1]

        # Bắn tia chiếu ra xa 25m
        f_right = self.cast_shadow_ray(observer_pt, pt_right_bound, R_max)
        f_left = self.cast_shadow_ray(observer_pt, pt_left_bound, R_max)

        # Trả về đa giác bóng khuất hình quạt không bị đứt đoạn hay tự cắt
        return [observer_pt, pt_left_bound, f_left, f_right, pt_right_bound]

    def compute_mirror_occlusion(self):
        """
        2. VÙNG MÙ GƯƠNG CHIẾU HẬU (Mirror Occlusion Shadows):
        Áp dụng Thuật toán Bắn tia Đỉnh nổi 2D Chuẩn hóa Hướng Lùi (Rearward Normalized Silhouette Ray-Casting).
        Triệt tiêu 100% lỗi quạt nêm bị cuộn 360 độ về phía trước cabin.
        """
        veh = self.get_vehicle_polygons()
        trailer = veh["trailer"]  # [front_left, front_right, rear_right, rear_left]
        
        # Thêm các đỉnh hậu cabin vào tập vật cản
        cab_rear_r = (config.CAB_REAR_X, -config.CAB_HALF_W)
        cab_rear_l = (config.CAB_REAR_X, config.CAB_HALF_W)

        right_obstacles = trailer + [cab_rear_r]
        left_obstacles = trailer + [cab_rear_l]

        m_r = (config.MIRROR_R_X, config.MIRROR_R_Y)
        m_l = (config.MIRROR_L_X, config.MIRROR_L_Y)

        right_occlusion = self.compute_generalized_silhouette_shadow(m_r, right_obstacles, R_max=25.0)
        left_occlusion = self.compute_generalized_silhouette_shadow(m_l, left_obstacles, R_max=25.0)

        return {
            "right_side_occlusion": right_occlusion,
            "left_side_occlusion": left_occlusion
        }

    def compute_swept_path_polygon(self):
        """
        3. DIỆN TÍCH QUÉT BÁNH XE (Pure Kinematic Swept Path Polygon):
        Quỹ đạo vật lý bánh xe rơ-moóc lấn lề do chênh lệch bán kính quay (Inner Wheel Difference):
        Δy = L_TRAIL * |sin(gamma)|
        """
        veh = self.get_vehicle_polygons()
        trailer = veh["trailer"]
        d_swept = config.L_TRAIL * abs(math.sin(self.gamma))

        t_fr, t_rr = trailer[1], trailer[2]
        t_fl, t_rl = trailer[0], trailer[3]

        if self.gamma < 0:   # Rẽ phải -> Quét lấn lề phải
            swept_poly = [t_fr, t_rr, (t_rr[0], t_rr[1] - d_swept), (t_fr[0], t_fr[1] - d_swept * 0.3)]
        elif self.gamma > 0: # Rẽ trái -> Quét lấn lề trái
            swept_poly = [t_fl, t_rl, (t_rl[0], t_rl[1] + d_swept), (t_fl[0], t_fl[1] + d_swept * 0.3)]
        else:
            swept_poly = []

        return {"swept_path": swept_poly, "d_swept_val": d_swept}

    def compute_stopping_hazard(self, v):
        """
        4. VÙNG NGUY HIỂM QUÃNG ĐƯỜNG PHANH (Kinematic Stopping Distance Hazard Zone):
        d_total = v * t_r + v^2 / (2 * mu * g)
        """
        v_mps = max(0.0, v)
        d_react = v_mps * config.REACTION_TIME
        d_brake = (v_mps ** 2) / (2.0 * config.FRICTION_COEFF * config.GRAVITY)
        d_total = d_react + d_brake

        front_hazard = [
            (config.CAB_FRONT_X, config.CAB_HALF_W),
            (config.CAB_FRONT_X + d_total, config.CAB_HALF_W * 1.2),
            (config.CAB_FRONT_X + d_total, -config.CAB_HALF_W * 1.2),
            (config.CAB_FRONT_X, -config.CAB_HALF_W)
        ]

        return {
            "d_reaction": d_react,
            "d_braking": d_brake,
            "d_total": d_total,
            "front_hazard_polygon": front_hazard
        }

    def compute_all(self, v, input_val, dt=config.DT_CAMERA, is_steering_angle=False):
        """
        Hàm tổng hợp tính toán độc lập các phân hệ toán học
        """
        gamma = self.update_kinematics(v, input_val, dt, is_steering_angle)
        veh = self.get_vehicle_polygons()
        a_b_pillars = self.compute_a_pillar_occlusion()
        front_bonnet = self.compute_front_bonnet_occlusion()
        mirrors = self.compute_mirror_occlusion()
        swept = self.compute_swept_path_polygon()
        stopping = self.compute_stopping_hazard(v)

        return {
            "gamma_rad": gamma,
            "gamma_deg": math.degrees(gamma),
            "yaw_rate": self.yaw_rate,
            "vehicle": veh,
            "occlusion_zones": {
                **a_b_pillars,
                **mirrors,
                "front_bonnet": front_bonnet
            },
            "swept_path": swept,
            "stopping_hazard": stopping
        }

    @staticmethod
    def is_point_in_polygon(point: tuple, polygon: list) -> bool:
        """
        Kiểm tra điểm 2D (x, y) có nằm trong Đa giác hay không (Point-in-Polygon Test).
        Sử dụng Thuật toán Ray-Casting Crossing Number.
        """
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
