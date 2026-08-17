"""Derived Config Architecture.

Suy ra toan bo hinh hoc xe tu 4 thong so so dang kiem + chieu cao tai xe.

CANH BAO QUAN TRONG
-------------------
Moi cong thuc trong file nay PHAI khop tuyet doi voi
`2_BlindSpot_Risk_Calculation/dynamic_blind_zone/config.py`.
Test `tests/test_derive_parity.py` so sanh tung gia tri voi module config that;
neu ai doi cong thuc ben engine ma khong doi ben nay, test se do.

He toa do (VCS): goc (0,0) tai tam truc sau dau keo, X huong truoc,
Y huong trai, don vi met.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Bang can cu tieu chuan cho tung he so suy luan.
# UI doc bang nay de hien "can cu: QCVN 09:2015/BGTVT" ben canh moi so,
# giup ky thuat vien tin vao con so ma he thong tu dien.
# ---------------------------------------------------------------------------
DERIVATION_BASIS: dict[str, dict[str, str]] = {
    "CAB_FRONT_X": {
        "label": "Mui xe (mep can truoc)",
        "formula": "L_f + 0.40",
        "standard": "QCVN 09:2015/BGTVT",
        "note": "Do nho can truoc co dinh 40 cm so voi truc banh truoc.",
    },
    "CAB_REAR_X": {
        "label": "Vach sau cabin",
        "formula": "L_f x 0.61",
        "standard": "Khao sat cabin dau bang (COE)",
        "note": "Cabin Cab-Over-Engine dat sau truc truoc.",
    },
    "D_HITCH": {
        "label": "Chot keo (mam xoay)",
        "formula": "L_f x 0.08",
        "standard": "SAE J694 / ISO 1726",
        "note": "Mam xoay lech 7.5-8.5% truoc truc sau de phan bo 33% tai cau truoc.",
    },
    "TRAIL_OVERHANG": {
        "label": "Nho ro-mooc truoc chot keo",
        "formula": "L_f x 0.25",
        "standard": "Ban kinh quay mam xoay keo container",
        "note": "",
    },
    "CHASSIS_HALF_W": {
        "label": "Nua rong khung gam",
        "formula": "W_cab x 0.18",
        "standard": "Khung gam hep bang 36% be rong cabin",
        "note": "",
    },
    "EYE_X": {
        "label": "Mat tai xe - doc",
        "formula": "L_f x 0.78",
        "standard": "SAE J941 (Eyellipse)",
        "note": "Vung oval mat tai xe chuan xe tai hang nang.",
    },
    "EYE_Y": {
        "label": "Mat tai xe - ngang",
        "formula": "W_cab x 0.20",
        "standard": "SAE J941 (Eyellipse)",
        "note": "Lech ve phia ghe lai (ben trai).",
    },
    "EYE_Z": {
        "label": "Do cao tam mat",
        "formula": "2.20 + (H_driver - 1.70) x 0.5",
        "standard": "San cabin 1.4 m + tam mat ngoi 0.8 m",
        "note": "Hieu chinh 50% theo chenh lech chieu cao tai xe.",
    },
    "MIRROR_X": {
        "label": "Guong chieu hau - doc",
        "formula": "L_f x 0.97",
        "standard": "QCVN 09:2015/BGTVT",
        "note": "Guong gan sat chan kinh truoc.",
    },
    "MIRROR_Y": {
        "label": "Guong chieu hau - ngang",
        "formula": "+/- (W_cab/2 + 0.10)",
        "standard": "QCVN 09:2015/BGTVT",
        "note": "Guong vuon ra ngoai hong xe 10 cm.",
    },
    "A_PILLAR": {
        "label": "Cot A",
        "formula": "X = X_mirror - 0.10 ; Y = +/- (W_cab/2 - 0.05)",
        "standard": "Khung gia cuong cua so truoc cabin",
        "note": "",
    },
    "B_PILLAR": {
        "label": "Cot B",
        "formula": "X = X_cab_rear ; Y = +/- W_cab/2",
        "standard": "Vach kim loai sau cua so, chan tam nhin ngoai vai",
        "note": "",
    },
}

# Ten camera va vung mu ma moi camera chiu trach nhiem giam sat.
# Giu dung thu tu / dung ten khoa nhu CAMERAS_EXTRINSICS trong config.py.
CAMERA_LAYOUT: dict[str, dict[str, Any]] = {
    "MIRROR_R": {
        "label": "Guong phai (phu xe)",
        "default_pitch_deg": -15.0,
        "default_yaw_deg": -165.0,
        "default_roll_deg": 0.0,
        "monitored_blind_zones": [
            "right_side_occlusion",
            "a_pillar_right",
            "b_pillar_right",
            "swept_path_right",
        ],
    },
    "MIRROR_L": {
        "label": "Guong trai (tai xe)",
        "default_pitch_deg": -15.0,
        "default_yaw_deg": 165.0,
        "default_roll_deg": 0.0,
        "monitored_blind_zones": [
            "left_side_occlusion",
            "a_pillar_left",
            "b_pillar_left",
            "swept_path_left",
        ],
    },
    "FRONT_CAM": {
        "label": "Camera mui xe",
        "default_pitch_deg": -10.0,
        "default_yaw_deg": 0.0,
        "default_roll_deg": 0.0,
        "monitored_blind_zones": ["front_bonnet", "stopping_hazard"],
    },
}

CAMERA_IDS = tuple(CAMERA_LAYOUT.keys())


@dataclass(frozen=True)
class DerivedGeometry:
    """Toan bo 25 thong so hinh hoc suy ra tu 4 thong so co ban."""

    # Nua chieu rong
    cab_half_w: float
    trail_half_w: float
    chassis_half_w: float
    # Cabin
    cab_front_x: float
    cab_rear_x: float
    d_hitch: float
    trail_overhang: float
    # Ro-mooc (mep truoc / mep sau trong VCS)
    trail_front_x: float
    trail_rear_x: float
    # Mat tai xe
    eye_x: float
    eye_y: float
    eye_z: float
    # Guong
    mirror_r_x: float
    mirror_r_y: float
    mirror_l_x: float
    mirror_l_y: float
    # Cot A / Cot B
    a_pillar_r_x: float
    a_pillar_r_y: float
    a_pillar_l_x: float
    a_pillar_l_y: float
    b_pillar_r_x: float
    b_pillar_r_y: float
    b_pillar_l_x: float
    b_pillar_l_y: float
    # Tong the (chi de hien thi / kiem tra hop ly)
    total_length: float
    max_width: float

    def as_dict(self) -> dict[str, float]:
        return {k: round(v, 4) for k, v in self.__dict__.items()}

    def camera_positions(self) -> dict[str, list[float]]:
        """Vi tri lap camera suy ra tu guong va mui xe (khop CAMERAS_EXTRINSICS)."""
        return {
            "MIRROR_R": [self.mirror_r_x, self.mirror_r_y, self.eye_z],
            "MIRROR_L": [self.mirror_l_x, self.mirror_l_y, self.eye_z],
            "FRONT_CAM": [self.cab_front_x, 0.0, self.eye_z + 0.3],
        }


def derive_geometry(
    wheelbase_tractor: float,
    cab_width: float,
    l_trail: float,
    w_trail: float,
    driver_height: float = 1.70,
) -> DerivedGeometry:
    """Suy ra hinh hoc day du. Cong thuc khop 1:1 voi config.py."""
    l_f = wheelbase_tractor
    w_cab = cab_width

    cab_half_w = w_cab / 2.0
    trail_half_w = w_trail / 2.0
    chassis_half_w = w_cab * 0.18

    cab_front_x = l_f + 0.40
    cab_rear_x = l_f * 0.61
    d_hitch = l_f * 0.08
    trail_overhang = l_f * 0.25

    eye_x = l_f * 0.78
    eye_y = w_cab * 0.20
    eye_z = 2.20 + (driver_height - 1.70) * 0.5

    mirror_x = l_f * 0.97
    mirror_r_y = -(cab_half_w + 0.10)
    mirror_l_y = cab_half_w + 0.10

    a_pillar_x = mirror_x - 0.10
    a_pillar_r_y = -(cab_half_w - 0.05)
    a_pillar_l_y = cab_half_w - 0.05

    trail_front_x = d_hitch + trail_overhang
    trail_rear_x = d_hitch - l_trail

    return DerivedGeometry(
        cab_half_w=cab_half_w,
        trail_half_w=trail_half_w,
        chassis_half_w=chassis_half_w,
        cab_front_x=cab_front_x,
        cab_rear_x=cab_rear_x,
        d_hitch=d_hitch,
        trail_overhang=trail_overhang,
        trail_front_x=trail_front_x,
        trail_rear_x=trail_rear_x,
        eye_x=eye_x,
        eye_y=eye_y,
        eye_z=eye_z,
        mirror_r_x=mirror_x,
        mirror_r_y=mirror_r_y,
        mirror_l_x=mirror_x,
        mirror_l_y=mirror_l_y,
        a_pillar_r_x=a_pillar_x,
        a_pillar_r_y=a_pillar_r_y,
        a_pillar_l_x=a_pillar_x,
        a_pillar_l_y=a_pillar_l_y,
        b_pillar_r_x=cab_rear_x,
        b_pillar_r_y=-cab_half_w,
        b_pillar_l_x=cab_rear_x,
        b_pillar_l_y=cab_half_w,
        total_length=cab_front_x - trail_rear_x,
        max_width=max(w_cab, w_trail),
    )


def sanity_warnings(
    wheelbase_tractor: float,
    cab_width: float,
    l_trail: float,
    w_trail: float,
    geometry: DerivedGeometry,
) -> list[dict[str, str]]:
    """Canh bao hop ly hoa - khong chan luu, chi nhac ky thuat vien kiem tra lai.

    Muc dich: bat loi nhap sai don vi (cm thay vi m) hoac lech so dang kiem,
    truoc khi cau hinh sai duoc nap vao xe dang chay.
    """
    out: list[dict[str, str]] = []

    def warn(field: str, message: str) -> None:
        out.append({"field": field, "message": message})

    if not 2.5 <= wheelbase_tractor <= 7.0:
        warn(
            "wheelbase_tractor",
            f"Chieu dai co so {wheelbase_tractor:.2f} m nam ngoai dai thuong gap "
            "cua dau keo (2.5-7.0 m). Kiem tra lai don vi met.",
        )
    if not 1.8 <= cab_width <= 2.8:
        warn(
            "cab_width",
            f"Chieu rong cabin {cab_width:.2f} m nam ngoai dai thuong gap "
            "(1.8-2.8 m). Gioi han phap dinh Viet Nam la 2.5 m.",
        )
    if cab_width > 2.5:
        warn(
            "cab_width",
            "Chieu rong vuot 2.5 m - gioi han kho gioi han phuong tien theo "
            "QCVN 09:2015/BGTVT. Xac nhan lai so dang kiem.",
        )
    if not 3.0 <= l_trail <= 16.0:
        warn(
            "l_trail",
            f"Chieu dai ro-mooc {l_trail:.2f} m nam ngoai dai thuong gap (3-16 m).",
        )
    if not 1.8 <= w_trail <= 3.0:
        warn("w_trail", f"Chieu rong ro-mooc {w_trail:.2f} m nam ngoai dai thuong gap.")
    if geometry.total_length > 20.0:
        warn(
            "l_trail",
            f"Tong chieu dai to hop {geometry.total_length:.2f} m vuot 20 m - "
            "gioi han to hop dau keo + so mi ro-mooc tai Viet Nam.",
        )
    if l_trail <= geometry.trail_overhang:
        warn(
            "l_trail",
            "Chieu dai ro-mooc nho hon phan nho truoc chot keo - hinh hoc khong hop le.",
        )
    if geometry.cab_rear_x >= geometry.cab_front_x:
        warn("wheelbase_tractor", "Vach sau cabin nam truoc mui xe - hinh hoc khong hop le.")
    return out
