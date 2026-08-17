"""Sinh khung hinh camera gia lap - de demo va cang chinh khi chua co phan cung.

Diem quan trong: anh gia lap duoc ve bang DUNG mo hinh camera that
(K + [R|T] trong `camera_calibration.py`), voi mot bo goc "su that vat ly" lech
nhe so voi goc mac dinh trong cau hinh. Nho vay:

  - Luoi met chieu tu cau hinh se KHONG khop ngay -> ky thuat vien co viec that
    de lam o buoc cang chinh, giong hien truong.
  - Chop non nam o toa do met da biet, nen bam vao chop non roi bam "Giai goc"
    se ra ket qua dung -> quy trinh nghiem thu chay tron ven khong can camera.

Khi cam camera that vao, chi doi bien moi truong; frontend khong doi mot dong.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass

from PIL import Image, ImageDraw

from ..domain import engine
from ..domain.schemas import CameraConfig, VehicleProfile

# Chop non hieu chuan: toa do met trong VCS, do san bang thuoc day.
# Bo tri hinh chu nhat de rang buoc du ca 3 goc pitch/yaw/roll.
CONE_COLORS = [(224, 76, 43), (34, 160, 88), (36, 118, 224), (232, 178, 36)]
CONE_NAMES = ["DO", "XANH LA", "XANH DUONG", "VANG"]
CONE_HEIGHT_M = 0.70

CALIBRATION_CONES: dict[str, list[tuple[float, float]]] = {
    # Guong phai: chop non rai doc hong phai xe (Y < 0).
    "MIRROR_R": [(1.0, -2.5), (1.0, -5.0), (-4.0, -5.0), (-4.0, -2.5)],
    # Guong trai: doi xung sang Y > 0.
    "MIRROR_L": [(1.0, 2.5), (1.0, 5.0), (-4.0, 5.0), (-4.0, 2.5)],
    # Camera mui xe: chop non phia truoc cabin.
    "FRONT_CAM": [(6.0, -2.0), (6.0, 2.0), (11.0, 2.0), (11.0, -2.0)],
    # Camera duoi xe: chop non phia sau ro-mooc.
    "REAR_CAM": [(-3.0, -2.0), (-3.0, 2.0), (-8.0, 2.0), (-8.0, -2.0)],
}

# Do lech "su that vat ly" so voi goc mac dinh - co dinh de ket qua tai lap duoc.
#
# d_roll = 0 co chu y: engine hien chua ap dung goc roll (xem
# engine.roll_is_supported). Neu dua roll vao anh gia lap thi bo giai khong the
# nao khop duoc va sai so se co san mot muc nen gia tao, lam ky thuat vien tuong
# minh do sai. Khi nao engine ho tro roll thi mo lai gia tri o day.
TRUTH_OFFSET: dict[str, tuple[float, float, float, float]] = {
    # (d_pitch, d_yaw, d_roll, d_height)
    "MIRROR_R": (2.5, -3.0, 0.0, -0.08),
    "MIRROR_L": (-2.0, 2.5, 0.0, 0.06),
    "FRONT_CAM": (1.5, 1.8, 0.0, -0.05),
    "REAR_CAM": (2.0, -2.5, 0.0, -0.06),
}

SKY = (206, 214, 222)
ASPHALT = (86, 90, 96)
ASPHALT_FAR = (118, 122, 128)
GRID = (128, 133, 140)
LANE = (222, 224, 226)
BODYWORK = (52, 60, 72)


@dataclass(frozen=True)
class MockScene:
    camera_id: str
    truth: CameraConfig
    cones: list[tuple[float, float]]


def build_truth_camera(camera_id: str, camera: CameraConfig) -> CameraConfig:
    """Tao pose 'su that vat ly' = pose cau hinh + do lech co dinh."""
    d_pitch, d_yaw, d_roll, d_height = TRUTH_OFFSET.get(camera_id, (0.0, 0.0, 0.0, 0.0))
    data = camera.model_dump()
    data["pitch_deg"] = camera.pitch_deg + d_pitch
    data["yaw_deg"] = camera.yaw_deg + d_yaw
    data["roll_deg"] = camera.roll_deg + d_roll
    position = list(camera.position or [0.0, 0.0, 2.2])
    position[2] += d_height
    data["position"] = position
    data["auto_position"] = False
    return CameraConfig.model_validate(data)


def build_scene(profile: VehicleProfile, camera_id: str) -> MockScene:
    camera = profile.cameras[camera_id]
    return MockScene(
        camera_id=camera_id,
        truth=build_truth_camera(camera_id, camera),
        cones=CALIBRATION_CONES.get(camera_id, []),
    )


def _project(scene: MockScene, points: list[tuple[float, float]], z: float = 0.0):
    return engine.ground_to_pixel(scene.truth, points, z=z)


def _draw_ground_line(
    draw: ImageDraw.ImageDraw,
    scene: MockScene,
    start: tuple[float, float],
    end: tuple[float, float],
    color: tuple[int, int, int],
    width: int,
    samples: int = 48,
) -> None:
    """Ve mot doan thang tren mat duong bang cach lay mau roi noi cac doan hop le.

    Cach nay tu dong xu ly duong chan troi: diem nam sau ong kinh tra ve None va
    doan tuong ung bi bo qua, khong can code cat (clip) rieng.
    """
    pts = [
        (
            start[0] + (end[0] - start[0]) * i / samples,
            start[1] + (end[1] - start[1]) * i / samples,
        )
        for i in range(samples + 1)
    ]
    projected = _project(scene, pts)
    previous = None
    for point in projected:
        if point is None:
            previous = None
            continue
        if previous is not None:
            draw.line([tuple(previous), tuple(point)], fill=color, width=width)
        previous = point


def render_frame(
    profile: VehicleProfile,
    camera_id: str,
    tick: float = 0.0,
    show_actor: bool = True,
) -> Image.Image:
    """Ve mot khung hinh gia lap.

    `tick` (giay) dung de di chuyen dien vien (xe may) -> luong MJPEG nhin nhu that.
    """
    camera = profile.cameras[camera_id]
    scene = build_scene(profile, camera_id)
    width, height = camera.width, camera.height

    image = Image.new("RGB", (width, height), SKY)
    draw = ImageDraw.Draw(image)

    # Mat duong: to tu duoi len den duong chan troi uoc luong.
    horizon = _estimate_horizon(scene, width, height)
    draw.rectangle([0, horizon, width, height], fill=ASPHALT_FAR)
    draw.rectangle([0, int(horizon + (height - horizon) * 0.45), width, height], fill=ASPHALT)

    # Luoi met 1 m x 1 m.
    for y in range(-14, 15):
        _draw_ground_line(draw, scene, (-30.0, float(y)), (30.0, float(y)), GRID, 1)
    for x in range(-30, 31):
        _draw_ground_line(draw, scene, (float(x), -14.0), (float(x), 14.0), GRID, 1)

    # Vach ke lan duong cho de doc bo cuc.
    for y in (-3.5, 3.5):
        _draw_ground_line(draw, scene, (-30.0, y), (30.0, y), LANE, 3)

    # Than xe nhin thay trong khung (dai toi mau) - chi mang tinh boi canh.
    _draw_bodywork(draw, scene, profile, camera_id)

    # Chop non hieu chuan.
    for index, cone in enumerate(scene.cones):
        _draw_cone(draw, scene, cone, CONE_COLORS[index % 4], index + 1)

    if show_actor:
        _draw_actor(draw, scene, camera_id, tick)

    _draw_watermark(draw, camera, camera_id, width, height)
    return image


def _estimate_horizon(scene: MockScene, width: int, height: int) -> int:
    """Tim dong pixel cua duong chan troi bang cach chieu diem rat xa."""
    far = _project(scene, [(600.0, 0.0), (-600.0, 0.0)])
    candidates = [p[1] for p in far if p is not None]
    if not candidates:
        return int(height * 0.42)
    return int(max(0, min(height - 1, min(candidates))))


def _draw_bodywork(
    draw: ImageDraw.ImageDraw, scene: MockScene, profile: VehicleProfile, camera_id: str
) -> None:
    """Ve mot phan than xe de khung hinh giong camera gan tren xe that."""
    geometry = profile.geometry()
    if camera_id == "MIRROR_R":
        edge_y = -geometry.trail_half_w
    elif camera_id == "MIRROR_L":
        edge_y = geometry.trail_half_w
    else:
        return  # REAR_CAM va FRONT_CAM khong ve than xe ben hong

    bottom = [(geometry.trail_front_x, edge_y), (geometry.trail_rear_x, edge_y)]
    top = [(geometry.trail_front_x, edge_y), (geometry.trail_rear_x, edge_y)]
    projected_bottom = _project(scene, bottom, z=0.0)
    projected_top = _project(scene, top, z=3.6)
    if any(p is None for p in projected_bottom + projected_top):
        return
    polygon = [
        tuple(projected_bottom[0]),
        tuple(projected_bottom[1]),
        tuple(projected_top[1]),
        tuple(projected_top[0]),
    ]
    draw.polygon(polygon, fill=BODYWORK)


def _draw_cone(
    draw: ImageDraw.ImageDraw,
    scene: MockScene,
    ground: tuple[float, float],
    color: tuple[int, int, int],
    number: int,
) -> None:
    base = _project(scene, [ground])[0]
    apex = _project(scene, [ground], z=CONE_HEIGHT_M)[0]
    if base is None or apex is None:
        return
    bx, by = base
    ax, ay = apex
    pixel_height = abs(by - ay)
    half_base = max(3.0, pixel_height * 0.34)

    # Bong do tren mat duong.
    draw.ellipse(
        [bx - half_base * 1.15, by - half_base * 0.32, bx + half_base * 1.15, by + half_base * 0.32],
        fill=(58, 60, 64),
    )
    # De chop non.
    draw.polygon(
        [
            (bx - half_base * 1.25, by),
            (bx + half_base * 1.25, by),
            (bx + half_base * 1.05, by - half_base * 0.28),
            (bx - half_base * 1.05, by - half_base * 0.28),
        ],
        fill=tuple(int(c * 0.72) for c in color),
    )
    # Than chop non.
    draw.polygon([(ax, ay), (bx + half_base, by), (bx - half_base, by)], fill=color)
    # Vach phan quang trang.
    band_y = ay + pixel_height * 0.42
    band_half = half_base * 0.58
    draw.polygon(
        [
            (bx - band_half, band_y),
            (bx + band_half, band_y),
            (bx + band_half * 0.78, band_y - pixel_height * 0.13),
            (bx - band_half * 0.78, band_y - pixel_height * 0.13),
        ],
        fill=(238, 238, 238),
    )
    # So thu tu de cham dung thu tu ma khong phu thuoc mau (ho tro mu mau).
    label = str(number)
    draw.text((bx - 4, ay - 22), label, fill=(20, 20, 20))
    draw.text((bx - 5, ay - 23), label, fill=(255, 255, 255))


def _draw_actor(
    draw: ImageDraw.ImageDraw, scene: MockScene, camera_id: str, tick: float
) -> None:
    """Mot xe may chay doc hong xe - de luong MJPEG co chuyen dong."""
    period = 12.0
    phase = (tick % period) / period
    if camera_id == "MIRROR_R":
        x = -8.0 + phase * 14.0
        y = -3.2
    elif camera_id == "MIRROR_L":
        x = -8.0 + phase * 14.0
        y = 3.2
    elif camera_id == "REAR_CAM":
        x = -10.0 + phase * 6.0
        y = -1.2 + math.sin(phase * math.tau) * 0.8
    else:
        x = 14.0 - phase * 8.0
        y = -1.6 + math.sin(phase * math.tau) * 0.8

    base = _project(scene, [(x, y)])[0]
    top = _project(scene, [(x, y)], z=1.55)[0]
    if base is None or top is None:
        return
    bx, by = base
    _, ty = top
    pixel_height = abs(by - ty)
    half_width = max(4.0, pixel_height * 0.24)
    draw.ellipse(
        [bx - half_width, by - half_width * 0.28, bx + half_width, by + half_width * 0.28],
        fill=(52, 54, 58),
    )
    draw.rectangle(
        [bx - half_width, by - pixel_height * 0.55, bx + half_width, by],
        fill=(38, 42, 50),
    )
    draw.ellipse(
        [
            bx - half_width * 0.62,
            by - pixel_height,
            bx + half_width * 0.62,
            by - pixel_height * 0.5,
        ],
        fill=(198, 84, 46),
    )


def _draw_watermark(
    draw: ImageDraw.ImageDraw, camera: CameraConfig, camera_id: str, width: int, height: int
) -> None:
    bar_height = max(28, height // 22)
    draw.rectangle([0, 0, width, bar_height], fill=(22, 25, 30))
    draw.text((12, bar_height // 3), f"{camera_id}  |  {camera.label}", fill=(240, 242, 245))
    text = "ANH MO PHONG - CHUA CO CAMERA THAT"
    draw.text((width - 340, bar_height // 3), text, fill=(232, 178, 36))


def encode_jpeg(image: Image.Image, quality: int = 82) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=False)
    return buffer.getvalue()


def cone_truth_table(camera_id: str) -> list[dict]:
    """Bang dap an chop non - UI hien de ky thuat vien biet cham vao dau.

    Tren hien truong, bang nay chinh la so do bang thuoc day.
    """
    cones = CALIBRATION_CONES.get(camera_id, [])
    return [
        {
            "index": index + 1,
            "name": CONE_NAMES[index % 4],
            "color": "#%02x%02x%02x" % CONE_COLORS[index % 4],
            "x": cone[0],
            "y": cone[1],
        }
        for index, cone in enumerate(cones)
    ]
