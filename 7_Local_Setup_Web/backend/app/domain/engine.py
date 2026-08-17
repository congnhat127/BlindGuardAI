"""Cau noi giua web va engine vung mu o 2_BlindSpot_Risk_Calculation.

Engine cua nhom dung `import config` phang va doc hang so o cap module, nen web
khong the truyen tham so vao ham. Cach lam o day: nap module engine mot lan, roi
truoc moi lan tinh thi *gan lai* cac hang so trong module `config` theo ho so
dang xem, duoi mot khoa (lock). Nho vay:

  - Khong sua mot dong nao trong code engine.
  - Cong thuc chay tren web va cong thuc chay tren xe la CUNG MOT ham.

Doi lai, phan nay khong an toan da luong -> moi loi goi engine deu di qua
`_ENGINE_LOCK`. Voi mot cong cu cau hinh 1 nguoi dung thi hoan toan du.
"""

from __future__ import annotations

import importlib
import math
import sys
import threading
from pathlib import Path
from typing import Any

import numpy as np

from .schemas import VehicleProfile

# ---------------------------------------------------------------------------
# Nap engine tu thu muc co ten bat dau bang chu so -> khong import duoc nhu
# package, phai chen vao sys.path.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[4]
ENGINE_DIR = _REPO_ROOT / "2_BlindSpot_Risk_Calculation" / "dynamic_blind_zone"

_ENGINE_LOCK = threading.RLock()
_engine_modules: dict[str, Any] = {}


class EngineUnavailable(RuntimeError):
    """Khong nap duoc engine - web van chay nhung tinh nang xem truoc vung bi tat."""


def _load_engine() -> dict[str, Any]:
    if _engine_modules:
        return _engine_modules
    if not ENGINE_DIR.is_dir():
        raise EngineUnavailable(f"Khong tim thay engine tai {ENGINE_DIR}")
    path = str(ENGINE_DIR)
    if path not in sys.path:
        sys.path.insert(0, path)
    try:
        config = importlib.import_module("config")
        _engine_modules["config"] = config
        _engine_modules["occlusion"] = importlib.import_module("occlusion_calculator")
        _engine_modules["calibration"] = importlib.import_module("camera_calibration")
        # Chup lai gia tri goc NGAY khi nap, truoc khi bat ky lan _bind nao ghi de.
        # Can thiet vi _bind sua truc tiep bien module: khong co ban chup nay thi
        # khong con cach nao doc lai gia tri mac dinh cua engine de doi chieu.
        _engine_modules["pristine"] = {
            name: getattr(config, name)
            for name in dir(config)
            if name.isupper() and not name.startswith("_")
        }
    except Exception as exc:  # pragma: no cover - phu thuoc moi truong
        _engine_modules.clear()
        raise EngineUnavailable(f"Nap engine that bai: {exc}") from exc
    return _engine_modules


def pristine_config() -> dict[str, Any]:
    """Gia tri hang so goc cua engine, chua bi _bind ghi de."""
    return dict(_load_engine()["pristine"])


def engine_status() -> dict[str, Any]:
    try:
        _load_engine()
    except EngineUnavailable as exc:
        return {"available": False, "path": str(ENGINE_DIR), "error": str(exc)}
    return {"available": True, "path": str(ENGINE_DIR), "error": None}


# ---------------------------------------------------------------------------
# Gan ho so vao module config
# ---------------------------------------------------------------------------
def _bind(profile: VehicleProfile) -> Any:
    """Ghi toan bo hang so cua ho so vao module config cua engine."""
    modules = _load_engine()
    config = modules["config"]
    geometry = profile.geometry()
    base, physics, zones, sensors = profile.base, profile.physics, profile.zones, profile.sensors

    values: dict[str, Any] = {
        # 4 thong so co ban
        "WHEELBASE_TRACTOR": base.wheelbase_tractor,
        "CAB_WIDTH": base.cab_width,
        "L_TRAIL": base.l_trail,
        "W_TRAIL": base.w_trail,
        "DRIVER_HEIGHT": base.driver_height,
        # Hinh hoc suy ra
        "CAB_HALF_W": geometry.cab_half_w,
        "TRAIL_HALF_W": geometry.trail_half_w,
        "CHASSIS_HALF_W": geometry.chassis_half_w,
        "CAB_FRONT_X": geometry.cab_front_x,
        "CAB_REAR_X": geometry.cab_rear_x,
        "D_HITCH": geometry.d_hitch,
        "TRAIL_OVERHANG": geometry.trail_overhang,
        "EYE_X": geometry.eye_x,
        "EYE_Y": geometry.eye_y,
        "EYE_Z": geometry.eye_z,
        "MIRROR_R_X": geometry.mirror_r_x,
        "MIRROR_R_Y": geometry.mirror_r_y,
        "MIRROR_L_X": geometry.mirror_l_x,
        "MIRROR_L_Y": geometry.mirror_l_y,
        "A_PILLAR_R_X": geometry.a_pillar_r_x,
        "A_PILLAR_R_Y": geometry.a_pillar_r_y,
        "A_PILLAR_L_X": geometry.a_pillar_l_x,
        "A_PILLAR_L_Y": geometry.a_pillar_l_y,
        "B_PILLAR_R_X": geometry.b_pillar_r_x,
        "B_PILLAR_R_Y": geometry.b_pillar_r_y,
        "B_PILLAR_L_X": geometry.b_pillar_l_x,
        "B_PILLAR_L_Y": geometry.b_pillar_l_y,
        # Vat ly / dong luc hoc
        "REACTION_TIME": physics.reaction_time,
        "FRICTION_COEFF": physics.friction_coeff,
        "GRAVITY": physics.gravity,
        "STEER_RATIO": physics.steer_ratio,
        "MAX_GAMMA_DEG": physics.max_gamma_deg,
        "MECHANICAL_MAX_GAMMA_DEG": physics.mechanical_max_gamma_deg,
        # Tham so vung
        "FRONT_BLIND_MIN": zones.front_blind_min,
        "SIDE_BLIND_MAX": zones.side_blind_max,
        "REAR_BLIND_DEPTH": zones.rear_blind_depth,
        "FRONT_RED_RATIO": zones.front_red_ratio,
        "A_PILLAR_WIDTH": zones.a_pillar_width,
        "A_PILLAR_BLIND_RANGE": zones.a_pillar_blind_range,
        # Cam bien
        "GPS_FREQ": sensors.gps_freq,
        "CAMERA_FREQ": sensors.camera_freq,
        "GPS_TIMEOUT_SEC": sensors.gps_timeout_sec,
        "DT_CAMERA": 1.0 / sensors.camera_freq,
        # Camera
        "K_CAMERA": np.array(
            next(iter(profile.cameras.values())).intrinsics.as_matrix(), dtype=float
        ),
        "CAMERAS_EXTRINSICS": {
            camera_id: {
                "position": list(camera.position or [0.0, 0.0, 0.0]),
                "pitch_deg": camera.pitch_deg,
                "yaw_deg": camera.yaw_deg,
                "roll_deg": camera.roll_deg,
                "monitored_blind_zones": list(camera.monitored_blind_zones),
            }
            for camera_id, camera in profile.cameras.items()
        },
    }
    for name, value in values.items():
        setattr(config, name, value)
    return config


def _poly(points: Any) -> list[list[float]]:
    """Doi list tuple sang list list, lam tron 4 chu so cho JSON gon."""
    if not points:
        return []
    return [[round(float(x), 4), round(float(y), 4)] for x, y in points]


def _vehicle_shape(profile: VehicleProfile, vehicle: dict, is_rigid: bool) -> dict:
    """Hinh dang than xe de frontend ve.

    Xe dau keo + ro-mooc (articulated): giu nguyen 3 khoi rieng (cab, chassis,
    trailer) nhu engine tra ve, vi than xe THAT co khop gap va tach roi.

    Xe than lien (rigid - bus, thung lien, xe bon): dung MOT khoi chu nhat duy
    nhat tu mui xe den duoi xe, KHONG chia cabin/khung gam/thung nhu xe khop noi.
    Day la yeu cau hien thi dung thuc te: xe than lien khong co khop noi nen
    khong duoc ve giong xe dau keo.
    """
    if not is_rigid:
        return {
            "kind": "articulated",
            "cab": _poly(vehicle["cab"]),
            "chassis": _poly(vehicle["chassis"]),
            "trailer": _poly(vehicle["trailer"]),
            "pivot": [round(vehicle["pivot"][0], 4), round(vehicle["pivot"][1], 4)],
        }

    geometry = profile.geometry()
    half_width = max(geometry.cab_half_w, geometry.trail_half_w)
    body = [
        [round(geometry.cab_front_x, 4), round(half_width, 4)],
        [round(geometry.cab_front_x, 4), round(-half_width, 4)],
        [round(geometry.trail_rear_x, 4), round(-half_width, 4)],
        [round(geometry.trail_rear_x, 4), round(half_width, 4)],
    ]
    return {
        "kind": "rigid",
        "body": body,
        "pivot": [round(vehicle["pivot"][0], 4), round(vehicle["pivot"][1], 4)],
    }


# ---------------------------------------------------------------------------
# Tinh vung mu
# ---------------------------------------------------------------------------
def compute_zones(
    profile: VehicleProfile,
    speed_kmh: float,
    control_value_deg: float,
    control_mode: str = "yaw_rate",
    settle_seconds: float = 2.0,
) -> dict[str, Any]:
    """Tinh toan bo vung mu o mot diem lam viec.

    control_mode:
      - "yaw_rate"       -> control_value_deg la toc do goc yaw (deg/s)
      - "steering_angle" -> control_value_deg la goc be lai vo-lang (deg)

    Tich phan `settle_seconds` giay de goc gap gamma dat trang thai on dinh,
    giong cach occlusion_visualizer.py mo phong. Neu chi tinh 1 buoc thi
    gamma gan 0 va hinh ve khong noi len dieu gi.
    """
    with _ENGINE_LOCK:
        modules = _load_engine()
        config = _bind(profile)
        calculator = modules["occlusion"].PureOcclusionCalculator()

        speed_mps = speed_kmh / 3.6
        control_rad = math.radians(control_value_deg)
        is_steering = control_mode == "steering_angle"
        is_rigid = profile.meta.vehicle_type == "rigid"

        dt = config.DT_CAMERA

        if is_rigid:
            # Xe than lien (bus, thung lien): khong co khop gap -> gamma = 0 tuyet doi
            # (tai lieu mo hinh toan, muc 3: "Triet tieu dong hoc khop noi").
            # Phai ep gamma = 0 NGAY TRONG update_kinematics, khong phai sau
            # compute_all: moi hinh hoc phia sau (than xe, bong khuat, banh quet)
            # deu doc self.gamma nen ep muon se ra hinh xe bi xoay nhe.
            original_update = calculator.update_kinematics

            def rigid_update(v, value, step=dt, is_steering_angle=False):
                original_update(v, value, step, is_steering_angle)
                calculator.gamma = 0.0
                return 0.0

            calculator.update_kinematics = rigid_update  # type: ignore[method-assign]

        steps = max(1, int(round(settle_seconds / dt)))
        result: dict[str, Any] = {}
        heading_rad = 0.0
        for _ in range(steps):
            result = calculator.compute_all(speed_mps, control_rad, dt, is_steering)
            heading_rad += calculator.yaw_rate * dt

        vehicle = result["vehicle"]
        occlusion = result["occlusion_zones"]
        swept = result["swept_path"]
        stopping = result["stopping_hazard"]

        turn_radius = None
        if abs(calculator.yaw_rate) > 1e-4 and speed_mps > 1e-3:
            turn_radius = abs(speed_mps / calculator.yaw_rate)

        vehicle_shape = _vehicle_shape(profile, vehicle, is_rigid)

        return {
            "input": {
                "speed_kmh": speed_kmh,
                "speed_mps": round(speed_mps, 4),
                "control_mode": control_mode,
                "control_value_deg": control_value_deg,
                "settle_seconds": settle_seconds,
            },
            "state": {
                "gamma_deg": round(result["gamma_deg"], 3),
                "yaw_rate_deg_s": round(math.degrees(result["yaw_rate"]), 3),
                "heading_deg": round(math.degrees(heading_rad), 3),
                "turn_radius_m": round(turn_radius, 3) if turn_radius else None,
                "d_swept_m": round(swept["d_swept_val"], 3),
                "is_rigid": is_rigid,
            },
            "stopping": {
                "d_reaction_m": round(stopping["d_reaction"], 3),
                "d_braking_m": round(stopping["d_braking"], 3),
                "d_total_m": round(stopping["d_total"], 3),
            },
            "vehicle": vehicle_shape,
            "reference_points": {
                "eye": [round(config.EYE_X, 4), round(config.EYE_Y, 4)],
                "mirror_right": [round(config.MIRROR_R_X, 4), round(config.MIRROR_R_Y, 4)],
                "mirror_left": [round(config.MIRROR_L_X, 4), round(config.MIRROR_L_Y, 4)],
                "a_pillar_right": [round(config.A_PILLAR_R_X, 4), round(config.A_PILLAR_R_Y, 4)],
                "a_pillar_left": [round(config.A_PILLAR_L_X, 4), round(config.A_PILLAR_L_Y, 4)],
            },
            "zones": {
                # 4 vung CHINH, dung theo de tai (phai / trai / truoc / sau).
                # right_side_occlusion va left_side_occlusion cua engine da la
                # vung gop tu guong -> khong can hop nhat them, chi doi ten hien thi
                # ("essential") de frontend biet day la 4 vung can hien mac dinh.
                "right_side_occlusion": _poly(occlusion["right_side_occlusion"]),
                "left_side_occlusion": _poly(occlusion["left_side_occlusion"]),
                "front_bonnet": _poly(occlusion["front_bonnet"]),
                "swept_path": _poly(swept["swept_path"]),
                # Vung CHI TIET - thanh phan nho hon nam trong vung ben phai/trai,
                # chi hien khi bat "Xem chi tiet" tren giao dien.
                "a_pillar_right": _poly(occlusion["a_pillar_right"]),
                "a_pillar_left": _poly(occlusion["a_pillar_left"]),
                "b_pillar_right": _poly(occlusion["b_pillar_right"]),
                "b_pillar_left": _poly(occlusion["b_pillar_left"]),
                "stopping_hazard": _poly(stopping["front_hazard_polygon"]),
            },
        }


def point_in_zones(profile: VehicleProfile, point: tuple[float, float], zones: dict) -> list[str]:
    """Tra ve danh sach ten vung chua diem - dung cho tinh nang cham thu tren ban do."""
    with _ENGINE_LOCK:
        modules = _load_engine()
        test = modules["occlusion"].PureOcclusionCalculator.is_point_in_polygon
        return [name for name, poly in zones.items() if poly and test(point, poly)]


# ---------------------------------------------------------------------------
# Camera: chieu xuoi va chieu nguoc
# ---------------------------------------------------------------------------
def _rotation_matrix(pitch_deg: float, yaw_deg: float, roll_deg: float = 0.0) -> np.ndarray:
    """Dung dung ham xoay cua engine de khong bao gio lech quy uoc truc."""
    modules = _load_engine()
    calibrator = modules["calibration"].CameraCalibrator()
    return calibrator.get_rotation_matrix_3d(pitch_deg, yaw_deg, roll_deg)


_roll_supported: bool | None = None


def roll_is_supported() -> bool:
    """Kiem tra xem engine co thuc su ap dung goc roll hay khong.

    Tinh den thoi diem viet: `camera_calibration.get_rotation_matrix_3d` co nhan
    tham so `roll_deg` va tinh `r = math.radians(roll_deg)`, nhung KHONG dua `r`
    vao ma tran ket qua (`Rz @ R0 @ Rx`) - thieu phep xoay quanh truc doc. Nghia
    la roll bi bo qua.

    Web khong tu sua engine (engine la thu chay tren xe, phai la nguon su that
    duy nhat). Thay vao do do thuc nghiem: neu doi roll ma ma tran khong doi thi
    tat o nhap roll tren giao dien va khong dua roll vao bo giai. Khi nao engine
    duoc sua, ham nay tu dong tra True va roll hoat dong lai ma khong can sua web.
    """
    global _roll_supported
    if _roll_supported is None:
        try:
            base = _rotation_matrix(0.0, 0.0, 0.0)
            rolled = _rotation_matrix(0.0, 0.0, 30.0)
            _roll_supported = bool(np.linalg.norm(base - rolled) > 1e-9)
        except EngineUnavailable:
            _roll_supported = False
    return _roll_supported


def ground_to_pixel(
    camera, points_xy: list[tuple[float, float]], z: float = 0.0, precision: int | None = 2
) -> list[list[float] | None]:
    """Chieu diem mat dat (X, Y, z) trong VCS len pixel (u, v).

    Tra None cho diem nam sau ong kinh. `precision=None` -> khong lam tron
    (bat buoc khi dung trong bo toi uu, xem chu thich o pixel_to_ground).
    """
    with _ENGINE_LOCK:
        rotation = _rotation_matrix(camera.pitch_deg, camera.yaw_deg, camera.roll_deg)
        translation = np.array(camera.position, dtype=float)
        intrinsic = np.array(camera.intrinsics.as_matrix(), dtype=float)

        out: list[list[float] | None] = []
        for x, y in points_xy:
            in_camera = rotation.T @ (np.array([x, y, z], dtype=float) - translation)
            if in_camera[2] <= 0.1:
                out.append(None)
                continue
            homogeneous = intrinsic @ in_camera
            u = float(homogeneous[0] / homogeneous[2])
            v = float(homogeneous[1] / homogeneous[2])
            out.append([u, v] if precision is None else [round(u, precision), round(v, precision)])
        return out


def pixel_to_ground(
    camera, points_uv: list[tuple[float, float]], precision: int | None = 3
) -> list[list[float] | None]:
    """Chieu nguoc pixel (u, v) ve toa do met (X, Y) tren mat duong Z = 0.

    `precision=None` -> tra so thuc day du. Bat buoc phai dung khi ham nay nam
    trong vong lap toi uu: bo giai dung Jacobian sai phan huu han voi buoc rat
    nho, neu ket qua bi lam tron ve 1e-3 m thi dao ham tinh ra bang 0 va bo giai
    khong nhich duoc (loi da gap trong lan chay dau).
    """
    with _ENGINE_LOCK:
        rotation = _rotation_matrix(camera.pitch_deg, camera.yaw_deg, camera.roll_deg)
        translation = np.array(camera.position, dtype=float)
        intrinsic_inv = np.linalg.inv(np.array(camera.intrinsics.as_matrix(), dtype=float))

        out: list[list[float] | None] = []
        for u, v in points_uv:
            ray_camera = intrinsic_inv @ np.array([u, v, 1.0], dtype=float)
            ray_vcs = rotation @ ray_camera
            if abs(ray_vcs[2]) < 1e-6:
                out.append(None)
                continue
            scale = -translation[2] / ray_vcs[2]
            if scale <= 0:
                out.append(None)
                continue
            x = float(translation[0] + scale * ray_vcs[0])
            y = float(translation[1] + scale * ray_vcs[1])
            out.append([x, y] if precision is None else [round(x, precision), round(y, precision)])
        return out
