"""File config.py sinh tu web phai nap duoc vao engine va cho ket qua y het.

Day la loi hua tich hop quan trong nhat cua ca cong cu: "copy file nay vao thay
config.py la chay, khong sua mot dong code nao". Test nay chung minh loi hua do
bang cach nap that file sinh ra roi so tung hang so voi ho so goc.
"""

from __future__ import annotations

import importlib.util
import math

import pytest

from app.domain import engine
from app.domain.derive import CAMERA_IDS
from app.domain.schemas import ProfileMeta, VehicleBase, VehicleProfile
from app.services import exporter


def _load_generated(path) -> object:
    spec = importlib.util.spec_from_file_location("generated_config", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def profile() -> VehicleProfile:
    built = VehicleProfile(
        meta=ProfileMeta(
            profile_id="export-truck",
            display_name="Xe xuat thu",
            plate_number="43C-777.77",
            installer_name="KTV Nam",
        ),
        base=VehicleBase(
            wheelbase_tractor=4.05,
            cab_width=2.42,
            l_trail=9.6,
            w_trail=2.48,
            driver_height=1.78,
        ),
    )
    # Gia lap ket qua cang chinh de kiem tra ca phan camera.
    built.cameras["MIRROR_R"].pitch_deg = -13.75
    built.cameras["MIRROR_R"].yaw_deg = -167.25
    built.cameras["MIRROR_R"].calibration_rms_m = 0.084
    built.cameras["MIRROR_R"].calibrated_at = "2026-08-17T10:00:00+00:00"
    built.cameras["MIRROR_R"].source = "rtsp://10.0.0.11:554/stream1"
    return built


def test_generated_config_is_importable_and_matches(profile, tmp_path):
    path = tmp_path / "config_generated.py"
    path.write_text(exporter.to_engine_config(profile), encoding="utf-8")

    generated = _load_generated(path)
    geometry = profile.geometry()

    # 4 thong so co ban
    assert generated.WHEELBASE_TRACTOR == profile.base.wheelbase_tractor
    assert generated.CAB_WIDTH == profile.base.cab_width
    assert generated.L_TRAIL == profile.base.l_trail
    assert generated.W_TRAIL == profile.base.w_trail
    assert generated.DRIVER_HEIGHT == profile.base.driver_height

    # Hinh hoc suy ra
    for name, expected in [
        ("CAB_HALF_W", geometry.cab_half_w),
        ("CAB_FRONT_X", geometry.cab_front_x),
        ("CAB_REAR_X", geometry.cab_rear_x),
        ("D_HITCH", geometry.d_hitch),
        ("EYE_X", geometry.eye_x),
        ("EYE_Y", geometry.eye_y),
        ("EYE_Z", geometry.eye_z),
        ("MIRROR_R_Y", geometry.mirror_r_y),
        ("A_PILLAR_L_Y", geometry.a_pillar_l_y),
        ("B_PILLAR_R_Y", geometry.b_pillar_r_y),
    ]:
        assert math.isclose(getattr(generated, name), expected, abs_tol=1e-6), name

    # Vat ly va tham so vung
    assert generated.REACTION_TIME == profile.physics.reaction_time
    assert generated.FRICTION_COEFF == profile.physics.friction_coeff
    assert generated.STEER_RATIO == profile.physics.steer_ratio
    assert generated.A_PILLAR_WIDTH == profile.zones.a_pillar_width
    assert generated.SIDE_BLIND_MAX == profile.zones.side_blind_max
    assert math.isclose(generated.DT_CAMERA, 1.0 / profile.sensors.camera_freq)

    # Camera
    assert set(generated.CAMERAS_EXTRINSICS) == set(CAMERA_IDS)
    mirror = generated.CAMERAS_EXTRINSICS["MIRROR_R"]
    assert mirror["pitch_deg"] == -13.75
    assert mirror["yaw_deg"] == -167.25
    assert mirror["source"] == "rtsp://10.0.0.11:554/stream1"
    assert mirror["calibration_rms_m"] == 0.084
    assert (
        mirror["monitored_blind_zones"]
        == profile.cameras["MIRROR_R"].monitored_blind_zones
    )
    assert generated.K_CAMERA.shape == (3, 3)
    assert math.isclose(generated.K_CAMERA[0][0], profile.cameras["MIRROR_R"].intrinsics.fx, abs_tol=1e-3)


def test_generated_config_names_cover_everything_engine_reads(profile, tmp_path):
    """File sinh ra phai co DU moi hang so ma engine doc.

    Neu engine bo sung mot hang so moi ma exporter chua sinh, test nay do ngay -
    thay vi de xe ngoai hien truong bao AttributeError.
    """
    path = tmp_path / "config_generated.py"
    path.write_text(exporter.to_engine_config(profile), encoding="utf-8")
    generated = _load_generated(path)

    if not engine.engine_status()["available"]:
        pytest.skip("Engine khong san sang")

    required = {
        name
        for name in engine.pristine_config()
        if name.isupper() and not name.startswith("_")
    }
    missing = {name for name in required if not hasattr(generated, name)}
    assert not missing, f"Exporter chua sinh cac hang so engine can: {sorted(missing)}"


def test_yaml_export_round_trips(profile):
    """YAML xuat ra phai doc lai duoc thanh dung ho so ban dau."""
    import yaml

    text = exporter.to_yaml(profile)
    restored = VehicleProfile.model_validate(yaml.safe_load(text))
    assert restored.base == profile.base
    assert restored.physics == profile.physics
    assert restored.zones == profile.zones
    assert restored.meta.profile_id == profile.meta.profile_id
    assert restored.cameras["MIRROR_R"].pitch_deg == profile.cameras["MIRROR_R"].pitch_deg
    assert restored.cameras["MIRROR_R"].calibrated_at == profile.cameras["MIRROR_R"].calibrated_at


def test_report_flags_uncalibrated_and_perfect_calibration(profile):
    """rms = 0.0 la ket qua tot nhat, khong duoc coi la 'chua hieu chuan'."""
    profile.cameras["MIRROR_L"].calibration_rms_m = 0.0
    profile.cameras["MIRROR_L"].calibrated_at = "2026-08-17T10:05:00+00:00"

    report = exporter.commissioning_report(profile)
    by_id = {camera["camera_id"]: camera for camera in report["cameras"]}

    assert by_id["MIRROR_R"]["status"] == "pass"
    assert by_id["MIRROR_L"]["status"] == "pass"
    assert by_id["FRONT_CAM"]["status"] == "not_calibrated"
