"""Xuat ho so ra dinh dang engine nap duoc truc tiep.

Muc dich: khong bat ai phai sua code engine. Web sinh ra mot file `config.py`
co dung ten hang so ma `occlusion_calculator.py` / `calculator.py` dang doc, nen
chi can copy file do vao thay cho config.py mac dinh la chay.
"""

from __future__ import annotations

from datetime import datetime, timezone

import yaml

from ..domain.derive import CAMERA_IDS
from ..domain.schemas import VehicleProfile


def to_yaml(profile: VehicleProfile) -> str:
    """Dinh dang chinh (canonical) - dung de luu tru, chuyen xe, backup."""
    return yaml.safe_dump(
        profile.model_dump(mode="json"), sort_keys=False, allow_unicode=True, width=100
    )


def to_engine_config(profile: VehicleProfile) -> str:
    """Sinh module config.py tuong duong cho engine vung mu."""
    geometry = profile.geometry()
    base, physics, zones, sensors = profile.base, profile.physics, profile.zones, profile.sensors
    meta = profile.meta
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    lines: list[str] = []
    add = lines.append

    add("# " + "=" * 76)
    add("# CONFIG.PY - SINH TU DONG, KHONG SUA TAY")
    add("# " + "=" * 76)
    add(f"# Ho so       : {meta.profile_id}")
    add(f"# Ten hien thi : {meta.display_name or '-'}")
    add(f"# Bien so      : {meta.plate_number or '-'}")
    add(f"# Loai xe      : {meta.vehicle_type}")
    add(f"# Nguoi lap dat: {meta.installer_name or '-'}")
    add(f"# Sinh luc     : {now}")
    add("#")
    add("# Sinh boi BlindGuard AI - Local Setup Web (Tier 1).")
    add("# Moi thay doi phai thuc hien tren web roi xuat lai file nay.")
    add("# " + "=" * 76)
    add("import numpy as np")
    add("")
    add("# --- Dinh danh ho so ---")
    add(f"PROFILE_ID = {meta.profile_id!r}")
    add(f"PROFILE_DISPLAY_NAME = {meta.display_name!r}")
    add(f"PLATE_NUMBER = {meta.plate_number!r}")
    add(f"VEHICLE_TYPE = {meta.vehicle_type!r}")
    add(f"IS_ARTICULATED = {meta.vehicle_type == 'articulated'}")
    add("")
    add("# --- [BUOC 1] 4 thong so co ban tu so dang kiem ---")
    add(f"WHEELBASE_TRACTOR = {base.wheelbase_tractor}")
    add(f"CAB_WIDTH = {base.cab_width}")
    add(f"L_TRAIL = {base.l_trail}")
    add(f"W_TRAIL = {base.w_trail}")
    add(f"DRIVER_HEIGHT = {base.driver_height}")
    add("")
    add("# --- [BUOC 2] Hinh hoc suy ra (Derived Config Architecture) ---")
    for name, value in [
        ("CAB_HALF_W", geometry.cab_half_w),
        ("TRAIL_HALF_W", geometry.trail_half_w),
        ("CHASSIS_HALF_W", geometry.chassis_half_w),
        ("CAB_FRONT_X", geometry.cab_front_x),
        ("CAB_REAR_X", geometry.cab_rear_x),
        ("D_HITCH", geometry.d_hitch),
        ("TRAIL_OVERHANG", geometry.trail_overhang),
        ("EYE_X", geometry.eye_x),
        ("EYE_Y", geometry.eye_y),
        ("EYE_Z", geometry.eye_z),
        ("MIRROR_R_X", geometry.mirror_r_x),
        ("MIRROR_R_Y", geometry.mirror_r_y),
        ("MIRROR_L_X", geometry.mirror_l_x),
        ("MIRROR_L_Y", geometry.mirror_l_y),
        ("A_PILLAR_R_X", geometry.a_pillar_r_x),
        ("A_PILLAR_R_Y", geometry.a_pillar_r_y),
        ("A_PILLAR_L_X", geometry.a_pillar_l_x),
        ("A_PILLAR_L_Y", geometry.a_pillar_l_y),
        ("B_PILLAR_R_X", geometry.b_pillar_r_x),
        ("B_PILLAR_R_Y", geometry.b_pillar_r_y),
        ("B_PILLAR_L_X", geometry.b_pillar_l_x),
        ("B_PILLAR_L_Y", geometry.b_pillar_l_y),
    ]:
        add(f"{name} = {round(value, 6)}")
    add("")
    add("# --- [BUOC 3] Vat ly va dong luc hoc ---")
    add(f"REACTION_TIME = {physics.reaction_time}")
    add(f"FRICTION_COEFF = {physics.friction_coeff}")
    add(f"GRAVITY = {physics.gravity}")
    add(f"MAX_GAMMA_DEG = {physics.max_gamma_deg}")
    add(f"MECHANICAL_MAX_GAMMA_DEG = {physics.mechanical_max_gamma_deg}")
    add(f"STEER_RATIO = {physics.steer_ratio}")
    add("")
    add("# --- Tham so vung mu ---")
    add(f"FRONT_BLIND_MIN = {zones.front_blind_min}")
    add(f"SIDE_BLIND_MAX = {zones.side_blind_max}")
    add(f"REAR_BLIND_DEPTH = {zones.rear_blind_depth}")
    add(f"FRONT_RED_RATIO = {zones.front_red_ratio}")
    add(f"A_PILLAR_WIDTH = {zones.a_pillar_width}")
    add(f"A_PILLAR_BLIND_RANGE = {zones.a_pillar_blind_range}")
    add("")
    add("# --- [BUOC 4] Cam bien va camera ---")
    add(f"GPS_FREQ = {sensors.gps_freq}")
    add(f"CAMERA_FREQ = {sensors.camera_freq}")
    add(f"GPS_TIMEOUT_SEC = {sensors.gps_timeout_sec}")
    add(f"DT_CAMERA = 1.0 / {sensors.camera_freq}")
    add("")

    primary = profile.cameras[CAMERA_IDS[0]].intrinsics
    add("# Ma tran noi tai mac dinh (lay tu camera dau tien).")
    add("# Neu moi camera dung ong kinh khac nhau, doc K rieng trong CAMERAS_EXTRINSICS.")
    add("K_CAMERA = np.array([")
    for row in primary.as_matrix():
        add(f"    [{row[0]:.4f}, {row[1]:.4f}, {row[2]:.4f}],")
    add("])")
    add("")
    add("CAMERAS_EXTRINSICS = {")
    for camera_id in CAMERA_IDS:
        camera = profile.cameras[camera_id]
        position = [round(v, 4) for v in (camera.position or [0.0, 0.0, 0.0])]
        add(f'    "{camera_id}": {{')
        add(f"        \"position\": {position},")
        add(f"        \"pitch_deg\": {round(camera.pitch_deg, 3)},")
        add(f"        \"yaw_deg\": {round(camera.yaw_deg, 3)},")
        add(f"        \"roll_deg\": {round(camera.roll_deg, 3)},")
        add(f"        \"enabled\": {camera.enabled},")
        add(f"        \"source\": {camera.source!r},")
        add(f"        \"resolution\": [{camera.width}, {camera.height}],")
        add("        \"intrinsics\": {")
        add(f"            \"fx\": {round(camera.intrinsics.fx, 4)},")
        add(f"            \"fy\": {round(camera.intrinsics.fy, 4)},")
        add(f"            \"cx\": {round(camera.intrinsics.cx, 4)},")
        add(f"            \"cy\": {round(camera.intrinsics.cy, 4)},")
        add("        },")
        add(f"        \"calibration_rms_m\": {camera.calibration_rms_m},")
        add(f"        \"calibrated_at\": {camera.calibrated_at!r},")
        add("        \"monitored_blind_zones\": [")
        for zone in camera.monitored_blind_zones:
            add(f"            {zone!r},")
        add("        ],")
        add("    },")
    add("}")
    add("")
    return "\n".join(lines)


def commissioning_report(profile: VehicleProfile, zones_preview: dict | None = None) -> dict:
    """Du lieu bien ban nghiem thu - frontend render ra trang in duoc."""
    geometry = profile.geometry()
    # Nguong danh gia hieu chuan, dong bo voi services/calibration.py.
    rms_pass_m, rms_warn_m = 0.30, 0.50

    def calibration_status(camera) -> str:
        """Chu y: rms = 0.0 la ket qua TOT NHAT nhung lai falsy trong Python.

        Phai kiem tra `is None` tuong minh; dung `camera.calibration_rms_m or 99`
        se bien hieu chuan hoan hao thanh 'khong dat' (loi da gap trong test).
        """
        if camera.calibrated_at is None:
            return "not_calibrated"
        rms = camera.calibration_rms_m
        if rms is None:
            return "not_calibrated"
        if rms <= rms_pass_m:
            return "pass"
        return "warn" if rms <= rms_warn_m else "fail"

    cameras = []
    for camera_id in CAMERA_IDS:
        camera = profile.cameras[camera_id]
        cameras.append(
            {
                "camera_id": camera_id,
                "label": camera.label,
                "enabled": camera.enabled,
                "position": camera.position,
                "angles": {
                    "pitch_deg": camera.pitch_deg,
                    "yaw_deg": camera.yaw_deg,
                    "roll_deg": camera.roll_deg,
                },
                "resolution": [camera.width, camera.height],
                "hfov_deg": round(camera.intrinsics.hfov_deg(camera.width), 2),
                "calibration_rms_m": camera.calibration_rms_m,
                "calibrated_at": camera.calibrated_at,
                "status": calibration_status(camera),
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "meta": profile.meta.model_dump(mode="json"),
        "base": profile.base.model_dump(mode="json"),
        "physics": profile.physics.model_dump(mode="json"),
        "zones": profile.zones.model_dump(mode="json"),
        "sensors": profile.sensors.model_dump(mode="json"),
        "geometry": geometry.as_dict(),
        "cameras": cameras,
        "zones_preview": zones_preview,
    }
