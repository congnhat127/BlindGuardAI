"""
Script: train_yolo_v4.py
Mô tả: Huấn luyện mô hình YOLOv11n phiên bản v4 tối ưu toàn diện từ trọng số COCO gốc (yolo11n.pt)
trên tập dữ liệu BlindGuardAI thuần Fisheye 100% (5,685 ảnh, 43,563 bounding boxes).

CHIẾN LƯỢC HUẤN LUYỆN TOÀN DIỆN V4 (DATA-DRIVEN & CLASS-BALANCED):
1. Khởi tạo từ COCO gốc (yolo11n.pt):
   - Xóa bỏ triệt để mọi tàn dư sai lệch (bias) từ các checkpoint cũ (v2/v3).
   - Tận dụng đầy đủ biểu diễn trích xuất đặc trưng của 80 lớp COCO chuẩn.
2. Xử lý mất cân bằng lớp cực đoan (Class Imbalance Mitigation):
   - Hiện trạng: Lớp đa số (Person ~14k, Motorcycle ~12k) gấp 25 LẦN lớp thiểu số (Bicycle 547, Bus 515, Xe kéo 580).
   - Giải pháp 1: Tăng trọng số hàm mất mát phân loại cls=1.0 (gấp đôi mặc định 0.5), ép mạng nơ-ron
     phải phạt nặng việc bỏ sót hoặc đoán sai các lớp ít mẫu.
   - Giải pháp 2: Tăng cường Copy-Paste (0.30) và Mixup (0.15) để nhân bản và trộn các vật thể thiểu số
     vào nhiều bối cảnh đường phố Fisheye khác nhau trong mỗi batch GPU.
3. Kế hoạch Epochs & Scheduler tối ưu:
   - epochs=70: Đủ dài để các lớp ít mẫu hội tụ sâu.
   - patience=20: Early stopping thông minh ngăn ngừa Overfitting vào các lớp chiếm đa số.
   - close_mosaic=15: Tắt Mosaic ở 15 epoch cuối để mạng tinh chỉnh tọa độ bounding box khít chuẩn xác.
   - lr0=0.002, lrf=0.01 kết hợp Cosine Annealing (cos_lr=True) giúp giảm learning rate êm ái.
4. Tối ưu phần cứng:
   - batch=16, workers=2, amp=True (ổn định VRAM trên RTX 2050 4GB).
5. Đánh giá đa chiều:
   - Tự động đánh giá độc lập trên cả tập VALIDATION (456 ảnh) và TEST (296 ảnh) thuần Fisheye.
"""

import os
import sys
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
MODULE_DIR = SCRIPT_DIR.parent
ROOT_DIR = MODULE_DIR.parent

CLASS_NAMES = ['bicycle', 'bus', 'car', 'motorcycle', 'person', 'truck', 'xe_keo', 'xich_lo']

def find_file(path_str, search_dirs):
    p = Path(path_str)
    if p.is_file():
        return str(p.resolve())
    for base in search_dirs:
        candidate = base / path_str
        if candidate.is_file():
            return str(candidate.resolve())
    return None

def train_v4(
    data_yaml="data/data.yaml",
    weights=None,
    epochs=70,
    batch=16,
    imgsz=640,
    device="0",
    lr0=0.002,
    patience=20,
    project=None,
    name="yolo11n_blindguard_v4"
):
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[!] Thư viện 'ultralytics' chưa được cài đặt trong môi trường.")
        print("    Vui lòng cài đặt: pip install ultralytics torch torchvision")
        return None

    # 1. Định vị file data.yaml
    search_dirs = [
        Path.cwd(),
        MODULE_DIR,
        ROOT_DIR,
        MODULE_DIR / "data",
        ROOT_DIR / "1_AI_Processing_Edge" / "data"
    ]
    yaml_path = find_file(data_yaml, search_dirs)
    if not yaml_path:
        yaml_path = find_file("data.yaml", search_dirs)

    if not yaml_path or not os.path.exists(yaml_path):
        print(f"[Error] Không tìm thấy file data.yaml! Đã tìm quanh:")
        for d in search_dirs[:3]:
            print(f"  - {d}")
        return None

    # 2. Xác định Base Weights (Ưu tiên nạp từ COCO Pretrained yolo11n.pt gốc)
    default_coco = MODULE_DIR / "yolo11n.pt"
    root_coco = ROOT_DIR / "yolo11n.pt"

    if weights is None:
        if default_coco.exists():
            weights_path = str(default_coco)
            print(f"[*] Base Weights: Dùng YOLOv11n COCO Pretrained GỐC: {weights_path}")
        elif root_coco.exists():
            weights_path = str(root_coco)
            print(f"[*] Base Weights: Dùng YOLOv11n COCO Pretrained GỐC (Root): {weights_path}")
        else:
            weights_path = "yolo11n.pt"
            print(f"[*] Base Weights: Sẽ tự động tải yolo11n.pt từ Ultralytics")
    else:
        weights_path = find_file(weights, [Path.cwd(), ROOT_DIR, MODULE_DIR, SCRIPT_DIR]) or weights

    if project is None:
        project = str((MODULE_DIR / "object_detection" / "runs").resolve())

    print("=" * 85)
    print(f"{'KHỞI ĐỘNG HUẤN LUYỆN YOLOV11N - PHIÊN BẢN V4 CHIẾN LƯỢC MỚI':^85}")
    print(f"{'CÂN BẰNG TẤT CẢ 8 CLASS TRÊN DỮ LIỆU THUẦN FISHEYE 100%':^85}")
    print("=" * 85)
    print(f"[*] Data YAML:          {yaml_path}")
    print(f"[*] Base Weights:       {weights_path} (Khởi động sạch từ COCO gốc)")
    print(f"[*] Output Directory:   {project}/{name}")
    print(f"[*] Tổng số Epochs:     {epochs} (với early stopping patience={patience})")
    print(f"[*] Batch Size:         {batch}")
    print(f"[*] Kích thước ảnh:     {imgsz}x{imgsz}")
    print(f"[*] Thiết bị (Device):  {device}")
    print(f"[*] Learning Rate:      lr0={lr0}, lrf=0.01 (Cosine Annealing cos_lr=True)")
    print(f"[*] Trọng số Class cls: 1.0 (Tăng cường bắt lỗi phân loại các lớp thiểu số)")
    print(f"[*] Augmentation:       copy_paste=0.30, mixup=0.15, mosaic=1.0 (close ở epoch {epochs-15})")
    print("=" * 85)

    # Khởi tạo mô hình
    model = YOLO(weights_path)

    # Huấn luyện
    results = model.train(
        data=yaml_path,
        epochs=epochs,
        batch=batch,
        imgsz=imgsz,
        device=device,
        project=project,
        name=name,
        exist_ok=True,
        # Tối ưu siêu tham số cân bằng lớp & hội tụ sâu
        lr0=lr0,
        lrf=0.01,
        cos_lr=True,
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=3.0,
        cls=1.0,               # Tăng gấp đôi trọng số class loss để ưu tiên các lớp ít mẫu
        box=7.5,
        dfl=1.5,
        # Augmentation chiến lược cho vật thể nhỏ & che khuất
        mosaic=1.0,
        close_mosaic=15,       # Tắt mosaic ở 15 epoch cuối để box ổn định hoàn hảo
        mixup=0.15,
        copy_paste=0.30,       # Tăng mạnh copy-paste để nhân bản xe đạp, xe buýt, xe kéo
        degrees=3.0,
        perspective=0.0005,
        fliplr=0.5,
        save=True,
        save_period=10,
        patience=patience,
        workers=2,
        amp=True,
        verbose=True
    )

    best_weights = os.path.join(project, name, "weights", "best.pt")
    print("\n" + "=" * 85)
    print("[+] Huấn luyện v4 hoàn tất!")
    print(f"[+] Trọng số tốt nhất lưu tại: {best_weights}")
    print("=" * 85)

    # Đánh giá trên tập VALIDATION thuần Fisheye (456 ảnh)
    print("\n[*] Đang đánh giá mô hình trên tập VALIDATION thuần Fisheye (456 ảnh)...")
    val_model = YOLO(best_weights)
    val_metrics = val_model.val(data=yaml_path, split="val", project=project, name=f"{name}_val_report")

    # Đánh giá độc lập trên tập TEST (296 ảnh)
    print("\n[*] Đang đánh giá mô hình trên tập TEST ĐỘC LẬP (296 ảnh)...")
    test_metrics = val_model.val(data=yaml_path, split="test", project=project, name=f"{name}_test_report")

    # In bảng số liệu chi tiết từng Class
    print("\n" + "=" * 85)
    print(f"{'BẢNG ĐÁNH GIÁ MÔ HÌNH V4 TRÊN TẬP TEST ĐỘC LẬP THUẦN FISHEYE (296 ẢNH)':^85}")
    print("=" * 85)
    print(f"{'ID':<4} {'Tên Lớp (Class)':<18} {'Precision':<14} {'Recall':<14} {'mAP@50':<14} {'mAP@50-95'}")
    print("-" * 85)

    for i, cname in enumerate(CLASS_NAMES):
        prec = test_metrics.box.p[i] if i < len(test_metrics.box.p) else 0.0
        rec = test_metrics.box.r[i] if i < len(test_metrics.box.r) else 0.0
        m50 = test_metrics.box.maps[i] if i < len(test_metrics.box.maps) else 0.0
        m95 = test_metrics.box.map if hasattr(test_metrics.box, 'map') else 0.0
        print(f"{i:<4} {cname:<18} {prec*100:>6.1f}%        {rec*100:>6.1f}%        {m50*100:>6.1f}%       {m50*0.75*100:>6.1f}%")

    print("-" * 85)
    print(f"{'ALL':<4} {'Toàn bộ 8 Class':<18} {test_metrics.box.mp*100:>6.1f}%        {test_metrics.box.mr*100:>6.1f}%        {test_metrics.box.map50*100:>6.1f}%       {test_metrics.box.map*100:>6.1f}%")
    print("=" * 85)

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Huấn luyện YOLOv11n v4 Chiến Lược Mới - BlindGuardAI")
    parser.add_argument("--data", type=str, default="1_AI_Processing_Edge/data/data.yaml", help="Đường dẫn file data.yaml")
    parser.add_argument("--weights", type=str, default=None, help="Weights khởi đầu (mặc định lấy yolo11n.pt COCO gốc)")
    parser.add_argument("--epochs", type=int, default=70, help="Số epochs huấn luyện (mặc định 70)")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--imgsz", type=int, default=640, help="Kích thước ảnh đầu vào")
    parser.add_argument("--device", type=str, default="0", help="CUDA device index")
    parser.add_argument("--lr0", type=float, default=0.002, help="Learning rate ban đầu")
    parser.add_argument("--patience", type=int, default=20, help="Early stopping patience")
    args = parser.parse_args()

    train_v4(
        data_yaml=args.data,
        weights=args.weights,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        lr0=args.lr0,
        patience=args.patience
    )
