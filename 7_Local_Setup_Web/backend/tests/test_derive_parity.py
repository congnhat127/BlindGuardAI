"""Bat buoc: cong thuc suy luan cua web phai khop engine tung chu so.

Neu ai doi ty le trong config.py ma khong doi derive.py (hoac nguoc lai), test
nay do ngay. Day la lop bao ve quan trong nhat cua ca backend: mot ho so sinh
tu web nhung hinh hoc lech voi engine se lam vung mu ve sai vi tri tren xe that.
"""

from __future__ import annotations

import math

import pytest

from app.domain import engine
from app.domain.derive import CAMERA_IDS, derive_geometry
from app.domain.schemas import ProfileMeta, VehicleProfile


@pytest.fixture(scope="module")
def engine_config():
    """Ban chup hang so goc cua engine duoi dang doi tuong truy cap bang thuoc tinh."""
    try:
        pristine = engine.pristine_config()
    except engine.EngineUnavailable as exc:
        pytest.skip(f"Khong nap duoc engine: {exc}")
    return type("PristineConfig", (), pristine)


def test_derived_geometry_matches_engine_config(engine_config):
    """Dung dung 4 thong so mac dinh cua config.py roi so tung gia tri."""
    geometry = derive_geometry(
        engine_config.WHEELBASE_TRACTOR,
        engine_config.CAB_WIDTH,
        engine_config.L_TRAIL,
        engine_config.W_TRAIL,
        engine_config.DRIVER_HEIGHT,
    )
    pairs = [
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
    ]
    for name, web_value in pairs:
        engine_value = getattr(engine_config, name)
        assert math.isclose(web_value, engine_value, rel_tol=1e-9, abs_tol=1e-9), (
            f"{name}: web={web_value} engine={engine_value}"
        )


def test_camera_positions_match_engine(engine_config):
    geometry = derive_geometry(
        engine_config.WHEELBASE_TRACTOR,
        engine_config.CAB_WIDTH,
        engine_config.L_TRAIL,
        engine_config.W_TRAIL,
        engine_config.DRIVER_HEIGHT,
    )
    positions = geometry.camera_positions()
    # Doc ban chup goc, khong doc thuoc tinh module: _bind ghi de bien module nen
    # mot test chay truoc co the da doi CAMERAS_EXTRINSICS.
    #
    # REAR_CAM la camera thu 4 rieng cua web (de dat du 4 camera nhu de tai),
    # engine goc chi co 3 camera nen khong co gia tri de doi chieu - bo qua no.
    pristine = engine.pristine_config()
    assert set(positions) == set(CAMERA_IDS)
    for camera_id, position in positions.items():
        if camera_id not in pristine["CAMERAS_EXTRINSICS"]:
            continue
        expected = pristine["CAMERAS_EXTRINSICS"][camera_id]["position"]
        for got, want in zip(position, expected):
            assert math.isclose(got, want, abs_tol=1e-9), f"{camera_id}: {position} != {expected}"


def test_monitored_zones_match_engine():
    pristine = engine.pristine_config()
    profile = VehicleProfile(meta=ProfileMeta(profile_id="parity-truck"))
    for camera_id in CAMERA_IDS:
        if camera_id not in pristine["CAMERAS_EXTRINSICS"]:
            continue  # REAR_CAM: camera thu 4 rieng cua web, engine goc chua co
        assert (
            profile.cameras[camera_id].monitored_blind_zones
            == pristine["CAMERAS_EXTRINSICS"][camera_id]["monitored_blind_zones"]
        )


@pytest.mark.parametrize(
    "wheelbase,cab_width,l_trail,w_trail",
    [
        (3.4, 2.44, 7.0, 2.44),
        (4.2, 2.35, 6.2, 2.35),
        (6.0, 2.5, 6.0, 2.5),
        (3.6, 2.5, 12.0, 2.5),
    ],
)
def test_derivation_invariants(wheelbase, cab_width, l_trail, w_trail):
    """Bat bien hinh hoc phai dung voi moi kich thuoc xe hop le."""
    geometry = derive_geometry(wheelbase, cab_width, l_trail, w_trail)

    # Mui xe luon o truoc vach sau cabin.
    assert geometry.cab_front_x > geometry.cab_rear_x
    # Chot keo nam giua truc sau va vach sau cabin.
    assert 0 < geometry.d_hitch < geometry.cab_rear_x
    # Ro-mooc keo ve phia sau goc toa do.
    assert geometry.trail_rear_x < 0 < geometry.trail_front_x
    # Guong vuon ra ngoai than cabin.
    assert abs(geometry.mirror_r_y) > geometry.cab_half_w
    assert abs(geometry.mirror_l_y) > geometry.cab_half_w
    # Cot A nam trong be rong cabin.
    assert abs(geometry.a_pillar_r_y) < geometry.cab_half_w
    # Doi xung trai/phai.
    assert math.isclose(geometry.mirror_l_y, -geometry.mirror_r_y)
    assert math.isclose(geometry.mirror_l_x, geometry.mirror_r_x)
    # Tam mat cao hon mui xe va thap hon 4 m.
    assert 1.5 < geometry.eye_z < 4.0
    # Tong chieu dai duong va lon hon chieu dai ro-mooc.
    assert geometry.total_length > l_trail
