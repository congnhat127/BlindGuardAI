"""Object-independent Dynamic Hazard Zone for a tractor-semitrailer.

DHZ = predicted ego swept occupancy + dynamic physical clearance.
Inputs are GPS/IMU vehicle state and vehicle geometry only.
"""
import math

from shapely.geometry import Polygon
from shapely.ops import unary_union

import config


class DynamicHazardZoneCalculator:
    """Build a potential hazard envelope from ego-vehicle state."""

    def __init__(self, gamma=0.0):
        self.gamma = self._clamp_gamma(float(gamma))

    @staticmethod
    def _clamp_gamma(gamma):
        limit = math.radians(config.MECHANICAL_MAX_GAMMA_DEG)
        return max(-limit, min(limit, gamma))

    @staticmethod
    def _validate_finite(**values):
        for name, value in values.items():
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")

    @staticmethod
    def transform_polygon(points, x, y, yaw):
        c, s = math.cos(yaw), math.sin(yaw)
        return [(px*c - py*s + x, px*s + py*c + y) for px, py in points]

    @staticmethod
    def yaw_rate_from_headings(previous, current, dt, degrees=True):
        """Wrapped GPS-heading difference divided by ``dt``."""
        if dt <= 0:
            raise ValueError("dt must be positive")
        p = math.radians(previous) if degrees else previous
        c = math.radians(current) if degrees else current
        return math.atan2(math.sin(c-p), math.cos(c-p)) / dt

    @staticmethod
    def _exterior(geometry):
        if geometry.geom_type == "MultiPolygon":
            geometry = max(geometry.geoms, key=lambda part: part.area)
        return list(geometry.exterior.coords)

    def get_vehicle_polygons(self, gamma=None):
        """Return local cab, chassis and trailer polygons."""
        gamma = self.gamma if gamma is None else self._clamp_gamma(float(gamma))
        cab = [
            (config.CAB_FRONT_X, config.CAB_HALF_W),
            (config.CAB_FRONT_X, -config.CAB_HALF_W),
            (config.CAB_REAR_X, -config.CAB_HALF_W),
            (config.CAB_REAR_X, config.CAB_HALF_W),
        ]
        chassis = [
            (config.CAB_REAR_X, config.CHASSIS_HALF_W),
            (config.CAB_REAR_X, -config.CHASSIS_HALF_W),
            (-0.3, -config.CHASSIS_HALF_W),
            (-0.3, config.CHASSIS_HALF_W),
        ]
        hitch = (config.D_HITCH, 0.0)
        front = config.D_HITCH + config.TRAIL_OVERHANG
        rear = config.D_HITCH - config.L_TRAIL
        base_trailer = [
            (front, config.TRAIL_HALF_W), (front, -config.TRAIL_HALF_W),
            (rear, -config.TRAIL_HALF_W), (rear, config.TRAIL_HALF_W),
        ]
        trailer = self.transform_polygon(base_trailer, 0.0, 0.0, -gamma)
        dx = hitch[0] - hitch[0] * math.cos(gamma)
        dy = hitch[0] * math.sin(gamma)
        trailer = [(x + dx, y + dy) for x, y in trailer]
        return {"cab": cab, "chassis": chassis, "trailer": trailer, "pivot": hitch}

    @staticmethod
    def _gamma_rate(speed, yaw_rate, gamma):
        length = config.TRAILER_KINGPIN_TO_AXLE
        if length <= 0:
            raise ValueError("TRAILER_KINGPIN_TO_AXLE must be positive")
        hitch_offset = config.D_HITCH
        return (yaw_rate * (1.0 - hitch_offset * math.cos(gamma) / length)
                - speed * math.sin(gamma) / length)

    @classmethod
    def estimate_steady_state_gamma(cls, speed_mps, yaw_rate_rad_s):
        """Demo initializer when no previous GPS/IMU samples are available."""
        speed = float(speed_mps)
        yaw_rate = float(yaw_rate_rad_s)
        if abs(speed) < config.DHZ_MIN_MOVING_SPEED_MPS:
            return 0.0
        curvature = yaw_rate / speed
        offset_term = config.D_HITCH * curvature
        scale = math.sqrt(1.0 + offset_term * offset_term)
        rhs = config.TRAILER_KINGPIN_TO_AXLE * curvature / scale
        rhs = max(-1.0, min(1.0, rhs))
        gamma = math.asin(rhs) - math.atan(offset_term)
        return cls._clamp_gamma(gamma)

    def update_articulation(self, speed_mps, yaw_rate_rad_s, dt):
        """Update the internal trailer state from one synchronized GPS/IMU sample."""
        speed = float(speed_mps)
        yaw_rate = float(yaw_rate_rad_s)
        if dt <= 0:
            raise ValueError("dt must be positive")
        self._validate_finite(speed=speed, yaw_rate=yaw_rate, dt=dt)
        k1 = self._gamma_rate(speed, yaw_rate, self.gamma)
        gamma_mid = self._clamp_gamma(self.gamma + 0.5 * dt * k1)
        self.gamma = self._clamp_gamma(
            self.gamma + dt * self._gamma_rate(speed, yaw_rate, gamma_mid))
        return self.gamma

    @staticmethod
    def dynamic_clearance(speed, yaw_rate, lateral_accel):
        """Base clearance plus displacement implied by lateral-model residual."""
        expected_ay = speed * yaw_rate
        residual_ay = lateral_accel - expected_ay
        response = config.DHZ_CLEARANCE_RESPONSE_SEC
        added = 0.5 * abs(residual_ay) * response * response
        added = min(added, config.DHZ_MAX_DYNAMIC_CLEARANCE_M)
        return config.DHZ_BASE_CLEARANCE_M + added, expected_ay, residual_ay, added

    @staticmethod
    def steady_state_offtracking_reference(speed, yaw_rate):
        """Low-speed steady-circle steer-axle to trailer-axle offtracking."""
        if speed < -config.DHZ_MIN_MOVING_SPEED_MPS:
            return None
        if (abs(speed) < config.DHZ_MIN_MOVING_SPEED_MPS
                or abs(yaw_rate) < 1e-10):
            return 0.0
        tractor_rear_radius = abs(speed / yaw_rate)
        hitch_radius = math.hypot(tractor_rear_radius, config.D_HITCH)
        trailer_length = config.TRAILER_KINGPIN_TO_AXLE
        if hitch_radius <= trailer_length:
            return None
        steer_radius = math.hypot(
            tractor_rear_radius, config.WHEELBASE_TRACTOR)
        trailer_axle_radius = math.sqrt(
            hitch_radius * hitch_radius - trailer_length * trailer_length)
        return max(0.0, steer_radius - trailer_axle_radius)

    def compute(self, speed_mps, yaw_rate_rad_s,
                longitudinal_accel_mps2=0.0, lateral_accel_mps2=None,
                gamma_rad=None):
        """Compute DHZ using only synchronized GPS/IMU state and geometry."""
        speed0 = float(speed_mps)
        yaw_rate = float(yaw_rate_rad_s)
        accel_x = float(longitudinal_accel_mps2)
        if lateral_accel_mps2 is None:
            lateral_accel = speed0 * yaw_rate
        else:
            lateral_accel = float(lateral_accel_mps2)
        gamma0 = self.gamma if gamma_rad is None else self._clamp_gamma(float(gamma_rad))
        self._validate_finite(speed=speed0, yaw_rate=yaw_rate, accel_x=accel_x,
                              lateral_accel=lateral_accel, gamma=gamma0)

        stationary_yaw = (abs(speed0) < config.DHZ_MIN_MOVING_SPEED_MPS
                          and abs(yaw_rate) > config.DHZ_MAX_STATIONARY_YAW_RATE_RAD_S)
        motion_yaw = 0.0 if stationary_yaw and abs(accel_x) < 1e-10 else yaw_rate
        clearance, expected_ay, residual_ay, added_clearance = self.dynamic_clearance(
            speed0, motion_yaw, lateral_accel)

        current_vehicle = self.get_vehicle_polygons(gamma0)
        x = y = heading = elapsed = travelled = signed_travel = 0.0
        speed = speed0
        gamma = gamma0
        swept_parts = []
        tractor_rear_axle_path = []
        tractor_steer_axle_path = []
        trailer_axle_path = []
        trailer_rear_corner_paths = [[], []]
        steps = 0

        def transform_point(point):
            return self.transform_polygon([point], x, y, heading)[0]

        def append_pose():
            local_vehicle = self.get_vehicle_polygons(gamma)
            for name in ("cab", "chassis", "trailer"):
                points = self.transform_polygon(local_vehicle[name], x, y, heading)
                swept_parts.append(Polygon(points))

            tractor_rear_axle_path.append((x, y))
            tractor_steer_axle_path.append(
                transform_point((config.WHEELBASE_TRACTOR, 0.0)))
            trailer_axle_local = (
                config.D_HITCH
                - config.TRAILER_KINGPIN_TO_AXLE * math.cos(gamma),
                config.TRAILER_KINGPIN_TO_AXLE * math.sin(gamma),
            )
            trailer_axle_path.append(transform_point(trailer_axle_local))
            trailer_rear_corner_paths[0].append(
                transform_point(local_vehicle["trailer"][2]))
            trailer_rear_corner_paths[1].append(
                transform_point(local_vehicle["trailer"][3]))

        append_pose()

        horizon = config.DHZ_PREDICTION_HORIZON_SEC
        dt_nominal = config.DHZ_INTEGRATION_DT_SEC
        while elapsed < horizon - 1e-10:
            dt = min(dt_nominal, horizon - elapsed)
            next_speed = speed + accel_x * dt
            reaches_stop = (
                abs(speed) > 1e-10
                and speed * accel_x < 0.0
                and speed * next_speed <= 0.0
            )
            if reaches_stop:
                dt = abs(speed / accel_x)
                next_speed = 0.0

            speed_mid = speed + 0.5 * accel_x * dt
            distance_step = speed_mid * dt
            if abs(distance_step) <= 1e-10 and abs(speed) <= 1e-10:
                break

            heading_mid = heading + 0.5 * motion_yaw * dt
            x += distance_step * math.cos(heading_mid)
            y += distance_step * math.sin(heading_mid)
            heading += motion_yaw * dt

            gamma_rate = self._gamma_rate(speed_mid, motion_yaw, gamma)
            gamma_mid = self._clamp_gamma(gamma + 0.5 * dt * gamma_rate)
            gamma = self._clamp_gamma(
                gamma + dt * self._gamma_rate(speed_mid, motion_yaw, gamma_mid))
            speed = next_speed
            elapsed += dt
            travelled += abs(distance_step)
            signed_travel += distance_step
            steps += 1
            append_pose()
            if reaches_stop:
                break

        current_body = unary_union([
            Polygon(current_vehicle[name])
            for name in ("cab", "chassis", "trailer")
        ]).buffer(0)
        raw_swept = unary_union(swept_parts).buffer(0)
        current_envelope = current_body.buffer(
            config.DHZ_BASE_CLEARANCE_M, join_style=2)
        dynamic_zone = raw_swept.buffer(clearance, join_style=2)

        curvature = (motion_yaw / speed0
                     if abs(speed0) >= config.DHZ_MIN_MOVING_SPEED_MPS else 0.0)
        turning_radius = math.inf if abs(curvature) < 1e-10 else 1.0 / abs(curvature)
        offtracking_reference = self.steady_state_offtracking_reference(
            speed0, motion_yaw)
        trailer_heading_change = heading - gamma + gamma0
        rear_overhang = max(
            0.0, config.L_TRAIL - config.TRAILER_KINGPIN_TO_AXLE)
        tail_swing_rotation_reference = (
            rear_overhang * abs(math.sin(trailer_heading_change)))
        swept_extension_area = raw_swept.difference(current_body).area
        state_is_plausible = (
            not stationary_yaw
            and abs(lateral_accel) <= config.DHZ_MAX_LATERAL_ACCEL_MPS2
        )
        return {
            "vehicle": current_vehicle,
            "current_footprint": self._exterior(current_body),
            "current_safety_envelope": self._exterior(current_envelope),
            "raw_swept_path": self._exterior(raw_swept),
            "dynamic_hazard_zone": self._exterior(dynamic_zone),
            "reference_paths": {
                "tractor_rear_axle": tractor_rear_axle_path,
                "tractor_steer_axle": tractor_steer_axle_path,
                "trailer_axle": trailer_axle_path,
                "trailer_rear_right": trailer_rear_corner_paths[0],
                "trailer_rear_left": trailer_rear_corner_paths[1],
            },
            "metrics": {
                "preview_distance_m": travelled,
                "signed_travel_m": signed_travel,
                "motion_direction": (
                    "forward" if speed0 > 0 else (
                        "reverse" if speed0 < 0 else "stationary")),
                "elapsed_prediction_sec": elapsed,
                "curvature_1pm": curvature,
                "turning_radius_m": turning_radius,
                "yaw_rate_rad_s": yaw_rate,
                "longitudinal_accel_mps2": accel_x,
                "measured_lateral_accel_mps2": lateral_accel,
                "expected_lateral_accel_mps2": expected_ay,
                "lateral_residual_mps2": residual_ay,
                "base_clearance_m": config.DHZ_BASE_CLEARANCE_M,
                "additional_clearance_m": added_clearance,
                "dynamic_clearance_m": clearance,
                "current_gamma_deg": math.degrees(gamma0),
                "predicted_gamma_deg": math.degrees(gamma),
                "steady_state_offtracking_reference_m": offtracking_reference,
                "tail_swing_rotation_reference_m": tail_swing_rotation_reference,
                "swept_extension_area_m2": swept_extension_area,
                "integration_steps": steps,
                "state_is_plausible": state_is_plausible,
            },
        }
