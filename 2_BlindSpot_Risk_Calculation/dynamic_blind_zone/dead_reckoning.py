# ==============================================================================
# DEAD_RECKONING.PY: THUẬT TOÁN ĐỒNG BỘ GPS (1Hz) VÀ CAMERA (30Hz) VIA DEAD RECKONING
# Bám sát Phần 5 trong Tài liệu Hướng dẫn Kỹ thuật VEDC 2026
# ==============================================================================

import time
import config

class GPSDeadReckoning:
    """
    [PHẦN 5 TÀI LIỆU]: Đồng bộ tần số GPS (1Hz) với Camera AI (30Hz).
    Sử dụng mô hình Vận tốc Không đổi (Constant Velocity - CV) để nội suy vị trí 
    và duy trì trạng thái 3-5 giây khi mất sóng GPS (đi vào hầm).
    """
    def __init__(self):
        self.last_gps_time = 0.0
        self.v_gps = 0.0      # m/s
        self.omega_gps = 0.0  # rad/s
        self.is_gps_lost = True

    def update_gps_signal(self, v_gps: float, omega_gps: float, timestamp: float = None):
        """
        Cập nhật tín hiệu xung GPS mới (tần số 1Hz).
        """
        if timestamp is None:
            timestamp = time.time()
            
        self.v_gps = v_gps
        self.omega_gps = omega_gps
        self.last_gps_time = timestamp
        self.is_gps_lost = False

    def predict_state_at_camera_frame(self, current_time: float = None) -> dict:
        """
        [30Hz Prediction]: Dự toán trạng thái v và omega tại thời điểm khung hình Camera hiện tại.
        Nếu mất sóng GPS quá 5 giây (GPS_TIMEOUT_SEC), tự động hạ vận tốc an toàn.
        """
        if current_time is None:
            current_time = time.time()

        elapsed_time = current_time - self.last_gps_time

        # Kiểm tra xem có bị mất sóng GPS hay không
        if elapsed_time > config.GPS_TIMEOUT_SEC:
            self.is_gps_lost = True
            # Mất sóng quá lâu -> Hạ vận tốc về 0 để an toàn
            predicted_v = 0.0
            predicted_omega = 0.0
        elif elapsed_time > (1.0 / config.GPS_FREQ):
            # Trong thời gian mất sóng ngắn (3-5s đi trong hầm): Duy trì mô hình Constant Velocity (CV)
            self.is_gps_lost = True
            predicted_v = self.v_gps
            predicted_omega = self.omega_gps
        else:
            # Sóng GPS bình thường: Nội suy theo tần số 30Hz
            self.is_gps_lost = False
            predicted_v = self.v_gps
            predicted_omega = self.omega_gps

        return {
            "v_predicted": predicted_v,
            "omega_predicted": predicted_omega,
            "is_gps_lost": self.is_gps_lost,
            "elapsed_since_gps": elapsed_time
        }
