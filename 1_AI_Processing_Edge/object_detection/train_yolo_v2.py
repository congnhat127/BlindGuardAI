"""
Script: train_yolo_v2.py
Mô tả: Huấn luyện mô hình YOLOv11n phiên bản v2 từ tập dữ liệu mới trong thư mục data/new
(BlindGuardAI All - 2,965 ảnh với 8 lớp phương tiện giao thông Việt Nam).

Cấu hình huấn luyện v2:
- Dữ liệu: 1_AI_Processing_Edge/data/new/data.yaml
- Output Project: 1_AI_Processing_Edge/object_detection/runs
- Tên Run: yolo11n_blindguard_v2
- Khởi tạo Base Weights: yolo11n.pt (hoặc có thể nạp weights từ v1 để fine-tune tiếp)
- Tối ưu phần cứng: batch=16, workers=2 (tối ưu VRAM 4GB cho NVIDIA RTX 2050)
- Tự động đánh giá trên tập TEST độc lập sau khi train xong.
"""

import os
import sys
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

def train_v2(
    data_yaml="data/new/data.yaml",
    weights="yolo11n.pt",
    epochs=60,
    batch=16,
    imgsz=640,
    device="0",
    freeze=10,
    project=None,
    name="yolo11n_blindguard_v2"
):
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[!] Thư viện 'ultralytics' chưa được cài đặt trong môi trường.")
        print("    Vui lòng cài đặt: pip install ultralytics torch torchvision")
        return None

    # Tự động định vị data.yaml
    search_dirs = [
        Path.cwd(),
        MODULE_DIR,
        ROOT_DIR,
        MODULE_DIR / "data" / "new",
        ROOT_DIR / "1_AI_Processing_Edge" / "data" / "new",
        MODULE_DIR / "data",
        ROOT_DIR / "1_AI_Processing_Edge" / "data"
    ]
    yaml_path = find_file(data_yaml, search_dirs)
    if not yaml_path:
        yaml_path = find_file("data/new/data.yaml", search_dirs)
    if not yaml_path:
        yaml_path = find_file("data.yaml", search_dirs)

    if not yaml_path or not os.path.exists(yaml_path):
        print(f"[Error] Không tìm thấy file cấu hình dữ liệu: {data_yaml}")
        print("Đã tìm kiếm tại các thư mục:")
        for d in search_dirs[:4]:
            print(f"  - {d}")
        return None

    # Tìm file weights
    weights_path = find_file(weights, [Path.cwd(), ROOT_DIR, MODULE_DIR, SCRIPT_DIR])
    if not weights_path:
        weights_path = weights  # Ultralytics tự tải nếu là model chuẩn (yolo11n.pt)

    if project is None:
        project = str((MODULE_DIR / "object_detection" / "runs").resolve())

    print("=" * 80)
    print(f"{'KHỞI ĐỘNG HUẤN LUYỆN YOLOV11N - PHIÊN BẢN V2 (BLINDGUARD AI)':^80}")
    print("=" * 80)
    print(f"[*] Thư mục hiện tại:   {Path.cwd()}")
    print(f"[*] Data YAML:          {yaml_path}")
    print(f"[*] Base Weights:       {weights_path}")
    print(f"[*] Output Directory:   {project}/{name}")
    print(f"[*] Số lượng Epochs:    {epochs}")
    print(f"[*] Batch Size:         {batch}")
    print(f"[*] Kích thước ảnh:     {imgsz}x{imgsz}")
    print(f"[*] Thiết bị (Device):  {device}")
    print(f"[*] Freeze layers:      {freeze} (Bảo tồn trích xuất đặc trưng COCO)")
    print("=" * 80)

    # Khởi tạo mô hình
    model = YOLO(weights_path)

    # Huấn luyện mô hình v2
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
        # Siêu tham số tối ưu cho Fisheye & cân bằng lớp
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

    best_weights = os.path.join(project, name, "weights", "best.pt")
    last_weights = os.path.join(project, name, "weights", "last.pt")
    print("\n" + "=" * 80)
    print(f"[✓] HUẤN LUYỆN V2 HOÀN TẤT!")
    print(f"[*] Best weights: {best_weights}")
    print(f"[*] Last weights: {last_weights}")
    print("=" * 80)

    # Đánh giá độc lập trên tập TEST của data/new
    print("\n[*] Đang tiến hành đánh giá mô hình V2 trên tập TEST độc lập...")
    try:
        best_model = YOLO(best_weights)
        metrics = best_model.val(
            data=yaml_path,
            split="test",
            project=project,
            name=f"{name}_test_val"
        )
        print("\n" + "-" * 60)
        print(f"{'KẾT QUẢ ĐÁNH GIÁ MÔ HÌNH V2 TRÊN TẬP TEST':^60}")
        print("-" * 60)
        print(f"  mAP@50:    {metrics.box.map50:.4f}")
        print(f"  mAP@50-95: {metrics.box.map:.4f}")
        print("-" * 60)
    except Exception as e:
        print(f"[!] Lỗi khi đánh giá tập test: {e}")

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Huấn luyện YOLOv11n V2 cho BlindGuardAI")
    parser.add_argument("--data", type=str, default="data/new/data.yaml", help="Đường dẫn tới data.yaml mới")
    parser.add_argument("--weights", type=str, default="yolo11n.pt", help="Weights ban đầu (yolo11n.pt hoặc path tới best v1)")
    parser.add_argument("--epochs", type=int, default=60, help="Số epochs huấn luyện (mặc định 60)")
    parser.add_argument("--batch", type=int, default=16, help="Batch size (mặc định 16)")
    parser.add_argument("--imgsz", type=int, default=640, help="Kích thước ảnh (mặc định 640)")
    parser.add_argument("--device", type=str, default="0", help="CUDA device ('0' hoặc 'cpu')")
    parser.add_argument("--freeze", type=int, default=10, help="Số layer backbone freeze (mặc định 10)")
    parser.add_argument("--name", type=str, default="yolo11n_blindguard_v2", help="Tên thư mục run lưu model")
    args = parser.parse_args()

    train_v2(
        data_yaml=args.data,
        weights=args.weights,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        freeze=args.freeze,
        name=args.name
    )

