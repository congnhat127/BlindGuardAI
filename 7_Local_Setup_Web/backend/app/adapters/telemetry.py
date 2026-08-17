"""Trang thai GPS / IMU. Che do mock sinh du lieu chay duoc de demo.

Che do mock tai su dung `GPSDeadReckoning` that trong engine, nen logic mat song
GPS (`is_gps_lost`, `GPS_TIMEOUT_SEC`) hien tren web dung y nhu tren xe.
"""

from __future__ import annotations

import math
import time
from typing import Any

from ..core.settings import settings
from ..domain import engine


class MockTelemetry:
    backend = "mock"

    def __init__(self) -> None:
        self._t0 = time.monotonic()
        self._dead_reckoning: Any | None = None

    def _engine_reckoning(self):
        if self._dead_reckoning is None:
            try:
                modules = engine._load_engine()  # noqa: SLF001 - dung noi bo co y
                module = __import__("dead_reckoning")
                self._dead_reckoning = module.GPSDeadReckoning()
                _ = modules
            except Exception:
                self._dead_reckoning = False
        return self._dead_reckoning or None

    def read(self) -> dict[str, Any]:
        """Kich ban gia lap: xe chay quanh vong tron roi vao doan re phai."""
        elapsed = time.monotonic() - self._t0
        speed_kmh = 12.0 + 6.0 * math.sin(elapsed / 9.0)
        yaw_rate_deg = 9.0 * math.sin(elapsed / 6.0)
        satellites = 9 + int(2 * math.sin(elapsed / 4.0))
        hdop = round(0.9 + 0.4 * abs(math.sin(elapsed / 7.0)), 2)

        reckoning = self._engine_reckoning()
        gps_lost = False
        if reckoning is not None:
            reckoning.update_gps_signal(speed_kmh / 3.6, math.radians(yaw_rate_deg))
            state = reckoning.predict_state_at_camera_frame()
            gps_lost = bool(state["is_gps_lost"])

        return {
            "backend": self.backend,
            "timestamp": time.time(),
            "gps": {
                "fix": True,
                "satellites": satellites,
                "hdop": hdop,
                "latitude": 16.0678 + 0.0004 * math.sin(elapsed / 20.0),
                "longitude": 108.2208 + 0.0004 * math.cos(elapsed / 20.0),
                "speed_kmh": round(speed_kmh, 2),
                "course_deg": round((elapsed * 6.0) % 360.0, 1),
                "is_lost": gps_lost,
                "quality": "tot" if hdop < 1.5 else "kem",
            },
            "imu": {
                "present": True,
                "yaw_rate_deg_s": round(yaw_rate_deg, 2),
                "pitch_deg": round(0.6 * math.sin(elapsed / 3.0), 2),
                "roll_deg": round(0.4 * math.cos(elapsed / 3.5), 2),
                "temperature_c": 38.5,
            },
            "note": "Du lieu gia lap - cam GPS/IMU that thi so nay den tu NMEA va I2C.",
        }


class JetsonTelemetry:
    backend = "jetson"

    def read(self) -> dict[str, Any]:  # pragma: no cover - can phan cung
        return {
            "backend": self.backend,
            "timestamp": time.time(),
            "gps": {"fix": False, "is_lost": True, "quality": "chua noi"},
            "imu": {"present": False},
            "note": (
                "Chua noi driver GPS/IMU that. Can trien khai doc NMEA tu "
                "/dev/ttyTHS1 va IMU qua I2C trong ban tren xe."
            ),
        }


_telemetry: MockTelemetry | JetsonTelemetry | None = None


def get_telemetry() -> MockTelemetry | JetsonTelemetry:
    global _telemetry
    if _telemetry is None:
        _telemetry = MockTelemetry() if settings.is_mock else JetsonTelemetry()
    return _telemetry
