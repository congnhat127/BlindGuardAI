"""
Script: train_yolo_v3.py
Mô tả: Huấn luyện mô hình YOLOv11n phiên bản v3 trên tập dữ liệu đã hợp nhất 5,717 ảnh
(Bổ sung 349 mẫu xe kéo thật ngoài đường phố Việt Nam từ camera Fisheye).

Chiến lược huấn luyện v3 (Fine-tuning từ v2):
- Base Weights: object_detection/runs/yolo11n_blindguard_v2/weights/best.pt
  (Đã có mAP50 ~73%, hiểu sẵn 8 lớp xe và độ méo góc rộng Fisheye 180 độ).
- Learning Rate: Khởi đầu lr0=0.003, lrf=0.01 (Cosine Decay) để bảo toàn khả năng nhận diện
  xe máy, ô tô, người, đồng thời tinh chỉnh sâu đặc trưng xe_keo mới.
- Tối ưu VRAM: batch=16, workers=2 (phù hợp RTX 2050 4GB).
- Tự động đánh giá độc lập trên tập TEST (319 ảnh) ngay sau khi huấn luyện.
"""

import os
import sys
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
MODULE_DIR = SCRIPT_DIR.parent
ROOT_DIR = MODULE_DIR.parent

def find_file(path_str, search_dirs):
    p = Path(path_str)
    if p.is_file():
        return str(p.resolve())
    for base in search_dirs:
        candidate = base / path_str
        if candidate.is_file():
            return str(candidate.resolve())
    return None

def train_v3(
    data_yaml="data/data.yaml",
    weights=None,
    epochs=50,
    batch=16,
    imgsz=640,
    device="0",
    freeze=5,
    project=None,
    name="yolo11n_blindguard_v3"
):
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[!] Thư viện 'ultralytics' chưa được cài đặt trong môi trường.")
        print("    Vui lòng cài đặt: pip install ultralytics torch torchvision")
        return None

    # 1. Tìm file cấu hình data.yaml
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

    # 2. Xác định Base Weights tốt nhất (Mặc định chọn best.pt của v2)
    default_v2_best = MODULE_DIR / "object_detection" / "runs" / "yolo11n_blindguard_v2" / "weights" / "best.pt"
    default_v1_best = MODULE_DIR / "object_detection" / "runs" / "yolo11n_blindguard" / "weights" / "best.pt"
    default_coco = MODULE_DIR / "yolo11n.pt"

    if weights is None:
        if default_v2_best.exists():
            weights_path = str(default_v2_best)
            print(f"[*] Tìm thấy checkpoint v2 tốt nhất: {weights_path}")
        elif default_v1_best.exists():
            weights_path = str(default_v1_best)
            print(f"[*] Tìm thấy checkpoint v1: {weights_path}")
        elif default_coco.exists():
            weights_path = str(default_coco)
            print(f"[*] Dùng weights COCO: {weights_path}")
        else:
            weights_path = "yolo11n.pt"
    else:
        weights_path = find_file(weights, [Path.cwd(), ROOT_DIR, MODULE_DIR, SCRIPT_DIR]) or weights

    if project is None:
        project = str((MODULE_DIR / "object_detection" / "runs").resolve())

    print("=" * 80)
    print(f"{'KHỞI ĐỘNG HUẤN LUYỆN YOLOV11N - PHIÊN BẢN V3 (BLINDGUARD AI)':^80}")
    print("=" * 80)
    print(f"[*] Data YAML:          {yaml_path}")
    print(f"[*] Base Weights:       {weights_path}")
    print(f"[*] Output Directory:   {project}/{name}")
    print(f"[*] Số lượng Epochs:    {epochs} (với early stopping patience=15)")
    print(f"[*] Batch Size:         {batch}")
    print(f"[*] Kích thước ảnh:     {imgsz}x{imgsz}")
    print(f"[*] Thiết bị (Device):  {device}")
    print(f"[*] Freeze layers:      {freeze} (Bảo tồn trích xuất góc nhìn mắt cá ban đầu)")
    print(f"[*] Learning Rate:      lr0=0.003, lrf=0.01 (Fine-tuning)")
    print("=" * 80)

    # Khởi tạo mô hình
    model = YOLO(weights_path)

    # Bắt đầu train
    results = model.train(
        data=yaml_path,
        epochs=epochs,
        batch=batch,
        imgsz=imgsz,
        device=device,
        freeze=freeze,
        project=project,
        name=name,
        exist_ok=True,
        lr0=0.003,
        lrf=0.01,
        mosaic=1.0,
        mixup=0.15,
        copy_paste=0.20,
        degrees=5.0,
        perspective=0.0005,
        save=True,
        save_period=10,
        patience=15,
        workers=2,
        verbose=True
    )

    print("\n" + "=" * 80)
    print("[+] Huấn luyện v3 hoàn tất!")
    best_weights = os.path.join(project, name, "weights", "best.pt")
    print(f"[+] Trọng số tốt nhất đã lưu tại: {best_weights}")

    # Đánh giá độc lập trên tập TEST (319 ảnh)
    print("\n[*] Đang đánh giá mô hình v3 trên tập TEST độc lập (319 ảnh)...")
    metrics = model.val(data=yaml_path, split="test", project=project, name=f"{name}_test_val")
    print(f"[✓] mAP50 trên tập Test:    {metrics.box.map50:.4f}")
    print(f"[✓] mAP50-95 trên tập Test: {metrics.box.map:.4f}")

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Huấn luyện YOLOv11n v3 cho BlindGuardAI")
    parser.add_argument("--data", type=str, default="1_AI_Processing_Edge/data/data.yaml")
    parser.add_argument("--weights", type=str, default=None, help="Đường dẫn file weights (mặc định lấy best.pt v2)")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", type=str, default="0")
    parser.add_argument("--freeze", type=int, default=5)
    args = parser.parse_args()

    train_v3(
        data_yaml=args.data,
        weights=args.weights,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        freeze=args.freeze
    )

