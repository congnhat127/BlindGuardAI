"""CRUD ho so xe, lich su phien ban, xuat cau hinh, bien ban nghiem thu."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from ..domain.schemas import VehicleProfile
from ..services import exporter
from ..services.store import ProfileLocked, ProfileNotFound, ProfileStore
from .deps import get_store, require_pin

router = APIRouter(prefix="/profiles", tags=["profiles"])


class SaveResponse(BaseModel):
    profile: VehicleProfile
    saved_at: str
    warnings: list[dict] = Field(default_factory=list)


def _load_or_404(store: ProfileStore, profile_id: str) -> VehicleProfile:
    try:
        return store.load(profile_id)
    except ProfileNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Khong tim thay ho so {profile_id!r}"
        ) from exc


@router.get("")
def list_profiles(store: ProfileStore = Depends(get_store)) -> dict:
    return {"profiles": store.list_profiles()}


class ScaffoldRequest(BaseModel):
    profile_id: str
    display_name: str = ""
    plate_number: str = ""
    installer_name: str = ""
    template_id: str | None = Field(None, description="Chon mau xe de dien san 4 thong so")


@router.post("/scaffold")
def scaffold(payload: ScaffoldRequest) -> VehicleProfile:
    """Tao khung ho so moi (chua luu) tu mau xe.

    Tra ve ho so day du da dien mac dinh: 3 camera, goc lap, tham so vat ly.
    Ky thuat vien chi con sua so do thuc te.
    """
    from ..domain.schemas import VEHICLE_TEMPLATES, ProfileMeta, VehicleBase

    base = VehicleBase()
    vehicle_type = "articulated"
    if payload.template_id:
        match = next(
            (t for t in VEHICLE_TEMPLATES if t.template_id == payload.template_id), None
        )
        if match is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Khong co mau xe {payload.template_id!r}",
            )
        base = match.base.model_copy()
        vehicle_type = match.vehicle_type

    try:
        meta = ProfileMeta(
            profile_id=payload.profile_id,
            display_name=payload.display_name,
            plate_number=payload.plate_number,
            installer_name=payload.installer_name,
            vehicle_type=vehicle_type,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return VehicleProfile(meta=meta, base=base)


@router.get("/{profile_id}")
def get_profile(profile_id: str, store: ProfileStore = Depends(get_store)) -> VehicleProfile:
    return _load_or_404(store, profile_id)


@router.put("/{profile_id}", dependencies=[Depends(require_pin)])
def save_profile(
    profile_id: str,
    profile: VehicleProfile,
    force: bool = False,
    store: ProfileStore = Depends(get_store),
) -> SaveResponse:
    if profile.meta.profile_id != profile_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="profile_id trong duong dan khac trong noi dung.",
        )
    from ..domain.derive import sanity_warnings

    try:
        saved = store.save(profile, force=force)
    except ProfileLocked as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Ho so da nghiem thu va dang khoa. Mo khoa (commissioned = false) "
                "hoac dung force=true neu chac chan."
            ),
        ) from exc

    geometry = saved.geometry()
    warnings = sanity_warnings(
        saved.base.wheelbase_tractor,
        saved.base.cab_width,
        saved.base.l_trail,
        saved.base.w_trail,
        geometry,
    )
    store.delete_draft(profile_id)
    return SaveResponse(
        profile=saved,
        saved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        warnings=warnings,
    )


@router.delete("/{profile_id}", dependencies=[Depends(require_pin)])
def delete_profile(profile_id: str, store: ProfileStore = Depends(get_store)) -> dict:
    try:
        store.delete(profile_id)
    except ProfileNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"deleted": profile_id, "note": "Thu muc duoc doi ten, khong xoa han."}


@router.get("/{profile_id}/versions")
def list_versions(profile_id: str, store: ProfileStore = Depends(get_store)) -> dict:
    _load_or_404(store, profile_id)
    return {"versions": store.versions(profile_id)}


@router.post("/{profile_id}/versions/{version}/restore", dependencies=[Depends(require_pin)])
def restore_version(
    profile_id: str, version: str, store: ProfileStore = Depends(get_store)
) -> VehicleProfile:
    try:
        return store.restore(profile_id, version)
    except ProfileNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{profile_id}/export")
def export_profile(
    profile_id: str,
    fmt: str = "yaml",
    store: ProfileStore = Depends(get_store),
) -> Response:
    """fmt=yaml (luu tru / chuyen xe) hoac fmt=python (config.py cho engine)."""
    profile = _load_or_404(store, profile_id)
    if fmt == "python":
        body = exporter.to_engine_config(profile)
        return Response(
            content=body,
            media_type="text/x-python; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="config_{profile_id}.py"'},
        )
    if fmt == "yaml":
        body = exporter.to_yaml(profile)
        return Response(
            content=body,
            media_type="application/x-yaml; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{profile_id}.yaml"'},
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="fmt chi nhan 'yaml' hoac 'python'."
    )


@router.get("/{profile_id}/preview-export")
def preview_export(
    profile_id: str, fmt: str = "python", store: ProfileStore = Depends(get_store)
) -> dict:
    """Tra ve noi dung dang text de hien trong o xem truoc (khong tai file)."""
    profile = _load_or_404(store, profile_id)
    body = (
        exporter.to_engine_config(profile) if fmt == "python" else exporter.to_yaml(profile)
    )
    return {"format": fmt, "content": body, "lines": body.count("\n") + 1}


@router.get("/{profile_id}/report")
def report(profile_id: str, store: ProfileStore = Depends(get_store)) -> dict:
    profile = _load_or_404(store, profile_id)
    zones_preview: dict[str, Any] | None = None
    try:
        from ..domain import engine

        zones_preview = engine.compute_zones(profile, speed_kmh=10.0, control_value_deg=8.0)
    except Exception:
        zones_preview = None
    return exporter.commissioning_report(profile, zones_preview)


class ImportPayload(BaseModel):
    content: str = Field(..., description="Noi dung YAML da xuat truoc do")
    new_profile_id: str | None = Field(None, description="Doi ten khi nhan ban sang xe khac")


@router.post("/import", dependencies=[Depends(require_pin)])
def import_profile(payload: ImportPayload, store: ProfileStore = Depends(get_store)) -> VehicleProfile:
    """Nhan ban cau hinh sang xe khac cung loai - chi phai hieu chuan lai camera."""
    import yaml

    try:
        raw = yaml.safe_load(payload.content) or {}
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"YAML khong doc duoc: {exc}"
        ) from exc

    if payload.new_profile_id:
        raw.setdefault("meta", {})["profile_id"] = payload.new_profile_id
        raw["meta"]["commissioned"] = False
        # Nhan ban sang xe khac: goc lap camera cua xe cu khong con dung.
        for camera in (raw.get("cameras") or {}).values():
            camera["calibrated_at"] = None
            camera["calibration_rms_m"] = None

    try:
        profile = VehicleProfile.model_validate(raw)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return store.save(profile, force=True)


# --- Ban nhap tu dong -------------------------------------------------------
class DraftPayload(BaseModel):
    data: dict[str, Any]


@router.put("/{profile_id}/draft")
def save_draft(
    profile_id: str, payload: DraftPayload, store: ProfileStore = Depends(get_store)
) -> dict:
    """Luu ban nhap. Wi-Fi tren xe hay rot, khong duoc de mat 30 phut cong."""
    store.save_draft(profile_id, payload.data)
    return {"saved": True, "profile_id": profile_id}


@router.get("/{profile_id}/draft")
def load_draft(profile_id: str, store: ProfileStore = Depends(get_store)) -> dict:
    draft = store.load_draft(profile_id)
    return {"exists": draft is not None, "draft": draft}


@router.delete("/{profile_id}/draft")
def drop_draft(profile_id: str, store: ProfileStore = Depends(get_store)) -> dict:
    store.delete_draft(profile_id)
    return {"deleted": True}
