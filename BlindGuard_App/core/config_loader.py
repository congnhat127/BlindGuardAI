"""
Module: config_loader.py
Vị trí: BlindGuard_App/core/config_loader.py
Mô tả: Quản lý nạp, cập nhật và lưu trữ cấu hình hệ thống BlindGuard AI
       (Thông số kích thước xe và ma trận Homography của 4 Camera).
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "system_config.json"


class SystemConfigManager:
    """Quản lý toàn bộ cấu hình Xe và 4 Camera điểm mù"""

    CAMERA_KEYS = ["MIRROR_RIGHT", "MIRROR_LEFT", "CAB_FRONT", "REAR_TRAILER"]

    CAMERA_LABELS = {
        "MIRROR_RIGHT": "Camera Gương Phụ (Hông phải)",
        "MIRROR_LEFT": "Camera Gương Lái (Hông trái)",
        "CAB_FRONT": "Camera Mũi Xe (Cản trước)",
        "REAR_TRAILER": "Camera Đuôi Xe (Điểm mù lùi)"
    }

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        if not self.config_path.is_file():
            raise FileNotFoundError(f"Không tìm thấy file cấu hình tại: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        return self.data

    def save(self, filepath: Optional[Path] = None):
        target = Path(filepath) if filepath else self.config_path
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)
        print(f"[Config] Đã lưu cấu hình thành công tại: {target.resolve()}")

    # --- Quản lý thông số xe ---
    @property
    def vehicle_profile(self) -> Dict[str, Any]:
        return self.data.get("vehicle_profile", {})

    def update_vehicle_profile(self, profile: Dict[str, Any]):
        self.data["vehicle_profile"] = profile

    # --- Quản lý Camera & Homography ---
    @property
    def selected_camera(self) -> str:
        return self.data.get("selected_camera", "MIRROR_RIGHT")

    @selected_camera.setter
    def selected_camera(self, cam_key: str):
        if cam_key in self.CAMERA_KEYS:
            self.data["selected_camera"] = cam_key

    def get_camera_config(self, cam_key: Optional[str] = None) -> Dict[str, Any]:
        key = cam_key or self.selected_camera
        return self.data.get("cameras", {}).get(key, {})

    def update_camera_config(self, cam_key: str, cam_data: Dict[str, Any]):
        if "cameras" not in self.data:
            self.data["cameras"] = {}
        self.data["cameras"][cam_key] = cam_data
