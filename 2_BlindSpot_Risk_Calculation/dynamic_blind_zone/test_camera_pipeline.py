# ==============================================================================
# TEST_CAMERA_PIPELINE.PY: KIỂM THỬ PIPELINE TÍCH HỢP CAMERA REALTIME
# ==============================================================================
import numpy as np
import occlusion_calculator as occ_module
from camera_calibration import CameraCalibrator

def main():
    print("=== KIỂM THỬ PIPELINE TÍCH HỢP MULTI-CAMERA AI REALTIME ===")
    
    calibrator = CameraCalibrator()
    calculator = occ_module.PureOcclusionCalculator()
    
    # 1. Giả lập xe đang chạy 30km/h, bẻ vô-lăng 25 độ
    v_ms = 30.0 / 3.6
    steer_deg = 25.0
    calculator.update_kinematics(v_ms, np.radians(steer_deg), dt=0.1, is_steering_angle=True)
    
    # Tính các vùng nguy hiểm thực tế
    zones = calculator.compute_all(v_ms, np.radians(steer_deg), dt=0.1, is_steering_angle=True)
    print(f"[1] Đã tính xong {len(zones['occlusion_zones'])} đa giác vùng mù và {len(zones['swept_path'])} vùng lấn lề.")

    # 2. Giả lập điểm thực trên mặt đường hông phải xe: X = -5.0m, Y = -3.0m (vùng nguy hiểm)
    real_gt_pt = (-5.0, -3.0, 0.0)
    camera_name = "MIRROR_R"
    
    # Chiếu xuôi từ 3D VCS -> 2D Camera Pixel
    pix_2d = calibrator.project_3d_ground_point_to_2d_image(real_gt_pt, camera_name)
    print(f"[2] Điểm thực 3D (X=-5.0m, Y=-3.0m) chiếu lên Camera {camera_name} tại Pixel: {pix_2d}")

    if pix_2d is not None:
        u_mid, v_max = float(pix_2d[0]), float(pix_2d[1])
        # Chiếu ngược từ 2D Pixel -> 3D VCS mặt đường
        ground_pt = calibrator.project_2d_image_point_to_3d_ground(u_mid, v_max, camera_name)
        print(f"    -> Giả lập YOLO11 trích xuất Pixel ({u_mid}, {v_max})")
        print(f"    -> Tọa độ khôi phục Homography Inverse: X = {ground_pt[0]:.2f}m, Y = {ground_pt[1]:.2f}m")

        # 3. Kiểm tra Point-in-Polygon (Đối tượng có nằm trong vùng mù không)
        is_in_blind_spot = False
        for name, poly in zones['occlusion_zones'].items():
            if calculator.is_point_in_polygon(ground_pt, poly):
                print(f"    [ALERT WARNING!] Đối tượng nằm TRONG {name}!")
                is_in_blind_spot = True
                break
                
        if not is_in_blind_spot:
            print("    [SAFE] Đối tượng ở khoảng an toàn ngoài vùng mù.")

    # 4. Chiếu ngược lại đa giác Vùng mù từ Metric 3D -> 2D Pixel Ảnh Camera để vẽ Overlay
    print(f"[3] Chiếu Đa giác Vùng mù từ Không gian Mét lên Khung ảnh Video 2D:")
    for name, poly in zones['occlusion_zones'].items():
        pixels_2d = []
        for pt in poly:
            pix = calibrator.project_3d_ground_point_to_2d_image((pt[0], pt[1], 0.0), camera_name)
            if pix is not None:
                pixels_2d.append(pix)
        print(f"    -> {name}: {len(pixels_2d)}/{len(poly)} đỉnh hiển thị trên camera screen.")

if __name__ == "__main__":
    main()
