"""Giai goc lap camera tu cac diem moc do bang thuoc.

Ky thuat vien dat vat moc (chop non) o vi tri da do san, roi cham vao chan vat
moc tren anh. Moi cap (pixel, toa do met) la mot rang buoc. Bai toan: tim
pitch / yaw / roll (va tuy chon do cao z) sao cho chieu nguoc pixel ra met khop
nhat voi so do thuc.

Sai so duoc do bang MET - dung don vi ma tieu chi nghiem thu dung, thay vi pixel.
Khong phu thuoc OpenCV: dung Gauss-Newton co giam (damped) voi Jacobian sai phan
huu han, du chinh xac cho 3-4 an va vai chuc diem.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from ..domain import engine
from ..domain.schemas import CameraConfig

# Sai so muc tieu: tai lieu nghien cuu yeu cau < 0.30 m trong pham vi 5 m.
RMS_TARGET_M = 0.30
RMS_WARN_M = 0.50


@dataclass
class Correspondence:
    """Mot cap tuong ung: pixel tren anh <-> toa do met do bang thuoc."""

    u: float
    v: float
    x: float
    y: float
    label: str = ""


@dataclass
class SolveResult:
    ok: bool
    pitch_deg: float
    yaw_deg: float
    roll_deg: float
    height_m: float
    rms_m: float
    max_error_m: float
    per_point: list[dict] = field(default_factory=list)
    iterations: int = 0
    message: str = ""
    verdict: str = "fail"
    roll_solved: bool = False


def _clone_camera(camera: CameraConfig, pitch: float, yaw: float, roll: float, z: float):
    data = camera.model_dump()
    data["pitch_deg"] = float(np.clip(pitch, -180.0, 180.0))
    data["yaw_deg"] = float(((yaw + 180.0) % 360.0) - 180.0)
    data["roll_deg"] = float(np.clip(roll, -180.0, 180.0))
    position = list(data["position"] or [0.0, 0.0, 0.0])
    position[2] = float(z)
    data["position"] = position
    data["auto_position"] = False
    return CameraConfig.model_validate(data)


@dataclass(frozen=True)
class _ParamLayout:
    """Thu tu an trong vector nghiem. Roll chi co mat khi engine ap dung roll."""

    solve_roll: bool
    solve_height: bool

    @property
    def size(self) -> int:
        return 2 + int(self.solve_roll) + int(self.solve_height)

    @property
    def roll_index(self) -> int | None:
        return 2 if self.solve_roll else None

    @property
    def height_index(self) -> int | None:
        if not self.solve_height:
            return None
        return 3 if self.solve_roll else 2

    def unpack(
        self, params: np.ndarray, base_roll: float, base_height: float
    ) -> tuple[float, float, float, float]:
        roll = params[self.roll_index] if self.roll_index is not None else base_roll
        height = params[self.height_index] if self.height_index is not None else base_height
        return float(params[0]), float(params[1]), float(roll), float(height)

    def step(self, column: int) -> float:
        return 1e-4 if column == self.height_index else 1e-3


def _residuals(
    camera: CameraConfig,
    params: np.ndarray,
    points: Sequence[Correspondence],
    base_roll: float,
    base_height: float,
    layout: _ParamLayout,
) -> np.ndarray:
    pitch, yaw, roll, height = layout.unpack(params, base_roll, base_height)
    probe = _clone_camera(camera, pitch, yaw, roll, height)
    # precision=None: tuyet doi khong lam tron trong vong toi uu.
    projected = engine.pixel_to_ground(probe, [(p.u, p.v) for p in points], precision=None)

    out = np.empty(2 * len(points), dtype=float)
    for index, (point, ground) in enumerate(zip(points, projected)):
        if ground is None:
            # Tia khong cat mat duong -> phat nang de bo giai thoat khoi vung sai.
            out[2 * index] = 1e3
            out[2 * index + 1] = 1e3
        else:
            out[2 * index] = ground[0] - point.x
            out[2 * index + 1] = ground[1] - point.y
    return out


def _cost(
    camera: CameraConfig,
    params: np.ndarray,
    points: Sequence[Correspondence],
    base_roll: float,
    base_height: float,
    layout: "_ParamLayout",
) -> float:
    residuals = _residuals(camera, params, points, base_roll, base_height, layout)
    return float(residuals @ residuals)


def solve_camera_angles(
    camera: CameraConfig,
    points: Sequence[Correspondence],
    solve_height: bool = False,
    max_iterations: int = 60,
) -> SolveResult:
    """Gauss-Newton co giam, khoi tao da diem de tranh cuc tieu dia phuong."""
    if len(points) < 2:
        return SolveResult(
            ok=False,
            pitch_deg=camera.pitch_deg,
            yaw_deg=camera.yaw_deg,
            roll_deg=camera.roll_deg,
            height_m=(camera.position or [0, 0, 0])[2],
            rms_m=float("inf"),
            max_error_m=float("inf"),
            message="Can it nhat 2 diem moc da do khoang cach. Nen dung 4 diem.",
        )

    base_height = float((camera.position or [0.0, 0.0, 2.2])[2])
    base_roll = float(camera.roll_deg)
    # Chi dua roll vao vector nghiem khi engine thuc su ap dung roll; neu khong,
    # cot Jacobian tuong ung se bang 0 va he phuong trinh suy bien.
    layout = _ParamLayout(solve_roll=engine.roll_is_supported(), solve_height=solve_height)
    n_params = layout.size

    def seed_vector(pitch: float, yaw: float) -> np.ndarray:
        values = [pitch, yaw]
        if layout.solve_roll:
            values.append(base_roll)
        if layout.solve_height:
            values.append(base_height)
        return np.array(values, dtype=float)

    # Nhieu diem khoi tao: gia tri hien tai + quet tho quanh no, tranh cuc tieu dia phuong.
    starts = [
        seed_vector(camera.pitch_deg + d_pitch, camera.yaw_deg + d_yaw)
        for d_pitch in (0.0, -8.0, 8.0, -16.0, 16.0)
        for d_yaw in (0.0, -10.0, 10.0, -20.0, 20.0)
    ]

    best_params: np.ndarray | None = None
    best_cost = math.inf
    total_iterations = 0

    for start in starts:
        params = start.copy()
        cost = _cost(camera, params, points, base_roll, base_height, layout)
        damping = 1e-2
        delta = np.zeros(n_params)

        for _ in range(max_iterations):
            total_iterations += 1
            residuals = _residuals(camera, params, points, base_roll, base_height, layout)

            # Jacobian sai phan huu han: buoc 1e-3 do / 1e-4 m.
            jacobian = np.zeros((len(residuals), n_params), dtype=float)
            for column in range(n_params):
                shifted = params.copy()
                shifted[column] += layout.step(column)
                jacobian[:, column] = (
                    _residuals(camera, shifted, points, base_roll, base_height, layout) - residuals
                ) / layout.step(column)

            jtj = jacobian.T @ jacobian
            jtr = jacobian.T @ residuals
            improved = False
            for _ in range(10):
                try:
                    delta = np.linalg.solve(jtj + damping * np.eye(n_params), -jtr)
                except np.linalg.LinAlgError:
                    damping *= 10.0
                    continue
                candidate = params + delta
                candidate_cost = _cost(camera, candidate, points, base_roll, base_height, layout)
                if candidate_cost < cost:
                    params, cost = candidate, candidate_cost
                    damping = max(damping * 0.5, 1e-9)
                    improved = True
                    break
                damping *= 10.0
            if not improved or float(np.linalg.norm(delta)) < 1e-9:
                break

        if cost < best_cost:
            best_cost, best_params = cost, params.copy()

    assert best_params is not None
    pitch, yaw, roll, height = layout.unpack(best_params, base_roll, base_height)
    solved = _clone_camera(camera, pitch, yaw, roll, height)

    projected = engine.pixel_to_ground(solved, [(p.u, p.v) for p in points])
    per_point: list[dict] = []
    errors: list[float] = []
    for point, ground in zip(points, projected):
        if ground is None:
            per_point.append(
                {
                    "label": point.label,
                    "measured": [point.x, point.y],
                    "estimated": None,
                    "error_m": None,
                    "note": "Tia khong cat mat duong",
                }
            )
            errors.append(float("inf"))
            continue
        error = math.dist(ground, (point.x, point.y))
        errors.append(error)
        per_point.append(
            {
                "label": point.label,
                "measured": [point.x, point.y],
                "estimated": ground,
                "error_m": round(error, 3),
                "note": "",
            }
        )

    finite = [e for e in errors if math.isfinite(e)]
    rms = math.sqrt(sum(e * e for e in finite) / len(finite)) if finite else float("inf")
    max_error = max(errors) if errors else float("inf")

    if not math.isfinite(rms):
        verdict, message = "fail", "Khong giai duoc: kiem tra lai thu tu diem va so do."
    elif rms <= RMS_TARGET_M:
        verdict = "pass"
        message = f"Dat: sai so RMS {rms:.3f} m (muc tieu <= {RMS_TARGET_M:.2f} m)."
    elif rms <= RMS_WARN_M:
        verdict = "warn"
        message = (
            f"Tam duoc: sai so RMS {rms:.3f} m. Nen do lai vat moc hoac them diem "
            f"de dat muc tieu {RMS_TARGET_M:.2f} m."
        )
    else:
        verdict = "fail"
        message = (
            f"Chua dat: sai so RMS {rms:.3f} m. Kiem tra lai so do khoang cach, "
            "chieu cao lap camera va tieu cu (fx, fy)."
        )

    if len(points) < 4:
        message += " Luu y: it hon 4 diem nen ket qua kem on dinh."
    if not layout.solve_roll:
        message += (
            " Roll khong duoc giai vi engine hien chua ap dung goc roll "
            "(camera_calibration.get_rotation_matrix_3d bo qua roll_deg)."
        )

    return SolveResult(
        ok=math.isfinite(rms),
        pitch_deg=round(solved.pitch_deg, 3),
        yaw_deg=round(solved.yaw_deg, 3),
        roll_deg=round(solved.roll_deg, 3),
        height_m=round(height, 3),
        rms_m=round(rms, 4) if math.isfinite(rms) else -1.0,
        max_error_m=round(max_error, 4) if math.isfinite(max_error) else -1.0,
        per_point=per_point,
        iterations=total_iterations,
        message=message,
        verdict=verdict,
        roll_solved=layout.solve_roll,
    )


def verify_points(
    camera: CameraConfig, points: Sequence[Correspondence]
) -> dict:
    """Kiem tra do chinh xac voi goc hien tai, khong giai lai.

    Dung cho buoc 'Kiem tra lai sau khi lap': dat chop non o khoang cach da biet,
    cham vao, xem he thong bao lech bao nhieu met.
    """
    projected = engine.pixel_to_ground(camera, [(p.u, p.v) for p in points])
    rows: list[dict] = []
    errors: list[float] = []
    for point, ground in zip(points, projected):
        if ground is None:
            rows.append(
                {
                    "label": point.label,
                    "measured": [point.x, point.y],
                    "estimated": None,
                    "error_m": None,
                }
            )
            continue
        error = math.dist(ground, (point.x, point.y))
        errors.append(error)
        rows.append(
            {
                "label": point.label,
                "measured": [point.x, point.y],
                "estimated": ground,
                "error_m": round(error, 3),
            }
        )
    rms = math.sqrt(sum(e * e for e in errors) / len(errors)) if errors else None
    return {
        "rms_m": round(rms, 4) if rms is not None else None,
        "max_error_m": round(max(errors), 4) if errors else None,
        "target_m": RMS_TARGET_M,
        "verdict": (
            "pass"
            if rms is not None and rms <= RMS_TARGET_M
            else "warn"
            if rms is not None and rms <= RMS_WARN_M
            else "fail"
        ),
        "per_point": rows,
    }
