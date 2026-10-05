#!/bin/bash
# ==============================================================================
#           DỰ ÁN BLINDGUARD AI — KỊCH BẢN THIẾT LẬP MÔI TRƯỜNG TOÀN DIỆN
#                 DÀNH CHO PHẦN CỨNG NVIDIA JETSON NANO B01 (4GB)
# ==============================================================================
# Hệ điều hành: Ubuntu 18.04 LTS (JetPack 4.6.x / L4T R32.7.x - aarch64)
# ==============================================================================

set -e

echo "=============================================================================="
echo "    BẮT ĐẦU CẤU HÌNH HỆ THỐNG BLINDGUARD AI CHO JETSON NANO B01 (4GB)        "
echo "=============================================================================="

# 1. KÍCH HOẠT HIỆU NĂNG TỐI ĐA (MAX-N 10W MODE & JETSON CLOCKS)
echo "[1/6] Thiết lập hiệu năng tối đa cho Jetson Nano..."
sudo nvpmodel -m 0          # Chuyển sang chế độ MAX-N (10W, bật đủ 4 nhân CPU)
sudo jetson_clocks          # Khóa xung nhịp CPU, GPU và EMC ở mức tần số cực đại

# 2. TẠO VÀ KÍCH HOẠT SWAP MEMORY 6GB (BẮT BUỘC ĐỂ TRÁNH OOM KILLER)
echo "[2/6] Kiểm tra và cấu hình bộ nhớ Swap 6GB..."
if [ ! -f /swapfile_blindguard ]; then
    echo "  -> Đang tạo swapfile 6GB (quá trình này mất khoảng 2-3 phút)..."
    sudo fallocate -l 6G /swapfile_blindguard || sudo dd if=/dev/zero of=/swapfile_blindguard bs=1M count=6144
    sudo chmod 600 /swapfile_blindguard
    sudo mkswap /swapfile_blindguard
    sudo swapon /swapfile_blindguard
    echo "/swapfile_blindguard none swap sw 0 0" | sudo tee -a /etc/fstab
    echo "  -> Đã tạo và kích hoạt 6GB Swap thành công!"
else
    echo "  -> Swapfile đã tồn tại. Đang kích hoạt..."
    sudo swapon /swapfile_blindguard || true
fi

# 3. CẤP QUYỀN VÀ GIẢI PHÓNG CỔNG UART J41 (/dev/ttyTHS1) KẾT NỐI ESP32
echo "[3/6] Cấu hình cổng UART /dev/ttyTHS1 cho ESP32..."
# Vô hiệu hóa tiến trình nvgetty (tiến trình chiếm dụng UART làm debug console)
if systemctl is-active --quiet nvgetty; then
    sudo systemctl stop nvgetty
    sudo systemctl disable nvgetty
    echo "  -> Đã vô hiệu hóa nvgetty để giải phóng /dev/ttyTHS1."
fi
sudo usermod -aG dialout $USER
sudo chmod 666 /dev/ttyTHS1 2>/dev/null || true
sudo chmod 666 /dev/ttyUSB0 2>/dev/null || true

# 4. CÀI ĐẶT CÁC GÓI HỆ THỐNG & GSTREAMER HARDWARE ACCELERATION
echo "[4/6] Cài đặt dependencies hệ thống Linux..."
sudo apt-get update
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    libopenblas-base \
    libopenmpi-dev \
    libomp-dev \
    libjpeg-dev \
    zlib1g-dev \
    v4l-utils \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    libcanberra-gtk-module \
    libcanberra-gtk3-module

# 5. CẬP NHẬT PIP VÀ CÀI ĐẶT CÁC THƯ VIỆN PYTHON CỐT LÕI
echo "[5/6] Cài đặt thư viện Python cho BlindGuard AI..."
python3 -m pip install --upgrade pip setuptools wheel

# Cài đặt các gói xử lý hình học và giao tiếp
python3 -m pip install \
    pyserial \
    shapely \
    numpy==1.19.5 \
    filterpy \
    pyyaml \
    tqdm \
    matplotlib

# 6. KIỂM TRA PYTORCH & TENSORRT WHEEL CHÍNH THỨC CỦA NVIDIA
echo "[6/6] Kiểm tra môi trường PyTorch & TensorRT..."
python3 -c "
try:
    import torch
    print('  [+] PyTorch phiên bản:', torch.__version__, '| CUDA available:', torch.cuda.is_available())
except ImportError:
    print('  [!] Chưa tìm thấy PyTorch cho Jetson!')
    print('  [*] Vui lòng cài wheel PyTorch chính thức của NVIDIA bằng lệnh:')
    print('      wget https://nvidia.box.com/shared/static/p57jwntv436lfrd78inwl7mk6vrrpqeq.whl -O torch-1.10.0+nv21.11-cp36-cp36m-linux_aarch64.whl')
    print('      python3 -m pip install torch-1.10.0+nv21.11-cp36-cp36m-linux_aarch64.whl')

try:
    import tensorrt as trt
    print('  [+] TensorRT phiên bản:', trt.__version__)
except ImportError:
    print('  [!] TensorRT Python binding chưa sẵn sàng trong môi trường này.')
"

# Cài đặt ultralytics cho YOLOv11 / YOLOv8
python3 -m pip install ultralytics || true

echo "=============================================================================="
echo "    THIẾT LẬP HOÀN TẤT! HỆ THỐNG ĐÃ SẴN SÀNG KHỞI CHẠY BLINDGUARD AI!        "
echo "=============================================================================="
echo "Khởi chạy hệ thống bằng lệnh:"
echo "  python3 main_pipeline.py --source csi://0 --model 1_AI_Processing_Edge/object_detection/runs/yolo11n_blindguard_v4/weights/best.engine"
echo "=============================================================================="
