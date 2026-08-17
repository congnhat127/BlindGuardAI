"""Cau hinh chay cua backend."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BLINDGUARD_", env_file=".env", extra="ignore")

    # mock  = khong can camera / GPS, sinh du lieu gia lap (mac dinh khi phat trien)
    # jetson = doc camera va GPS that tren xe
    device_backend: Literal["mock", "jetson"] = "mock"

    data_dir: Path = BACKEND_DIR / "data"
    static_dir: Path = BACKEND_DIR / "static"

    host: str = "0.0.0.0"
    port: int = 8080

    # Bat CORS cho Vite dev server. Tren xe khong can (SPA duoc serve cung goc).
    dev_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Ma PIN bao ve cau hinh. De trong = khong yeu cau (chi dung khi phat trien).
    setup_pin: str = ""

    stream_fps: int = 8
    jpeg_quality: int = 82

    @property
    def is_mock(self) -> bool:
        return self.device_backend == "mock"


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
