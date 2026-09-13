# ==============================================================================
# CAMERA_CALIBRATION.PY: HIỆU CHUẨN GIAO THOA VÀ CHIẾU PHỐI CẢNH 3D-TO-2D
# Bám sát Phần 2 và Phần 6 trong Tài liệu Hướng dẫn Kỹ thuật VEDC 2026
# ==============================================================================

import math
import numpy as np
import config

class CameraCalibrator:
    """
    [PHẦN 2 TÀI LIỆU]: Ma trận Nội tại (K), Ngoại tại [R|T] và Khử méo Ống kính.
    [PHẦN 6 TÀI LIỆU]: Chiếu Perspective (3D-to-2D) theo công thức s * m = K * [R|T] * M
    """
    def __init__(self):
        self.K = config.K_CAMERA

    def get_rotation_matrix_3d(self, pitch_deg: float, yaw_deg: float, roll_deg: float = 0.0) -> np.ndarray:
        """
        Tạo Ma trận Xoay 3D (R) từ các góc Pitch, Yaw, Roll chuẩn OpenCV Camera Frame -> VCS.
        """
        p = math.radians(pitch_deg)
        y = math.radians(yaw_deg)
        r = math.radians(roll_deg)

        # Ma trận cơ sở: OpenCV Cam (X-Right, Y-Down, Z-Forward) -> VCS (X-Forward, Y-Left, Z-Up)
        R0 = np.array([
            [ 0,  0, 1],
            [-1,  0, 0],
            [ 0, -1, 0]
        ])

        # Xoay Yaw (quanh trục Z xe)
        Rz = np.array([
            [math.cos(y), -math.sin(y), 0],
            [math.sin(y),  math.cos(y), 0],
            [0,            0,           1]
        ])

        # Xoay Pitch (nghiêng ống kính)
        Rx = np.array([
            [1, 0, 0],
            [0, math.cos(p), -math.sin(p)],
            [0, math.sin(p),  math.cos(p)]
        ])

        return Rz @ R0 @ Rx

    def project_3d_ground_point_to_2d_image(self, point_3d_vcs: tuple, camera_name: str) -> tuple:
        """
        [PHẦN 6 TÀI LIỆU]: Công thức s * m = K * [R|T] * M
        Chiếu 1 điểm 3D từ mặt đất (X_vcs, Y_vcs, Z_vcs=0) lên khung hình Camera 2D (u, v).
        """
        if camera_name not in config.CAMERAS_EXTRINSICS:
            raise ValueError(f"Không tìm thấy cấu hình camera: {camera_name}")

        cam_cfg = config.CAMERAS_EXTRINSICS[camera_name]
        T_cam = cam_cfg["position"] # [tx, ty, tz]
        R_cam = self.get_rotation_matrix_3d(cam_cfg["pitch_deg"], cam_cfg["yaw_deg"])

        # Tọa độ 3D trong hệ Ego-Vehicle (VCS)
        M_3d = np.array([point_3d_vcs[0], point_3d_vcs[1], point_3d_vcs[2] if len(point_3d_vcs) > 2 else 0.0])

        # Chuyển sang hệ tọa độ Camera: M_cam = R^T * (M_3d - T_cam)
        M_cam = R_cam.T @ (M_3d - T_cam)

        # Trục Z_cam phải > 0 (vật thể phải ở phía trước ống kính camera)
        if M_cam[2] <= 0.1:
            return None # Nằm phía sau ống kính

        # Chiếu qua Ma trận Nội tại K: s * m = K * M_cam
        m_homo = self.K @ M_cam
        u = m_homo[0] / m_homo[2]
        v = m_homo[1] / m_homo[2]

        return (int(u), int(v))

    def project_2d_image_point_to_3d_ground(self, u: float, v: float, camera_name: str) -> tuple:
        """
        [CHIẾU NGƯỢC HOMOGRAPHY 2D-TO-3D]:
        Chuyển đổi từ tọa độ Pixel bàn chân đối tượng (u, v) trên khung ảnh camera
        ra tọa độ thực mét (X_vcs, Y_vcs, Z_vcs=0) trên mặt đường trong hệ VCS.
        """
        if camera_name not in config.CAMERAS_EXTRINSICS:
            raise ValueError(f"Không tìm thấy cấu hình camera: {camera_name}")

        cam_cfg = config.CAMERAS_EXTRINSICS[camera_name]
        T_cam = np.array(cam_cfg["position"]) # [tx, ty, tz]
        R_cam = self.get_rotation_matrix_3d(cam_cfg["pitch_deg"], cam_cfg["yaw_deg"])

        # Vector tia nhìn trong hệ tọa độ Camera: v_cam = K^(-1) * [u, v, 1]^T
        m_pixel = np.array([u, v, 1.0])
        v_cam = np.linalg.inv(self.K) @ m_pixel

        # Chuyển vector hướng tia nhìn sang hệ tọa độ xe VCS: v_vcs = R_cam * v_cam
        v_vcs = R_cam @ v_cam

        # Giao điểm với mặt phẳng mặt đường Z_vcs = 0:
        # T_cam[2] + lambda * v_vcs[2] = 0  =>  lambda = -T_cam[2] / v_vcs[2]
        if abs(v_vcs[2]) < 1e-5:
            return None # Tia song song mặt đường

        lmbda = -T_cam[2] / v_vcs[2]
        if lmbda <= 0:
            return None # Điểm hướng lên trời

        X_vcs = T_cam[0] + lmbda * v_vcs[0]
        Y_vcs = T_cam[1] + lmbda * v_vcs[1]

        return (float(X_vcs), float(Y_vcs))
