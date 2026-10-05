# 🛡️ BLINDGUARD AI — TÀI LIỆU KỸ THUẬT & HƯỚNG DẪN TRIỂN KHAI HỆ THỐNG (BLINDGUARD APP)

> **Hệ thống hỗ trợ an toàn & cảnh báo điểm mù thông minh phi xâm lấn dành cho xe tải hạng nặng & xe đầu kéo sơ-mi rơ-moóc.**  
> Tuân thủ các tiêu chuẩn an toàn quốc tế: **ISO 8855, ISO 15623, UNECE R151 (BSIS), UNECE R158 (Reversing), UNECE R159 (MOIS)**.

---

## 📑 MỤC LỤC
1. [Tổng quan Kiến trúc & Chức năng từng File](#1-tổng-quan-kiến-trúc--chức-năng-từng-file)
2. [Hướng dẫn sử dụng trên PC/Laptop (Môi trường Phát triển)](#2-hướng-dẫn-sử-dụng-trên-pclaptop-môi-trường-phát-triển)
3. [Gói Triển khai Tối giản lên Jetson (Cần nạp những file nào? Bỏ những file nào?)](#3-gói-triển-khai-tối-giản-lên-jetson-cần-nạp-những-file-nào-bỏ-những-file-nào)
4. [Triển khai Môi trường trên NVIDIA Jetson (Nano / Xavier NX / Orin)](#4-triển-khai-môi-trường-trên-nvidia-jetson-nano--xavier-nx--orin)
5. [Thay đổi Code khi chuyển sang Live Camera, ESP32 & Cảm biến](#5-thay-đổi-code-khi-chuyển-sang-live-camera-esp32--cảm-biến)
6. [Bảng Phân tích Thư viện & Độ tương thích Jetson (ARM64)](#6-bảng-phân-tích-thư-viện--độ-tương-thích-jetson-arm64)
7. [Sơ đồ Đấu nối Phần cứng (Jetson ↔ ESP32 ↔ Cảm biến)](#7-sơ-đồ-đấu-nối-phần-cứng-jetson--esp32--cảm-biến)
8. [Các lỗi thường gặp và Cách khắc phục (Troubleshooting)](#8-các-lỗi-thường-gặp-và-cách-khắc-phục-troubleshooting)

---

## 1. TỔNG QUAN KIẾN TRÚC & CHỨC NĂNG TỪNG FILE

Toàn bộ ứng dụng được đóng gói gọn trong thư mục `BlindGuard_App/` theo cấu trúc module phân tầng:

```text
BlindGuard_App/
│
├── 📜 README.md                         # Tài liệu hướng dẫn sử dụng & triển khai chi tiết này
├── 📜 SYSTEM_MATHEMATICAL_MODEL.md      # Đặc tả toàn diện các công thức toán học, động học & tiêu chuẩn
│
├── 🚀 run_demo.py                       # Pipeline trình diễn chính: Video -> YOLOv11 -> ByteTrack -> Homography -> BSRI -> HUD
├── ⚡ run_demo.bat                      # Phím tắt Click-and-Run khởi chạy Demo tức thì trên Windows
│
├── 🎛️ run_bsri_simulator_gui.py         # Ứng dụng GUI mô phỏng kiểm thử độc lập động học xe & giải thuật BSRI (Không cần video/YOLO)
├── ⚡ run_bsri_simulator.bat             # Phím tắt mở Simulator GUI trên Windows
│
├── ⚙️ run_config.bat                    # Phím tắt mở Trình cấu hình xe & Homography trên Windows
│
├── 📁 config/                           # Thư mục chứa cấu hình hệ thống
│   ├── system_config.json               # Lưu thông số hình học xe tải & ma trận Homography 4 góc camera
│   └── bytetrack_fisheye.yaml           # Siêu tham số ByteTrack tối ưu riêng cho camera góc rộng/mắt cá
│
├── 📁 system_configurator/              # Module cấu hình giao diện Wizard 2 bước
│   ├── run_configurator_gui.py          # GUI Wizard: Bước 1 (Thông số xe) -> Bước 2 (Chụp ảnh & Click mốc tính Homography)
│   └── __init__.py
│
├── 📁 core/                             # Thư viện xử lý logic nghiệp vụ cốt lõi
│   ├── config_loader.py                 # Tự động nạp, kiểm tra tính hợp lệ và ghi file JSON cấu hình
│   ├── risk_models.py                   # Định nghĩa các Data Class chuẩn: EgoVehicleState, TrackedObstacle, BSRIResult, RiskLevel
│   ├── homography_manager.py            # Quản lý ma trận biến đổi phối cảnh 3x3: Pixel (u,v) <-> Hệ tọa độ xe VCS (X,Y) mét
│   ├── bsri_calculator.py               # Lõi tính toán rủi ro BSRI, đa giác động DHZ (0.5s), vi phân Ellis 1969, TTC, R151/R158/R159
│   ├── hud_renderer.py                  # Dựng khung hình Cabin HUD: Vẽ Bounding Box, vệt nguy hiểm DHZ, nhãn giải thích XAI
│   └── motion_analyzer.py               # Phân tích trạng thái chuyển động xe chủ phi xâm lấn (Non-invasive CAN-bus free)
│
└── 📁 weights/                          # Trọng số mô hình AI đã huấn luyện
    ├── yolo11n_v4.onnx                  # Trọng số YOLOv11n v4 định dạng ONNX (sẵn sàng nạp hoặc convert sang TensorRT Engine)
    └── yolo11n_v3.onnx                  # Trọng số YOLOv11n v3 định dạng ONNX (dự phòng)
```

### Chi tiết chức năng từng file mã nguồn:

| Tên File | Vai trò & Trách nhiệm chính | Đầu vào (Input) | Đầu ra (Output) |
|---|---|---|---|
| **`run_demo.py`** | Pipeline kết nối toàn bộ hệ thống từ đầu vào video đến màn hình hiển thị HUD buồng lái. | Video file / Camera stream, `system_config.json`, weights YOLO. | Luồng hiển thị Cabin HUD, cảnh báo nguy cơ theo thời gian thực. |
| **`run_bsri_simulator_gui.py`** | Công cụ mô phỏng 2D cho phép người dùng kéo thả vật thể, chỉnh góc lái, vận tốc, gia tốc để kiểm chứng thuật toán toán học BSRI & DHZ độc lập. | Thao tác chuột, thanh trượt trên UI. | Bản đồ trực quan 2D hệ tọa độ VCS, đa giác DHZ, bảng giải thích XAI. |
| **`system_configurator/run_configurator_gui.py`** | Giao diện đồ họa hướng dẫn người dùng thiết lập kích thước xe và căn chỉnh 4 điểm mốc mặt đất để hệ thống tự tính ma trận Homography. | Ảnh chụp thực tế từ 4 camera, thông số thước đo thật (mét). | Ma trận Homography $H_{3 \times 3}$, lưu tự động vào `system_config.json`. |
| **`core/risk_models.py`** | Khai báo các cấu trúc dữ liệu cốt lõi (Enums, Dataclasses) tuân thủ tiêu chuẩn ISO 8855 (VCS: $+X$ tiến, $+Y$ trái). | N/A | `EgoVehicleState`, `TrackedObstacle`, `BSRIResult`, `RiskLevel`. |
| **`core/config_loader.py`** | Trình nạp và kiểm tra dữ liệu cấu hình, tự động tạo giá trị mặc định nếu file cấu hình bị thiếu hoặc hỏng. | Đường dẫn file `system_config.json`. | Object `SystemConfigManager` với các thuộc tính xe và ma trận camera. |
| **`core/homography_manager.py`** | Chuyển đổi tọa độ từ mặt phẳng ảnh pixel sang hệ trục tọa độ xe VCS (mét) và ngược lại; lọc bỏ các điểm ảo trên đường chân trời. | Tọa độ pixel $(u, v)$, tên góc camera. | Tọa độ mặt đất $(X, Y)$ mét, khoảng cách Euclidean. |
| **`core/bsri_calculator.py`** | "Bộ não" tính toán rủi ro: Tích phân quỹ đạo xe $0.5\text{s}$ (Midpoint), mô hình góc gập rơ-moóc Ellis 1969, chém cua Inswing, văng đuôi Tail-swing, TTC va chạm, sinh lời giải thích XAI. | `EgoVehicleState`, danh sách `TrackedObstacle`. | Đa giác `DHZ`, danh sách `BSRIResult`, đối tượng nguy hiểm nhất `highest_threat`. |
| **`core/hud_renderer.py`** | Vẽ lớp hiển thị giao diện người lái (HUD) công nghệ cao, hiển thị bounding box màu theo mức nguy hiểm, đa giác DHZ, la bàn rủi ro. | Ảnh gốc `frame`, kết quả BSRI. | Khung hình OpenCV đã gắn đồ họa HUD. |
| **`core/motion_analyzer.py`** | Ước lượng trạng thái vận tốc và hướng lái của xe chủ mà không cần can thiệp cổng CAN-bus của xe (bảo toàn bảo hành xe). | Dữ liệu kẹp dòng xi-nhan / IMU / Phím bấm mô phỏng. | Tuple `(speed_mps, yaw_rate_rad_s, turn_signal, gear)`. |

---

## 2. HƯỚNG DẪN SỬ DỤNG TRÊN PC/LAPTOP (MÔI TRƯỜNG PHÁT TRIỂN)

### Bước 1: Chuẩn bị môi trường Python
Yêu cầu Python phiên bản `3.8`, `3.9`, `3.10` hoặc `3.11`.
```bash
# Tạo môi trường ảo (Khuyến nghị)
python -m venv .venv

# Kích hoạt trên Windows
.venv\Scripts\activate

# Cài đặt các thư viện cần thiết
pip install ultralytics opencv-python numpy shapely pyyaml pyserial
```

### Bước 2: Chạy các chương trình

#### Cách 1: Chạy Trình Diễn Video Demo
* **Cách nhanh nhất**: Nhấp đúp chuột vào file **`run_demo.bat`**.
* **Hoặc chạy bằng dòng lệnh**:
  ```bash
  python run_demo.py
  ```
* **Thao tác trong lúc xem video**:
  * `[SPACE]` : Tạm dừng / Tiếp tục video.
  * `[C]`     : Chuyển đổi qua lại giữa 4 góc camera (`MIRROR_RIGHT` $\to$ `MIRROR_LEFT` $\to$ `CAB_FRONT` $\to$ `REAR_TRAILER`).
  * `[V]`     : Mở hộp thoại chọn video khác.
  * `[D]`     : Bật / Tắt hiển thị vùng nguy hiểm động DHZ.
  * `[+]` / `[-]` : Tăng / Giảm tốc độ xe chủ; `[0]` : Dừng xe khẩn cấp.
  * `[J]` / `[L]` : Bẻ lái Trái / Phải; `[K]` : Trả lái thẳng.
  * `[R]`     : Gài số lùi (Kích hoạt kịch bản UNECE R158).
  * `[Q]` hoặc `[ESC]` : Thoát chương trình.

#### Cách 2: Chạy Môi Trường Mô Phỏng BSRI Simulator (Không cần Video/AI)
* **Cách nhanh nhất**: Nhấp đúp chuột vào file **`run_bsri_simulator.bat`**.
* **Tính năng**:
  * Kiểm tra và tương tác trực quan với 6 kịch bản điểm nóng: *Xe máy chui bụng cua phải/trái (Inswing), Người đi bộ cắt đầu xe (MOIS R159), Xe máy bị quét đuôi (Tail-swing), Người đứng sau đuôi xe lùi (R158), Chạy song song an toàn*.
  * Cho phép bấm chuột trái để kéo thả vị trí vật thể theo thời gian thực.
  * Click chuột phải để tạo nhanh vật thể mới; điều chỉnh vận tốc, góc hướng di chuyển của vật thể và xem BSRI nhảy số tức thì.

#### Cách 3: Chạy Trình Cấu Hình Căn Chỉnh Xe & Camera
* **Cách nhanh nhất**: Nhấp đúp chuột vào file **`run_config.bat`**.
* Dùng khi bạn thay đổi loại xe tải hoặc gắn camera ở góc đặt mới để tính lại ma trận Homography.

---

## 3. GÓI TRIỂN KHAI TỐI GIẢN LÊN JETSON (CẦN NẠP NHỮNG FILE NÀO? BỎ NHỮNG FILE NÀO?)

> ⚠️ **CẢNH BÁO QUAN TRỌNG: TUYỆT ĐỐI KHÔNG COPY NGUYÊN CẢ PROJECT LÊN JETSON!**  
> 1. Thẻ nhớ của Jetson (thường 32GB - 64GB) rất hạn chế; riêng hệ điều hành Ubuntu và JetPack đã chiếm ~18GB, cộng thêm 6GB Swap thì dung lượng trống chỉ còn khoảng 6 - 8GB.  
> 2. Toàn bộ thư mục dự án trên PC có thể nặng **5 - 10 GB** (chứa video test, datasets, `.venv` Windows, file cache). Nếu copy bừa bãi sẽ làm tràn thẻ nhớ, treo hệ điều hành.  
> 3. Thư mục môi trường ảo `.venv` trên Windows chứa các file binary x86-64 và thư viện `.dll`, nếu nạp sang chip ARM64 của Jetson sẽ **gây lỗi xung đột và hỏng hoàn toàn môi trường Python của Jetson**.

---

### 3.1. Cây thư mục Tối giản Dành riêng cho Jetson (Chỉ ~15 - 20 MB)

Để Jetson chạy tự hành thời gian thực, bạn **chỉ cần nạp duy nhất các file/thư mục sau đây**:

```text
blindguard_edge/                      <-- Thư mục làm việc trên Jetson (Tổng dung lượng ~15 MB)
│
├── run_demo.py                       # Pipeline suy luận AI chính (đã sửa sang Live cam + ESP32)
├── setup_jetson_nano.sh              # Script cấu hình swap, uart và dependencies cho Jetson
│
├── config/                           # Thư mục cấu hình (BẮT BUỘC)
│   ├── system_config.json            # File cấu hình xe & Homography (Căn chỉnh xong trên PC rồi copy qua)
│   └── bytetrack_fisheye.yaml        # Siêu tham số ByteTrack
│
├── core/                             # Thư viện thuật toán cốt lõi (BẮT BUỘC)
│   ├── bsri_calculator.py            # Lõi tính BSRI, DHZ, TTC, mô hình Ellis 1969
│   ├── homography_manager.py         # Chiếu tọa độ pixel sang tọa độ mét VCS
│   ├── risk_models.py                # Định nghĩa Dataclass EgoVehicleState, Obstacle, RiskLevel
│   ├── config_loader.py              # Đọc file system_config.json
│   ├── motion_analyzer.py            # Phân tích trạng thái xe
│   └── hud_renderer.py               # Dựng hình Cabin HUD (cần nếu có xuất màn hình trong cabin)
│
├── weights/                          # Thư mục model AI (BẮT BUỘC)
│   └── yolo11n_v4.onnx               # Model ONNX (~10 MB) để Jetson tự build thành .engine
│
└── 3_Hardware_Embedded/              # Giao tiếp phần cứng (BẮT BUỘC)
    └── jetson_serial_driver.py       # Driver UART giao tiếp 2 chiều với ESP32
```

---

### 3.2. Bảng Đối chiếu Chi tiết: File CẦN nạp vs File TUYỆT ĐỐI BỎ LẠI

| Thành phần | Cần nạp lên Jetson? | Dung lượng | Lý do & Giải thích |
|---|:---:|:---:|---|
| **`run_demo.py`** | ✅ **BẮT BUỘC** | ~22 KB | File thực thi chính chạy vòng lặp Camera $\to$ YOLO $\to$ BSRI $\to$ ESP32. |
| **`config/system_config.json`** | ✅ **BẮT BUỘC** | ~10 KB | Chứa thông số xe và ma trận Homography đã căn chỉnh chuẩn xác từ PC. |
| **`config/bytetrack_fisheye.yaml`** | ✅ **BẮT BUỘC** | ~1 KB | Tham số bộ lọc ByteTrack theo dõi vật thể. |
| **`core/`** (toàn bộ 6 file) | ✅ **BẮT BUỘC** | ~100 KB | Bộ não tính toán động học và rủi ro điểm mù. |
| **`weights/yolo11n_v4.onnx`** | ✅ **BẮT BUỘC** | ~10 MB | Trọng số mô hình AI để chuyển đổi sang TensorRT `.engine` trên Jetson. |
| **`3_Hardware_Embedded/jetson_serial_driver.py`** | ✅ **BẮT BUỘC** | ~8 KB | Nhận GPS/IMU từ ESP32 và gửi lệnh còi hú cảnh báo. |
| **`setup_jetson_nano.sh`** | ✅ **BẮT BUỘC** | ~5 KB | Script thiết lập môi trường MAX-N, Swap 6GB, UART trên Jetson. |
| **TẤT CẢ FILE `.bat`** (`run_demo.bat`,...) | ❌ **BỎ QUA** | 0 KB | Batch script của Windows, Linux Ubuntu trên Jetson không hỗ trợ. |
| **`run_bsri_simulator_gui.py`** | ❌ **BỎ QUA** | 0 KB | GUI mô phỏng kéo thả test thuật toán trên PC. Trên xe chạy camera thật, không cần. |
| **`system_configurator/`** | ❌ **BỎ QUA** | 0 KB | Trình wizard căn chỉnh camera bằng chuột. Chỉ chạy trên Laptop, sau đó copy file `system_config.json` sang. |
| **Môi trường ảo `.venv/`** | ❌ **TUYỆT ĐỐI BỎ** | ~2 - 4 GB | **Nguy hiểm**: Chứa binary x86 của Windows, gây crash môi trường ARM64 trên Jetson. |
| **Video test `.mp4`, `.avi`** | ❌ **BỎ QUA** | ~1 - 5 GB | Nặng thẻ nhớ; trên xe Jetson nhận tín hiệu trực tiếp từ camera thật. |
| **Thư mục huấn luyện AI `runs/`, `data/`** | ❌ **BỎ QUA** | ~5 - 10 GB | Chỉ phục vụ quá trình train model trên máy tính GPU mạnh. |
| **Trọng số trùng lặp `.pt` cũ** | ❌ **BỎ QUA** | ~200 MB | Đã có file ONNX tối ưu, không cần đem theo nhiều bản PyTorch nặng nề. |
| **`__pycache__/`, `.git/`** | ❌ **BỎ QUA** | ~100 MB | Rác bộ nhớ đệm và lịch sử git không cần thiết trên thiết bị nhúng. |

---

### 3.3. Lệnh Đóng gói Nhanh 1-Click từ PC sang Jetson

Để không phải copy thủ công từng file, bạn mở **PowerShell** trên máy tính (tại thư mục gốc của dự án `d:\Programing\BlindGuardAI`) và chạy lệnh sau để tự động nén đúng các file cần thiết thành 1 file zip siêu nhẹ **`blindguard_jetson_deploy.zip`** (~15 MB):

```powershell
# Chạy trên Windows PowerShell:
Compress-Archive -Path `
    BlindGuard_App\run_demo.py, `
    BlindGuard_App\config, `
    BlindGuard_App\core, `
    BlindGuard_App\weights\yolo11n_v4.onnx, `
    3_Hardware_Embedded\jetson_serial_driver.py, `
    setup_jetson_nano.sh `
    -DestinationPath blindguard_jetson_deploy.zip -Force

Write-Host "✅ Đã đóng gói thành công blindguard_jetson_deploy.zip! Dung lượng chỉ ~15MB!" -ForegroundColor Green
```

Sau đó copy file `blindguard_jetson_deploy.zip` này vào USB hoặc gửi sang Jetson qua Wi-Fi/LAN bằng lệnh `scp`:
```bash
# Bắn file sang Jetson qua mạng nội bộ (IP ví dụ: 192.168.1.50):
scp blindguard_jetson_deploy.zip nano@192.168.1.50:~/

# Trên terminal Jetson, chỉ cần giải nén:
unzip ~/blindguard_jetson_deploy.zip -d ~/blindguard_edge
cd ~/blindguard_edge
```

---

## 4. TRIỂN KHAI MÔI TRƯỜNG TRÊN NVIDIA JETSON (NANO / XAVIER NX / ORIN)

Khi đưa lên phần cứng nhúng NVIDIA Jetson, hệ thống sẽ chuyển từ chế độ "phát lại video giả lập" sang chế độ **"Real-time Edge AI System"** kết nối trực tiếp với Camera thật và Vi điều khiển ESP32.

### 4.1. Thiết lập ban đầu trên Jetson (Chạy 1 lần)
Mở Terminal trên Jetson và chạy các lệnh tối ưu hóa phần cứng (hoặc chạy script `bash setup_jetson_nano.sh`):

```bash
# 1. Kích hoạt chế độ công suất tối đa (MAX-N) và khóa xung nhịp cực đại
sudo nvpmodel -m 0
sudo jetson_clocks

# 2. Tạo bộ nhớ ảo SWAP 6GB (BẮT BUỘC ĐỂ TRÁNH TRÀN RAM GÂY OOM KHI LOAD MODEL)
sudo fallocate -l 6G /swapfile_blindguard
sudo chmod 600 /swapfile_blindguard
sudo mkswap /swapfile_blindguard
sudo swapon /swapfile_blindguard
echo "/swapfile_blindguard none swap sw 0 0" | sudo tee -a /etc/fstab

# 3. Giải phóng cổng UART phần cứng (/dev/ttyTHS1) kết nối ESP32
# Vô hiệu hóa nvgetty (tiến trình chiếm cổng serial làm console debug)
sudo systemctl stop nvgetty
sudo systemctl disable nvgetty
sudo usermod -aG dialout $USER
sudo chmod 666 /dev/ttyTHS1
```

### 4.2. Cài đặt các thư viện cần thiết trên Jetson
```bash
# Cập nhật hệ thống
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev libopenblas-base libopenmpi-dev \
                        libomp-dev libjpeg-dev zlib1g-dev v4l-utils \
                        gstreamer1.0-tools gstreamer1.0-plugins-base \
                        gstreamer1.0-plugins-good gstreamer1.0-plugins-bad

# Cài đặt các gói Python nền tảng
python3 -m pip install --upgrade pip
python3 -m pip install pyserial shapely filterpy pyyaml tqdm matplotlib
```

> ⚠️ **LƯU Ý CỰC KỲ QUAN TRỌNG VỀ PYTORCH TRÊN JETSON**:  
> **TUYỆT ĐỐI KHÔNG DÙNG LỆNH `pip install torch torchvision`!** Lệnh này sẽ tải bản binary x86 không chạy được trên chip ARM64 hoặc bản CPU không có CUDA.  
> Hãy cài wheel PyTorch chính thức dành riêng cho JetPack do NVIDIA cung cấp (xem bảng ở Mục 6).

---

## 5. THAY ĐỔI CODE KHI CHUYỂN SANG LIVE CAMERA, ESP32 & CẢM BIẾN

Dưới đây là bảng hướng dẫn chi tiết những vị trí cần chỉnh sửa trong `run_demo.py` khi chuyển từ bản Demo PC sang bản Triển khai Thực tế trên xe:

### 5.1. Thay đổi nguồn Video (`cv2.VideoCapture`) sang Live Camera

Trong file `run_demo.py` (khoảng dòng 248):

```python
# ==============================================================================
# CODE CŨ (DEMO FILE VIDEO TRÊN PC):
# ==============================================================================
cap = cv2.VideoCapture(video_path)


# ==============================================================================
# CODE MỚI KHI LÊN JETSON (CHỌN 1 TRONG 3 LOẠI CAMERA THỰC TẾ DƯỚI ĐÂY):
# ==============================================================================

# --- TRƯỜNG HỢP A: Camera USB thông thường (Webcam / USB Fisheye) ---
CAMERA_INDEX = 0  # /dev/video0
cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 30)

# --- TRƯỜNG HỢP B: Camera CSI (MIPI IMX219 / IMX477 cắm trực tiếp cáp FPC) ---
# Dùng GStreamer pipeline tận dụng phần cứng giải mã phần cứng NVMM của Jetson:
def get_csi_gstreamer_pipeline(sensor_id=0, capture_w=1280, capture_h=720, display_w=1280, display_h=720, fps=30, flip_method=0):
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        f"video/x-raw(memory:NVMM), width=(int){capture_w}, height=(int){capture_h}, format=(string)NV12, framerate=(fraction){fps}/1 ! "
        f"nvvidconv flip-method={flip_method} ! "
        f"video/x-raw, width=(int){display_w}, height=(int){display_h}, format=(string)BGRx ! "
        f"videoconvert ! "
        f"video/x-raw, format=(string)BGR ! appsink drop=1"
    )

cap = cv2.VideoCapture(get_csi_gstreamer_pipeline(sensor_id=0), cv2.CAP_GSTREAMER)

# --- TRƯỜNG HỢP C: Camera IP Xe Tải / RTSP Stream (Camera HIKVISION/Dahua gắn quanh xe) ---
# Bổ sung flag độ trễ thấp (latency=0) để không bị lag khung hình:
rtsp_url = "rtsp://admin:password123@192.168.1.100:554/Streaming/Channels/101"
gstreamer_rtsp = f"rtspsrc location={rtsp_url} latency=0 ! rtph264depay ! h264parse ! nvv4l2decoder ! nvvidconv ! video/x-raw, format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink drop=1"
cap = cv2.VideoCapture(gstreamer_rtsp, cv2.CAP_GSTREAMER)
```

---

### 5.2. Chuyển đổi Model AI sang NVIDIA TensorRT Engine (`.engine`)

Chạy PyTorch trực tiếp trên Jetson Nano chỉ đạt khoảng 3-5 FPS. Để đạt tốc độ thời gian thực **25 - 35 FPS**, bắt buộc phải xuất model sang TensorRT Engine:

#### Bước 1: Build file `.engine` ngay trên Jetson
Chạy lệnh bằng công cụ `trtexec` tích hợp sẵn của Jetson:
```bash
/usr/src/tensorrt/bin/trtexec \
    --onnx=weights/yolo11n_v4.onnx \
    --saveEngine=weights/yolo11n_v4.engine \
    --fp16 \
    --workspace=1024
```

#### Bước 2: Nạp file `.engine` trong code
Trong file `run_demo.py` (khoảng dòng 236):
```python
# ==============================================================================
# CODE CŨ:
# ==============================================================================
model_path = discover_best_model_path()
model = YOLO(model_path)

# ==============================================================================
# CODE MỚI DÀNH CHO JETSON:
# ==============================================================================
engine_path = "weights/yolo11n_v4.engine"
if not os.path.exists(engine_path):
    raise FileNotFoundError(f"Chưa tìm thấy file TensorRT engine: {engine_path}. Hãy chạy trtexec để build trước!")

model = YOLO(engine_path, task="detect")
print(f"[+] Đã kích hoạt TensorRT Engine tăng tốc phần cứng: {engine_path}")
```

---

### 5.3. Tích hợp ESP32 Serial Driver để nhận dữ liệu Xe & Bắn cảnh báo

Trong bản demo, trạng thái xe được giả lập cố định hoặc điều khiển bằng phím bấm. Khi triển khai thật, ta sẽ dùng driver [jetson_serial_driver.py](file:///d:/Programing/BlindGuardAI/3_Hardware_Embedded/jetson_serial_driver.py):

#### Bước 1: Khởi tạo Driver trước vòng lặp chính
Thêm vào trước `while True:` trong `run_demo.py`:
```python
# Import driver phần cứng nối tiếp
from 3_Hardware_Embedded.jetson_serial_driver import JetsonSerialDriver

# Khởi tạo kết nối UART tới ESP32 (cổng J41 UART hoặc USB to TTL)
serial_driver = JetsonSerialDriver(port="/dev/ttyTHS1", baudrate=115200)
serial_driver.start()
print("[+] Đã kết nối với bộ điều khiển ESP32 Hardware Warning Hub.")
```

#### Bước 2: Lấy dữ liệu xe thật (GPS, IMU, Xi-nhan) từ ESP32
Thay thế đoạn đọc `motion_analyzer.get_motion_state()` (khoảng dòng 324):
```python
# ==============================================================================
# CODE CŨ (GIẢ LẬP):
# ==============================================================================
# spd, yaw_r, turn_dir, gear = motion_analyzer.get_motion_state()
# ego_state = EgoVehicleState(speed_mps=spd, yaw_rate_rad_s=yaw_r, turn_signal=turn_dir, gear=gear)

# ==============================================================================
# CODE MỚI (LẤY DỮ LIỆU CẢM BIẾN THẬT THỜI GIAN THỰC TỪ ESP32 QUA GÓI $EGO):
# ==============================================================================
ego_state = serial_driver.get_ego_state()
# ego_state này chứa đầy đủ:
# - ego_state.speed_mps       : Lấy từ GPS u-blox NEO-8M
# - ego_state.yaw_rate_rad_s  : Lấy từ con quay hồi chuyển IMU (gyro trục Z)
# - ego_state.turn_signal     : Nhận biết qua kẹp cảm biến dòng xi-nhan ("LEFT", "RIGHT", "OFF")
# - ego_state.gear            : "D" (Tiến) hoặc "R" (Số lùi)
```

#### Bước 3: Phát tín hiệu cảnh báo BSRI xuống Còi & Đèn LED của ESP32
Ngay sau khi có kết quả tính toán `highest_threat = bsri_calc.evaluate_scene(...)` (khoảng dòng 389):
```python
# Gửi gói tin cảnh báo chuẩn NMEA ($BSRI,level,score,track_id,zone_id,ttc*CS) xuống ESP32
if highest_threat is not None:
    serial_driver.send_threat_result(highest_threat)
else:
    # Không có vật thể nguy hiểm -> Gửi mức 0 (SAFE) để ngắt còi hú
    serial_driver.send_bsri_warning(level_code=0, score=0.0, track_id=0, zone_id=0, ttc_seconds=None)
```

#### Bước 4: Đóng cổng an toàn khi kết thúc
Trong khối thoát chương trình (sau khi break vòng lặp `while`):
```python
serial_driver.stop()
```

---

### 5.4. Tối ưu chạy Headless (Không cần màn hình Desktop)

Trên xe tải, Jetson thường hoạt động như một máy tính điều khiển nhúng ẩn dưới taplo, không gắn màn hình máy tính. Nếu cố gọi `cv2.imshow()`, chương trình sẽ báo lỗi `cannot connect to X server`.

Cách sửa đổi:
Thêm tham số dòng lệnh `--headless`:
```python
parser.add_argument("--headless", action="store_true", help="Chạy chế độ nền không mở cửa sổ GUI")
args = parser.parse_args()

# Trong vòng lặp while:
if not args.headless:
    cv2.imshow(win_name, display_frame)
    key = cv2.waitKey(wait_ms) & 0xFF
else:
    # Ở chế độ headless: Không vẽ imshow, chỉ duy trì nhịp frame
    time.sleep(0.005)
```

---

## 6. BẢNG PHÂN TÍCH THƯ VIỆN & ĐỘ TƯƠNG THÍCH JETSON (ARM64)

| Tên Thư Viện | Phiên bản khuyến nghị | Độ tương thích Jetson | Hướng dẫn cài đặt & Lưu ý quan trọng |
|---|---|:---:|---|
| **Python** | 3.6 (JP 4.6) hoặc 3.8 (JP 5.x) | 🟢 100% | Có sẵn theo bản cài đặt JetPack của NVIDIA. |
| **OpenCV** | 4.5.x (kèm CUDA & GStreamer) | 🟢 100% | **KHÔNG DÙNG** `pip install opencv-python`. Hãy dùng bản OpenCV dựng sẵn đi kèm JetPack để hỗ trợ giải mã phần cứng qua GStreamer. |
| **PyTorch (torch)** | 1.10.0 (JP 4.6) hoặc 2.0.0+ (JP 5.x) | 🟡 Cần cài đúng | **Bắt buộc tải wheel NVIDIA:**<br>`wget https://nvidia.box.com/shared/static/p57jwntv436lfrd78inwl7mk6vrrpqeq.whl -O torch-1.10.0-cp36-linux_aarch64.whl`<br>`pip3 install torch-1.10.0-cp36-linux_aarch64.whl` |
| **Torchvision** | 0.11.1 | 🟡 Cần cài đúng | Biên dịch từ source khớp với bản PyTorch hoặc dùng wheel của NVIDIA. |
| **TensorRT** | 8.2.x (tích hợp JetPack) | 🟢 100% | Cài sẵn qua JetPack. Thư viện Python: `import tensorrt as trt`. |
| **Ultralytics** | >= 8.3.0 | 🟢 Hoạt động tốt | `pip3 install ultralytics`. Chạy suy luận trực tiếp với file `.engine`. |
| **Shapely** | 1.8.x / 2.0.x | 🟢 100% | `pip3 install shapely`. Tính toán đa giác hình học DHZ rất nhanh trên ARM CPU. |
| **FilterPy** | 1.4.5 | 🟢 100% | `pip3 install filterpy`. Dùng cho thuật toán Kalman Filter của tracker. |
| **PySerial** | 3.5 | 🟢 100% | `pip3 install pyserial`. Giao tiếp UART với ESP32 qua `/dev/ttyTHS1`. |
| **NumPy** | 1.19.5 (Python 3.6) hoặc 1.23+ | 🟢 100% | `pip3 install numpy==1.19.5` (tránh lỗi xung đột ABI trên Python 3.6). |
| **PyYAML** | >= 5.4 | 🟢 100% | `pip3 install pyyaml`. Nạp cấu hình ByteTrack fisheye. |

---

## 7. SƠ ĐỒ ĐẤU NỐI PHẦN CỨNG (JETSON ↔ ESP32 ↔ CẢM BIẾN)

### 7.1. Kết nối Cổng Nối Tiếp UART giữa Jetson Nano và ESP32
Sử dụng header J41 (40 chân) trên Jetson Nano:

| Chân Jetson Nano B01 (Header J41) | Chân ESP32 DevKit V1 | Chức năng | Ghi chú |
|---|---|---|---|
| **Pin 6 (GND)** | **GND** | Nối đất chung | **BẮT BUỘC** chung Mass để tín hiệu không bị nhiễu |
| **Pin 8 (UART1 TXD - /dev/ttyTHS1)** | **GPIO 3 (RX0)** | Truyền từ Jetson sang ESP32 | Gửi gói tin cảnh báo `$BSRI` |
| **Pin 10 (UART1 RXD - /dev/ttyTHS1)**| **GPIO 1 (TX0)** | Nhận từ ESP32 về Jetson | Gửi dữ liệu telemetry xe `$EGO` |

*(Lưu ý: Nếu không dùng header J41, bạn có thể cắm ESP32 qua cáp Micro-USB vào cổng USB của Jetson, cổng nhận diện sẽ là `/dev/ttyUSB0`)*.

### 7.2. Kết nối Ngoại vi trên ESP32:
* **GPS u-blox NEO-6M / M8N**:
  * `GPS TX` $\to$ `ESP32 GPIO 16 (RX2)`
  * `GPS RX` $\to$ `ESP32 GPIO 17 (TX2)`
* **Còi Buzzer báo động**: Chân `GPIO 25` (điều khiển qua Transistor / MOSFET kích còi 12V/24V).
* **Dải LED cảnh báo RGB (WS2812B)**: Chân tín hiệu Data cắm vào `GPIO 27`.
* **Kẹp cảm biến dòng xi-nhan (Cách ly Optocoupler)**:
  * Xi-nhan Trái $\to$ `GPIO 32`
  * Xi-nhan Phải $\to$ `GPIO 33`
  * Đèn Số lùi $\to$ `GPIO 34`

### 7.3. Cú pháp Giao thức Truyền thông (ASCII NMEA Protocol 115200 baud):
1. **Từ ESP32 $\to$ Jetson (Tần số 20 Hz):**
   ```text
   $EGO,<speed_mps>,<yaw_rate_rad_s>,<turn_signal>,<gear>*<Checksum>\r\n
   Ví dụ: $EGO,4.17,-0.28,RIGHT,D*4A
   ```
2. **Từ Jetson $\to$ ESP32 (Khi phát hiện rủi ro - Tần số tối đa 30 Hz):**
   ```text
   $BSRI,<level_code>,<score>,<track_id>,<zone_id>,<ttc_x10>*<Checksum>\r\n
   Ví dụ: $BSRI,3,0.85,1,4,12*5F
   (Giải mã: Mức 3=CRITICAL, Điểm rủi ro 0.85, Track ID 1, Zone 4=Bụng cua phải, TTC = 1.2s)
   ```

---

## 8. CÁC LỖI THƯỜNG GẶP VÀ CÁCH KHẮC PHỤC (TROUBLESHOOTING)

### 🔴 Lỗi 1: `MemoryError` hoặc tiến trình bị `Killed` đột ngột khi nạp Model
* **Nguyên nhân**: Jetson Nano chỉ có 4GB RAM vật lý, khi load model YOLO hoặc thư viện lớn sẽ bị tràn RAM và bị Linux OOM Killer tắt tiến trình.
* **Khắc phục**: Chưa kích hoạt Swap file. Hãy tạo và bật Swap 6GB theo hướng dẫn ở Mục 4.1:
  ```bash
  sudo swapon /swapfile_blindguard
  free -h  # Kiểm tra Swap phải hiển thị >= 6.0G
  ```

### 🔴 Lỗi 2: `Permission denied: '/dev/ttyTHS1'`
* **Nguyên nhân**: User hiện tại chưa thuộc nhóm `dialout` quản lý cổng serial.
* **Khắc phục**:
  ```bash
  sudo usermod -aG dialout $USER
  sudo chmod 666 /dev/ttyTHS1
  # Khởi động lại Jetson để áp dụng quyền nhóm
  sudo reboot
  ```

### 🔴 Lỗi 3: ESP32 không nhận được lệnh cảnh báo / Dữ liệu bị rác
* **Nguyên nhân**: 
  1. Chưa nối chung chân **GND** giữa Jetson và ESP32.
  2. Tiến trình `nvgetty` trên Ubuntu của Jetson vẫn đang chạy và tranh chấp dữ liệu cổng serial.
* **Khắc phục**:
  ```bash
  sudo systemctl stop nvgetty
  sudo systemctl disable nvgetty
  ```

### 🔴 Lỗi 4: Video Camera bị trễ hình (High Latency / Lag)
* **Nguyên nhân**: Bộ đệm OpenCV `VideoCapture` tích lũy nhiều khung hình chưa kịp xử lý.
* **Khắc phục**: 
  1. Thêm `appsink drop=1` vào chuỗi GStreamer pipeline.
  2. Đọc frame trong một luồng riêng (`threading.Thread`) chỉ giữ lại frame mới nhất (`latest_frame`), luồng AI chỉ lấy frame mới nhất để suy luận.

### 🔴 Lỗi 5: Tốc độ FPS quá thấp (< 10 FPS)
* **Nguyên nhân**: Đang chạy model `.pt` hoặc `.onnx` bằng PyTorch CPU runtime thay vì GPU TensorRT.
* **Khắc phục**: Chuyển đổi sang `yolo11n_v4.engine` bằng lệnh `trtexec --fp16` (xem chi tiết tại Mục 5.2). Đảm bảo đã bật `sudo nvpmodel -m 0` và `sudo jetson_clocks`.

---

## 9. LIÊN HỆ & BẢN QUYỀN
Hệ thống được thiết kế và tối ưu bởi Đội ngũ Nghiên cứu & Phát triển **BlindGuard AI**. Mọi đóng góp kỹ thuật và thắc mắc triển khai vui lòng tạo Issue hoặc trao đổi trực tiếp qua kênh kỹ thuật của dự án.
