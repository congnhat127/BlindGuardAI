"""Suy hinh hoc va xem truoc vung mu.

Cac endpoint o day nhan ca ho so trong body (chua can luu) de wizard xem truoc
tuc thi trong luc ky thuat vien dang nhap so.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..domain import engine
from ..domain.derive import DERIVATION_BASIS, MEASUREMENT_GUIDE, derive_geometry, sanity_warnings
from ..domain.schemas import VehicleBase, VehicleProfile

router = APIRouter(tags=["geometry"])


class DeriveRequest(VehicleBase):
    pass


@router.post("/derive")
def derive(payload: DeriveRequest) -> dict:
    """4 thong so co ban -> 25 thong so hinh hoc, kem canh bao hop ly hoa.

    Frontend goi endpoint nay moi khi ky thuat vien doi so, de so do top-down
    ve lai ngay va canh bao hien ra truoc khi luu.
    """
    geometry = derive_geometry(
        payload.wheelbase_tractor,
        payload.cab_width,
        payload.l_trail,
        payload.w_trail,
        payload.driver_height,
    )
    return {
        "base": payload.model_dump(),
        "geometry": geometry.as_dict(),
        "camera_positions": {
            name: [round(v, 4) for v in position]
            for name, position in geometry.camera_positions().items()
        },
        "warnings": sanity_warnings(
            payload.wheelbase_tractor,
            payload.cab_width,
            payload.l_trail,
            payload.w_trail,
            geometry,
        ),
        "basis": DERIVATION_BASIS,
        "measurement_guide": MEASUREMENT_GUIDE,
    }


class ZonePreviewRequest(BaseModel):
    profile: VehicleProfile
    speed_kmh: float = Field(10.0, ge=0, le=120)
    control_value_deg: float = Field(0.0, ge=-720, le=720)
    control_mode: str = Field("yaw_rate", pattern="^(yaw_rate|steering_angle)$")
    settle_seconds: float = Field(2.0, ge=0.0, le=10.0)


@router.post("/zones/preview")
def zones_preview(payload: ZonePreviewRequest) -> dict:
    """Tinh toan bo da giac vung mu tai mot diem lam viec (v, omega)."""
    try:
        return engine.compute_zones(
            payload.profile,
            speed_kmh=payload.speed_kmh,
            control_value_deg=payload.control_value_deg,
            control_mode=payload.control_mode,
            settle_seconds=payload.settle_seconds,
        )
    except engine.EngineUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"{exc} Kiem tra lai thu muc 2_BlindSpot_Risk_Calculation/dynamic_blind_zone."
            ),
        ) from exc


class ZoneSweepRequest(BaseModel):
    profile: VehicleProfile
    speed_kmh: float = Field(10.0, ge=0, le=120)
    control_mode: str = Field("yaw_rate", pattern="^(yaw_rate|steering_angle)$")
    values_deg: list[float] = Field(..., min_length=1, max_length=40)


@router.post("/zones/sweep")
def zones_sweep(payload: ZoneSweepRequest) -> dict:
    """Quet nhieu gia tri dieu khien - dung cho hoat hinh vung bien dang khi re.

    Frontend nap san mot loat khung roi tua nhu video, khong phai goi lien tuc.
    """
    frames = []
    for value in payload.values_deg:
        frames.append(
            engine.compute_zones(
                payload.profile,
                speed_kmh=payload.speed_kmh,
                control_value_deg=value,
                control_mode=payload.control_mode,
            )
        )
    return {"frames": frames}


class PointTestRequest(BaseModel):
    profile: VehicleProfile
    point: list[float] = Field(..., min_length=2, max_length=2, description="[x, y] met trong VCS")
    speed_kmh: float = Field(10.0, ge=0, le=120)
    control_value_deg: float = 0.0
    control_mode: str = Field("yaw_rate", pattern="^(yaw_rate|steering_angle)$")


@router.post("/zones/point-test")
def point_test(payload: PointTestRequest) -> dict:
    """Cham mot diem tren ban do top-down -> cho biet diem do nam trong vung nao.

    Dung de ky thuat vien tu kiem chung: dat vat o vi tri X, he thong co bao khong.
    """
    computed = engine.compute_zones(
        payload.profile,
        speed_kmh=payload.speed_kmh,
        control_value_deg=payload.control_value_deg,
        control_mode=payload.control_mode,
    )
    point = (payload.point[0], payload.point[1])
    inside = engine.point_in_zones(payload.profile, point, computed["zones"])
    return {
        "point": payload.point,
        "inside_zones": inside,
        "is_dangerous": bool(inside),
        "state": computed["state"],
    }
