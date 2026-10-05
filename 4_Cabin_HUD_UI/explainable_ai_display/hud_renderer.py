"""
Module: hud_renderer.py
Phân hệ: 4_Cabin_HUD_UI / explainable_ai_display
Mô tả: Bộ dựng hình Giao diện Cabin HUD Trực quan hóa Giải thích (Explainable AI - XAI)
       hiển thị thông tin an toàn điểm mù theo chuẩn công thái học buồng lái xe tải nặng.
"""

import time
import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple

try:
    from risk_models import RiskLevel, BlindSpotZone, EgoVehicleState, TrackedObstacle, BSRIResult
except ImportError:
    from bsri_engine.risk_models import RiskLevel, BlindSpotZone, EgoVehicleState, TrackedObstacle, BSRIResult


class CabinHUDRenderer:
    """
    Bộ vẽ giao diện buồng lái hiển thị thông tin rủi ro BSRI và giải thích XAI.
    Tối ưu hóa bộ nhớ cho phần cứng nhúng NVIDIA Jetson Nano B01:
    - Không cấp phát mảng tạm thời kích thước lớn.
    - Vẽ trực tiếp trên frame in-place.
    """

    CLASS_NAMES_VI = {
        "person": "Nguoi di bo",
        "bicycle": "Xe dap",
        "motorcycle": "Xe may",
        "car": "O to con",
        "truck": "Xe tai",
        "bus": "Xe buyt",
        "xe_keo": "Xe keo hang",
        "xich_lo": "Xich lo"
    }

    def __init__(self, show_dhz_overlay: bool = True):
        self.show_dhz_overlay = show_dhz_overlay
        self.blink_state = False
        self.last_blink_time = time.time()

    def update_blink(self):
        now = time.time()
        if now - self.last_blink_time >= 0.25:
            self.last_blink_time = now
            self.blink_state = not self.blink_state

    def render(self,
               frame: np.ndarray,
               obstacles: List[TrackedObstacle],
               bsri_results: List[BSRIResult],
               highest_threat: BSRIResult,
               ego_state: EgoVehicleState,
               fps: float,
               is_serial_connected: bool = False,
               calibrator = None) -> np.ndarray:
        """
        Dựng toàn bộ các thành phần HUD lên khung hình OpenCV.
        """
        self.update_blink()
        h, w = frame.shape[:2]

        bsri_map: Dict[int, BSRIResult] = {r.track_id: r for r in bsri_results}

        # 1. Vẽ Đa giác Nguy hiểm Động (DHZ) chiếu ngược lên mặt đường (nếu có calibrator)
        if self.show_dhz_overlay and calibrator is not None and calibrator.is_calibrated:
            self._draw_dhz_overlay(frame, calibrator, highest_threat.risk_level)

        # 2. Vẽ Bounding Box & Nhãn thông tin cho từng chướng ngại vật
        for obs in obstacles:
            r_info = bsri_map.get(obs.track_id)
            if not r_info:
                continue
            self._draw_obstacle_box(frame, obs, r_info)

        # 3. Vẽ Top Bar (Thanh thông tin đỉnh buồng lái)
        self._draw_top_bar(frame, ego_state, fps, highest_threat, is_serial_connected)

        # 4. Vẽ Bottom Banner (Thanh cảnh báo XAI đáy màn hình)
        self._draw_bottom_banner(frame, highest_threat)

        return frame

    def _draw_obstacle_box(self, frame: np.ndarray, obs: TrackedObstacle, r_info: BSRIResult):
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = [int(v) for v in obs.bbox_xyxy]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w - 1, x2), min(h - 1, y2)

        color = r_info.risk_level.color_bgr
        # Hiệu ứng viền nhấp nháy khi ở mức CRITICAL
        if r_info.risk_level == RiskLevel.CRITICAL and not self.blink_state:
            color = (0, 160, 255)  # Đổi màu cam nháy

        thick = 3 if r_info.risk_level in [RiskLevel.CRITICAL, RiskLevel.WARNING] else 2
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thick)

        # Vẽ điểm neo chân tiếp xúc mặt đất (Ground Anchor Point)
        ground_u = (x1 + x2) // 2
        ground_v = y2
        cv2.circle(frame, (ground_u, ground_v), 4, (0, 255, 255), -1)

        # Chuẩn bị nội dung thẻ nhãn thông tin
        c_vn = self.CLASS_NAMES_VI.get(obs.class_name.lower(), obs.class_name)
        ttc_str = f"TTC: {r_info.ttc_seconds:.1f}s" if (r_info.ttc_seconds and r_info.ttc_seconds > 0) else f"D: {obs.distance_m:.1f}m"
        line1 = f"#{obs.track_id} {c_vn} | BSRI: {r_info.bsri_score:.2f}"
        line2 = f"X:{obs.vcs_x:+.1f}m Y:{obs.vcs_y:+.1f}m | {ttc_str}"

        font = cv2.FONT_HERSHEY_DUPLEX
        scale1, scale2 = 0.44, 0.40
        (w_l1, h_l1), _ = cv2.getTextSize(line1, font, scale1, 1)
        (w_l2, h_l2), _ = cv2.getTextSize(line2, font, scale2, 1)

        tag_w = max(w_l1, w_l2) + 12
        tag_h = h_l1 + h_l2 + 14
        tag_x = x1
        tag_y = max(55, y1 - tag_h - 4)

        if tag_x + tag_w > w:
            tag_x = w - tag_w - 4

        # Nền đen bán trong suốt cho thẻ nhãn
        cv2.rectangle(frame, (tag_x, tag_y), (tag_x + tag_w, tag_y + tag_h), (20, 20, 20), -1)
        cv2.rectangle(frame, (tag_x, tag_y), (tag_x + tag_w, tag_y + tag_h), color, 1)

        cv2.putText(frame, line1, (tag_x + 6, tag_y + h_l1 + 3), font, scale1, color, 1, cv2.LINE_AA)
        cv2.putText(frame, line2, (tag_x + 6, tag_y + h_l1 + h_l2 + 9), font, scale2, (220, 220, 220), 1, cv2.LINE_AA)

    def _draw_top_bar(self, frame: np.ndarray, ego: EgoVehicleState, fps: float, highest: BSRIResult, is_serial: bool):
        h, w = frame.shape[:2]
        top_h = 48

        # Nền Top Bar
        cv2.rectangle(frame, (0, 0), (w, top_h), (18, 18, 22), -1)
        cv2.line(frame, (0, top_h), (w, top_h), (60, 60, 70), 1)

        # 1. Logo & Tên dự án
        cv2.putText(frame, "BLINDGUARD AI", (14, 30), cv2.FONT_HERSHEY_DUPLEX, 0.62, (0, 255, 255), 1, cv2.LINE_AA)

        # 2. Chỉ thị FPS & Tốc độ xe Ego
        spd_kmh = abs(ego.speed_mps) * 3.6
        status_txt = f"{fps:.1f} FPS | {spd_kmh:.0f} km/h"
        cv2.putText(frame, status_txt, (180, 30), cv2.FONT_HERSHEY_DUPLEX, 0.48, (200, 240, 200), 1, cv2.LINE_AA)

        # 3. Trạng thái Xi-nhan & Số xe
        turn_col = (0, 255, 255) if (ego.turn_signal != "OFF" and self.blink_state) else (140, 140, 140)
        turn_str = f"SIGNAL: {ego.turn_signal} [{ego.gear}]"
        cv2.putText(frame, turn_str, (340, 30), cv2.FONT_HERSHEY_DUPLEX, 0.48, turn_col, 1, cv2.LINE_AA)

        # 4. Trạng thái kết nối Hardware UART ESP32
        hw_col = (0, 220, 0) if is_serial else (120, 120, 120)
        hw_txt = "ESP32: ON" if is_serial else "ESP32: SIM"
        cv2.putText(frame, hw_txt, (530, 30), cv2.FONT_HERSHEY_DUPLEX, 0.44, hw_col, 1, cv2.LINE_AA)

        # 5. Badge Mức độ Đe dọa Cao nhất (Top Right)
        b_color = highest.risk_level.color_bgr
        if highest.risk_level == RiskLevel.CRITICAL and not self.blink_state:
            b_color = (0, 0, 160)

        badge_txt = f"{highest.risk_level.label_vi} (BSRI: {highest.bsri_score:.2f})"
        (b_w, b_h), _ = cv2.getTextSize(badge_txt, cv2.FONT_HERSHEY_DUPLEX, 0.52, 1)

        bx1 = w - b_w - 26
        by1 = 6
        bx2 = w - 8
        by2 = top_h - 6
        cv2.rectangle(frame, (bx1, by1), (bx2, by2), b_color, -1)
        text_col = (0, 0, 0) if highest.risk_level in [RiskLevel.SAFE, RiskLevel.CAUTION] else (255, 255, 255)
        cv2.putText(frame, badge_txt, (bx1 + 9, by1 + b_h + 8), cv2.FONT_HERSHEY_DUPLEX, 0.50, text_col, 1, cv2.LINE_AA)

    def _draw_bottom_banner(self, frame: np.ndarray, highest: BSRIResult):
        h, w = frame.shape[:2]
        bot_h = 48
        y_start = h - bot_h

        # Nền Banner đáy
        b_color = highest.risk_level.color_bgr
        border_col = b_color if highest.risk_level != RiskLevel.SAFE else (60, 60, 70)
        cv2.rectangle(frame, (0, y_start), (w, h), (14, 14, 18), -1)
        cv2.rectangle(frame, (0, y_start), (w, h), border_col, 2)

        # Dòng 1: Giải thích ngữ cảnh XAI
        xai_txt = f"[XAI] {highest.explanation}"
        # Cắt ngắn nếu quá dài so với chiều ngang khung hình
        if len(xai_txt) > 95:
            xai_txt = xai_txt[:92] + "..."
        cv2.putText(frame, xai_txt, (14, y_start + 20), cv2.FONT_HERSHEY_DUPLEX, 0.44, (255, 255, 255), 1, cv2.LINE_AA)

        # Dòng 2: Lời khuyên hành động
        rec_txt = f"-> {highest.recommendation}"
        if len(rec_txt) > 95:
            rec_txt = rec_txt[:92] + "..."
        rec_col = (0, 255, 255) if highest.risk_level != RiskLevel.SAFE else (180, 180, 180)
        cv2.putText(frame, rec_txt, (14, y_start + 40), cv2.FONT_HERSHEY_DUPLEX, 0.42, rec_col, 1, cv2.LINE_AA)

    def _draw_dhz_overlay(self, frame: np.ndarray, calibrator, risk_level: RiskLevel):
        """
        Chiếu ngược một lưới hình học đại diện cho Vùng Nguy hiểm Động (DHZ) lên mặt đường.
        Tạo cảm giác chân thực của hệ thống ADAS cao cấp.
        """
        try:
            # 4 điểm đa giác DHZ tượng trưng quanh hông phụ xe tải trong hệ VCS:
            # X: từ đuôi rơ-moóc (-8m) đến cản trước (+5m), Y: từ -1.3m đến -3.2m
            dhz_vcs_pts = [
                (4.5, -1.3),
                (4.5, -3.2),
                (-8.0, -3.5),
                (-8.0, -1.3)
            ]
            pixel_pts = []
            for vx, vy in dhz_vcs_pts:
                u, v = calibrator.world_to_pixel(vx, vy)
                if 0 <= u < frame.shape[1] and 0 <= v < frame.shape[0]:
                    pixel_pts.append([int(u), int(v)])

            if len(pixel_pts) >= 4:
                pts_arr = np.array([pixel_pts], dtype=np.int32)
                overlay = frame.copy()
                dhz_color = (0, 0, 200) if risk_level == RiskLevel.CRITICAL else (0, 140, 255)
                cv2.fillPoly(overlay, pts_arr, dhz_color)
                # Trộn độ trong suốt 25%
                cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
                cv2.polylines(frame, pts_arr, True, dhz_color, 2, cv2.LINE_AA)
        except Exception:
            pass
