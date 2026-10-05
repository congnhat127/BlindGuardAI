"""
Module: homography_manager.py
Vị trí: BlindGuard_App/core/homography_manager.py
Mô tả: Quản lý ma trận Homography chuyển đổi Pixel -> Mét mặt đất VCS ISO 8855
       cho cả 4 góc Camera của xe tải nặng.

Ghi chú tính đúng đắn:
- Nếu config có >= 4 cặp điểm mốc, ma trận H được TÍNH LẠI từ điểm mốc và H_inv = inv(H)
  để đảm bảo hai chiều chiếu luôn nhất quán (tránh ma trận nhập tay sai lệch).
- Homography gắn với độ phân giải lúc hiệu chuẩn (image_shape). Khi khung hình đầu vào có
  độ phân giải khác, tọa độ pixel được tự động quy đổi tỉ lệ (set_frame_size).
- Điểm nằm trên đường chân trời / sau camera (mẫu số w' <= 0) bị loại (trả về None).
"""

import numpy as np
import cv2
from typing import Optional, Tuple, Dict, List

DEFAULT_CALIB_SHAPE = (720, 1280)  # (h, w)
MAX_GROUND_RANGE_M = 60.0


class MultiCameraHomographyManager:
    """Quản lý và tính toán ma trận Homography cho 4 góc camera"""

    CAMERA_KEYS = ["MIRROR_RIGHT", "MIRROR_LEFT", "CAB_FRONT", "REAR_TRAILER"]

    def __init__(self, config_manager=None, default_camera: str = "MIRROR_RIGHT"):
        self.config_manager = config_manager
        self.active_camera = default_camera
        self.H_matrices: Dict[str, np.ndarray] = {}
        self.H_inv_matrices: Dict[str, np.ndarray] = {}
        self.calib_shapes: Dict[str, Tuple[int, int]] = {}
        self.reproj_errors: Dict[str, float] = {}
        self.frame_size: Optional[Tuple[int, int]] = None  # (w, h) của khung hình hiện tại
        self.load_from_config()

    def load_from_config(self):
        if not self.config_manager:
            return

        cameras_data = self.config_manager.data.get("cameras", {})
        for cam_key, c_info in cameras_data.items():
            shape = c_info.get("image_shape") or DEFAULT_CALIB_SHAPE
            self.calib_shapes[cam_key] = (int(shape[0]), int(shape[1]))

            pts_px = c_info.get("points_pixel") or []
            pts_vcs = c_info.get("points_vcs_meter") or []
            H = None
            if len(pts_px) >= 4 and len(pts_px) == len(pts_vcs):
                H, err = self.compute_homography_from_points(pts_px, pts_vcs)
                if H is not None:
                    self.reproj_errors[cam_key] = err

            if H is None:
                h_raw = c_info.get("homography_matrix_pixel_to_vcs")
                if h_raw and len(h_raw) == 3:
                    H = np.array(h_raw, dtype=np.float64)

            if H is None:
                continue
            try:
                H_inv = np.linalg.inv(H)
            except np.linalg.LinAlgError:
                continue
            self.H_matrices[cam_key] = H
            self.H_inv_matrices[cam_key] = H_inv

    def set_active_camera(self, cam_key: str):
        if cam_key in self.CAMERA_KEYS:
            self.active_camera = cam_key

    def set_frame_size(self, width: int, height: int):
        """Khai báo độ phân giải khung hình đầu vào để quy đổi về độ phân giải hiệu chuẩn."""
        self.frame_size = (int(width), int(height))

    def _scale_factors(self) -> Tuple[float, float]:
        """Hệ số (sx, sy): pixel_calib = pixel_frame * s"""
        if self.frame_size is None:
            return 1.0, 1.0
        ch, cw = self.calib_shapes.get(self.active_camera, DEFAULT_CALIB_SHAPE)
        fw, fh = self.frame_size
        return cw / max(1, fw), ch / max(1, fh)

    def resolution_mismatch(self) -> bool:
        if self.frame_size is None:
            return False
        sx, sy = self._scale_factors()
        return abs(sx - 1.0) > 1e-3 or abs(sy - 1.0) > 1e-3

    def aspect_mismatch(self) -> bool:
        sx, sy = self._scale_factors()
        return abs(sx - sy) / max(sx, sy) > 0.02

    @property
    def is_calibrated(self) -> bool:
        return self.active_camera in self.H_matrices

    def pixel_to_world(self, u: float, v: float) -> Optional[Tuple[float, float, float]]:
        """
        Chuyển đổi 1 điểm (u, v) trên khung hình hiện tại sang tọa độ xe VCS (X, Y, khoảng cách mét).
        Trả về None nếu điểm nằm trên/ngoài đường chân trời hoặc quá xa (không tin cậy).
        """
        sx, sy = self._scale_factors()
        u_c, v_c = u * sx, v * sy

        if not self.is_calibrated:
            # Fallback xấp xỉ thô (chưa hiệu chuẩn)
            ch, cw = self.calib_shapes.get(self.active_camera, DEFAULT_CALIB_SHAPE)
            x = 3.0 + 8.0 * max(0.0, 1.0 - v_c / ch)
            y = (u_c / cw - 0.5) * 5.0
            return float(x), float(y), float((x ** 2 + y ** 2) ** 0.5)

        H = self.H_matrices[self.active_camera]
        denom = H[2, 0] * u_c + H[2, 1] * v_c + H[2, 2]
        if denom <= 1e-9:
            return None

        x_vcs = float((H[0, 0] * u_c + H[0, 1] * v_c + H[0, 2]) / denom)
        y_vcs = float((H[1, 0] * u_c + H[1, 1] * v_c + H[1, 2]) / denom)
        dist_m = float((x_vcs ** 2 + y_vcs ** 2) ** 0.5)
        if not np.isfinite(dist_m) or dist_m > MAX_GROUND_RANGE_M:
            return None
        return x_vcs, y_vcs, dist_m

    def world_to_pixel(self, x: float, y: float) -> Optional[Tuple[float, float]]:
        """Chiếu ngược từ tọa độ mét VCS sang pixel khung hình hiện tại. None nếu điểm sau camera."""
        if self.active_camera not in self.H_inv_matrices:
            return None

        H_inv = self.H_inv_matrices[self.active_camera]
        denom = H_inv[2, 0] * x + H_inv[2, 1] * y + H_inv[2, 2]
        if denom <= 1e-9:
            return None

        u_c = (H_inv[0, 0] * x + H_inv[0, 1] * y + H_inv[0, 2]) / denom
        v_c = (H_inv[1, 0] * x + H_inv[1, 1] * y + H_inv[1, 2]) / denom
        sx, sy = self._scale_factors()
        return float(u_c / sx), float(v_c / sy)

    def visible_ground_polygon(self, width: int, height: int, step: int = 8) -> Optional[List[Tuple[float, float]]]:
        """
        Vùng mặt đất (VCS) mà camera hiện tại nhìn thấy hợp lệ: từ đáy ảnh lên tới hàng pixel cao nhất
        còn chiếu được (dưới chân trời và trong phạm vi MAX_GROUND_RANGE_M).
        """
        if not self.is_calibrated:
            return None
        v_top = None
        for v in range(height - 1, -1, -step):
            l = self.pixel_to_world(0, v)
            r = self.pixel_to_world(width - 1, v)
            if l is None or r is None:
                break
            v_top = v
        if v_top is None or v_top >= height - 1:
            return None
        corners = [(0, height - 1), (width - 1, height - 1), (width - 1, v_top), (0, v_top)]
        pts = []
        for u, v in corners:
            p = self.pixel_to_world(u, v)
            if p is None:
                return None
            pts.append((p[0], p[1]))
        return pts

    @staticmethod
    def compute_homography_from_points(pts_pixel: List[Tuple[float, float]], pts_vcs: List[Tuple[float, float]]) -> Tuple[Optional[np.ndarray], float]:
        """
        Tính ma trận Homography và sai số tái chiếu trung bình (mét).
        Lưu ý: với đúng 4 điểm, nghiệm luôn khớp tuyệt đối (sai số ~0) nên con số này KHÔNG
        phản ánh độ chính xác thực. Cần >= 5 điểm để sai số có ý nghĩa kiểm chứng.
        """
        if len(pts_pixel) < 4 or len(pts_vcs) < 4 or len(pts_pixel) != len(pts_vcs):
            return None, 999.0

        src = np.array(pts_pixel, dtype=np.float64).reshape(-1, 1, 2)
        dst = np.array(pts_vcs, dtype=np.float64).reshape(-1, 1, 2)

        H, _ = cv2.findHomography(src, dst, 0)
        if H is None or not np.all(np.isfinite(H)):
            return None, 999.0

        projected = cv2.perspectiveTransform(src, H)
        errors = np.linalg.norm(projected - dst, axis=2)
        mean_err = float(np.mean(errors))
        return H, round(mean_err, 4)
