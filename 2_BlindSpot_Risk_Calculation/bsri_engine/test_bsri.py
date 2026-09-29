"""
Script: test_bsri.py
Phân hệ: 2_BlindSpot_Risk_Calculation / bsri_engine
Mô tả: Bộ kiểm thử tự động (Unit Test & Scenario Test) cho Phân hệ Tính toán Chỉ số Rủi ro BSRI.
       Mô phỏng 5 kịch bản giao thông thực tế thường gặp của xe đầu kéo tại Việt Nam.
"""

import sys
from pathlib import Path

# Đảm bảo import được module bsri_engine
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from risk_models import RiskLevel, BlindSpotZone, EgoVehicleState, TrackedObstacle
from bsri_calculator import BSRICalculator


def test_scenario_1_pedestrian_in_right_turn():
    """
    Kịch bản 1: Người đi bộ lọt vào hông phụ bên phải khi xe đầu kéo đang xi-nhan và rẽ phải.
    Kỳ vọng: Rủi ro cực đại BSRI >= 0.80 -> CRITICAL DANGER.
    """
    print("\n--- [TEST 1]: Người đi bộ tại điểm mù hông phụ khi xe rẽ phải ---")
    calc = BSRICalculator()

    ego = EgoVehicleState(
        speed_mps=4.0,           # ~15 km/h xe đang bò vào cua
        yaw_rate_rad_s=-0.08,    # Đang quay đầu sang phải (yaw_rate < 0)
        steering_angle_deg=-15.0,
        turn_signal="RIGHT"
    )

    pedestrian = TrackedObstacle(
        track_id=1,
        class_name="person",
        confidence=0.88,
        bbox_xyxy=(850, 400, 920, 600),
        vcs_x=2.0,               # Ngang hông cabin đầu kéo
        vcs_y=-1.8,              # Bên phải xe 1.8m (gần sát thân xe)
        vel_x=-0.5,
        vel_y=0.2                # Đang bước lại gần xe
    )

    dhz = calc.compute_dynamic_hazard_zone(ego)
    result = calc.evaluate_obstacle(pedestrian, ego, dhz)

    print(f"  + Đối tượng: {result.class_name} #{result.track_id}")
    print(f"  + Vị trí: ({pedestrian.vcs_x:.1f}m, {pedestrian.vcs_y:.1f}m) -> {result.zone.value}")
    print(f"  + Nằm trong DHZ: {result.is_in_dhz} (Khoảng cách tới viền: {result.dist_to_dhz}m)")
    print(f"  + Điểm BSRI: {result.bsri_score:.3f}")
    print(f"  + Cấp độ: {result.risk_level.label_vi} ({result.risk_level.name})")
    print(f"  + Giải thích: {result.explanation}")
    print(f"  + Khuyến nghị: {result.recommendation}")

    assert result.risk_level == RiskLevel.CRITICAL, f"Kỳ vọng CRITICAL nhưng nhận {result.risk_level}"
    assert result.zone == BlindSpotZone.MIRROR_RIGHT, f"Kỳ vọng MIRROR_RIGHT nhưng nhận {result.zone}"
    print("  => [PASS] Đã phát hiện chính xác mối đe dọa khẩn cấp!")


def test_scenario_2_distant_car_moving_away():
    """
    Kịch bản 2: Ô tô con ở cự ly xa bên trái (15m), đang di chuyển ra xa xe.
    Kỳ vọng: Rủi ro an toàn BSRI < 0.30 -> SAFE.
    """
    print("\n--- [TEST 2]: Ô tô con ở cự ly xa, đi xa dần ---")
    calc = BSRICalculator()

    ego = EgoVehicleState(speed_mps=10.0, yaw_rate_rad_s=0.0)

    car = TrackedObstacle(
        track_id=2,
        class_name="car",
        confidence=0.92,
        bbox_xyxy=(100, 150, 250, 300),
        vcs_x=12.0,
        vcs_y=8.0,               # Cách xa bên trái 8m
        vel_x=2.0,               # Đang chạy nhanh hơn vượt lên xa dần
        vel_y=1.0
    )

    dhz = calc.compute_dynamic_hazard_zone(ego)
    result = calc.evaluate_obstacle(car, ego, dhz)

    print(f"  + Đối tượng: {result.class_name} #{result.track_id}")
    print(f"  + Khoảng cách: {car.distance_m:.1f}m -> {result.zone.value}")
    print(f"  + Điểm BSRI: {result.bsri_score:.3f}")
    print(f"  + Cấp độ: {result.risk_level.label_vi} ({result.risk_level.name})")

    assert result.risk_level == RiskLevel.SAFE, f"Kỳ vọng SAFE nhưng nhận {result.risk_level}"
    print("  => [PASS] Không phát sinh cảnh báo giả (Zero False Alarm)!")


def test_scenario_3_fast_approaching_motorcycle():
    """
    Kịch bản 3: Xe máy phóng nhanh tiếp cận từ phía sau vào điểm mù hông xe (TTC < 1.5s).
    Kỳ vọng: BSRI đạt WARNING hoặc CRITICAL với TTC được tính toán chuẩn xác.
    """
    print("\n--- [TEST 3]: Xe máy tiếp cận nhanh từ phía sau (TTC thấp) ---")
    calc = BSRICalculator()

    ego = EgoVehicleState(speed_mps=8.0, yaw_rate_rad_s=0.0)

    # Xe máy đi 14 m/s (chạy nhanh hơn xe tải 6 m/s, tiếp cận ở cự ly 8m)
    motorcycle = TrackedObstacle(
        track_id=3,
        class_name="motorcycle",
        confidence=0.85,
        bbox_xyxy=(950, 500, 1020, 650),
        vcs_x=-4.0,              # Bên hông rơ-moóc
        vcs_y=-2.0,              # Cách hông 2m bên phải
        vel_x=6.0,               # Lao tới với vận tốc tương đối 6m/s
        vel_y=0.0
    )

    dhz = calc.compute_dynamic_hazard_zone(ego)
    result = calc.evaluate_obstacle(motorcycle, ego, dhz)

    print(f"  + Đối tượng: {result.class_name} #{result.track_id}")
    print(f"  + TTC: {result.ttc_seconds}s")
    print(f"  + Điểm BSRI: {result.bsri_score:.3f}")
    print(f"  + Cấp độ: {result.risk_level.label_vi} ({result.risk_level.name})")
    print(f"  + Giải thích: {result.explanation}")

    assert result.ttc_seconds is not None and result.ttc_seconds <= 2.0, f"Kỳ vọng TTC <= 2.0s nhưng nhận {result.ttc_seconds}"
    assert result.risk_level in [RiskLevel.WARNING, RiskLevel.CRITICAL], f"Kỳ vọng WARNING/CRITICAL nhưng nhận {result.risk_level}"
    print("  => [PASS] Đo đạc TTC và cảnh báo va chạm trước thời gian chính xác!")


def test_scenario_4_vru_handcart_xe_keo():
    """
    Kịch bản 4: Xe kéo tự chế (xe_keo) của Việt Nam lọt vào vùng bụng rơ-moóc quét qua.
    Kỳ vọng: Trọng số VRU cao (0.92) đẩy mức cảnh báo lên cao.
    """
    print("\n--- [TEST 4]: Xe kéo (xe_keo) trong vùng lấn lề rơ-moóc ---")
    calc = BSRICalculator()

    ego = EgoVehicleState(
        speed_mps=3.0,
        yaw_rate_rad_s=-0.06,    # Rẽ phải
        turn_signal="RIGHT",
        trailer_gamma_rad=0.25   # Rơ-moóc đang gập góc
    )

    xe_keo = TrackedObstacle(
        track_id=4,
        class_name="xe_keo",
        confidence=0.81,
        bbox_xyxy=(700, 450, 850, 620),
        vcs_x=-3.5,              # Ngang bụng rơ-moóc
        vcs_y=-2.2,              # Bị quét trúng
        vel_x=0.0,
        vel_y=0.1
    )

    dhz = calc.compute_dynamic_hazard_zone(ego)
    result = calc.evaluate_obstacle(xe_keo, ego, dhz)

    print(f"  + Đối tượng: {result.class_name} #{result.track_id} (Trọng số VRU: {result.vru_weight})")
    print(f"  + Vị trí: {result.zone.value}")
    print(f"  + Nằm trong DHZ: {result.is_in_dhz}")
    print(f"  + Điểm BSRI: {result.bsri_score:.3f}")
    print(f"  + Cấp độ: {result.risk_level.label_vi} ({result.risk_level.name})")

    assert result.vru_weight >= 0.90, "Trọng số VRU xe kéo phải đạt mức cao >= 0.90"
    assert result.risk_level in [RiskLevel.WARNING, RiskLevel.CRITICAL]
    print("  => [PASS] Đã áp dụng chuẩn xác trọng số phương tiện đặc thù Việt Nam!")


def test_scenario_5_multi_object_scene_evaluation():
    """
    Kịch bản 5: Đánh giá toàn cảnh với đồng thời nhiều phương tiện (xe con an toàn, xe máy nguy cơ cao).
    Kỳ vọng: Hệ thống tự động trích xuất đúng đối tượng nguy hiểm nhất để ưu tiên cảnh báo tài xế.
    """
    print("\n--- [TEST 5]: Đánh giá toàn cảnh đa đối tượng (Multi-object Scene) ---")
    calc = BSRICalculator()

    ego = EgoVehicleState(speed_mps=6.0, yaw_rate_rad_s=-0.04, turn_signal="RIGHT")

    obstacles = [
        TrackedObstacle(track_id=10, class_name="car", confidence=0.9, bbox_xyxy=(0,0,10,10), vcs_x=20.0, vcs_y=5.0),
        TrackedObstacle(track_id=11, class_name="person", confidence=0.85, bbox_xyxy=(0,0,10,10), vcs_x=1.5, vcs_y=-1.6, vel_x=0.0, vel_y=0.3),
        TrackedObstacle(track_id=12, class_name="truck", confidence=0.8, bbox_xyxy=(0,0,10,10), vcs_x=30.0, vcs_y=-6.0),
    ]

    all_results, highest = calc.evaluate_scene(ego, obstacles)

    print(f"  + Tổng số đối tượng được theo dõi: {len(all_results)}")
    for res in all_results:
        print(f"    - ID #{res.track_id} ({res.class_name}): BSRI={res.bsri_score:.2f} [{res.risk_level.name}]")

    print(f"  => ĐỐI TƯỢNG NGUY HIỂM NHẤT TRÍCH XUẤT: ID #{highest.track_id} ({highest.class_name}) - BSRI {highest.bsri_score:.2f}")
    assert highest.track_id == 11, f"Kỳ vọng đối tượng #11 là nguy hiểm nhất nhưng nhận #{highest.track_id}"
    assert highest.risk_level == RiskLevel.CRITICAL
    print("  => [PASS] Bộ giải mã ưu tiên hiện trường hoạt động chính xác 100%!")


if __name__ == "__main__":
    print("=" * 75)
    print(f"{'BLINDGUARD AI - KIỂM THỬ PHÂN HỆ TÍNH TOÁN RỦI RO BSRI':^75}")
    print("=" * 75)
    test_scenario_1_pedestrian_in_right_turn()
    test_scenario_2_distant_car_moving_away()
    test_scenario_3_fast_approaching_motorcycle()
    test_scenario_4_vru_handcart_xe_keo()
    test_scenario_5_multi_object_scene_evaluation()
    print("\n" + "=" * 75)
    print(f"{'[V] TẤT CẢ 5/5 BÀI KIỂM THỬ KỊCH BẢN BSRI ĐÃ VƯỢT QUA XUẤT SẮC!':^75}")
    print("=" * 75)

