# BlindGuard AI - Video ByteTrack Testing System

Hệ thống kiểm thử & theo dõi đối tượng (Object Detection & ByteTrack Tracking) cho dự án BlindGuard AI.

---

## 🛠️ Hướng dẫn cài đặt thư viện (Pip Installation)

Mở Terminal / Command Prompt và chạy lệnh cài đặt:

```bash
pip install ultralytics opencv-python numpy torch python-dotenv
```

---

## 📌 Đặc điểm kỹ thuật (Model & Preprocessing)

1. **Danh sách 8 lớp giao thông Việt Nam (Ultralytics YOLO11n):**
   - `['bicycle', 'bus', 'car', 'motorcycle', 'person', 'truck', 'xe_keo', 'xich_lo']`

2. **Tiền xử lý Kéo giãn (Stretch 640x640):**
   - Mỗi khung hình video được kéo giãn trực tiếp về `640x640` bằng `cv2.resize(frame, (640, 640))` trước khi đưa vào mô hình.
   - Tọa độ Bounding Box dự đoán sau đó được quy đổi chính xác về kích thước khung hình gốc (`W_orig`, `H_orig`) để vẽ nét căng.

3. **Thuật toán theo dõi ByteTrack:**
   - Sử dụng API công khai `model.track(..., persist=True, tracker="bytetrack_bg.yaml")`.
   - File cấu hình `bytetrack_bg.yaml` được tạo tự động với các ngưỡng tối ưu:
     - `track_high_thresh: 0.25`
     - `track_low_thresh: 0.1` (YOLO conf đặt ở `0.1` để ghép cặp điểm thấp vòng 2)
     - `new_track_thresh: 0.3`
     - `track_buffer: 30`
     - `match_thresh: 0.8`
     - `fuse_score: True`

4. **Trực quan hóa trực tiếp trên Frame gốc:**
   - Box, Tên Lớp, Track ID, Confidence score.
   - **Màu sắc cố định theo từng Track ID:** Giúp phát hiện nhanh hiện tượng nhảy ID / đổi ID.
   - **Vệt quỹ đạo (Trajectory Trail):** Lưu 30 điểm gần nhất tính từ tâm đáy Box (`(x1+x2)/2`, `y2`).

5. **Giao diện Nút bấm GUI Chuột & Báo cáo Thống kê:**
   - Nút bấm Top Panel click trực tiếp bằng chuột.
   - Báo cáo số lượng Unique ID theo từng lớp khi kết thúc để đánh giá ID Switch / Drift.

---

## 💻 Lệnh chạy mẫu (Usage Commands)

### 1. Chạy trực tiếp (Hộp thoại chọn file tự bật lên):
```bash
python 1_AI_Processing_Edge/object_detection/test_video.py
```

### 2. Truyền tham số tùy chỉnh:
```bash
# Chỉ định file weights best.pt và file video
python 1_AI_Processing_Edge/object_detection/test_video.py --weights 1_AI_Processing_Edge/object_detection/weights/best.pt --video my_video.mp4

# Thay đổi ngưỡng Conf và Lưu video kết quả ra file .mp4
python 1_AI_Processing_Edge/object_detection/test_video.py --video input.mp4 --conf 0.1 --save-output
```

---

## ⌨️ Phím tắt & Thao tác

- **Thanh kéo tua (Seekbar Slider):** Click chuột hoặc kéo giữ chuột trên thanh slider ở Top Panel để tua video.
- **Phím Mũi tên `[←]` / `[→]` (hoặc `,` / `.`):** Tua lùi / Tua tới 5 giây.
- **Click chuột:** Sử dụng các nút bấm trực tiếp ở thanh **Top Panel** phía trên màn hình.
- **Phím `[Q]` / `[Esc]`:** Thoát trình xem và in Báo cáo Thống kê ra Terminal.
- **Phím `[Space]`:** Tạm dừng / Tiếp tục phát.
- **Phím `[+]` / `[-]`:** Tăng / Giảm tốc độ phát.
- **Phím `[H]`:** Ẩn / Hiện thanh thông số HUD.
