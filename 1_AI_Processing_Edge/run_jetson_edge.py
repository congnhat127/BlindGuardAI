import cv2
import time
# TODO: Import các module xử lý sau khi viết xong
# from object_detection.yolo_detector import YoloDetector
# from mot_tracking.byte_tracker import ByteTracker
# from trajectory_prediction.kalman import TrajectoryPredictor

def main():
    print("Khởi động hệ thống BlindGuard AI Edge...")
    
    # 1. Khởi tạo Camera stream
    # cap = cv2.VideoCapture("rtsp://...")
    
    # 2. Khởi tạo các model AI
    # detector = YoloDetector(model_path="weights/yolo11s.engine")
    # tracker = ByteTracker()
    
    try:
        while True: # while cap.isOpened():
            # ret, frame = cap.read()
            # if not ret: break
            
            # --- Pipeline Xử lý ---
            # 1. Nhận diện đối tượng (YOLO)
            # 2. Tracking đối tượng (ByteTrack)
            # 3. Dự đoán quỹ đạo (Kalman Filter)
            # 4. Tính toán BSRI (Chỉ số rủi ro điểm mù)
            
            # --- Cảnh báo ---
            # Nếu BSRI > Ngưỡng -> Gửi tín hiệu UART/Socket xuống ESP32
            
            time.sleep(1) # Chờ tạm thời
            print("Đang xử lý luồng video...")
            
    except KeyboardInterrupt:
        print("Tắt hệ thống.")
    # finally:
    #     cap.release()

if __name__ == "__main__":
    main()
