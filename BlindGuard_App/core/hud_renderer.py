"""
Module: hud_renderer.py
Vị trí: BlindGuard_App/core/hud_renderer.py
Mô tả: Bộ dựng hình Giao diện Cabin HUD XAI cho BlindGuard App.
       Hỗ trợ hiển thị trực quan thông tin của 4 góc Camera khác nhau.
"""

import time
import cv2
import numpy as np
from typing import List, Dict, Optional

from shapely.geometry import Polygon, box

# QUAN TRỌNG: Phải import cùng đường dẫn gói với bsri_calculator (core.risk_models).
# Nếu import "risk_models" dạng module gốc, Python tạo ra 2 class RiskLevel khác nhau
# và mọi phép so sánh "== RiskLevel.CRITICAL" đều sai.
try:
    from .risk_models import RiskLevel, BlindSpotZone, EgoVehicleState, TrackedObstacle, BSRIResult
except ImportError:
    from risk_models import RiskLevel, BlindSpotZone, EgoVehicleState, TrackedObstacle, BSRIResult


class MultiCamCabinHUDRenderer:
    """Bộ vẽ HUD thông minh cho buồng lái xe tải nặng theo chuẩn XAI"""

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

    CAMERA_NAMES_VI = {
        "MIRROR_RIGHT": "GUONG PHU (HONG PHAI)",
        "MIRROR_LEFT": "GUONG LAI (HONG TRAI)",
        "CAB_FRONT": "MUI XE (CAN TRUOC)",
        "REAR_TRAILER": "DUOI XE (DIEM MU LUI)"
    }

    def __init__(self, show_dhz: bool = True):
        self.show_dhz = show_dhz
        self.blink_state = False
        self.last_blink = time.time()

    def update_blink(self):
        now = time.time()
        if now - self.last_blink >= 0.25:
            self.last_blink = now
            self.blink_state = not self.blink_state

    def render(self,
               frame: np.ndarray,
               camera_key: str,
               obstacles: List[TrackedObstacle],
               bsri_results: List[BSRIResult],
               highest_threat: BSRIResult,
               ego_state: EgoVehicleState,
               fps: float,
               homo_manager = None,
               dhz_poly: Optional[Polygon] = None) -> np.ndarray:

        self.update_blink()
        h, w = frame.shape[:2]
        bsri_map: Dict[int, BSRIResult] = {r.track_id: r for r in bsri_results}

        # 1. Vẽ Đa giác DHZ thật (từ BSRICalculator) chiếu ngược lên mặt đường
        if self.show_dhz and homo_manager and homo_manager.is_calibrated and dhz_poly is not None:
            self._draw_dhz(frame, homo_manager, dhz_poly, highest_threat.risk_level, camera_key)

        # 2. Vẽ Bounding Box & Thẻ thông tin
        for obs in obstacles:
            r_info = bsri_map.get(obs.track_id)
            if not r_info:
                continue
            self._draw_box(frame, obs, r_info)

        # 3. Vẽ Top Bar
        self._draw_top_bar(frame, camera_key, ego_state, fps, highest_threat)

        # 4. Vẽ Bottom XAI Banner
        self._draw_bottom_banner(frame, highest_threat)

        return frame

    def _draw_box(self, frame: np.ndarray, obs: TrackedObstacle, r_info: BSRIResult):
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = [int(v) for v in obs.bbox_xyxy]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w - 1, x2), min(h - 1, y2)

        color = r_info.risk_level.color_bgr
        if r_info.risk_level == RiskLevel.CRITICAL and not self.blink_state:
            color = (0, 165, 255)

        thick = 3 if r_info.risk_level in [RiskLevel.CRITICAL, RiskLevel.WARNING] else 2
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thick)

        # Điểm tiếp đất chân vật thể
        cv2.circle(frame, ((x1 + x2) // 2, y2), 4, (0, 255, 255), -1)

        c_vn = self.CLASS_NAMES_VI.get(obs.class_name.lower(), obs.class_name)
        ttc_str = f"TTC: {r_info.ttc_seconds:.1f}s" if (r_info.ttc_seconds and r_info.ttc_seconds > 0) else f"D: {obs.distance_m:.1f}m"
        line1 = f"#{obs.track_id} {c_vn} | BSRI: {r_info.bsri_score:.2f}"
        line2 = f"X:{obs.vcs_x:+.1f}m Y:{obs.vcs_y:+.1f}m | {ttc_str}"

        font = cv2.FONT_HERSHEY_DUPLEX
        (w1, h1), _ = cv2.getTextSize(line1, font, 0.44, 1)
        (w2, h2), _ = cv2.getTextSize(line2, font, 0.40, 1)

        tw = max(w1, w2) + 12
        th = h1 + h2 + 14
        tx = max(0, min(x1, w - tw - 4))
        ty = max(55, y1 - th - 4)

        cv2.rectangle(frame, (tx, ty), (tx + tw, ty + th), (20, 20, 20), -1)
        cv2.rectangle(frame, (tx, ty), (tx + tw, ty + th), color, 1)
        cv2.putText(frame, line1, (tx + 5, ty + h1 + 3), font, 0.44, color, 1, cv2.LINE_AA)
        cv2.putText(frame, line2, (tx + 5, ty + h1 + h2 + 9), font, 0.40, (220, 220, 220), 1, cv2.LINE_AA)

    def _draw_top_bar(self, frame: np.ndarray, cam_key: str, ego: EgoVehicleState, fps: float, highest: BSRIResult):
        h, w = frame.shape[:2]
        top_h = 48
        cv2.rectangle(frame, (0, 0), (w, top_h), (18, 18, 22), -1)
        cv2.line(frame, (0, top_h), (w, top_h), (60, 60, 70), 1)

        # 1. Logo
        cv2.putText(frame, "BLINDGUARD AI", (14, 30), cv2.FONT_HERSHEY_DUPLEX, 0.60, (0, 255, 255), 1, cv2.LINE_AA)

        # 2. Camera đang chọn
        cam_label = self.CAMERA_NAMES_VI.get(cam_key, cam_key)
        cv2.putText(frame, f"CAM: {cam_label}", (185, 30), cv2.FONT_HERSHEY_DUPLEX, 0.46, (0, 255, 200), 1, cv2.LINE_AA)

        # 3. Tốc độ & FPS (từ GPS/IMU phi xâm lấn)
        spd_kmh = abs(ego.speed_mps) * 3.6
        turn_info = "THANG" if abs(ego.yaw_rate_rad_s) < 0.035 else ("RE PHAI" if ego.yaw_rate_rad_s < 0 else "RE TRAI")
        turn_str = f"| {fps:.1f} FPS | {spd_kmh:.0f} km/h | {ego.gear} | Yaw {ego.yaw_rate_rad_s:+.2f} ({turn_info})"
        cv2.putText(frame, turn_str, (460, 30), cv2.FONT_HERSHEY_DUPLEX, 0.46, (200, 240, 200), 1, cv2.LINE_AA)

        # 4. Badge rủi ro cao nhất (Top Right)
        b_color = highest.risk_level.color_bgr
        if highest.risk_level == RiskLevel.CRITICAL and not self.blink_state:
            b_color = (0, 0, 160)

        badge_txt = f"{highest.risk_level.label_vi} ({highest.bsri_score:.2f})"
        (bw, bh), _ = cv2.getTextSize(badge_txt, cv2.FONT_HERSHEY_DUPLEX, 0.50, 1)
        bx1 = w - bw - 26
        cv2.rectangle(frame, (bx1, 6), (w - 8, top_h - 6), b_color, -1)
        text_col = (0, 0, 0) if highest.risk_level in [RiskLevel.SAFE, RiskLevel.CAUTION] else (255, 255, 255)
        cv2.putText(frame, badge_txt, (bx1 + 9, bh + 14), cv2.FONT_HERSHEY_DUPLEX, 0.48, text_col, 1, cv2.LINE_AA)

    def _draw_bottom_banner(self, frame: np.ndarray, highest: BSRIResult):
        h, w = frame.shape[:2]
        bot_h = 48
        y_start = h - bot_h

        b_color = highest.risk_level.color_bgr
        border_col = b_color if highest.risk_level != RiskLevel.SAFE else (60, 60, 70)
        cv2.rectangle(frame, (0, y_start), (w, h), (14, 14, 18), -1)
        cv2.rectangle(frame, (0, y_start), (w, h), border_col, 2)

        xai_txt = f"[XAI] {highest.explanation}"
        if len(xai_txt) > 95:
            xai_txt = xai_txt[:92] + "..."
        cv2.putText(frame, xai_txt, (14, y_start + 20), cv2.FONT_HERSHEY_DUPLEX, 0.44, (255, 255, 255), 1, cv2.LINE_AA)

        rec_txt = f"-> {highest.recommendation}"
        if len(rec_txt) > 95:
            rec_txt = rec_txt[:92] + "..."
        rec_col = (0, 255, 255) if highest.risk_level != RiskLevel.SAFE else (180, 180, 180)
        cv2.putText(frame, rec_txt, (14, y_start + 40), cv2.FONT_HERSHEY_DUPLEX, 0.42, rec_col, 1, cv2.LINE_AA)

    def _draw_dhz(self, frame: np.ndarray, homo_manager, dhz_poly: Polygon, risk_level: RiskLevel, camera_key: str = "MIRROR_RIGHT"):
        """
        Chiếu DHZ thật lên ảnh, cắt theo phân vùng hành lang điểm mù vật lý (FOV corridor)
        của từng camera và vùng mặt đất hợp lệ để tránh biến dạng/chiếu nhầm cản trước sang gương sườn.
        """
        h, w = frame.shape[:2]

        # 1. Giới hạn DHZ theo phân vùng không gian thực tế mà camera đó phụ trách (VCS ISO 8855)
        # Thân xe tải rộng 2.5m (từ Y = -1.25m đến +1.25m) che khuất hoàn toàn phía đối diện
        cam = camera_key or getattr(homo_manager, "active_camera", "MIRROR_RIGHT")
        if cam == "MIRROR_RIGHT":
            # Camera Gương phụ: chỉ nhìn thấy dải hành lang hông phải xe (Y <= -1.20m)
            fov_box = box(-35.0, -15.0, 3.0, -1.20)
        elif cam == "MIRROR_LEFT":
            # Camera Gương lái: chỉ nhìn thấy dải hành lang hông trái xe (Y >= +1.20m)
            fov_box = box(-35.0, 1.20, 3.0, 15.0)
        elif cam == "CAB_FRONT":
            # Camera Mũi xe: chỉ nhìn thấy vùng cản trước mũi xe (X >= 2.0m)
            fov_box = box(2.0, -12.0, 35.0, 12.0)
        elif cam == "REAR_TRAILER":
            # Camera Đuôi xe: chỉ nhìn thấy vùng lùi sau rơ-moóc (X <= -7.5m)
            fov_box = box(-40.0, -12.0, -7.5, 12.0)
        else:
            fov_box = None

        scoped_dhz = dhz_poly.intersection(fov_box) if fov_box is not None else dhz_poly
        if scoped_dhz.is_empty:
            return

        visible = homo_manager.visible_ground_polygon(w, h)
        if not visible:
            return
        clipped = scoped_dhz.intersection(Polygon(visible).buffer(0))
        if clipped.is_empty:
            return

        geoms = getattr(clipped, "geoms", [clipped])
        polys_px = []
        for g in geoms:
            if g.geom_type != "Polygon" or g.is_empty:
                continue
            pts = []
            for vx, vy in g.exterior.coords:
                p = homo_manager.world_to_pixel(vx, vy)
                if p is None:
                    pts = []
                    break
                pts.append([int(np.clip(p[0], -4 * w, 5 * w)), int(np.clip(p[1], -4 * h, 5 * h))])
            if len(pts) >= 3:
                polys_px.append(np.array(pts, dtype=np.int32))
        if not polys_px:
            return

        dhz_col = (0, 0, 200) if risk_level == RiskLevel.CRITICAL else (0, 140, 255)
        all_pts = np.vstack(polys_px)
        x1, y1 = max(0, int(all_pts[:, 0].min())), max(0, int(all_pts[:, 1].min()))
        x2, y2 = min(w, int(all_pts[:, 0].max()) + 1), min(h, int(all_pts[:, 1].max()) + 1)
        if x2 <= x1 or y2 <= y1:
            return
        roi = frame[y1:y2, x1:x2]
        overlay = roi.copy()
        cv2.fillPoly(overlay, [(p - np.array([x1, y1])).astype(np.int32) for p in polys_px], dhz_col)
        cv2.addWeighted(overlay, 0.22, roi, 0.78, 0, roi)
        cv2.polylines(frame, polys_px, True, dhz_col, 2, cv2.LINE_AA)
