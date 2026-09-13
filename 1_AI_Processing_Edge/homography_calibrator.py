"""
Module: homography_calibrator.py
Mô tả: Module tính toán và chuyển đổi tọa độ từ mặt phẳng ảnh 2D (pixel) sang mặt đất 3D (mét)
       bằng ma trận Homography theo chuẩn Hệ tọa độ xe (Vehicle Coordinate System - VCS)
       tuân thủ tiêu chuẩn ISO 8855 / SAE J670 của dự án BlindGuard AI.

QUY ƯỚC HỆ TỌA ĐỘ XE (VCS - VEHICLE COORDINATE SYSTEM):
- Gốc (0, 0, 0): Tâm trục sau xe đầu kéo (Rear Axle Center), mặt đường Z = 0.
- Trục X (Longitudinal): Hướng dọc thân xe về PHÍA TRƯỚC (X > 0: Phía trước đầu xe, X < 0: Phía sau xe/rơ-moóc).
- Trục Y (Lateral): Hướng ngang thân xe sang BÊN TRÁI (Y > 0: Bên Trái xe, Y < 0: Bên Phải xe).
- Trục Z (Vertical): Hướng đứng lên trời (Up, Z = 0 là mặt đường phẳng).

CÔNG THỨC QUY ĐỔI HOMOGRAPHY (2D PIXEL -> 3D MÉT MẶT ĐẤT Z_vcs = 0):
    [x']       [u]
    [y'] = H * [v]   ===>   X_vcs = x' / w'   (Khoảng cách dọc - Tiến/Lùi)
    [w']       [1]          Y_vcs = y' / w'   (Khoảng cách ngang - Trái(+)/Phải(-))
"""

import json
import time
from pathlib import Path
import cv2
import numpy as np


class HomographyCalibrator:
    def __init__(self, config_path=None):
        self.H = None          # Ma trận Homography Pixel -> Mét (3x3)
        self.H_inv = None      # Ma trận nghịch đảo Mét -> Pixel (3x3)
        self.pts_image = []    # 4 điểm pixel trên ảnh [(u1, v1), ...]
        self.pts_world = []    # 4 điểm VCS mặt đất [(X1_vcs, Y1_vcs), ...] (đơn vị: mét)
        self.image_shape = None
        self.reprojection_error = 0.0
        self.created_at = None
        self.camera_name = "FRONT_CAM"  # Mặc định hoặc 'MIRROR_R', 'MIRROR_L'

        if config_path:
            self.load_from_json(config_path)

    @property
    def is_calibrated(self):
        return self.H is not None and self.H.shape == (3, 3)

    def compute_homography(self, pts_image, pts_world, image_shape=None, camera_name="FRONT_CAM"):
        """
        Tính toán ma trận Homography từ 4 cặp điểm tương ứng.
        :param pts_image: [(u, v), ...] - Tọa độ pixel trên ảnh
        :param pts_world: [(X_vcs, Y_vcs), ...] - Tọa độ mét theo hệ VCS
                          X: Dọc (tiến > 0, lùi < 0)
                          Y: Ngang (trái > 0, phải < 0)
        :param image_shape: (height, width) ảnh gốc
        :param camera_name: Tên camera ('FRONT_CAM', 'MIRROR_R', 'MIRROR_L', ...)
        :return: (H, reprojection_error)
        """
        if len(pts_image) < 4 or len(pts_world) < 4 or len(pts_image) != len(pts_world):
            raise ValueError("Cần ít nhất 4 cặp điểm tương ứng (Pixel và Mét) để tính ma trận Homography!")

        src_pts = np.array(pts_image, dtype=np.float32).reshape(-1, 1, 2)
        dst_pts = np.array(pts_world, dtype=np.float32).reshape(-1, 1, 2)

        method = cv2.RANSAC if len(pts_image) > 4 else 0
        H, mask = cv2.findHomography(src_pts, dst_pts, method)

        if H is None:
            raise RuntimeError("Không thể tìm ma trận Homography (các điểm có thể bị đồng tuyến hoặc suy biến)!")

        self.H = H
        self.H_inv = np.linalg.inv(H)
        self.pts_image = [tuple(map(float, p)) for p in pts_image]
        self.pts_world = [tuple(map(float, p)) for p in pts_world]
        self.image_shape = image_shape
        self.camera_name = camera_name
        self.created_at = time.strftime("%Y-%m-%d %H:%M:%S")

        # Tính sai số tái chiếu trung bình (Mean Reprojection Error - mét)
        projected = cv2.perspectiveTransform(src_pts, self.H)
        errors = np.linalg.norm(projected - dst_pts, axis=2)
        self.reprojection_error = float(np.mean(errors))

        return self.H, self.reprojection_error

    def pixel_to_world(self, u, v):
        """
        Chuyển đổi 1 điểm tọa độ pixel (u, v) sang tọa độ thế giới thực (X_vcs, Y_vcs) theo chuẩn ISO/SAE (mét).
        :return: (X_vcs, Y_vcs, distance_m)
                 X_vcs: Dọc (tiến > 0, lùi < 0)
                 Y_vcs: Ngang (trái > 0, phải < 0)
                 distance_m: Khoảng cách Euclid tới gốc tọa độ
        """
        if not self.is_calibrated:
            raise RuntimeError("Chưa tính toán ma trận Homography!")

        pt = np.array([[[float(u), float(v)]]], dtype=np.float32)
        dst = cv2.perspectiveTransform(pt, self.H)
        x_vcs = float(dst[0][0][0])
        y_vcs = float(dst[0][0][1])
        dist_m = float(np.sqrt(x_vcs**2 + y_vcs**2))
        return x_vcs, y_vcs, dist_m

    def batch_pixel_to_world(self, pts_pixel):
        """
        Chuyển đổi nhiều điểm pixel sang tọa độ mét VCS.
        :param pts_pixel: Mảng hoặc danh sách [(u, v), ...]
        :return: Mảng Nx2 [(X_vcs, Y_vcs), ...]
        """
        if not self.is_calibrated:
            raise RuntimeError("Chưa tính toán ma trận Homography!")

        pts = np.array(pts_pixel, dtype=np.float32).reshape(-1, 1, 2)
        dst = cv2.perspectiveTransform(pts, self.H)
        return dst.reshape(-1, 2)

    def world_to_pixel(self, x_vcs, y_vcs):
        """
        Chiếu ngược từ tọa độ mét VCS (X, Y) ra tọa độ pixel (u, v) trên ảnh.
        :return: (u, v)
        """
        if not self.is_calibrated:
            raise RuntimeError("Chưa tính toán ma trận Homography!")

        pt = np.array([[[float(x_vcs), float(y_vcs)]]], dtype=np.float32)
        dst = cv2.perspectiveTransform(pt, self.H_inv)
        u = float(dst[0][0][0])
        v = float(dst[0][0][1])
        return u, v

    def save_to_json(self, filepath, metadata=None):
        """Lưu ma trận và metadata theo chuẩn cấu hình hệ thống BlindGuard AI"""
        if not self.is_calibrated:
            raise RuntimeError("Chưa có ma trận Homography để lưu!")

        data = {
            "created_at": self.created_at or time.strftime("%Y-%m-%d %H:%M:%S"),
            "camera_name": self.camera_name,
            "coordinate_system": {
                "standard": "ISO 8855 / SAE J670 (Vehicle Coordinate System - VCS)",
                "unit": "meter",
                "axis_x": "Longitudinal (Forward > 0, Rearward < 0)",
                "axis_y": "Lateral (Left > 0, Right < 0)",
                "axis_z": "Vertical (Upward > 0, Ground Z = 0)",
                "origin": "Tractor Rear Axle Center"
            },
            "homography_matrix_pixel_to_vcs": self.H.tolist(),
            "homography_matrix_vcs_to_pixel": self.H_inv.tolist(),
            "points_image_pixel": self.pts_image,
            "points_world_vcs_meter": self.pts_world,
            "reprojection_error_meters": self.reprojection_error,
            "image_shape": list(self.image_shape) if self.image_shape else None
        }
        if metadata and isinstance(metadata, dict):
            data["metadata"] = metadata

        target = Path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"[+] Đã lưu cấu hình Homography chuẩn VCS tại: {target.resolve()}")
        return str(target.resolve())

    def load_from_json(self, filepath):
        """Đọc ma trận và cấu hình từ file JSON"""
        target = Path(filepath)
        if not target.is_file():
            raise FileNotFoundError(f"Không tìm thấy file cấu hình: {filepath}")

        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Hỗ trợ cả key chuẩn mới và key cũ
        h_key = "homography_matrix_pixel_to_vcs" if "homography_matrix_pixel_to_vcs" in data else "homography_matrix_pixel_to_meter"
        h_inv_key = "homography_matrix_vcs_to_pixel" if "homography_matrix_vcs_to_pixel" in data else "homography_matrix_meter_to_pixel"
        pts_w_key = "points_world_vcs_meter" if "points_world_vcs_meter" in data else "points_world_meter"

        self.H = np.array(data[h_key], dtype=np.float64)
        self.H_inv = np.array(data[h_inv_key], dtype=np.float64)
        self.pts_image = [tuple(p) for p in data.get("points_image_pixel", [])]
        self.pts_world = [tuple(p) for p in data.get(pts_w_key, [])]
        self.reprojection_error = float(data.get("reprojection_error_meters", 0.0))
        self.image_shape = tuple(data["image_shape"]) if data.get("image_shape") else None
        self.created_at = data.get("created_at")
        self.camera_name = data.get("camera_name", "FRONT_CAM")
        print(f"[+] Đã nạp thành công ma trận Homography VCS từ: {target.resolve()} (Sai số: {self.reprojection_error:.4f}m)")
        return self
