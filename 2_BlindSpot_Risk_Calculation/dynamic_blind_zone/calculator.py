# ==============================================================================
# CALCULATOR.PY - THUẬT TOÁN TÍNH VÙNG MÙ ĐỘNG XE ĐẦU KÉO RƠ-MOÓC
# ==============================================================================
#
# PHƯƠNG PHÁP: Occlusion Shadow (Bóng che khuất)
#   Vùng mù = Khu vực mà tia nhìn từ MẮT TÀI XẾ bị THÂN XE che khuất.
#   Mỗi cạnh che khuất tạo ra một hình thang/nêm mở rộng dần theo khoảng cách.
#
# HỆ TỌA ĐỘ (VCS - Vehicle Coordinate System):
#   Gốc (0,0): Tâm trục bánh sau Đầu kéo, trên mặt đất.
#   X(+): Hướng tiến về trước.  Y(+): Hướng sang trái.
#   omega(+): Bẻ trái.          gamma(+): Rơ-moóc lệch trái.
#
# CÁC CÔNG THỨC TOÁN HỌC CHÍNH:
#   1) Phương trình vi phân rơ-moóc ảo (Leng & Minor, IEEE/RSJ IROS 2010):
#        d(gamma)/dt = omega - (v / L) * sin(gamma)
#      Dấu ÂM trước (v/L)*sin(gamma) đảm bảo hệ ỔN ĐỊNH:
#        khi gamma lệch, lực kéo v*sin(gamma) sẽ KÉO VỀ 0.
#      Điểm cân bằng: sin(gamma_eq) = omega*L / v
#
#   2) Quãng đường phanh:
#        d_total = v * t_react + v^2 / (2 * mu * g)
#
#   3) Độ lệch ngang quét bánh sau (Swept Path lateral offset):
#        d_swept = L_trail * |sin(gamma)|
#      Đây là thành phần lệch theo trục Y (ngang), KHÔNG phải 1-cos(gamma)
#      vốn là thành phần co rút theo trục X (dọc).
#
#   4) Ma trận xoay 2D quanh pivot:
#        x' = (x-px)*cos(a) - (y-py)*sin(a) + px
#        y' = (x-px)*sin(a) + (y-py)*cos(a) + py
#
#   5) Vùng mù cột A (A-Pillar Wedge):
#        Nửa góc mở = arctan((pillar_width / 2) / khoảng cách mắt đến cột)
#        Chiếu thành hình nêm từ cột ra xa tầm A_PILLAR_BLIND_RANGE mét.
#
#   6) Vùng mù hông (Side Occlusion Trapezoid):
#        Cạnh trong: Bám sát thân xe (khoảng cách = 0).
#        Cạnh ngoài: Mở rộng tuyến tính theo khoảng cách từ mắt tài xế.
#        Gần cabin (gương phủ tới): hẹp.  Xa cabin: rộng dần.
#
# ==============================================================================

import math
import config

class BlindZoneCalculator:
    def __init__(self):
        self.gamma = 0.0

    def reset(self):
        self.gamma = 0.0

    # === CÔNG THỨC 1: Động học rơ-moóc ảo (Leng & Minor, IROS 2010) ===
    def update_gamma(self, v, omega, dt=config.DT_CAMERA):
        """d(gamma)/dt = omega - (v/L) * sin(gamma)"""
        if abs(config.L_TRAIL) > 1e-5:
            d_gamma = omega - (v / config.L_TRAIL) * math.sin(self.gamma)
        else:
            d_gamma = 0.0
        self.gamma += d_gamma * dt
        max_rad = math.radians(config.MAX_GAMMA_DEG)
        self.gamma = max(-max_rad, min(max_rad, self.gamma))
        return self.gamma

    # === CÔNG THỨC 2: Quãng đường phanh ===
    def stopping_distance(self, v):
        va = abs(v)
        d_r = va * config.REACTION_TIME
        d_b = va**2 / (2 * config.FRICTION_COEFF * config.GRAVITY)
        return {"d_reaction": d_r, "d_braking": d_b, "d_total": d_r + d_b}

    # === CÔNG THỨC 3: Swept path lateral offset (lệch ngang Y) ===
    def swept_offset(self, gamma):
        """d_swept = L * |sin(gamma)| — lệch ngang thực sự, không phải 1-cos."""
        return config.L_TRAIL * abs(math.sin(gamma))

    # === CÔNG THỨC 4: Xoay điểm 2D quanh pivot ===
    def rotate(self, pts, angle, pivot=(0, 0)):
        c, s = math.cos(angle), math.sin(angle)
        px, py = pivot
        return [((x-px)*c - (y-py)*s + px, (x-px)*s + (y-py)*c + py) for x, y in pts]

    # === HÌNH HỌC THÂN XE (3 phần tách biệt) ===
    def vehicle_geometry(self):
        hw_c = config.CAB_HALF_W
        hw_ch = config.CHASSIS_HALF_W
        hw_t = config.TRAIL_HALF_W
        pivot = (config.D_HITCH, 0)

        # 1. Cabin (hình chữ nhật rộng phía trước)
        cab = [
            (config.CAB_FRONT_X, hw_c),
            (config.CAB_FRONT_X, -hw_c),
            (config.CAB_REAR_X, -hw_c),
            (config.CAB_REAR_X, hw_c)
        ]
        # 2. Khung gầm (hẹp, nối cabin với trục sau và chốt kéo)
        chassis = [
            (config.CAB_REAR_X, hw_ch),
            (config.CAB_REAR_X, -hw_ch),
            (-0.3, -hw_ch),
            (-0.3, hw_ch)
        ]
        # 3. Rơ-moóc (xoay theo gamma quanh chốt kéo)
        trail_front = config.D_HITCH + config.TRAIL_OVERHANG
        trail_rear = config.D_HITCH - config.L_TRAIL
        base_trail = [
            (trail_front, hw_t),
            (trail_front, -hw_t),
            (trail_rear, -hw_t),
            (trail_rear, hw_t)
        ]
        trailer = self.rotate(base_trail, -self.gamma, pivot)

        return {"cab": cab, "chassis": chassis, "trailer": trailer, "hitch": pivot}

    # === CÔNG THỨC 5: Vùng mù Cột A (A-Pillar Wedge) ===
    def _a_pillar_zones(self):
        """
        Tính toán vùng mù cột A dựa trên phép chiếu tia quang học (Ray Casting):
        Phương trình tia: P(t) = E + t * (P_pillar - E)
        Xuất phát từ Mắt tài xế (E) -> Đi qua 2 mép cột A -> Kéo dài ra xa (R)
        """
        eye = (config.EYE_X, config.EYE_Y)
        w = config.A_PILLAR_WIDTH / 2.0
        R = config.A_PILLAR_BLIND_RANGE

        def cast_wedge(pillar_center):
            px, py = pillar_center
            # Hai mép của cột A
            p1 = (px, py - w)
            p2 = (px, py + w)

            # Vector hướng tia từ mắt tài xế đến 2 mép
            d1 = (p1[0] - eye[0], p1[1] - eye[1])
            d2 = (p2[0] - eye[0], p2[1] - eye[1])

            len1 = math.sqrt(d1[0]**2 + d1[1]**2)
            len2 = math.sqrt(d2[0]**2 + d2[1]**2)

            u1 = (d1[0] / len1, d1[1] / len1) if len1 > 1e-5 else (1, 0)
            u2 = (d2[0] / len2, d2[1] / len2) if len2 > 1e-5 else (1, 0)

            # Đỉnh xa kéo dài R mét
            p1_far = (p1[0] + u1[0] * R, p1[1] + u1[1] * R)
            p2_far = (p2[0] + u2[0] * R, p2[1] + u2[1] * R)

            return [p1, p2, p2_far, p1_far]

        right_pillar = (config.A_PILLAR_R_X, config.A_PILLAR_R_Y)
        left_pillar = (config.A_PILLAR_L_X, config.A_PILLAR_L_Y)

        return cast_wedge(right_pillar), cast_wedge(left_pillar)

    # === CÔNG THỨC 6: Vùng mù hông (Side Occlusion Trapezoid) ===
    def _side_blind_zone(self, x_start, x_end, y_body, side_sign, near_width, far_width):
        """
        Tạo hình thang bám sát thân xe.
        Cạnh trong: trùng với thân xe (y_body).
        Cạnh ngoài: mở rộng tuyến tính (near_width ở x_start, far_width ở x_end).
        side_sign: -1 cho bên phải, +1 cho bên trái.
        """
        return [
            (x_start, y_body),                                    # Trong-gần
            (x_start, y_body + side_sign * near_width),           # Ngoài-gần
            (x_end,   y_body + side_sign * far_width),            # Ngoài-xa
            (x_end,   y_body)                                     # Trong-xa
        ]

    # === HÀM CHÍNH: Tính toàn bộ vùng mù động ===
    def compute(self, v, omega, dt=config.DT_CAMERA):
        gamma = self.update_gamma(v, omega, dt)
        stop = self.stopping_distance(v)
        d_swept = self.swept_offset(gamma)
        pivot = (config.D_HITCH, 0)

        hw_c = config.CAB_HALF_W
        hw_t = config.TRAIL_HALF_W
        trail_front = config.D_HITCH + config.TRAIL_OVERHANG
        trail_rear = config.D_HITCH - config.L_TRAIL

        # ---- A. VÙNG MÙ PHÍA TRƯỚC (Bonnet blind spot) ----
        # Hoàn toàn tĩnh về mặt hình học, không cộng thêm quãng đường phanh 
        # (Quãng đường phanh là Hazard Zone, không phải Blind Zone vật lý)
        front_depth = config.FRONT_BLIND_MIN
        front = [
            (config.CAB_FRONT_X, hw_c * 0.8),
            (config.CAB_FRONT_X + front_depth, hw_c * 1.5),
            (config.CAB_FRONT_X + front_depth, -hw_c * 1.5),
            (config.CAB_FRONT_X, -hw_c * 0.8)
        ]
        # Vùng vàng (Hazard zone - cảnh báo va chạm trước do phanh)
        # Đây mới là vùng phụ thuộc vào vận tốc
        yellow_depth = config.FRONT_BLIND_MIN + stop["d_total"]
        front_yellow = [
            (config.CAB_FRONT_X + front_depth, hw_c * 1.5),
            (config.CAB_FRONT_X + yellow_depth, hw_c * 2.5),
            (config.CAB_FRONT_X + yellow_depth, -hw_c - 2.5),
            (config.CAB_FRONT_X + front_depth, -hw_c * 1.5)
        ]

        # ---- B. VÙNG MÙ CỘT A ----
        pillar_zones = self._a_pillar_zones()

        # ---- C. VÙNG MÙ HÔNG PHẢI (Passenger Side) ----
        # Dựa trên phép chiếu hình học tia nhìn từ gương phụ (Right Mirror)
        extra_r = d_swept if gamma < 0 else 0.0
        outer_w_r = config.SIDE_BLIND_MAX + extra_r

        # Tọa độ các góc rơ-moóc sau khi xoay theo -gamma
        t_fr = self.rotate([(trail_front, -hw_t)], -gamma, pivot)[0]
        t_rr = self.rotate([(trail_rear, -hw_t)], -gamma, pivot)[0]
        t_rl = self.rotate([(trail_rear, hw_t)], -gamma, pivot)[0]

        # Vector hướng ngang đuôi rơ-moóc (từ trái sang phải)
        dx_r = t_rr[0] - t_rl[0]
        dy_r = t_rr[1] - t_rl[1]
        len_r = math.sqrt(dx_r**2 + dy_r**2)
        ux_r, uy_r = (dx_r / len_r, dy_r / len_r) if len_r > 1e-5 else (0, -1)

        # Đỉnh ngoài xa ở đuôi rơ-moóc
        t_outer_rr = (t_rr[0] + ux_r * outer_w_r, t_rr[1] + uy_r * outer_w_r)

        mirror_r = (config.CAB_FRONT_X, -hw_c)
        cab_rear_r = (config.CAB_REAR_X, -hw_c)
        outer_front_r = (config.CAB_FRONT_X - 1.0, -hw_c - 2.0)

        # Xây dựng đa giác kín không tự cắt (Non-self-intersecting Polygon)
        if gamma < 0:  # Rẽ phải: Rơ-moóc bẻ sang phải hướng về phía gương
            right_blind_zone = [mirror_r, cab_rear_r, t_fr, t_rr, t_outer_rr, outer_front_r]
        else:          # Rẽ trái hoặc đi thẳng: Rơ-moóc bẻ sang trái ra xa gương
            right_blind_zone = [mirror_r, cab_rear_r, t_rr, t_outer_rr, outer_front_r]

        # ---- D. VÙNG MÙ HÔNG TRÁI (Driver Side) ----
        # Dựa trên phép chiếu tia nhìn từ gương tài xế (Left Mirror)
        extra_l = d_swept if gamma > 0 else 0.0
        outer_w_l = 2.5 + extra_l

        # Vector hướng ngang đuôi rơ-moóc (từ phải sang trái)
        ux_l, uy_l = -ux_r, -uy_r
        t_outer_rl = (t_rl[0] + ux_l * outer_w_l, t_rl[1] + uy_l * outer_w_l)

        t_fl = self.rotate([(trail_front, hw_t)], -gamma, pivot)[0]
        mirror_l = (config.CAB_FRONT_X, hw_c)
        cab_rear_l = (config.CAB_REAR_X, hw_c)
        outer_front_l = (config.CAB_FRONT_X - 1.0, hw_c + 1.5)

        if gamma > 0:  # Rẽ trái: Rơ-moóc bẻ sang trái hướng về phía gương tài xế
            left_blind_zone = [mirror_l, cab_rear_l, t_fl, t_rl, t_outer_rl, outer_front_l]
        else:          # Rẽ phải hoặc đi thẳng
            left_blind_zone = [mirror_l, cab_rear_l, t_rl, t_outer_rl, outer_front_l]

        # ---- E. VÙNG MÙ SAU ĐUÔI RƠ-MOÓC ----
        base_rear = [
            (trail_rear, hw_t),
            (trail_rear - config.REAR_BLIND_DEPTH, hw_t),
            (trail_rear - config.REAR_BLIND_DEPTH, -hw_t),
            (trail_rear, -hw_t)
        ]
        rear = self.rotate(base_rear, -gamma, pivot)

        # ---- H. VÙNG MÙ KHE GẬP (Articulation Gap) ----
        #   Khi rơ-moóc gập, khe hở giữa sau cabin và đầu rơ-moóc mở ra.
        #   Tạo vùng tam giác nguy hiểm.
        gap_zone = None
        if abs(gamma) > math.radians(3):  # Chỉ xuất hiện khi gập > 3 độ
            trail_front_pts = self.rotate(
                [(trail_front, -hw_t), (trail_front, hw_t)], -gamma, pivot
            )
            if gamma > 0:  # Rơ-moóc lệch trái -> khe mở bên PHẢI
                gap_zone = [
                    (config.CAB_REAR_X, -hw_c),
                    trail_front_pts[0],  # Góc phải đầu rơ-moóc (đã xoay)
                    pivot
                ]
            else:  # Rơ-moóc lệch phải -> khe mở bên TRÁI
                gap_zone = [
                    (config.CAB_REAR_X, hw_c),
                    trail_front_pts[1],  # Góc trái đầu rơ-moóc (đã xoay)
                    pivot
                ]

        return {
            "gamma_deg": math.degrees(gamma),
            "gamma": gamma,
            "stopping": stop,
            "d_swept": d_swept,
            "vehicle": self.vehicle_geometry(),
            "red_zones": {
                "front": front,
                "a_pillar_right": pillar_zones[0],
                "a_pillar_left": pillar_zones[1],
                "right_side": right_blind_zone,
                "left_side": left_blind_zone,
                "rear": rear
            },
            "yellow_zones": {"front": front_yellow},
            "gap_zone": gap_zone
        }
