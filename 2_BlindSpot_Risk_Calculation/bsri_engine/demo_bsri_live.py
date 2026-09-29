"""
Script: demo_bsri_live.py
Phân hệ: 2_BlindSpot_Risk_Calculation / bsri_engine
Mô tả: Ứng dụng kiểm thử trực quan toàn diện (End-to-End Visual Demo):
       Tích hợp YOLOv11n + ByteTrack + Homography (VCS) + BSRI Engine
       chạy trực tiếp trên video camera mắt cá xe tải.

Cách chạy:
    python 2_BlindSpot_Risk_Calculation/bsri_engine/demo_bsri_live.py
    (Hoặc truyền đường dẫn video: python demo_bsri_live.py --video "D:/video.mp4")
"""

import sys
import time
import argparse
from pathlib import Path
import cv2
import numpy as np

# Thiết lập đường dẫn thư viện
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "1_AI_Processing_Edge"))
sys.path.insert(0, str(PROJECT_ROOT / "2_BlindSpot_Risk_Calculation"))

from homography_calibrator import HomographyCalibrator
from bsri_engine import (
    BSRICalculator,
    EgoVehicleState,
    TrackedObstacle,
    RiskLevel,
    BlindSpotZone
)
from ultralytics import YOLO


def parse_args():
    parser = argparse.ArgumentParser(description="BlindGuard AI - BSRI Live Demo")
    parser.add_argument("--video", type=str, default=r"D:\Download\Videotest\1789054186478_372350579548644477_372350579548644477.mp4",
                        help="Đường dẫn file video kiểm thử")
    parser.add_argument("--model", type=str, default=str(PROJECT_ROOT / "1_AI_Processing_Edge" / "object_detection" / "runs" / "yolo11n_blindguard_v3" / "weights" / "best.pt"),
                        help="Đường dẫn trọng số mô hình YOLO")
    parser.add_argument("--speed", type=float, default=5.0, help="Vận tốc xe chủ giả lập (m/s)")
    parser.add_argument("--turn", type=str, default="RIGHT", choices=["OFF", "RIGHT", "LEFT"], help="Xi-nhan giả lập")
    return parser.parse_args()


def main():
    args = parse_args()
    print("=" * 75)
    print(f"{'BLINDGUARD AI — TRÌNH DIỄN THỊ GIÁC BSRI RISK ENGINE':^75}")
    print("=" * 75)

    # 1. Nạp ma trận Homography
    homo_cfg = PROJECT_ROOT / "1_AI_Processing_Edge" / "homography_config.json"
    calibrator = HomographyCalibrator(homo_cfg if homo_cfg.exists() else None)
    if not calibrator.is_calibrated:
        print("[!] Không tìm thấy homography_config.json chuẩn. Sử dụng ánh xạ xấp xỉ mặt đất.")

    # 2. Nạp mô hình AI & Tracker
    model_path = args.model
    if not Path(model_path).exists():
        model_path = "yolo11n.pt"
    print(f"[*] Nạp mô hình YOLO: {model_path}")
    model = YOLO(model_path)

    tracker_yaml = str(PROJECT_ROOT / "1_AI_Processing_Edge" / "mot_tracking" / "bytetrack_fisheye.yaml")
    if not Path(tracker_yaml).exists():
        tracker_yaml = "bytetrack.yaml"

    # 3. Khởi tạo BSRI Engine
    bsri_calc = BSRICalculator()

    # 4. Trạng thái xe chủ giả lập
    yaw_rate = -0.06 if args.turn == "RIGHT" else (0.06 if args.turn == "LEFT" else 0.0)
    ego_state = EgoVehicleState(
        speed_mps=args.speed,
        yaw_rate_rad_s=yaw_rate,
        turn_signal=args.turn,
        gear="D"
    )

    # 5. Mở video
    video_path = args.video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[Error] Không thể mở video: {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"[+] Video: {Path(video_path).name} | FPS: {fps:.1f} | Tổng frames: {total_frames}")
    print("[*] Phím tắt: [SPACE] Tạm dừng/Tiếp tục | [T] Đổi Xi-nhan (Phải/Trái/Thẳng) | [Q] Thoát")

    # Lưu vết lịch sử tọa độ VCS để tính vận tốc
    prev_positions = {}  # track_id -> (vcs_x, vcs_y, timestamp)
    frame_idx = 0
    paused = False

    window_name = "BlindGuard AI - BSRI Risk Engine Live HUD"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Lặp lại video khi kết thúc
                prev_positions.clear()
                continue
            frame_idx += 1

            h, w = frame.shape[:2]
            current_time = frame_idx / fps

            # A. Thực hiện suy luận ByteTrack
            results = model.track(
                source=frame,
                tracker=tracker_yaml,
                conf=0.12,
                persist=True,
                verbose=False
            )

            obstacles = []
            if results and results[0].boxes and results[0].boxes.id is not None:
                boxes = results[0].boxes
                for idx_b, box in enumerate(boxes):
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    cname = model.names.get(cls_id, f"cls_{cls_id}")
                    if box.id is None:
                        continue
                    tid = int(box.id[0].item())
                    xyxy = box.xyxy[0].cpu().numpy().tolist()

                    # Bỏ qua box toàn màn hình che thấu kính
                    bw = xyxy[2] - xyxy[0]
                    bh = xyxy[3] - xyxy[1]
                    if (bw * bh) > 0.85 * (w * h):
                        continue

                    # Điểm chạm đất chân vật thể (bottom center)
                    ground_u = (xyxy[0] + xyxy[2]) / 2.0
                    ground_v = xyxy[3]

                    # Chuyển đổi Homography sang mét VCS
                    if calibrator.is_calibrated:
                        try:
                            vcs_x, vcs_y, dist_m = calibrator.pixel_to_world(ground_u, ground_v)
                        except Exception:
                            vcs_x, vcs_y, dist_m = 3.0, -1.8, 3.5
                    else:
                        # Ánh xạ xấp xỉ dự phòng
                        vcs_x = float(2.0 + 8.0 * (1.0 - ground_v / h))
                        vcs_y = float((ground_u / w - 0.5) * 6.0)
                        dist_m = float((vcs_x**2 + vcs_y**2)**0.5)

                    # Tính vận tốc thực tế m/s từ sai phân vị trí
                    vel_x, vel_y = 0.0, 0.0
                    if tid in prev_positions:
                        old_x, old_y, old_t = prev_positions[tid]
                        dt = max(0.01, current_time - old_t)
                        vel_x = (vcs_x - old_x) / dt
                        vel_y = (vcs_y - old_y) / dt
                        # Giới hạn lọc nhiễu vận tốc
                        vel_x = float(np.clip(vel_x, -15.0, 15.0))
                        vel_y = float(np.clip(vel_y, -15.0, 15.0))

                    prev_positions[tid] = (vcs_x, vcs_y, current_time)

                    obs = TrackedObstacle(
                        track_id=tid,
                        class_name=cname,
                        confidence=conf,
                        bbox_xyxy=tuple(xyxy),
                        vcs_x=vcs_x,
                        vcs_y=vcs_y,
                        vel_x=vel_x,
                        vel_y=vel_y,
                        distance_m=dist_m
                    )
                    obstacles.append(obs)

            # B. Tính toán rủi ro BSRI toàn cảnh
            all_bsri, highest_threat = bsri_calc.evaluate_scene(ego_state, obstacles)
            bsri_map = {r.track_id: r for r in all_bsri}

            # C. Vẽ Bounding Box & Thẻ thông tin rủi ro
            for obs in obstacles:
                r_info = bsri_map.get(obs.track_id)
                if not r_info:
                    continue

                color = r_info.risk_level.color_bgr
                x1, y1, x2, y2 = [int(v) for v in obs.bbox_xyxy]
                thick = 3 if r_info.risk_level in [RiskLevel.CRITICAL, RiskLevel.WARNING] else 2
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, thick)

                # Nhãn thông tin BSRI
                ttc_txt = f"TTC:{r_info.ttc_seconds}s" if r_info.ttc_seconds else f"{obs.distance_m:.1f}m"
                tag_line1 = f"#{obs.track_id} {obs.class_name} | BSRI:{r_info.bsri_score:.2f}"
                tag_line2 = f"X:{obs.vcs_x:+.1f}m Y:{obs.vcs_y:+.1f}m | {ttc_txt}"

                (tw1, th1), _ = cv2.getTextSize(tag_line1, cv2.FONT_HERSHEY_DUPLEX, 0.44, 1)
                (tw2, th2), _ = cv2.getTextSize(tag_line2, cv2.FONT_HERSHEY_DUPLEX, 0.40, 1)
                box_tw = max(tw1, tw2) + 10
                box_th = th1 + th2 + 12

                tag_y1 = max(50, y1 - box_th - 6)
                cv2.rectangle(frame, (x1, tag_y1), (x1 + box_tw, tag_y1 + box_th), (25, 25, 25), -1)
                cv2.rectangle(frame, (x1, tag_y1), (x1 + box_tw, tag_y1 + box_th), color, 1)
                cv2.putText(frame, tag_line1, (x1 + 5, tag_y1 + th1 + 2), cv2.FONT_HERSHEY_DUPLEX, 0.44, color, 1, cv2.LINE_AA)
                cv2.putText(frame, tag_line2, (x1 + 5, tag_y1 + th1 + th2 + 7), cv2.FONT_HERSHEY_DUPLEX, 0.40, (220, 220, 220), 1, cv2.LINE_AA)

            # D. Giao diện Top Bar (HUD Header)
            top_h = 52
            cv2.rectangle(frame, (0, 0), (w, top_h), (20, 20, 20), -1)
            cv2.putText(frame, "BLINDGUARD AI | BSRI RISK ENGINE", (15, 32), cv2.FONT_HERSHEY_DUPLEX, 0.58, (255, 255, 255), 1, cv2.LINE_AA)

            turn_txt = f"XI-NHAN: {ego_state.turn_signal}"
            cv2.putText(frame, turn_txt, (380, 32), cv2.FONT_HERSHEY_DUPLEX, 0.50, (0, 255, 255) if ego_state.turn_signal != "OFF" else (180, 180, 180), 1, cv2.LINE_AA)

            # Badge mức đe dọa cao nhất
            badge_color = highest_threat.risk_level.color_bgr
            badge_text = f"RISK: {highest_threat.risk_level.label_vi} (BSRI: {highest_threat.bsri_score:.2f})"
            (bw, _), _ = cv2.getTextSize(badge_text, cv2.FONT_HERSHEY_DUPLEX, 0.52, 1)
            cv2.rectangle(frame, (w - bw - 30, 8), (w - 10, 44), badge_color, -1)
            text_color = (0, 0, 0) if highest_threat.risk_level in [RiskLevel.CAUTION, RiskLevel.SAFE] else (255, 255, 255)
            cv2.putText(frame, badge_text, (w - bw - 20, 31), cv2.FONT_HERSHEY_DUPLEX, 0.52, text_color, 1, cv2.LINE_AA)

            # E. Giao diện Bottom Banner (Explainable AI Alert Banner)
            bot_h = 44
            cv2.rectangle(frame, (0, h - bot_h), (w, h), (15, 15, 25), -1)
            border_col = badge_color if highest_threat.risk_level != RiskLevel.SAFE else (60, 60, 60)
            cv2.rectangle(frame, (0, h - bot_h), (w, h), border_col, 2)
            cv2.putText(frame, f"[XAI] {highest_threat.explanation}", (15, h - 26), cv2.FONT_HERSHEY_DUPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(frame, f"-> {highest_threat.recommendation}", (15, h - 8), cv2.FONT_HERSHEY_DUPLEX, 0.42, (0, 255, 255), 1, cv2.LINE_AA)

        cv2.imshow(window_name, frame)
        key = cv2.waitKey(int(1000 / fps)) & 0xFF

        if key in [ord('q'), ord('Q'), 27]:
            break
        elif key in [ord(' '), ord('p'), ord('P')]:
            paused = not paused
        elif key in [ord('t'), ord('T')]:
            # Đổi tuần hoàn xi-nhan: RIGHT -> LEFT -> OFF -> RIGHT
            if ego_state.turn_signal == "RIGHT":
                ego_state.turn_signal = "LEFT"
                ego_state.yaw_rate_rad_s = 0.06
            elif ego_state.turn_signal == "LEFT":
                ego_state.turn_signal = "OFF"
                ego_state.yaw_rate_rad_s = 0.0
            else:
                ego_state.turn_signal = "RIGHT"
                ego_state.yaw_rate_rad_s = -0.06
            print(f"[*] Chuyển trạng thái xe: Xi-nhan = {ego_state.turn_signal}, YawRate = {ego_state.yaw_rate_rad_s}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
