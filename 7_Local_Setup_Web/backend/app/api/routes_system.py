"""Endpoint he thong: suc khoe, chan doan truoc khi lap, mau xe, tu dien vung."""

from __future__ import annotations

import platform
import shutil
import sys
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from ..adapters.cameras import get_camera_source
from ..adapters.telemetry import get_telemetry
from ..core.settings import settings
from ..domain import engine
from ..domain.derive import CAMERA_LAYOUT, DERIVATION_BASIS
from ..domain.schemas import VEHICLE_TEMPLATES
from ..services.store import ProfileStore
from .deps import get_store

router = APIRouter(tags=["system"])

# Ten vung mu -> nhan tieng Viet + mau. Frontend dung chung bang nay de khong
# bao gio lech chu / lech mau giua cac man hinh.
# Mau lay tu occlusion_visualizer.py de web va ban mo phong matplotlib giong nhau.
ZONE_DICTIONARY: dict[str, dict[str, str]] = {
    "right_side_occlusion": {
        "label": "Mu guong phai",
        "short": "Guong phai",
        "color": "#ef4444",
        "group": "mirror",
        "note": "Bong khuat sau thung ro-mooc nhin tu guong phu xe.",
    },
    "left_side_occlusion": {
        "label": "Mu guong trai",
        "short": "Guong trai",
        "color": "#ef4444",
        "group": "mirror",
        "note": "Bong khuat sau thung ro-mooc nhin tu guong tai xe.",
    },
    "a_pillar_right": {
        "label": "Cot A phai",
        "short": "Cot A phai",
        "color": "#f97316",
        "group": "pillar",
        "note": "Hinh nem bi cum cot A + chan guong che.",
    },
    "a_pillar_left": {
        "label": "Cot A trai",
        "short": "Cot A trai",
        "color": "#f97316",
        "group": "pillar",
        "note": "Hinh nem bi cum cot A + chan guong che.",
    },
    "b_pillar_right": {
        "label": "Cot B phai",
        "short": "Cot B phai",
        "color": "#a855f7",
        "group": "pillar",
        "note": "Vach cabin sau cua so chan tam nhin ngoai vai.",
    },
    "b_pillar_left": {
        "label": "Cot B trai",
        "short": "Cot B trai",
        "color": "#a855f7",
        "group": "pillar",
        "note": "Vach cabin sau cua so chan tam nhin ngoai vai.",
    },
    "front_bonnet": {
        "label": "Mu mui xe",
        "short": "Mui xe",
        "color": "#dc2626",
        "group": "front",
        "note": "Vung mat duong bi nap capo / mep kinh chan gio che.",
    },
    "swept_path": {
        "label": "Quy dao banh quet",
        "short": "Banh quet",
        "color": "#38bdf8",
        "group": "kinematic",
        "note": "Dai duong banh ro-mooc lan le khi re (off-tracking).",
    },
    "stopping_hazard": {
        "label": "Nguy hiem phanh",
        "short": "Phanh",
        "color": "#eab308",
        "group": "hazard",
        "note": "Quang duong phan ung + phanh o toc do hien tai.",
    },
}

VEHICLE_COLORS = {
    "cab": "#334155",
    "chassis": "#475569",
    "trailer": "#0284c7",
}


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "blindguard-local-setup",
        "device_backend": settings.device_backend,
        "engine": engine.engine_status(),
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


@router.get("/templates")
def templates() -> dict:
    return {
        "templates": [template.model_dump(mode="json") for template in VEHICLE_TEMPLATES],
    }


@router.get("/dictionary")
def dictionary() -> dict:
    """Tu dien dung chung: ten vung, mau, can cu tieu chuan cua tung cong thuc."""
    return {
        "zones": ZONE_DICTIONARY,
        "vehicle_colors": VEHICLE_COLORS,
        "derivation_basis": DERIVATION_BASIS,
        "camera_layout": CAMERA_LAYOUT,
    }


@router.get("/diagnostics")
def diagnostics(
    profile_id: str | None = None,
    store: ProfileStore = Depends(get_store),
) -> dict:
    """Danh sach kiem tra truoc khi lap - moi dong xanh/do, bam la thu lai.

    Muc dich: ky thuat vien biet ngay thieu gi truoc khi mat 30 phut cang chinh.
    """
    checks: list[dict] = []

    def check(key: str, label: str, ok: bool, detail: str, severity: str = "error") -> None:
        checks.append(
            {
                "key": key,
                "label": label,
                "status": "pass" if ok else severity,
                "detail": detail,
            }
        )

    engine_state = engine.engine_status()
    check(
        "engine",
        "Engine vung mu",
        engine_state["available"],
        engine_state["error"] or f"Nap tu {engine_state['path']}",
    )

    usage = shutil.disk_usage(settings.data_dir)
    free_gb = usage.free / 1024**3
    check(
        "disk",
        "Dung luong dia",
        free_gb > 1.0,
        f"Con trong {free_gb:.1f} GB",
        severity="warn",
    )

    check(
        "clock",
        "Dong ho he thong",
        True,
        datetime.now().astimezone().isoformat(timespec="seconds"),
    )

    check(
        "pin",
        "Ma PIN bao ve cau hinh",
        bool(settings.setup_pin),
        "Da dat PIN." if settings.setup_pin else
        "CHUA dat PIN - bat ky ai trong mang Wi-Fi deu sua duoc cau hinh. "
        "Dat bien BLINDGUARD_SETUP_PIN truoc khi giao xe.",
        severity="warn",
    )

    telemetry = get_telemetry().read()
    gps = telemetry.get("gps", {})
    check(
        "gps",
        "Tin hieu GPS",
        bool(gps.get("fix")),
        f"Ve tinh {gps.get('satellites', '-')}, HDOP {gps.get('hdop', '-')}"
        if gps.get("fix")
        else str(telemetry.get("note", "Khong co fix")),
        severity="warn",
    )
    imu = telemetry.get("imu", {})
    check(
        "imu",
        "Cam bien IMU",
        bool(imu.get("present")),
        f"Yaw rate {imu.get('yaw_rate_deg_s', '-')} deg/s"
        if imu.get("present")
        else "Chua phat hien IMU",
        severity="warn",
    )

    cameras: list[dict] = []
    if profile_id and store.exists(profile_id):
        profile = store.load(profile_id)
        try:
            cameras = get_camera_source().status(profile)
        except Exception as exc:
            cameras = [{"camera_id": "-", "online": False, "message": str(exc)}]
        online = sum(1 for camera in cameras if camera.get("online"))
        check(
            "cameras",
            "Camera",
            online == len(cameras) and bool(cameras),
            f"{online}/{len(cameras)} camera phan hoi",
        )
        calibrated = sum(1 for c in profile.cameras.values() if c.calibrated_at)
        check(
            "calibration",
            "Hieu chuan camera",
            calibrated == len(profile.cameras),
            f"{calibrated}/{len(profile.cameras)} camera da hieu chuan",
            severity="warn",
        )

    summary = {
        "pass": sum(1 for c in checks if c["status"] == "pass"),
        "warn": sum(1 for c in checks if c["status"] == "warn"),
        "error": sum(1 for c in checks if c["status"] == "error"),
    }
    return {
        "checks": checks,
        "cameras": cameras,
        "telemetry": telemetry,
        "summary": summary,
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "device_backend": settings.device_backend,
            "data_dir": str(settings.data_dir),
        },
    }


@router.get("/telemetry")
def telemetry_now() -> dict:
    return get_telemetry().read()
