"""Smoke test toan bo API - chay o che do mock, khong can phan cung."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.core.settings import settings
from app.main import app
from app.services.store import ProfileStore


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    data_dir = tmp_path_factory.mktemp("data")
    store = ProfileStore(data_dir)
    app.dependency_overrides[deps.get_store] = lambda: store
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["device_backend"] == settings.device_backend


def test_templates_and_dictionary(client):
    templates = client.get("/api/templates").json()["templates"]
    assert any(t["template_id"] == "container_40ft" for t in templates)
    assert all(t["base"]["wheelbase_tractor"] > 0 for t in templates)

    dictionary = client.get("/api/dictionary").json()
    assert "right_side_occlusion" in dictionary["zones"]
    assert dictionary["zones"]["right_side_occlusion"]["color"].startswith("#")
    assert "CAB_FRONT_X" in dictionary["derivation_basis"]


def test_derive_endpoint_returns_geometry_and_warnings(client):
    response = client.post(
        "/api/derive",
        json={
            "wheelbase_tractor": 3.6,
            "cab_width": 2.5,
            "l_trail": 12.0,
            "w_trail": 2.5,
            "driver_height": 1.7,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["geometry"]["cab_front_x"] == pytest.approx(4.0)
    assert body["geometry"]["eye_z"] == pytest.approx(2.2)
    assert set(body["camera_positions"]) == {"MIRROR_R", "MIRROR_L", "FRONT_CAM"}
    assert body["warnings"] == []


def test_derive_warns_on_unit_mistake(client):
    """Nhap centimet thay vi met phai bi canh bao, khong duoc im lang cho qua."""
    response = client.post(
        "/api/derive",
        json={
            "wheelbase_tractor": 36.0,
            "cab_width": 2.5,
            "l_trail": 12.0,
            "w_trail": 2.5,
            "driver_height": 1.7,
        },
    )
    warnings = response.json()["warnings"]
    assert any(w["field"] == "wheelbase_tractor" for w in warnings)


def test_profile_lifecycle(client):
    scaffold = client.post(
        "/api/profiles/scaffold",
        json={
            "profile_id": "demo-truck",
            "display_name": "Xe demo",
            "plate_number": "43C-123.45",
            "template_id": "container_40ft",
        },
    )
    assert scaffold.status_code == 200
    profile = scaffold.json()
    assert profile["meta"]["vehicle_type"] == "articulated"
    assert len(profile["cameras"]) == 3

    saved = client.put("/api/profiles/demo-truck", json=profile)
    assert saved.status_code == 200, saved.text
    assert saved.json()["warnings"] == []

    listed = client.get("/api/profiles").json()["profiles"]
    assert any(p["profile_id"] == "demo-truck" for p in listed)

    # Luu lan hai -> phai sinh 1 ban lich su.
    client.put("/api/profiles/demo-truck", json=profile)
    versions = client.get("/api/profiles/demo-truck/versions").json()["versions"]
    assert len(versions) >= 1

    python_export = client.get("/api/profiles/demo-truck/export", params={"fmt": "python"})
    assert python_export.status_code == 200
    body = python_export.text
    assert "WHEELBASE_TRACTOR = 3.6" in body
    assert "CAMERAS_EXTRINSICS" in body
    assert "K_CAMERA" in body

    yaml_export = client.get("/api/profiles/demo-truck/export", params={"fmt": "yaml"})
    assert yaml_export.status_code == 200
    assert "profile_id: demo-truck" in yaml_export.text

    report = client.get("/api/profiles/demo-truck/report").json()
    assert report["meta"]["profile_id"] == "demo-truck"
    assert len(report["cameras"]) == 3
    assert all(c["status"] == "not_calibrated" for c in report["cameras"])


def test_zones_preview_deforms_when_turning(client):
    profile = client.post(
        "/api/profiles/scaffold", json={"profile_id": "zone-truck", "template_id": "container_40ft"}
    ).json()

    straight = client.post(
        "/api/zones/preview",
        json={"profile": profile, "speed_kmh": 10, "control_value_deg": 0},
    ).json()
    turning = client.post(
        "/api/zones/preview",
        json={"profile": profile, "speed_kmh": 10, "control_value_deg": 12},
    ).json()

    assert straight["state"]["gamma_deg"] == pytest.approx(0.0, abs=1e-6)
    assert abs(turning["state"]["gamma_deg"]) > 5.0
    # Di thang khong co dai banh quet; re thi phai co.
    assert straight["zones"]["swept_path"] == []
    assert len(turning["zones"]["swept_path"]) >= 3
    # Quang duong phanh phai tang theo toc do.
    fast = client.post(
        "/api/zones/preview",
        json={"profile": profile, "speed_kmh": 40, "control_value_deg": 0},
    ).json()
    assert fast["stopping"]["d_total_m"] > straight["stopping"]["d_total_m"]


def test_rigid_vehicle_has_no_articulation(client):
    """Xe than lien: gamma phai luon bang 0 du be lai gap the nao."""
    profile = client.post(
        "/api/profiles/scaffold", json={"profile_id": "bus-47", "template_id": "bus_47"}
    ).json()
    assert profile["meta"]["vehicle_type"] == "rigid"

    result = client.post(
        "/api/zones/preview",
        json={"profile": profile, "speed_kmh": 20, "control_value_deg": 20},
    ).json()
    assert result["state"]["gamma_deg"] == pytest.approx(0.0, abs=1e-9)
    assert result["state"]["is_rigid"] is True
    assert result["state"]["d_swept_m"] == pytest.approx(0.0, abs=1e-9)


def test_point_test_flags_dangerous_point(client):
    """Diem ngay truoc mui xe phai bi coi la nguy hiem; diem o xa thi khong.

    Chon vung mui xe vi bien cua no tinh duoc bang tay:
    d_front = z_bonnet * (CAB_FRONT_X - EYE_X) / (EYE_Z - z_bonnet)
            = 1.4 * (4.0 - 2.808) / (2.2 - 1.4) = 2.086 m
    -> vung keo tu x = 4.0 den x = 6.09, nen (5.0, 0.0) chac chan nam trong.
    """
    profile = client.post(
        "/api/profiles/scaffold", json={"profile_id": "pip-truck", "template_id": "container_40ft"}
    ).json()

    inside = client.post(
        "/api/zones/point-test",
        json={"profile": profile, "point": [5.0, 0.0], "speed_kmh": 10},
    ).json()
    assert inside["is_dangerous"] is True
    assert "front_bonnet" in inside["inside_zones"]

    far = client.post(
        "/api/zones/point-test",
        json={"profile": profile, "point": [80.0, 60.0], "speed_kmh": 10},
    ).json()
    assert far["is_dangerous"] is False
    assert far["inside_zones"] == []


def test_camera_snapshot_and_calibration_flow(client):
    profile = client.post(
        "/api/profiles/scaffold", json={"profile_id": "cam-truck", "template_id": "container_40ft"}
    ).json()
    client.put("/api/profiles/cam-truck", json=profile)

    status = client.get("/api/cameras/cam-truck/status").json()
    assert status["backend"] == "mock"
    assert len(status["cameras"]) == 3
    assert all(c["online"] for c in status["cameras"])

    snapshot = client.get("/api/cameras/cam-truck/MIRROR_R/snapshot")
    assert snapshot.status_code == 200
    assert snapshot.headers["content-type"] == "image/jpeg"
    assert len(snapshot.content) > 5000

    cones = client.get("/api/cameras/cam-truck/MIRROR_R/reference-cones").json()
    assert len(cones["cones"]) == 4
    assert cones["cones"][0]["name"] == "DO"

    camera = profile["cameras"]["MIRROR_R"]

    grid = client.post(
        "/api/cameras/project-grid",
        json={"camera": camera, "x_range": [-10, 6], "y_range": [-8, 0], "step": 2.0},
    ).json()
    assert grid["lines"], "luoi met phai co it nhat mot doan nam trong khung hinh"
    assert grid["image_size"] == [camera["width"], camera["height"]]

    unprojected = client.post(
        "/api/cameras/unproject", json={"camera": camera, "pixels": [[960, 1000]]}
    ).json()["points"][0]
    assert unprojected["ground"] is not None
    assert unprojected["side"] == "phai"

    # Mo phong ky thuat vien cham dung 4 chop non tren anh mock.
    from app.adapters import scene as scene_module
    from app.domain import engine as engine_module
    from app.domain.schemas import CameraConfig

    camera_model = CameraConfig.model_validate(camera)
    truth = scene_module.build_truth_camera("MIRROR_R", camera_model)
    ground = scene_module.CALIBRATION_CONES["MIRROR_R"]
    pixels = engine_module.ground_to_pixel(truth, ground, precision=None)
    points = [
        {"u": p[0], "v": p[1], "x": g[0], "y": g[1], "label": f"cone{i + 1}"}
        for i, (p, g) in enumerate(zip(pixels, ground))
    ]

    solved = client.post(
        "/api/cameras/solve-angles",
        json={"camera": camera, "points": points, "solve_height": True},
    ).json()
    assert solved["verdict"] == "pass", solved["message"]
    assert solved["rms_m"] < 0.05
    assert solved["roll_supported_by_engine"] is False

    camera["pitch_deg"] = solved["angles"]["pitch_deg"]
    camera["yaw_deg"] = solved["angles"]["yaw_deg"]
    camera["position"] = [camera["position"][0], camera["position"][1], solved["height_m"]]
    camera["auto_position"] = False

    committed = client.put(
        "/api/cameras/cam-truck/MIRROR_R",
        json={"camera": camera, "rms_m": solved["rms_m"]},
    ).json()
    assert committed["camera"]["calibrated_at"] is not None
    assert committed["calibrated_count"] == 1

    report = client.get("/api/profiles/cam-truck/report").json()
    mirror = next(c for c in report["cameras"] if c["camera_id"] == "MIRROR_R")
    assert mirror["status"] == "pass"


def test_draft_survives_reload(client):
    """Ban nhap phai giu duoc - Wi-Fi tren xe rot khong duoc mat cong nhap lieu."""
    payload = {"data": {"step": 2, "base": {"wheelbase_tractor": 4.1}}}
    assert client.put("/api/profiles/draft-truck/draft", json=payload).status_code == 200
    loaded = client.get("/api/profiles/draft-truck/draft").json()
    assert loaded["exists"] is True
    assert loaded["draft"]["data"]["base"]["wheelbase_tractor"] == 4.1
    client.delete("/api/profiles/draft-truck/draft")
    assert client.get("/api/profiles/draft-truck/draft").json()["exists"] is False


def test_import_clone_resets_calibration(client):
    """Nhan ban sang xe khac: goc lap camera cua xe cu khong con dung nua."""
    profile = client.post(
        "/api/profiles/scaffold", json={"profile_id": "src-truck", "template_id": "container_40ft"}
    ).json()
    profile["cameras"]["MIRROR_R"]["calibrated_at"] = "2026-01-01T00:00:00+00:00"
    profile["cameras"]["MIRROR_R"]["calibration_rms_m"] = 0.12
    client.put("/api/profiles/src-truck", json=profile)

    exported = client.get("/api/profiles/src-truck/export", params={"fmt": "yaml"}).text
    cloned = client.post(
        "/api/profiles/import",
        json={"content": exported, "new_profile_id": "dst-truck"},
    ).json()
    assert cloned["meta"]["profile_id"] == "dst-truck"
    assert cloned["meta"]["commissioned"] is False
    assert cloned["cameras"]["MIRROR_R"]["calibrated_at"] is None
    assert cloned["base"] == profile["base"]


def test_commissioned_profile_is_locked(client):
    profile = client.post(
        "/api/profiles/scaffold", json={"profile_id": "lock-truck", "template_id": "truck_8t"}
    ).json()
    client.put("/api/profiles/lock-truck", json=profile)

    profile["meta"]["commissioned"] = True
    assert client.put("/api/profiles/lock-truck", json=profile).status_code == 200

    profile["base"]["wheelbase_tractor"] = 5.0
    blocked = client.put("/api/profiles/lock-truck", json=profile)
    assert blocked.status_code == 409
    assert "khoa" in blocked.json()["detail"].lower()

    forced = client.put("/api/profiles/lock-truck", json=profile, params={"force": True})
    assert forced.status_code == 200


def test_diagnostics_flags_missing_pin(client):
    body = client.get("/api/diagnostics").json()
    keys = {c["key"]: c for c in body["checks"]}
    assert keys["engine"]["status"] == "pass"
    # Khong dat PIN trong moi truong test -> phai canh bao, khong duoc im lang.
    assert keys["pin"]["status"] == "warn"
    assert "PIN" in keys["pin"]["detail"]
