"""
Script: split_new_data.py
Mô tả: Phân chia 264 ảnh mới trong 'New folder' và gộp trực tiếp vào 3 tập
Train, Valid, Test hiện có trong '1_AI_Processing_Edge/data'.
"""

import os
import shutil
from collections import defaultdict, Counter

def add_and_split_new_data(
    data_dir="1_AI_Processing_Edge/data",
    new_data_dir="1_AI_Processing_Edge/data/New folder/train",
    dry_run=False
):
    src_images = os.path.join(new_data_dir, "images")
    src_labels = os.path.join(new_data_dir, "labels")

    if not os.path.exists(src_images) or not os.path.exists(src_labels):
        print(f"[Error] Không tìm thấy thư mục nguồn: {src_images} hoặc {src_labels}")
        return

    images = sorted([f for f in os.listdir(src_images) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    print(f"[*] Tìm thấy {len(images)} ảnh mới trong {src_images}")

    # Nhóm theo Video Sequence Prefix
    video_groups = defaultdict(list)
    for img in images:
        vid = "_".join(img.split("_")[:3])
        video_groups[vid].append(img)

    print(f"[*] Tổng số video sequence mới: {len(video_groups)}")

    new_train_imgs, new_val_imgs, new_test_imgs = [], [], []

    for vid, imgs in sorted(video_groups.items()):
        imgs.sort()
        n = len(imgs)
        if n == 1:
            new_train_imgs.append(imgs[0])
        elif n == 2:
            new_train_imgs.append(imgs[0])
            new_val_imgs.append(imgs[1])
        else:
            for idx, img in enumerate(imgs):
                mod = idx % 7
                if mod == 5:
                    new_val_imgs.append(img)
                elif mod == 6:
                    new_test_imgs.append(img)
                else:
                    new_train_imgs.append(img)

    new_splits = {
        "train": new_train_imgs,
        "valid": new_val_imgs,
        "test": new_test_imgs
    }

    class_names = ['bicycle', 'bus', 'car', 'motorcycle', 'person', 'truck', 'xe_keo', 'xich_lo']

    print(f"\n[*] Phân chia dữ liệu mới:")
    print(f"    - Train: {len(new_train_imgs)} ảnh ({len(new_train_imgs)/len(images)*100:.1f}%)")
    print(f"    - Valid: {len(new_val_imgs)} ảnh ({len(new_val_imgs)/len(images)*100:.1f}%)")
    print(f"    - Test:  {len(new_test_imgs)} ảnh ({len(new_test_imgs)/len(images)*100:.1f}%)")

    if dry_run:
        print("\n[!] DRY RUN: Chưa di chuyển file.")
        return

    # Di chuyển file vào từng tập tương ứng
    for split_name, img_list in new_splits.items():
        dst_img_dir = os.path.join(data_dir, split_name, "images")
        dst_lbl_dir = os.path.join(data_dir, split_name, "labels")
        os.makedirs(dst_img_dir, exist_ok=True)
        os.makedirs(dst_lbl_dir, exist_ok=True)

        for img in img_list:
            # Move image
            s_img = os.path.join(src_images, img)
            d_img = os.path.join(dst_img_dir, img)
            if os.path.exists(s_img):
                shutil.move(s_img, d_img)

            # Move label
            lbl_name = img.rsplit('.', 1)[0] + '.txt'
            s_lbl = os.path.join(src_labels, lbl_name)
            d_lbl = os.path.join(dst_lbl_dir, lbl_name)
            if os.path.exists(s_lbl):
                shutil.move(s_lbl, d_lbl)

    print(f"\n[+] Đã di chuyển toàn bộ {len(images)} ảnh và nhãn vào {data_dir}/(train, valid, test)!")

    # Thống kê tổng thể toàn bộ dataset sau khi gộp
    print("\n" + "="*75)
    print(f"{'BẢNG THỐNG KÊ TOÀN BỘ DATASET SAU KHI GỘP THÊM DỮ LIỆU MỚI':^75}")
    print("="*75)
    
    total_imgs = {}
    for split_name in ["train", "valid", "test"]:
        p = os.path.join(data_dir, split_name, "images")
        total_imgs[split_name] = len(os.listdir(p)) if os.path.exists(p) else 0

    all_total_imgs = sum(total_imgs.values())
    print(f"Tổng số ảnh hiện tại: {all_total_imgs} ảnh")
    print(f"  - Train: {total_imgs['train']} ảnh ({total_imgs['train']/all_total_imgs*100:.1f}%)")
    print(f"  - Valid: {total_imgs['valid']} ảnh ({total_imgs['valid']/all_total_imgs*100:.1f}%)")
    print(f"  - Test:  {total_imgs['test']} ảnh ({total_imgs['test']/all_total_imgs*100:.1f}%)")
    print("-"*75)
    print(f"{'Class ID':<10}{'Tên Class':<15}{'Train':<15}{'Valid':<15}{'Test':<15}{'Tổng':<10}")
    print("-"*75)

    split_counts = {k: Counter() for k in ["train", "valid", "test"]}
    for split_name in ["train", "valid", "test"]:
        lbl_p = os.path.join(data_dir, split_name, "labels")
        if os.path.exists(lbl_p):
            for f in os.listdir(lbl_p):
                with open(os.path.join(lbl_p, f), 'r') as fp:
                    for line in fp:
                        parts = line.strip().split()
                        if parts:
                            split_counts[split_name][int(parts[0])] += 1

    for cid, cname in enumerate(class_names):
        tr = split_counts["train"].get(cid, 0)
        va = split_counts["valid"].get(cid, 0)
        te = split_counts["test"].get(cid, 0)
        total = tr + va + te
        print(f"{cid:<10}{cname:<15}{tr:<15}{va:<15}{te:<15}{total:<10}")

    print("="*75)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Thực thi di chuyển dữ liệu")
    args = parser.parse_args()

    add_and_split_new_data(dry_run=not args.execute)

