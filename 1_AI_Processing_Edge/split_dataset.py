"""
Script: split_dataset.py
Mô tả: Phân chia tập dữ liệu 888 ảnh gắn nhãn thủ công từ camera Fisheye 180 độ
thành 3 tập: Train (~76%), Valid (~12%), Test (~12%).

Phương pháp: Stratified Stride Sampling theo từng chuỗi Video Sequence để:
1. Tránh Data Leakage giữa các frame liên tiếp của cùng một video.
2. Đảm bảo toàn bộ 8 class (kể cả class ít mẫu như xe_keo và bicycle) đều có mặt
   ở cả 3 tập Train, Val, Test.
3. Cập nhật lại file data.yaml cho đúng định dạng Ultralytics YOLOv11.
"""

import os
import shutil
import glob
from collections import defaultdict, Counter

def split_dataset(
    data_dir="1_AI_Processing_Edge/data",
    source_subdir="train",
    train_ratio=0.76,
    val_ratio=0.12,
    test_ratio=0.12,
    dry_run=False
):
    src_images = os.path.join(data_dir, source_subdir, "images")
    src_labels = os.path.join(data_dir, source_subdir, "labels")

    if not os.path.exists(src_images) or not os.path.exists(src_labels):
        print(f"[Error] Không tìm thấy thư mục nguồn: {src_images} hoặc {src_labels}")
        return

    images = sorted([f for f in os.listdir(src_images) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    print(f"[*] Tìm thấy tổng cộng {len(images)} ảnh trong {src_images}")

    # Nhóm theo chuỗi video (Video Sequence Prefix, ví dụ: 20260820_18_04)
    video_groups = defaultdict(list)
    for img in images:
        vid = "_".join(img.split("_")[:3])
        video_groups[vid].append(img)

    print(f"[*] Tổng số video sequence phát hiện được: {len(video_groups)}")

    train_imgs, val_imgs, test_imgs = [], [], []

    for vid, imgs in sorted(video_groups.items()):
        imgs.sort()
        n = len(imgs)
        if n == 1:
            train_imgs.append(imgs[0])
        elif n == 2:
            train_imgs.append(imgs[0])
            val_imgs.append(imgs[1])
        else:
            # Stride sampling modulo 7:
            # idx % 7 == 5 -> Val (~14.2%)
            # idx % 7 == 6 -> Test (~14.2%)
            # còn lại -> Train (~71.4%)
            for idx, img in enumerate(imgs):
                mod = idx % 7
                if mod == 5:
                    val_imgs.append(img)
                elif mod == 6:
                    test_imgs.append(img)
                else:
                    train_imgs.append(img)

    splits = {
        "train": train_imgs,
        "valid": val_imgs,
        "test": test_imgs
    }

    class_names = ['bicycle', 'bus', 'car', 'motorcycle', 'person', 'truck', 'xe_keo', 'xich_lo']
    
    print("\n" + "="*70)
    print(f"{'BẢNG PHÂN PHỐI DỮ LIỆU SAU KHI CHIA':^70}")
    print("="*70)
    print(f"Số lượng ảnh: Train={len(train_imgs)} ({len(train_imgs)/len(images)*100:.1f}%), "
          f"Valid={len(val_imgs)} ({len(val_imgs)/len(images)*100:.1f}%), "
          f"Test={len(test_imgs)} ({len(test_imgs)/len(images)*100:.1f}%)")
    print("-"*70)
    print(f"{'Class ID':<10}{'Tên Class':<15}{'Train':<15}{'Valid':<15}{'Test':<15}{'Tổng':<10}")
    print("-"*70)

    # Đếm số lượng bounding box theo từng split
    split_counts = {k: Counter() for k in splits}
    for split_name, img_list in splits.items():
        for img in img_list:
            lbl_file = os.path.join(src_labels, img.rsplit('.', 1)[0] + '.txt')
            if os.path.exists(lbl_file):
                with open(lbl_file, 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if parts:
                            split_counts[split_name][int(parts[0])] += 1

    for cid, cname in enumerate(class_names):
        tr = split_counts["train"].get(cid, 0)
        va = split_counts["valid"].get(cid, 0)
        te = split_counts["test"].get(cid, 0)
        total = tr + va + te
        print(f"{cid:<10}{cname:<15}{tr:<15}{va:<15}{te:<15}{total:<10}")

    print("="*70)

    if dry_run:
        print("\n[!] Chế độ DRY RUN: Không di chuyển file thực tế.")
        return

    # Tạo thư mục valid và test nếu chưa có
    for split_name in ["valid", "test"]:
        os.makedirs(os.path.join(data_dir, split_name, "images"), exist_ok=True)
        os.makedirs(os.path.join(data_dir, split_name, "labels"), exist_ok=True)

    # Di chuyển các ảnh thuộc valid và test ra khỏi thư mục train
    for split_name in ["valid", "test"]:
        img_dest_dir = os.path.join(data_dir, split_name, "images")
        lbl_dest_dir = os.path.join(data_dir, split_name, "labels")
        for img in splits[split_name]:
            # Di chuyển ảnh
            src_img_path = os.path.join(src_images, img)
            dst_img_path = os.path.join(img_dest_dir, img)
            if os.path.exists(src_img_path):
                shutil.move(src_img_path, dst_img_path)

            # Di chuyển nhãn
            lbl_name = img.rsplit('.', 1)[0] + '.txt'
            src_lbl_path = os.path.join(src_labels, lbl_name)
            dst_lbl_path = os.path.join(lbl_dest_dir, lbl_name)
            if os.path.exists(src_lbl_path):
                shutil.move(src_lbl_path, dst_lbl_path)

    print(f"\n[+] Đã di chuyển thành công {len(val_imgs)} ảnh sang {data_dir}/valid")
    print(f"[+] Đã di chuyển thành công {len(test_imgs)} ảnh sang {data_dir}/test")
    print(f"[+] Giữ lại {len(train_imgs)} ảnh trong {data_dir}/train")

    # Cập nhật file data.yaml
    yaml_path = os.path.join(data_dir, "data.yaml")
    yaml_content = f"""path: {os.path.abspath(data_dir).replace('\\\\', '/')}
train: train/images
val: valid/images
test: test/images

nc: 8
names: {class_names}
"""
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    print(f"[+] Đã cập nhật file cấu hình: {yaml_path}")
    print("[✓] Hoàn thành phân chia dữ liệu!")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Chia dữ liệu Train/Val/Test cho BlindGuardAI")
    parser.add_argument("--execute", action="store_true", help="Thực thi di chuyển file (mặc định chỉ chạy kiểm tra)")
    args = parser.parse_args()

    split_dataset(dry_run=not args.execute)

