"""Kiem chung phep chieu camera va bo giai goc lap.

Tinh chat can dung: neu ky thuat vien cham DUNG vao cac vat moc, bo giai phai
khoi phuc lai dung pose that. Test nay tao ra "su that" nhan tao roi kiem tra
bo giai tim lai duoc - tuc la quy trinh cang chinh tren web dung ve mat toan hoc.
"""

from __future__ import annotations

import math

import pytest

from app.adapters import scene
from app.domain import engine
from app.domain.schemas import CameraConfig, ProfileMeta, VehicleProfile
from app.services import calibration as cal


@pytest.fixture(scope="module")
def profile() -> VehicleProfile:
    if not engine.engine_status()["available"]:
        pytest.skip("Engine khong san sang")
    return VehicleProfile(meta=ProfileMeta(profile_id="calib-truck"))


def _perturb(camera: CameraConfig, d_pitch: float, d_yaw: float, d_height: float) -> CameraConfig:
    data = camera.model_dump()
    data["pitch_deg"] = camera.pitch_deg + d_pitch
    data["yaw_deg"] = camera.yaw_deg + d_yaw
    position = list(camera.position)
    position[2] += d_height
    data["position"] = position
    data["auto_position"] = False
    return CameraConfig.model_validate(data)


@pytest.mark.parametrize("camera_id", ["MIRROR_R", "MIRROR_L", "FRONT_CAM"])
def test_projection_roundtrip(profile, camera_id):
    """met -> pixel -> met phai tra ve dung diem ban dau."""
    camera = profile.cameras[camera_id]
    cones = scene.CALIBRATION_CONES[camera_id]
    pixels = engine.ground_to_pixel(camera, cones, precision=None)
    assert all(p is not None for p in pixels), "chop non phai nam trong khung hinh"

    back = engine.pixel_to_ground(camera, [(p[0], p[1]) for p in pixels], precision=None)
    for original, recovered in zip(cones, back):
        assert recovered is not None
        assert math.dist(original, recovered) < 1e-6


@pytest.mark.parametrize("camera_id", ["MIRROR_R", "MIRROR_L", "FRONT_CAM"])
@pytest.mark.parametrize(
    "d_pitch,d_yaw,d_height",
    [(2.5, -3.0, -0.08), (-4.0, 5.0, 0.12), (0.0, 0.0, 0.0), (6.0, -7.5, -0.2)],
)
def test_solver_recovers_truth(profile, camera_id, d_pitch, d_yaw, d_height):
    """Bo giai phai tim lai pose that voi sai so duoi nguong nghiem thu."""
    nominal = profile.cameras[camera_id]
    truth = _perturb(nominal, d_pitch, d_yaw, d_height)
    cones = scene.CALIBRATION_CONES[camera_id]

    pixels = engine.ground_to_pixel(truth, cones, precision=None)
    points = [
        cal.Correspondence(u=pixel[0], v=pixel[1], x=cone[0], y=cone[1], label=f"cone{i}")
        for i, (pixel, cone) in enumerate(zip(pixels, cones))
        if pixel is not None
    ]
    if len(points) < 3:
        pytest.skip("pose thu nghiem lam chop non ra ngoai khung hinh")

    result = cal.solve_camera_angles(nominal, points, solve_height=True)
    assert result.ok
    assert result.rms_m < cal.RMS_TARGET_M, result.message
    assert result.verdict == "pass"
    assert abs(result.pitch_deg - truth.pitch_deg) < 0.5
    assert abs(result.height_m - truth.position[2]) < 0.1


def test_solver_needs_enough_points(profile):
    camera = profile.cameras["MIRROR_R"]
    result = cal.solve_camera_angles(camera, [cal.Correspondence(u=100, v=900, x=1.0, y=-2.5)])
    assert not result.ok
    assert "2 diem" in result.message


def test_verify_reports_error_in_metres(profile):
    """Sai so phai bao bang met - dung don vi cua tieu chi nghiem thu."""
    camera = profile.cameras["MIRROR_R"]
    cones = scene.CALIBRATION_CONES["MIRROR_R"]
    pixels = engine.ground_to_pixel(camera, cones, precision=None)
    points = [
        cal.Correspondence(u=p[0], v=p[1], x=c[0], y=c[1])
        for p, c in zip(pixels, cones)
        if p is not None
    ]
    perfect = cal.verify_points(camera, points)
    assert perfect["rms_m"] == pytest.approx(0.0, abs=1e-6)
    assert perfect["verdict"] == "pass"

    # Bao so do sai 1 m -> phai bi danh truot.
    shifted = [cal.Correspondence(u=p.u, v=p.v, x=p.x + 1.0, y=p.y) for p in points]
    bad = cal.verify_points(camera, shifted)
    assert bad["rms_m"] == pytest.approx(1.0, abs=1e-3)
    assert bad["verdict"] == "fail"


def test_mock_scene_is_consistent_with_camera_model(profile):
    """Anh gia lap phai ve tu pose lech so voi cau hinh - de co viec cang chinh.

    Neu anh mock ve dung pose cau hinh thi ky thuat vien khong hoc duoc gi va
    khong the demo quy trinh nghiem thu.
    """
    for camera_id in ("MIRROR_R", "MIRROR_L", "FRONT_CAM"):
        nominal = profile.cameras[camera_id]
        truth = scene.build_truth_camera(camera_id, nominal)
        assert (truth.pitch_deg, truth.yaw_deg) != (nominal.pitch_deg, nominal.yaw_deg)
        # Roll phai bang nhau: engine chua ap dung roll nen mock khong duoc dung roll.
        assert truth.roll_deg == nominal.roll_deg
