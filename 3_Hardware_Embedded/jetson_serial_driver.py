"""
Module: jetson_serial_driver.py
Phân hệ: 3_Hardware_Embedded
Mô tả: Giao tiếp nối tiếp tốc độ cao (UART/Serial) giữa NVIDIA Jetson Nano B01 và ESP32 Controller.
       Quản lý luồng I/O bất đồng bộ, phân tích telemetry Ego vehicle và phát gói cảnh báo BSRI.
Chuẩn giao thức: NMEA-style Checksum ASCII Frame
"""

import time
import threading
from typing import Optional, Tuple
try:
    import serial
except ImportError:
    serial = None

try:
    from risk_models import EgoVehicleState, RiskLevel, BlindSpotZone, BSRIResult
except ImportError:
    from bsri_engine.risk_models import EgoVehicleState, RiskLevel, BlindSpotZone, BSRIResult


class JetsonSerialDriver:
    """
    Driver điều khiển giao tiếp UART giữa Jetson Nano và ESP32.
    - Cổng mặc định trên Jetson Nano: /dev/ttyTHS1 (J41 UART Pin 8/10) hoặc /dev/ttyUSB0.
    - Tự động fallback sang chế độ Giả lập (Dummy Mode) nếu không tìm thấy phần cứng.
    """

    ZONE_TO_ID = {
        BlindSpotZone.CAB_FRONT: 1,
        BlindSpotZone.MIRROR_RIGHT: 2,
        BlindSpotZone.MIRROR_LEFT: 3,
        BlindSpotZone.SWEPT_PATH_RIGHT: 4,
        BlindSpotZone.SWEPT_PATH_LEFT: 5,
        BlindSpotZone.REAR_TRAILER: 6,
        BlindSpotZone.CLEAR_ZONE: 0
    }

    def __init__(self, port: Optional[str] = "/dev/ttyTHS1", baudrate: int = 115200, dummy_mode: bool = False):
        self.port = port
        self.baudrate = baudrate
        self.dummy_mode = dummy_mode
        self.ser: Optional[serial.Serial] = None
        self.is_connected = False
        self.is_running = False

        # Trạng thái xe chủ Ego nhận từ ESP32
        self.ego_state = EgoVehicleState()
        self.state_lock = threading.Lock()

        self.rx_thread: Optional[threading.Thread] = None
        self.last_rx_time = 0.0
        self.last_tx_time = 0.0

        if not self.dummy_mode and self.port:
            self._connect()

    def _connect(self):
        if serial is None:
            print(f"[Serial] Thư viện pyserial chưa được cài đặt. Tự động kích hoạt DUMMY SIMULATION MODE.")
            self.is_connected = False
            self.dummy_mode = True
            return

        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.05)
            self.is_connected = True
            print(f"[Serial] Đã kết nối thành công tới ESP32 qua cổng {self.port} ({self.baudrate} baud)")
        except Exception as e:
            print(f"[Serial] Không thể mở cổng {self.port} ({e}). Tự động kích hoạt DUMMY SIMULATION MODE.")
            self.is_connected = False
            self.dummy_mode = True

    @staticmethod
    def calculate_checksum(sentence: str) -> str:
        """Tính Checksum XOR chuẩn NMEA"""
        cs = 0
        for char in sentence:
            if char == '$':
                continue
            if char == '*':
                break
            cs ^= ord(char)
        return f"{cs:02X}"

    def start(self):
        """Khởi động luồng đọc nền bất đồng bộ"""
        if self.is_running:
            return
        self.is_running = True
        self.rx_thread = threading.Thread(target=self._rx_loop, daemon=True, name="JetsonSerialRX")
        self.rx_thread.start()

    def stop(self):
        """Dừng giao tiếp và đóng cổng Serial"""
        self.is_running = False
        if self.rx_thread and self.rx_thread.is_alive():
            self.rx_thread.join(timeout=0.5)
        if self.ser and self.ser.is_open:
            try:
                # Gửi lệnh an toàn ngắt còi trước khi đóng cổng
                self.send_bsri_warning(0, 0.0, 0, 0, None)
                self.ser.close()
            except Exception:
                pass
        self.is_connected = False
        print("[Serial] Đã đóng kết nối Serial an toàn.")

    def _rx_loop(self):
        """Luồng đọc gói tin $EGO từ ESP32"""
        while self.is_running:
            if not self.is_connected or not self.ser:
                time.sleep(0.05)
                continue

            try:
                line = self.ser.readline().decode('ascii', errors='ignore').strip()
                if line.startswith("$EGO,") or line.startswith("EGO,"):
                    self._parse_ego_packet(line)
                    self.last_rx_time = time.time()
            except Exception:
                time.sleep(0.01)

    def _parse_ego_packet(self, line: str):
        """
        Phân tích gói tin: $EGO,<speed_mps>,<yaw_rate_rad_s>,<turn_signal>,<gear>*<CS>
        """
        try:
            content = line.split('*')[0]
            if content.startswith('$'):
                content = content[1:]
            parts = content.split(',')
            if len(parts) >= 5:
                speed = float(parts[1])
                yaw_rate = float(parts[2])
                turn = str(parts[3]).upper()
                gear = str(parts[4]).upper()

                with self.state_lock:
                    self.ego_state.speed_mps = speed
                    self.ego_state.yaw_rate_rad_s = yaw_rate
                    self.ego_state.turn_signal = turn
                    self.ego_state.gear = gear
        except Exception:
            pass

    def get_ego_state(self) -> EgoVehicleState:
        """Lấy bản sao trạng thái xe chủ (thread-safe)"""
        with self.state_lock:
            return EgoVehicleState(
                speed_mps=self.ego_state.speed_mps,
                yaw_rate_rad_s=self.ego_state.yaw_rate_rad_s,
                steering_angle_deg=self.ego_state.steering_angle_deg,
                accel_x_mps2=self.ego_state.accel_x_mps2,
                accel_y_mps2=self.ego_state.accel_y_mps2,
                turn_signal=self.ego_state.turn_signal,
                trailer_gamma_rad=self.ego_state.trailer_gamma_rad,
                gear=self.ego_state.gear
            )

    def set_dummy_ego_state(self, speed_mps: float = 0.0, yaw_rate_rad_s: float = 0.0, turn_signal: str = "OFF", gear: str = "D"):
        """Dùng cho chế độ test khi không có ESP32 thật"""
        with self.state_lock:
            self.ego_state.speed_mps = speed_mps
            self.ego_state.yaw_rate_rad_s = yaw_rate_rad_s
            self.ego_state.turn_signal = turn_signal
            self.ego_state.gear = gear

    def send_bsri_warning(self, level_code: int, score: float, track_id: int, zone_id: int, ttc_seconds: Optional[float] = None):
        """
        Gửi gói tin cảnh báo BSRI xuống ESP32.
        Cú pháp: $BSRI,<level>,<score>,<track_id>,<zone_id>,<ttc_x10>*<CS>\n
        """
        if self.dummy_mode or not self.is_connected or not self.ser:
            return

        now = time.time()
        # Giới hạn tốc độ gửi tối đa 30 Hz để tránh tràn buffer UART của ESP32
        if now - self.last_tx_time < 0.033:
            return
        self.last_tx_time = now

        ttc_int = int(round(ttc_seconds * 10)) if (ttc_seconds is not None and ttc_seconds >= 0) else -1
        body = f"BSRI,{level_code},{score:.2f},{track_id},{zone_id},{ttc_int}"
        cs = self.calculate_checksum(body)
        packet = f"${body}*{cs}\r\n"

        try:
            self.ser.write(packet.encode('ascii'))
        except Exception as e:
            print(f"[Serial] Lỗi gửi UART: {e}")
            self.is_connected = False

    def send_threat_result(self, highest_threat: BSRIResult):
        """Hàm tiện ích gửi trực tiếp từ đối tượng BSRIResult"""
        zone_id = self.ZONE_TO_ID.get(highest_threat.zone, 0)
        self.send_bsri_warning(
            level_code=highest_threat.risk_level.code,
            score=highest_threat.bsri_score,
            track_id=highest_threat.track_id,
            zone_id=zone_id,
            ttc_seconds=highest_threat.ttc_seconds
        )
