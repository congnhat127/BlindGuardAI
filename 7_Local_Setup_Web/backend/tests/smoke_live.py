"""Kiem tra nhanh tren server dang chay that (khong phai TestClient).

Muc dich khac voi test_api.py: xac nhan duong HTTP that hoat dong, dac biet la
luong MJPEG - thu ma TestClient khong mo phong duoc dung.

    python tests/smoke_live.py [http://127.0.0.1:8080]
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"
PROFILE = "smoke-live"


def call(method: str, path: str, payload=None, raw=False):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read()
        return body if raw else json.loads(body or b"null")


def ok(label: str, detail: str = "") -> None:
    print(f"  [OK]   {label}" + (f" - {detail}" if detail else ""))


def main() -> int:
    print(f"Kiem tra {BASE}")

    health = call("GET", "/api/health")
    assert health["status"] == "ok"
    ok("health", f"engine={health['engine']['available']} backend={health['device_backend']}")

    profile = call(
        "POST",
        "/api/profiles/scaffold",
        {"profile_id": PROFILE, "plate_number": "43C-999.99", "template_id": "container_40ft"},
    )
    ok("scaffold", f"{len(profile['cameras'])} camera")

    saved = call("PUT", f"/api/profiles/{PROFILE}", profile)
    assert saved["warnings"] == []
    ok("luu ho so")

    derived = call(
        "POST",
        "/api/derive",
        {**profile["base"]},
    )
    ok("suy hinh hoc", f"tong dai {derived['geometry']['total_length']:.2f} m")

    zones = call(
        "POST",
        "/api/zones/preview",
        {"profile": profile, "speed_kmh": 10, "control_value_deg": -12},
    )
    ok(
        "vung mu",
        f"gamma={zones['state']['gamma_deg']:.2f} deg, banh quet={zones['state']['d_swept_m']:.2f} m",
    )

    snapshot = call("GET", f"/api/cameras/{PROFILE}/MIRROR_R/snapshot", raw=True)
    assert snapshot[:2] == b"\xff\xd8", "khong phai JPEG"
    ok("snapshot", f"{len(snapshot) // 1024} KB JPEG")

    # Luong MJPEG: doc du 2 khung roi ngat.
    with urllib.request.urlopen(f"{BASE}/api/cameras/{PROFILE}/MIRROR_R/stream", timeout=30) as stream:
        buffer = b""
        frames = 0
        while frames < 2 and len(buffer) < 3_000_000:
            chunk = stream.read(16384)
            if not chunk:
                break
            buffer += chunk
            frames = buffer.count(b"--blindguardframe")
    assert frames >= 2, f"chi nhan duoc {frames} khung MJPEG"
    ok("luong MJPEG", f"{frames} khung, {len(buffer) // 1024} KB")

    cones = call("GET", f"/api/cameras/{PROFILE}/MIRROR_R/reference-cones")
    ground = [[cone["x"], cone["y"]] for cone in cones["cones"]]
    ok("bang vat moc", f"{len(ground)} chop non")

    grid = call(
        "POST",
        "/api/cameras/project-grid",
        {"camera": profile["cameras"]["MIRROR_R"], "step": 2.0},
    )
    assert grid["lines"], "luoi met rong"
    ok("chieu luoi met", f"{len(grid['lines'])} doan")

    # Mo phong tho cham dung 4 chop non tren anh gia lap.
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
    from app.adapters import scene
    from app.domain import engine
    from app.domain.schemas import CameraConfig

    camera_model = CameraConfig.model_validate(profile["cameras"]["MIRROR_R"])
    truth = scene.build_truth_camera("MIRROR_R", camera_model)
    pixels = engine.ground_to_pixel(truth, [(g[0], g[1]) for g in ground], precision=None)
    points = [
        {"u": pixel[0], "v": pixel[1], "x": g[0], "y": g[1], "label": f"cone{index + 1}"}
        for index, (pixel, g) in enumerate(zip(pixels, ground))
        if pixel is not None
    ]

    solved = call(
        "POST",
        "/api/cameras/solve-angles",
        {"camera": profile["cameras"]["MIRROR_R"], "points": points, "solve_height": True},
    )
    assert solved["verdict"] == "pass", solved["message"]
    ok("giai goc lap", f"RMS={solved['rms_m']:.5f} m, {solved['iterations']} vong lap")

    camera = dict(profile["cameras"]["MIRROR_R"])
    camera["pitch_deg"] = solved["angles"]["pitch_deg"]
    camera["yaw_deg"] = solved["angles"]["yaw_deg"]
    camera["position"] = [camera["position"][0], camera["position"][1], solved["height_m"]]
    camera["auto_position"] = False

    verified = call("POST", "/api/cameras/verify", {"camera": camera, "points": points})
    assert verified["verdict"] == "pass"
    ok("kiem tra sai so", f"RMS={verified['rms_m']:.5f} m")

    committed = call(
        "PUT",
        f"/api/cameras/{PROFILE}/MIRROR_R",
        {"camera": camera, "rms_m": verified["rms_m"]},
    )
    ok("chot camera", f"{committed['calibrated_count']}/{committed['total']}")

    export = call("GET", f"/api/profiles/{PROFILE}/preview-export?fmt=python")
    assert "CAMERAS_EXTRINSICS" in export["content"]
    ok("xuat config.py", f"{export['lines']} dong")

    report = call("GET", f"/api/profiles/{PROFILE}/report")
    mirror = next(c for c in report["cameras"] if c["camera_id"] == "MIRROR_R")
    assert mirror["status"] == "pass", mirror
    ok("bien ban nghiem thu", f"MIRROR_R = {mirror['status']}")

    diagnostics = call("GET", f"/api/diagnostics?profile_id={PROFILE}")
    ok(
        "chan doan",
        f"{diagnostics['summary']['pass']} dat / {diagnostics['summary']['warn']} canh bao",
    )

    call("DELETE", f"/api/profiles/{PROFILE}")
    ok("don dep ho so thu")

    print("\nToan bo kiem tra tren server that: DAT")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, urllib.error.HTTPError, urllib.error.URLError) as exc:
        print(f"\n[LOI] {exc}")
        if isinstance(exc, urllib.error.HTTPError):
            print(exc.read().decode(errors="replace"))
        raise SystemExit(1)
