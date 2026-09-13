"""
Script: train_yolo.py
Mô tả: Huấn luyện mô hình YOLOv11n cho bài toán nhận diện 8 lớp phương tiện giao thông
Việt Nam từ camera Fisheye 180 độ (BlindGuardAI Edge).

Cấu hình chống quên thảm họa (Catastrophic Forgetting) & thích nghi Fisheye:
- Khởi tạo weights: yolo11n.pt (COCO Pretrained)
- Đóng băng Backbone: freeze=10 trong các epoch đầu
- Tối ưu VRAM: batch=16 (phù hợp RTX 2050 4GB VRAM) hoặc batch=8
- Siêu tham số: mosaic=1.0, mixup=0.15, degrees=5.0
"""

import os
import argparse
from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent
MODULE_DIR = SCRIPT_DIR.parent
ROOT_DIR = MODULE_DIR.parent

def find_file(path_str, search_dirs):
    """Tìm file theo đường dẫn tương đối từ các thư mục khác nhau"""
    p = Path(path_str)
    if p.is_file():
        return str(p.resolve())
    for base in search_dirs:
        candidate = base / path_str
        if candidate.is_file():
            return str(candidate.resolve())
    return None

def train(
    data_yaml="data/data.yaml",
    weights="yolo11n.pt",
    epochs=60,
    batch=16,
    imgsz=640,
    device="0",
    freeze=10,
    project=None,
    name="yolo11n_blindguard"
):
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[!] Thư viện 'ultralytics' chưa được cài đặt.")
        print("    Vui lòng cài đặt: py -3.11 -m pip install ultralytics torch torchvision")
        return

    # Tự động tìm data.yaml bất kể chạy từ root hay từ 1_AI_Processing_Edge
    search_dirs = [Path.cwd(), MODULE_DIR, ROOT_DIR, MODULE_DIR / "data", ROOT_DIR / "1_AI_Processing_Edge" / "data"]
    yaml_path = find_file(data_yaml, search_dirs)
    if not yaml_path:
        yaml_path = find_file("data.yaml", search_dirs)

    if not yaml_path or not os.path.exists(yaml_path):
        print(f"[Error] Không tìm thấy file data.yaml! Đã tìm quanh:")
        for d in [Path.cwd(), MODULE_DIR / "data", ROOT_DIR / "1_AI_Processing_Edge" / "data"]:
            print(f"  - {d}")
        return

    # Tự động tìm file weights
    weights_path = find_file(weights, [Path.cwd(), ROOT_DIR, MODULE_DIR, SCRIPT_DIR])
    if not weights_path:
        weights_path = weights  # YOLO sẽ tự tải nếu là model chuẩn

    if project is None:
        project = str((MODULE_DIR / "object_detection" / "runs").resolve())

    print("="*75)
    print(f"{'KHỞI ĐỘNG HUẤN LUYỆN YOLOV11N - BLINDGUARD AI':^75}")
    print("="*75)
    print(f"Thư mục làm việc: {Path.cwd()}")
    print(f"Data config:      {yaml_path}")
    print(f"Base weights:     {weights_path}")
    print(f"Output project:   {project}")
    print(f"Epochs:           {epochs}")
    print(f"Batch size:       {batch}")
    print(f"Image size:       {imgsz}")
    print(f"Device:           {device}")
    print(f"Freeze:           {freeze} layers (Bảo vệ kiến thức COCO gốc)")
    print("="*75)

    # Khởi tạo mô hình
    model = YOLO(weights_path)

    # Bắt đầu huấn luyện
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
        # Siêu tham số tối ưu cho dữ liệu Fisheye & mất cân bằng lớp
        lr0=0.005,
        lrf=0.01,
        mosaic=1.0,
        mixup=0.15,
        copy_paste=0.20,
        degrees=5.0,
        perspective=0.0005,
        save=True,
        save_period=10,
        patience=20,
        workers=2,
        verbose=True
    )

    print("\n[+] Huấn luyện hoàn tất!")
    best_weights = os.path.join(project, name, "weights", "best.pt")
    print(f"[+] Trọng số tốt nhất đã lưu tại: {best_weights}")

    # Đánh giá trên tập Test độc lập
    print("\n[*] Đang đánh giá mô hình trên tập TEST độc lập...")
    metrics = model.val(data=yaml_path, split="test", project=project, name=f"{name}_test_val")
    print(f"[✓] Kết quả mAP50 trên tập Test: {metrics.box.map50:.4f}")
    print(f"[✓] Kết quả mAP50-95 trên tập Test: {metrics.box.map:.4f}")

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Huấn luyện YOLOv11n cho BlindGuardAI")
    parser.add_argument("--data", type=str, default="1_AI_Processing_Edge/data/data.yaml")
    parser.add_argument("--weights", type=str, default="yolo11n.pt")
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", type=str, default="0")
    parser.add_argument("--freeze", type=int, default=10)
    args = parser.parse_args()

    train(
        data_yaml=args.data,
        weights=args.weights,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        freeze=args.freeze
    )

