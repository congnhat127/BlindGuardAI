"""Camera: khung hinh, chieu xuoi/nguoc, giai goc lap, kiem chung do chinh xac."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..adapters import scene
from ..adapters.cameras import BOUNDARY, get_camera_source, mjpeg_stream
from ..core.settings import settings
from ..domain import engine
from ..domain.derive import CAMERA_IDS
from ..domain.schemas import CameraConfig, VehicleProfile
from ..services import calibration as calibration_service
from ..services.store import ProfileNotFound, ProfileStore
from .deps import get_store, require_pin

router = APIRouter(prefix="/cameras", tags=["cameras"])


def _profile(store: ProfileStore, profile_id: str) -> VehicleProfile:
    try:
        return store.load(profile_id)
    except ProfileNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Khong tim thay ho so {profile_id!r}"
        ) from exc


def _check_camera(camera_id: str) -> None:
    if camera_id not in CAMERA_IDS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id!r} khong ton tai. Cho phep: {list(CAMERA_IDS)}",
        )


@router.get("/{profile_id}/status")
def camera_status(profile_id: str, store: ProfileStore = Depends(get_store)) -> dict:
    profile = _profile(store, profile_id)
    try:
        rows = get_camera_source().status(profile)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"backend": settings.device_backend, "cameras": rows}


@router.get("/{profile_id}/{camera_id}/snapshot")
def snapshot(
    profile_id: str, camera_id: str, store: ProfileStore = Depends(get_store)
) -> Response:
    """Mot khung hinh JPEG. Che do mock: ve tu mo hinh camera."""
    _check_camera(camera_id)
    profile = _profile(store, profile_id)
    try:
        payload = get_camera_source().snapshot(profile, camera_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return Response(content=payload, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.get("/{profile_id}/{camera_id}/stream")
def stream(profile_id: str, camera_id: str, store: ProfileStore = Depends(get_store)):
    """Luong MJPEG - dat truc tiep vao thuoc tinh src cua the img."""
    _check_camera(camera_id)
    profile = _profile(store, profile_id)
    return StreamingResponse(
        mjpeg_stream(profile, camera_id),
        media_type=f"multipart/x-mixed-replace; boundary={BOUNDARY}",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.get("/{profile_id}/{camera_id}/reference-cones")
def reference_cones(profile_id: str, camera_id: str) -> dict:
    """Bang vi tri chop non tham chieu.

    Che do mock: day dung la vi tri chop non da ve trong anh, nen ky thuat vien
    tap cang chinh duoc ngay. Tren hien truong: day la so do bang thuoc day va
    ky thuat vien phai sua lai theo thuc te.
    """
    _check_camera(camera_id)
    return {
        "camera_id": camera_id,
        "cones": scene.cone_truth_table(camera_id),
        "editable": True,
        "note": (
            "Che do mock: day la vi tri chop non that trong anh gia lap. "
            "Ngoai hien truong phai thay bang so do bang thuoc."
            if settings.is_mock
            else "Nhap toa do met da do bang thuoc cho tung chop non."
        ),
    }


# --- Chieu xuoi / chieu nguoc ----------------------------------------------
class ProjectRequest(BaseModel):
    camera: CameraConfig
    ground_points: list[list[float]] = Field(default_factory=list, description="[[x, y], ...]")
    z: float = Field(0.0, description="Do cao diem so voi mat duong (m)")


@router.post("/project")
def project(payload: ProjectRequest) -> dict:
    """Met -> pixel. Dung de ve luoi met va da giac vung mu chong len anh camera."""
    points = [(p[0], p[1]) for p in payload.ground_points]
    return {"pixels": engine.ground_to_pixel(payload.camera, points, z=payload.z)}


class GridRequest(BaseModel):
    camera: CameraConfig
    x_range: list[float] = Field([-20.0, 20.0], min_length=2, max_length=2)
    y_range: list[float] = Field([-10.0, 10.0], min_length=2, max_length=2)
    step: float = Field(1.0, gt=0.1, le=10)
    samples_per_line: int = Field(60, ge=8, le=240)


@router.post("/project-grid")
def project_grid(payload: GridRequest) -> dict:
    """Luoi met chieu san sang duoi dang cac chuoi polyline pixel.

    Ky thuat vien chinh pitch/yaw cho den khi luoi nay trung voi vach ke duong
    va cac vat moc that trong anh - do la cach cang chinh bang mat de nhat.
    """
    camera = payload.camera
    x0, x1 = sorted(payload.x_range)
    y0, y1 = sorted(payload.y_range)
    step = payload.step
    samples = payload.samples_per_line

    def polyline(start: tuple[float, float], end: tuple[float, float]) -> list[list[list[float]]]:
        pts = [
            (
                start[0] + (end[0] - start[0]) * i / samples,
                start[1] + (end[1] - start[1]) * i / samples,
            )
            for i in range(samples + 1)
        ]
        projected = engine.ground_to_pixel(camera, pts)
        segments: list[list[list[float]]] = []
        current: list[list[float]] = []
        for point in projected:
            if point is None:
                if len(current) > 1:
                    segments.append(current)
                current = []
                continue
            current.append(point)
        if len(current) > 1:
            segments.append(current)
        return segments

    lines: list[dict] = []
    value = y0
    while value <= y1 + 1e-9:
        for segment in polyline((x0, value), (x1, value)):
            lines.append({"axis": "y", "value": round(value, 3), "points": segment})
        value += step
    value = x0
    while value <= x1 + 1e-9:
        for segment in polyline((value, y0), (value, y1)):
            lines.append({"axis": "x", "value": round(value, 3), "points": segment})
        value += step

    return {"lines": lines, "image_size": [camera.width, camera.height]}


class UnprojectRequest(BaseModel):
    camera: CameraConfig
    pixels: list[list[float]] = Field(..., min_length=1, description="[[u, v], ...]")


@router.post("/unproject")
def unproject(payload: UnprojectRequest) -> dict:
    """Pixel -> met. Cham vao anh de doc ngay toa do met, so voi thuoc day."""
    pixels = [(p[0], p[1]) for p in payload.pixels]
    ground = engine.pixel_to_ground(payload.camera, pixels)
    rows = []
    for pixel, point in zip(payload.pixels, ground):
        distance = None
        if point is not None:
            distance = round((point[0] ** 2 + point[1] ** 2) ** 0.5, 3)
        rows.append(
            {
                "pixel": pixel,
                "ground": point,
                "distance_from_origin_m": distance,
                "side": None if point is None else ("phai" if point[1] < 0 else "trai"),
            }
        )
    return {"points": rows}


# --- Giai goc lap va kiem chung -------------------------------------------
class CorrespondenceIn(BaseModel):
    u: float
    v: float
    x: float
    y: float
    label: str = ""


class SolveRequest(BaseModel):
    camera: CameraConfig
    points: list[CorrespondenceIn] = Field(..., min_length=2, max_length=64)
    solve_height: bool = Field(
        False, description="Giai them do cao lap camera - dung khi khong do duoc chinh xac"
    )


@router.post("/solve-angles")
def solve_angles(payload: SolveRequest) -> dict:
    """Tu cac diem moc da do -> tim pitch / yaw / roll khop nhat.

    Sai so bao bang MET, dung don vi cua tieu chi nghiem thu (< 0.30 m).
    """
    points = [
        calibration_service.Correspondence(u=p.u, v=p.v, x=p.x, y=p.y, label=p.label)
        for p in payload.points
    ]
    result = calibration_service.solve_camera_angles(
        payload.camera, points, solve_height=payload.solve_height
    )
    return {
        "ok": result.ok,
        "verdict": result.verdict,
        "message": result.message,
        "angles": {
            "pitch_deg": result.pitch_deg,
            "yaw_deg": result.yaw_deg,
            "roll_deg": result.roll_deg,
        },
        "height_m": result.height_m,
        "rms_m": result.rms_m,
        "max_error_m": result.max_error_m,
        "target_m": calibration_service.RMS_TARGET_M,
        "per_point": result.per_point,
        "iterations": result.iterations,
        "roll_solved": result.roll_solved,
        "roll_supported_by_engine": engine.roll_is_supported(),
    }


class VerifyRequest(BaseModel):
    camera: CameraConfig
    points: list[CorrespondenceIn] = Field(..., min_length=1, max_length=64)


@router.post("/verify")
def verify(payload: VerifyRequest) -> dict:
    """Kiem tra do chinh xac voi goc hien tai (khong giai lai).

    Quy trinh: dat chop non o khoang cach da biet -> cham vao -> doc sai so.
    Day chinh la thi nghiem nghiem thu bien thanh tinh nang trong web.
    """
    points = [
        calibration_service.Correspondence(u=p.u, v=p.v, x=p.x, y=p.y, label=p.label)
        for p in payload.points
    ]
    return calibration_service.verify_points(payload.camera, points)


class CommitRequest(BaseModel):
    camera: CameraConfig
    rms_m: float | None = None


@router.put("/{profile_id}/{camera_id}", dependencies=[Depends(require_pin)])
def commit_camera(
    profile_id: str,
    camera_id: str,
    payload: CommitRequest,
    store: ProfileStore = Depends(get_store),
) -> dict:
    """Chot ket qua hieu chuan mot camera vao ho so da luu."""
    _check_camera(camera_id)
    profile = _profile(store, profile_id)
    camera = payload.camera
    camera.calibration_rms_m = payload.rms_m
    camera.calibrated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    profile.cameras[camera_id] = camera
    saved = store.save(profile, force=True)
    return {
        "camera_id": camera_id,
        "camera": saved.cameras[camera_id].model_dump(mode="json"),
        "calibrated_count": sum(1 for c in saved.cameras.values() if c.calibrated_at),
        "total": len(saved.cameras),
    }
