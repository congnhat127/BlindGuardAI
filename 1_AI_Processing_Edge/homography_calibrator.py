"""
Module: homography_calibrator.py
Mô tả: Module tính toán và chuyển đổi tọa độ từ mặt phẳng ảnh 2D (pixel) sang mặt đất thế giới thực 3D (mét)
       bằng ma trận Homography (Z_w = 0).

Hệ tọa độ xe (Vehicle / Camera Ground Frame):
- Trục Y (m): Khoảng cách dọc về phía trước tính từ camera (Longitudinal distance, Y > 0)
- Trục X (m): Khoảng cách ngang tính từ tâm camera (Lateral distance, X < 0: bên trái, X > 0: bên phải)
- Khoảng cách tổng thể: D = sqrt(X^2 + Y^2) (m)
"""

import json
import time
from pathlib import Path
import cv2
import numpy as np


class HomographyCalibrator:
    def __init__(self, config_path=None):
        self.H = None          # Ma trận chuyển đổi 2D Pixel -> 3D Mét (3x3)
        self.H_inv = None      # Ma trận nghịch đảo 3D Mét -> 2D Pixel (3x3)
        self.pts_image = []    # 4 điểm pixel trên ảnh [(u1, v1), ...]
        self.pts_world = []    # 4 điểm thực tế [(X1, Y1), ...] (đơn vị: mét)
        self.image_shape = None
        self.reprojection_error = 0.0
        self.created_at = None

        if config_path:
            self.load_from_json(config_path)

    @property
    def is_calibrated(self):
        return self.H is not None and self.H.shape == (3, 3)

    def compute_homography(self, pts_image, pts_world, image_shape=None):
        """
        Tính toán ma trận Homography từ các cặp điểm tương ứng.
        :param pts_image: Danh sách ít nhất 4 điểm pixel: [(u, v), ...]
        :param pts_world: Danh sách ít nhất 4 điểm thực tế: [(X, Y), ...] đơn vị mét
        :param image_shape: (height, width) của ảnh gốc
        :return: (H, reprojection_error)
        """
        if len(pts_image) < 4 or len(pts_world) < 4 or len(pts_image) != len(pts_world):
            raise ValueError("Cần ít nhất 4 cặp điểm tương ứng để tính ma trận Homography!")

        src_pts = np.array(pts_image, dtype=np.float32).reshape(-1, 1, 2)
        dst_pts = np.array(pts_world, dtype=np.float32).reshape(-1, 1, 2)

        # Tính ma trận H: Pixel -> Mét
        method = cv2.RANSAC if len(pts_image) > 4 else 0
        H, mask = cv2.findHomography(src_pts, dst_pts, method)

        if H is None:
            raise RuntimeError("Không thể tìm ma trận Homography (các điểm có thể bị suy biến hoặc đồng tuyến)!")

        self.H = H
        self.H_inv = np.linalg.inv(H)
        self.pts_image = [tuple(map(float, p)) for p in pts_image]
        self.pts_world = [tuple(map(float, p)) for p in pts_world]
        self.image_shape = image_shape
        self.created_at = time.strftime("%Y-%m-%d %H:%M:%S")

        # Tính sai số tái chiếu trung bình (Mean Reprojection Error - mét)
        projected = cv2.perspectiveTransform(src_pts, self.H)
        errors = np.linalg.norm(projected - dst_pts, axis=2)
        self.reprojection_error = float(np.mean(errors))

        return self.H, self.reprojection_error

    def pixel_to_world(self, u, v):
        """
        Chuyển đổi 1 điểm tọa độ pixel (u, v) sang tọa độ thế giới thực (X, Y) tính bằng mét.
        :return: (X_m, Y_m, distance_m)
        """
        if not self.is_calibrated:
            raise RuntimeError("Chưa tính toán ma trận Homography!")

        pt = np.array([[[float(u), float(v)]]], dtype=np.float32)
        dst = cv2.perspectiveTransform(pt, self.H)
        x_m = float(dst[0][0][0])
        y_m = float(dst[0][0][1])
        dist_m = float(np.sqrt(x_m**2 + y_m**2))
        return x_m, y_m, dist_m

    def batch_pixel_to_world(self, pts_pixel):
        """
        Chuyển đổi danh sách nhiều điểm pixel sang tọa độ mét.
        :param pts_pixel: Mảng hoặc list [(u, v), ...]
        :return: Mảng Nx2 chứa tọa độ [(X_m, Y_m), ...]
        """
        if not self.is_calibrated:
            raise RuntimeError("Chưa tính toán ma trận Homography!")

        pts = np.array(pts_pixel, dtype=np.float32).reshape(-1, 1, 2)
        dst = cv2.perspectiveTransform(pts, self.H)
        return dst.reshape(-1, 2)

    def world_to_pixel(self, x_m, y_m):
        """
        Chiếu ngược tọa độ thực tế (X, Y) mét về tọa độ pixel (u, v) trên ảnh.
        :return: (u, v) là float hoặc int
        """
        if not self.is_calibrated:
            raise RuntimeError("Chưa tính toán ma trận Homography!")

        pt = np.array([[[float(x_m), float(y_m)]]], dtype=np.float32)
        dst = cv2.perspectiveTransform(pt, self.H_inv)
        u = float(dst[0][0][0])
        v = float(dst[0][0][1])
        return u, v

    def generate_ground_grid_lines(self, x_range=(-4.0, 4.0), y_range=(1.0, 15.0), step_x=1.0, step_y=1.0, num_samples=30):
        """
        Tạo các đoạn thẳng lưới ô cờ 3D trên mặt đất (mỗi ô 1m x 1m) và chiếu ngược lên tọa độ pixel ảnh.
        Dùng để vẽ trực quan phối cảnh mặt đất trên ảnh.
        :return: Danh sách các đoạn thẳng pixel [ [(u1, v1), (u2, v2), ...], ... ]
        """
        if not self.is_calibrated:
            return []

        grid_polylines = []
        min_x, max_x = x_range
        min_y, max_y = y_range

        # 1. Các đường ngang (cách camera theo trục Y, mỗi đường cách nhau step_y mét)
        y_vals = np.arange(min_y, max_y + 0.1, step_y)
        for y in y_vals:
            xs = np.linspace(min_x, max_x, num_samples)
            line_pts_world = np.stack([xs, np.full_like(xs, y)], axis=1).reshape(-1, 1, 2).astype(np.float32)
            pts_img = cv2.perspectiveTransform(line_pts_world, self.H_inv).reshape(-1, 2)
            grid_polylines.append((pts_img, f"{y:.0f}m"))

        # 2. Các đường dọc (song song hướng nhìn xe, mỗi đường cách nhau step_x mét)
        x_vals = np.arange(min_x, max_x + 0.1, step_x)
        for x in x_vals:
            ys = np.linspace(min_y, max_y, num_samples)
            line_pts_world = np.stack([np.full_like(ys, x), ys], axis=1).reshape(-1, 1, 2).astype(np.float32)
            pts_img = cv2.perspectiveTransform(line_pts_world, self.H_inv).reshape(-1, 2)
            grid_polylines.append((pts_img, f"{x:+.0f}m" if x != 0 else "0m"))

        return grid_polylines

    def save_to_json(self, filepath, metadata=None):
        """Lưu ma trận và cấu hình ra file JSON"""
        if not self.is_calibrated:
            raise RuntimeError("Chưa có ma trận Homography để lưu!")

        data = {
            "created_at": self.created_at or time.strftime("%Y-%m-%d %H:%M:%S"),
            "homography_matrix_pixel_to_meter": self.H.tolist(),
            "homography_matrix_meter_to_pixel": self.H_inv.tolist(),
            "points_image_pixel": self.pts_image,
            "points_world_meter": self.pts_world,
            "reprojection_error_meters": self.reprojection_error,
            "image_shape": list(self.image_shape) if self.image_shape else None,
            "coordinate_system": {
                "unit": "meter",
                "axis_x": "Lateral (Left < 0, Right > 0)",
                "axis_y": "Longitudinal (Forward > 0)",
                "origin": "Camera Ground Projection (X=0, Y=0)"
            }
        }
        if metadata and isinstance(metadata, dict):
            data["metadata"] = metadata

        target = Path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"[+] Đã lưu cấu hình Homography thành công tại: {target.resolve()}")
        return str(target.resolve())

    def load_from_json(self, filepath):
        """Đọc ma trận và cấu hình từ file JSON"""
        target = Path(filepath)
        if not target.is_file():
            raise FileNotFoundError(f"Không tìm thấy file cấu hình: {filepath}")

        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.H = np.array(data["homography_matrix_pixel_to_meter"], dtype=np.float64)
        self.H_inv = np.array(data["homography_matrix_meter_to_pixel"], dtype=np.float64)
        self.pts_image = [tuple(p) for p in data.get("points_image_pixel", [])]
        self.pts_world = [tuple(p) for p in data.get("points_world_meter", [])]
        self.reprojection_error = float(data.get("reprojection_error_meters", 0.0))
        self.image_shape = tuple(data["image_shape"]) if data.get("image_shape") else None
        self.created_at = data.get("created_at")
        print(f"[+] Đã nạp thành công ma trận Homography từ: {target.resolve()} (Sai số: {self.reprojection_error:.3f}m)")
        return self

