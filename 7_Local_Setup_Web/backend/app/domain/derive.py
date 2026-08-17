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
        "label": "Mũi xe (mép cản trước)",
        "formula": "L_f + 0.40",
        "standard": "QCVN 09:2015/BGTVT",
        "how_to_measure": "Đo từ tâm trục bánh trước ra tới đầu cản trước. Đây là số tự suy ra, không cần đo trực tiếp.",
        "note": "Độ nhô cản trước cố định 40 cm so với trục bánh trước.",
    },
    "CAB_REAR_X": {
        "label": "Vách sau cabin",
        "formula": "L_f x 0.61",
        "standard": "Khảo sát cabin đầu bằng (COE)",
        "how_to_measure": "Tự suy ra từ chiều dài cơ sở, không cần đo.",
        "note": "Cabin đầu bằng (Cab-Over-Engine) đặt vách sau ngay trên trục trước.",
    },
    "D_HITCH": {
        "label": "Chốt kéo (mâm xoay)",
        "formula": "L_f x 0.08",
        "standard": "SAE J694 / ISO 1726",
        "how_to_measure": "Tự suy ra. Nếu muốn kiểm tra: đo từ tâm trục sau đầu kéo tới tâm mâm xoay (thường nhô ra 7.5–8.5% chiều dài cơ sở).",
        "note": "Mâm xoay lệch 7.5–8.5% trước trục sau để phân bổ 33% tải lên cầu trước.",
    },
    "TRAIL_OVERHANG": {
        "label": "Nhô rơ-moóc trước chốt kéo",
        "formula": "L_f x 0.25",
        "standard": "Bán kính quay mâm xoay kéo container",
        "how_to_measure": "Tự suy ra, không cần đo.",
        "note": "",
    },
    "CHASSIS_HALF_W": {
        "label": "Nửa rộng khung gầm",
        "formula": "W_cab x 0.18",
        "standard": "Khung gầm hẹp bằng 36% bề rộng cabin",
        "how_to_measure": "Tự suy ra, không cần đo.",
        "note": "",
    },
    "EYE_X": {
        "label": "Mắt tài xế — dọc xe",
        "formula": "L_f x 0.78",
        "standard": "SAE J941 (Eyellipse)",
        "how_to_measure": "Tự suy ra từ chiều dài cơ sở và chiều cao tài xế đã nhập.",
        "note": "Vùng oval mắt tài xế chuẩn xe tải hạng nặng.",
    },
    "EYE_Y": {
        "label": "Mắt tài xế — ngang xe",
        "formula": "W_cab x 0.20",
        "standard": "SAE J941 (Eyellipse)",
        "how_to_measure": "Tự suy ra, không cần đo.",
        "note": "Lệch về phía ghế lái (bên trái).",
    },
    "EYE_Z": {
        "label": "Độ cao tầm mắt",
        "formula": "2.20 + (chiều cao tài xế - 1.70) x 0.5",
        "standard": "Sàn cabin 1.4 m + tầm mắt ngồi 0.8 m",
        "how_to_measure": "Đo chiều cao tài xế thường lái xe (đứng thẳng, từ chân đến đỉnh đầu). Hệ thống tự quy đổi ra độ cao tầm mắt khi ngồi lái.",
        "note": "Hiệu chỉnh 50% theo chênh lệch chiều cao tài xế so với 1.70 m.",
    },
    "MIRROR_X": {
        "label": "Gương chiếu hậu — dọc xe",
        "formula": "L_f x 0.97",
        "standard": "QCVN 09:2015/BGTVT",
        "how_to_measure": "Tự suy ra, không cần đo. Gương thường gắn sát chân kính chắn gió trước.",
        "note": "Gương gắn sát chân kính trước.",
    },
    "MIRROR_Y": {
        "label": "Gương chiếu hậu — ngang xe",
        "formula": "±(W_cab/2 + 0.10)",
        "standard": "QCVN 09:2015/BGTVT",
        "how_to_measure": "Tự suy ra, không cần đo.",
        "note": "Gương vươn ra ngoài hông xe 10 cm.",
    },
    "A_PILLAR": {
        "label": "Cột A",
        "formula": "X = X_gương - 0.10 ; Y = ±(W_cab/2 - 0.05)",
        "standard": "Khung gia cường cửa sổ trước cabin",
        "how_to_measure": "Tự suy ra, không cần đo.",
        "note": "",
    },
    "B_PILLAR": {
        "label": "Cột B",
        "formula": "X = vách sau cabin ; Y = ±W_cab/2",
        "standard": "Vách kim loại sau cửa sổ, chắn tầm nhìn ngoái vai",
        "how_to_measure": "Tự suy ra, không cần đo.",
        "note": "",
    },
}

# Danh sách "cách đo" cho đúng 5 số phải đo tay - hien thi truc tiep trong
# man hinh nhap kich thuoc (yeu cau: liet ke thong so + cach do).
MEASUREMENT_GUIDE: list[dict[str, str]] = [
    {
        "key": "wheelbase_tractor",
        "label": "Chiều dài cơ sở đầu kéo (L_f)",
        "how_to_measure": (
            "Dùng thước dây đo khoảng cách giữa tâm trục bánh trước và tâm trục "
            "bánh sau (bánh đơn hoặc giữa 2 cụm trục sau nếu là trục đôi). Đo "
            "theo phương dọc thân xe, không đo theo đường chéo."
        ),
        "typical_range": "2.5 – 7.0 m",
    },
    {
        "key": "cab_width",
        "label": "Chiều rộng cabin (W_cab)",
        "how_to_measure": (
            "Đo bề rộng ngoài cùng của cabin (không tính gương chiếu hậu), tại "
            "điểm rộng nhất — thường ngay dưới cửa kính."
        ),
        "typical_range": "1.8 – 2.8 m",
    },
    {
        "key": "l_trail",
        "label": "Chiều dài rơ-moóc (L_trail)",
        "how_to_measure": (
            "Đo từ tâm chốt kéo (mâm xoay dưới gầm đầu kéo) đến tâm cụm trục "
            "bánh sau của rơ-moóc. Không đo tổng chiều dài rơ-moóc."
        ),
        "typical_range": "3 – 16 m",
    },
    {
        "key": "w_trail",
        "label": "Chiều rộng rơ-moóc (W_trail)",
        "how_to_measure": "Đo bề rộng ngoài cùng của thùng/sơ-mi rơ-moóc.",
        "typical_range": "1.8 – 3.0 m",
    },
    {
        "key": "driver_height",
        "label": "Chiều cao tài xế thường lái xe",
        "how_to_measure": (
            "Đo chiều cao đứng thẳng (chân đến đỉnh đầu) của tài xế chính. Nếu "
            "có nhiều tài xế, dùng người cao trung bình trong nhóm."
        ),
        "typical_range": "1.4 – 2.1 m",
    },
]

# Ten camera va vung mu ma moi camera chiu trach nhiem giam sat.
# 4 camera: guong phai, guong trai, mui xe, duoi xe (dung theo de tai 4 camera).
CAMERA_LAYOUT: dict[str, dict[str, Any]] = {
    "MIRROR_R": {
        "label": "Camera gương phải",
        "short_label": "Bên phải",
        "direction": "right",
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
        "label": "Camera gương trái",
        "short_label": "Bên trái",
        "direction": "left",
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
        "label": "Camera mũi xe",
        "short_label": "Phía trước",
        "direction": "front",
        "default_pitch_deg": -10.0,
        "default_yaw_deg": 0.0,
        "default_roll_deg": 0.0,
        "monitored_blind_zones": ["front_bonnet", "stopping_hazard"],
    },
    "REAR_CAM": {
        "label": "Camera đuôi xe",
        "short_label": "Phía sau",
        "direction": "rear",
        "default_pitch_deg": -12.0,
        "default_yaw_deg": 180.0,
        "default_roll_deg": 0.0,
        "monitored_blind_zones": ["swept_path"],
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
        """Vi tri lap camera suy ra tu guong, mui xe, duoi xe."""
        return {
            "MIRROR_R": [self.mirror_r_x, self.mirror_r_y, self.eye_z],
            "MIRROR_L": [self.mirror_l_x, self.mirror_l_y, self.eye_z],
            "FRONT_CAM": [self.cab_front_x, 0.0, self.eye_z + 0.3],
            "REAR_CAM": [self.trail_rear_x, 0.0, self.eye_z],
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
