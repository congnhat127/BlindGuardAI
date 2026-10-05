#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: export_tensorrt.py
Phân hệ: 1_AI_Processing_Edge / model_optimization
Mô tả: Tối ưu hóa và xuất khẩu mô hình YOLOv11n sang TensorRT FP16 Engine (.engine)
       chuyên biệt cho GPU NVIDIA Jetson Nano B01 (128 Maxwell CUDA Cores).
"""

import sys
import argparse
from pathlib import Path

def export_model(
    weights_path: str,
    imgsz: int = 640,
    half: bool = True,
    device: int = 0,
    workspace: int = 2
):
    w_path = Path(weights_path).resolve()
    if not w_path.is_file():
        print(f"[Error] Không tìm thấy file trọng số: {weights_path}")
        return False

    print("=" * 75)
    print(f"{'BLINDGUARD AI — XUẤT MÔ HÌNH TENSORRT FP16 CHO JETSON NANO':^75}")
    print("=" * 75)
    print(f"[*] Input Weights : {w_path}")
    print(f"[*] Input Size    : {imgsz}x{imgsz}")
    print(f"[*] Precision     : {'FP16 (Half)' if half else 'FP32'}")
    print(f"[*] Workspace     : {workspace} GB (Tối ưu cho RAM 4GB Jetson Nano)")
    print(f"[*] Target Device : CUDA GPU #{device}")
    print("=" * 75)

    try:
        from ultralytics import YOLO
        model = YOLO(str(w_path))
        print("[*] Đang tiến hành biên dịch TensorRT Engine trực tiếp trên GPU phần cứng...")
        print("[*] Quá trình này có thể mất từ 8-15 phút trên Jetson Nano B01. Vui lòng chờ...")

        exported_path = model.export(
            format="engine",
            imgsz=imgsz,
            half=half,
            device=device,
            workspace=workspace,
            verbose=True
        )

        print("=" * 75)
        print(f"[+] BIÊN DỊCH TENSORRT THÀNH CÔNG!")
        print(f"[+] File Engine sẵn sàng: {exported_path}")
        print("=" * 75)
        return True

    except Exception as e:
        print(f"[Error] Lỗi trong quá trình xuất TensorRT: {e}")
        print("\n[!] Gợi ý xử lý lỗi phổ biến trên Jetson Nano:")
        print("  1. Jetson Nano thiếu RAM khi build engine -> Hãy tạo Swapfile tối thiểu 4GB-8GB.")
        print("  2. Lỗi TensorRT version mismatch -> Hãy build trực tiếp trên Jetson Nano bằng lệnh này.")
        print("  3. Thử giảm workspace xuống 1GB: --workspace 1")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export YOLO to TensorRT FP16 for Jetson Nano B01")
    parser.add_argument("--weights", type=str,
                        default=str(Path(__file__).parent / "object_detection" / "runs" / "yolo11n_blindguard_v4" / "weights" / "best.pt"),
                        help="Đường dẫn file trọng số YOLO PyTorch (.pt)")
    parser.add_argument("--imgsz", type=int, default=640, help="Kích thước ảnh inference (mặc định: 640)")
    parser.add_argument("--half", action="store_true", default=True, help="Kích hoạt FP16 Half precision (khuyến nghị trên Jetson Nano)")
    parser.add_argument("--workspace", type=int, default=2, help="Kích thước TensorRT workspace bộ nhớ (GB, mặc định: 2)")
    parser.add_argument("--device", type=int, default=0, help="CUDA device index (mặc định: 0)")

    args = parser.parse_args()
    export_model(
        weights_path=args.weights,
        imgsz=args.imgsz,
        half=args.half,
        device=args.device,
        workspace=args.workspace
    )
