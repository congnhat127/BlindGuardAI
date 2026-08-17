"""Nguon khung hinh camera: gia lap hoac phan cung that.

Frontend chi biet den hai endpoint `/snapshot` va `/stream`. Doi tu che do mock
sang che do jetson chi la doi bien moi truong BLINDGUARD_DEVICE_BACKEND.
"""

from __future__ import annotations

import time
from typing import Iterator, Protocol

from ..core.settings import settings
from ..domain.schemas import VehicleProfile
from . import scene


class CameraSource(Protocol):
    backend: str

    def snapshot(self, profile: VehicleProfile, camera_id: str) -> bytes: ...

    def status(self, profile: VehicleProfile) -> list[dict]: ...

    def release(self) -> None: ...


class MockCameraSource:
    """Sinh anh tu mo hinh camera - dung khi chua co phan cung."""

    backend = "mock"

    def __init__(self) -> None:
        self._t0 = time.monotonic()

    def snapshot(self, profile: VehicleProfile, camera_id: str, animate: bool = False) -> bytes:
        tick = (time.monotonic() - self._t0) if animate else 0.0
        image = scene.render_frame(profile, camera_id, tick=tick, show_actor=True)
        return scene.encode_jpeg(image, settings.jpeg_quality)

    def status(self, profile: VehicleProfile) -> list[dict]:
        rows = []
        for camera_id, camera in profile.cameras.items():
            rows.append(
                {
                    "camera_id": camera_id,
                    "label": camera.label,
                    "enabled": camera.enabled,
                    "online": True,
                    "backend": self.backend,
                    "resolution": [camera.width, camera.height],
                    "source": camera.source or "mock://synthetic",
                    "fps": settings.stream_fps,
                    "message": "Khung hình mô phỏng, dựng từ đúng mô hình camera thật.",
                }
            )
        return rows

    def release(self) -> None:
        return None


class JetsonCameraSource:
    """Doc camera that qua OpenCV. Chi khoi tao khi thuc su can."""

    backend = "jetson"

    def __init__(self) -> None:
        self._captures: dict[str, object] = {}
        try:
            import cv2  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Che do jetson can opencv-python-headless. "
                "Cai bang: pip install opencv-python-headless"
            ) from exc

    def _capture(self, camera_id: str, source: str):
        import cv2

        if camera_id in self._captures:
            return self._captures[camera_id]
        target: object = source
        if source.isdigit():
            target = int(source)
        capture = cv2.VideoCapture(target)
        if not capture.isOpened():
            raise RuntimeError(f"Không mở được camera {camera_id} tại nguồn {source!r}")
        self._captures[camera_id] = capture
        return capture

    def snapshot(self, profile: VehicleProfile, camera_id: str, animate: bool = False) -> bytes:
        import cv2

        camera = profile.cameras[camera_id]
        if not camera.source:
            raise RuntimeError(f"Camera {camera_id} chưa khai báo nguồn (RTSP hoặc số USB).")
        capture = self._capture(camera_id, camera.source)
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"Không đọc được khung hình từ camera {camera_id}.")
        frame = cv2.resize(frame, (camera.width, camera.height))
        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, settings.jpeg_quality])
        if not ok:
            raise RuntimeError("Mã hoá JPEG thất bại.")
        return encoded.tobytes()

    def status(self, profile: VehicleProfile) -> list[dict]:
        rows = []
        for camera_id, camera in profile.cameras.items():
            online, message = False, ""
            if not camera.source:
                message = "Chưa khai báo nguồn."
            else:
                try:
                    self._capture(camera_id, camera.source)
                    online, message = True, "Kết nối được."
                except Exception as exc:
                    message = str(exc)
            rows.append(
                {
                    "camera_id": camera_id,
                    "label": camera.label,
                    "enabled": camera.enabled,
                    "online": online,
                    "backend": self.backend,
                    "resolution": [camera.width, camera.height],
                    "source": camera.source,
                    "fps": settings.stream_fps,
                    "message": message,
                }
            )
        return rows

    def release(self) -> None:
        for capture in self._captures.values():
            try:
                capture.release()  # type: ignore[attr-defined]
            except Exception:
                pass
        self._captures.clear()


_source: CameraSource | None = None


def get_camera_source() -> CameraSource:
    global _source
    if _source is None:
        _source = MockCameraSource() if settings.is_mock else JetsonCameraSource()
    return _source


BOUNDARY = "blindguardframe"


def mjpeg_stream(profile: VehicleProfile, camera_id: str) -> Iterator[bytes]:
    """Luong MJPEG: don gian, khong signaling, chay tren moi trinh duyet."""
    source = get_camera_source()
    interval = 1.0 / max(1, settings.stream_fps)
    while True:
        started = time.monotonic()
        try:
            payload = source.snapshot(profile, camera_id, animate=True)  # type: ignore[call-arg]
        except Exception:
            break
        yield (
            f"--{BOUNDARY}\r\nContent-Type: image/jpeg\r\n"
            f"Content-Length: {len(payload)}\r\n\r\n".encode()
            + payload
            + b"\r\n"
        )
        elapsed = time.monotonic() - started
        if elapsed < interval:
            time.sleep(interval - elapsed)
