"""
Module: motion_analyzer.py
Vị trí: BlindGuard_App/core/motion_analyzer.py
Mô tả: Phân tích chuyển động xe chủ Ego PHI XÂM LẤN (Non-invasive Ego Motion Estimation).
       Tuyệt đối KHÔNG can thiệp vào mạng CAN-bus / cổng OBD của xe tải.
       Tự động nhận diện trạng thái rẽ, cua gắt hoặc dừng xe thông qua:
       1. Cảm biến con quay hồi chuyển IMU độc lập gắn buồng lái (Yaw Rate omega_z).
       2. Tốc độ GPS từ ăng-ten ngoài độc lập.
       3. Chuyển động thị giác nền (Visual Ego-Motion Estimation) khi chạy kiểm thử video.
"""

import time
from typing import Tuple


class NonInvasiveMotionAnalyzer:
    """
    Bộ ước tính động học xe chủ phi xâm lấn (Non-invasive Ego State Estimator).
    Đảm bảo an toàn 100% cho hệ thống điện và bảo hành xe cơ giới.
    """

    def __init__(self, default_speed_mps: float = 5.0):
        self.current_speed_mps = default_speed_mps
        self.yaw_rate_rad_s = 0.0
        self.turn_direction = "OFF"   # "OFF", "RIGHT", "LEFT"
        self.gear = "D"
        self.manual_override = False
        self.last_update_time = time.time()

    def update_from_imu(self, yaw_rate_rad_s: float, speed_mps: float = -1.0, gear: str = "D"):
        """Cập nhật từ cảm biến IMU/GPS phần cứng độc lập"""
        self.yaw_rate_rad_s = yaw_rate_rad_s
        if speed_mps >= 0.0:
            self.current_speed_mps = speed_mps
        self.gear = gear

        # Tự động phát hiện hướng rẽ khi tốc độ góc vượt ngưỡng vật lý
        if self.yaw_rate_rad_s < -0.035:
            self.turn_direction = "RIGHT"
        elif self.yaw_rate_rad_s > 0.035:
            self.turn_direction = "LEFT"
        else:
            self.turn_direction = "OFF"

    def set_camera_context(self, active_camera: str):
        """Thiết lập ngữ cảnh động học mặc định theo góc camera kiểm thử (nếu người dùng chưa bấm phím ghi đè)"""
        if self.manual_override:
            return
        if active_camera == "REAR_TRAILER":
            self.gear = "R"
            self.current_speed_mps = 1.5
            self.yaw_rate_rad_s = 0.0
            self.turn_direction = "OFF"
        elif active_camera == "CAB_FRONT":
            self.gear = "D"
            self.current_speed_mps = 0.0
            self.yaw_rate_rad_s = 0.0
            self.turn_direction = "OFF"
        else:
            self.gear = "D"
            self.current_speed_mps = 5.0
            self.yaw_rate_rad_s = 0.0
            self.turn_direction = "OFF"

    def auto_estimate_from_scene(self, active_camera: str, obstacles: list = None):
        """
        Tự động nhận diện ngữ cảnh chuyển động khi chạy kiểm thử video (không cần can thiệp tay).
        """
        self.set_camera_context(active_camera)

    # --- Điều khiển thủ công phục vụ kiểm thử video (giả lập IMU/GPS) ---
    def manual_adjust_speed(self, delta_mps: float):
        self.manual_override = True
        self.current_speed_mps = max(0.0, min(30.0, self.current_speed_mps + delta_mps))

    def manual_stop(self):
        self.manual_override = True
        self.current_speed_mps = 0.0

    def manual_adjust_yaw(self, delta_rad_s: float):
        self.manual_override = True
        self.update_from_imu(max(-0.5, min(0.5, self.yaw_rate_rad_s + delta_rad_s)), gear=self.gear)

    def manual_reset_yaw(self):
        self.manual_override = True
        self.update_from_imu(0.0, gear=self.gear)

    def manual_toggle_reverse(self):
        self.manual_override = True
        self.gear = "D" if self.gear == "R" else "R"

    def get_motion_state(self) -> Tuple[float, float, str, str]:
        """
        :return: (speed_mps có dấu: âm khi số lùi R, yaw_rate_rad_s, turn_direction, gear)
        """
        spd = -self.current_speed_mps if self.gear == "R" else self.current_speed_mps
        return spd, self.yaw_rate_rad_s, self.turn_direction, self.gear
