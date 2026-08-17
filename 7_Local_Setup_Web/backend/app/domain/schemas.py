"""Pydantic schema cho ho so cau hinh xe (vehicle profile).

Day la nguon su that duy nhat cho du lieu ma web sinh ra. Moi truong deu co
rang buoc so hoc, nen mot ho so da luu chac chan nap duoc vao engine.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .derive import CAMERA_IDS, CAMERA_LAYOUT, derive_geometry

SCHEMA_VERSION = 1

Metre = Annotated[float, Field(gt=0, le=40, description="Don vi: met")]
Degrees = Annotated[float, Field(ge=-180, le=180, description="Don vi: do")]

PROFILE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,48}$")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Intrinsics(BaseModel):
    """Ma tran noi tai K. Nhap truc tiep fx/fy/cx/cy hoac suy tu FOV ngang."""

    model_config = ConfigDict(extra="forbid")

    fx: float = Field(1000.0, gt=0, description="Tieu cu theo pixel, truc u")
    fy: float = Field(1000.0, gt=0, description="Tieu cu theo pixel, truc v")
    cx: float = Field(960.0, ge=0, description="Tam anh u")
    cy: float = Field(540.0, ge=0, description="Tam anh v")

    @classmethod
    def from_fov(cls, width: int, height: int, hfov_deg: float) -> "Intrinsics":
        """Suy K tu FOV ngang ghi tren datasheet ong kinh.

        fx = (W/2) / tan(HFOV/2). Gia thiet pixel vuong nen fy = fx.
        """
        half = math.radians(hfov_deg) / 2.0
        fx = (width / 2.0) / math.tan(half)
        return cls(fx=fx, fy=fx, cx=width / 2.0, cy=height / 2.0)

    def as_matrix(self) -> list[list[float]]:
        return [[self.fx, 0.0, self.cx], [0.0, self.fy, self.cy], [0.0, 0.0, 1.0]]

    def hfov_deg(self, width: int) -> float:
        return math.degrees(2.0 * math.atan((width / 2.0) / self.fx))


class CameraConfig(BaseModel):
    """Cau hinh mot camera. Vi tri mac dinh suy tu hinh hoc xe (auto_position)."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    label: str = ""
    source: str = Field("", description="RTSP/USB index. De trong khi chay che do mock.")
    width: int = Field(1920, ge=320, le=7680)
    height: int = Field(1080, ge=240, le=4320)
    intrinsics: Intrinsics = Field(default_factory=Intrinsics)

    auto_position: bool = Field(
        True, description="True = lay vi tri suy ra tu hinh hoc xe; False = nhap tay."
    )
    position: list[float] | None = Field(
        None, min_length=3, max_length=3, description="[x, y, z] met trong VCS"
    )

    pitch_deg: Degrees = 0.0
    yaw_deg: Degrees = 0.0
    roll_deg: Degrees = 0.0

    monitored_blind_zones: list[str] = Field(default_factory=list)

    # Ket qua kiem chung hieu chuan, do buoc 'Kiem tra do chinh xac' ghi lai.
    calibration_rms_m: float | None = Field(None, ge=0)
    calibrated_at: str | None = None


class VehicleBase(BaseModel):
    """4 thong so co ban trich tu So dang kiem + chieu cao tai xe."""

    model_config = ConfigDict(extra="forbid")

    wheelbase_tractor: Metre = Field(3.6, description="L_f: truc truoc -> truc sau dau keo")
    cab_width: Metre = Field(2.5, description="W_cab: chieu rong tong the cabin")
    l_trail: Metre = Field(12.0, description="L_trail: chot keo -> truc banh sau ro-mooc")
    w_trail: Metre = Field(2.5, description="W_trail: chieu rong thung ro-mooc")
    driver_height: float = Field(1.70, ge=1.40, le=2.10, description="Chieu cao tai xe (m)")


class Physics(BaseModel):
    """Tham so vat ly va dong luc hoc."""

    model_config = ConfigDict(extra="forbid")

    reaction_time: float = Field(1.5, gt=0, le=5, description="Thoi gian phan ung phanh (s)")
    friction_coeff: float = Field(0.7, gt=0.1, le=1.2, description="Hoac 0.4 khi duong uot")
    gravity: float = Field(9.81, gt=9.0, le=10.0)
    steer_ratio: float = Field(16.0, gt=1, le=40, description="Ty so truyen he thong lai")
    max_gamma_deg: float = Field(85.0, gt=0, le=120, description="Gioi han mo hinh so")
    mechanical_max_gamma_deg: float = Field(
        65.0, gt=0, le=120, description="Gioi han va cham cabin (cab-strike)"
    )

    @model_validator(mode="after")
    def _check_gamma_order(self) -> "Physics":
        if self.mechanical_max_gamma_deg > self.max_gamma_deg:
            raise ValueError(
                "mechanical_max_gamma_deg phai <= max_gamma_deg "
                "(gioi han co khi khong the vuot gioi han mo hinh)"
            )
        return self


class ZoneParams(BaseModel):
    """Tham so hinh hoc vung mu. Mac dinh theo tai lieu mo hinh toan."""

    model_config = ConfigDict(extra="forbid")

    front_blind_min: float = Field(2.0, ge=0, le=10, description="Do sau vung mu mui xe (m)")
    side_blind_max: float = Field(4.0, ge=0, le=12, description="Be rong vung mu hong phai (m)")
    rear_blind_depth: float = Field(3.0, ge=0, le=12, description="Do sau vung mu duoi (m)")
    front_red_ratio: float = Field(0.3, gt=0, le=1)
    a_pillar_width: float = Field(
        0.28, gt=0, le=1.0, description="Be rong hieu dung cum Cot A + chan guong (m)"
    )
    a_pillar_blind_range: float = Field(
        15.0, gt=0, le=60, description="Tam xa chieu duong cot A (m)"
    )


class SensorParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gps_freq: float = Field(1.0, gt=0, le=50, description="Hz")
    camera_freq: float = Field(30.0, gt=0, le=240, description="Hz")
    gps_timeout_sec: float = Field(5.0, gt=0, le=60, description="Qua nguong nay coi la mat song")


class ProfileMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str = Field(..., description="Dinh danh ho so, kebab/snake khong dau")
    display_name: str = Field("", max_length=120)
    plate_number: str = Field("", max_length=20, description="Bien so xe")
    vehicle_type: Literal["articulated", "rigid"] = Field(
        "articulated",
        description="articulated = dau keo + ro-mooc; rigid = xe than lien (bus, thung lien)",
    )
    fleet_name: str = Field("", max_length=120)
    installer_name: str = Field("", max_length=120)
    notes: str = Field("", max_length=2000)
    schema_version: int = SCHEMA_VERSION
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)
    commissioned: bool = Field(False, description="Da nghiem thu va khoa cau hinh")

    @field_validator("profile_id")
    @classmethod
    def _check_id(cls, value: str) -> str:
        value = value.strip().lower()
        if not PROFILE_ID_RE.match(value):
            raise ValueError(
                "profile_id chi gom chu thuong, so, gach ngang, gach duoi; dai 2-49 ky tu"
            )
        return value


class VehicleProfile(BaseModel):
    """Ho so day du cua mot xe vat ly."""

    model_config = ConfigDict(extra="forbid")

    meta: ProfileMeta
    base: VehicleBase = Field(default_factory=VehicleBase)
    physics: Physics = Field(default_factory=Physics)
    zones: ZoneParams = Field(default_factory=ZoneParams)
    sensors: SensorParams = Field(default_factory=SensorParams)
    cameras: dict[str, CameraConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _fill_cameras(self) -> "VehicleProfile":
        """Bao dam du 3 camera, dien nhan/goc/vung giam sat mac dinh neu thieu."""
        geometry = derive_geometry(
            self.base.wheelbase_tractor,
            self.base.cab_width,
            self.base.l_trail,
            self.base.w_trail,
            self.base.driver_height,
        )
        auto_positions = geometry.camera_positions()

        for camera_id in CAMERA_IDS:
            layout = CAMERA_LAYOUT[camera_id]
            camera = self.cameras.get(camera_id)
            if camera is None:
                camera = CameraConfig(
                    label=layout["label"],
                    pitch_deg=layout["default_pitch_deg"],
                    yaw_deg=layout["default_yaw_deg"],
                    roll_deg=layout["default_roll_deg"],
                    monitored_blind_zones=list(layout["monitored_blind_zones"]),
                )
            if not camera.label:
                camera.label = layout["label"]
            if not camera.monitored_blind_zones:
                camera.monitored_blind_zones = list(layout["monitored_blind_zones"])
            if camera.auto_position or camera.position is None:
                camera.position = [round(v, 4) for v in auto_positions[camera_id]]
            self.cameras[camera_id] = camera

        unknown = set(self.cameras) - set(CAMERA_IDS)
        if unknown:
            raise ValueError(f"Camera khong hop le: {sorted(unknown)}. Cho phep: {list(CAMERA_IDS)}")
        return self

    def geometry(self):
        return derive_geometry(
            self.base.wheelbase_tractor,
            self.base.cab_width,
            self.base.l_trail,
            self.base.w_trail,
            self.base.driver_height,
        )

    def touch(self) -> None:
        self.meta.updated_at = _utcnow()


# ---------------------------------------------------------------------------
# Mau xe: ky thuat vien chon mau roi chinh lai, nhanh hon nhap tu dau.
# So lieu la gia tri dien hinh tai Viet Nam, van phai doi chieu so dang kiem.
# ---------------------------------------------------------------------------
class VehicleTemplate(BaseModel):
    template_id: str
    label: str
    description: str
    vehicle_type: Literal["articulated", "rigid"]
    base: VehicleBase


VEHICLE_TEMPLATES: list[VehicleTemplate] = [
    VehicleTemplate(
        template_id="container_40ft",
        label="Dau keo + so mi ro-mooc 40 ft",
        description="To hop container 40 feet pho bien tuyen cang.",
        vehicle_type="articulated",
        base=VehicleBase(wheelbase_tractor=3.6, cab_width=2.5, l_trail=12.0, w_trail=2.5),
    ),
    VehicleTemplate(
        template_id="container_20ft",
        label="Dau keo + so mi ro-mooc 20 ft",
        description="To hop container 20 feet, ro-mooc ngan hon.",
        vehicle_type="articulated",
        base=VehicleBase(wheelbase_tractor=3.4, cab_width=2.5, l_trail=7.0, w_trail=2.44),
    ),
    VehicleTemplate(
        template_id="truck_8t",
        label="Xe tai thung 8 tan (than lien)",
        description="Xe tai thung mui bat 1 than, khong khop gap.",
        vehicle_type="rigid",
        base=VehicleBase(wheelbase_tractor=4.2, cab_width=2.35, l_trail=6.2, w_trail=2.35),
    ),
    VehicleTemplate(
        template_id="bus_47",
        label="Xe khach 47 cho (than lien)",
        description="Xe khach giuong nam / ghe ngoi duong dai.",
        vehicle_type="rigid",
        base=VehicleBase(wheelbase_tractor=6.0, cab_width=2.5, l_trail=6.0, w_trail=2.5),
    ),
    VehicleTemplate(
        template_id="mixer_truck",
        label="Xe bon tron be tong",
        description="Xe chuyen dung, tam nhin hong bi bon che nang.",
        vehicle_type="rigid",
        base=VehicleBase(wheelbase_tractor=4.5, cab_width=2.5, l_trail=5.5, w_trail=2.5),
    ),
]
