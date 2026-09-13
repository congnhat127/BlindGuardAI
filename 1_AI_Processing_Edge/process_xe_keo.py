"""
Script: process_xe_keo.py
Mô tả:
1. Đọc dữ liệu xe kéo từ thư mục 1_AI_Processing_Edge/data/data_xe_keo
2. Chuẩn hóa tên file sang định dạng ASCII an toàn (tránh lỗi ký tự tiếng Việt / emoji trên OpenCV/PyTorch)
3. Xử lý ảnh kích thước quá lớn (downscale ảnh có cạnh > 1280px về max 1280px giữ nguyên tỷ lệ)
4. Chuyển đổi Class ID từ 0 (xe-ba-gac) -> 6 (xe_keo theo BlindGuardAI)
5. Gộp trực tiếp vào 3 tập train, valid, test trong 1_AI_Processing_Edge/data
6. Báo cáo thống kê số lượng trước khi thực hiện bước Data Augmentation.
"""

import os
from PIL import Image
from collections import Counter

def process_and_merge_xe_keo(
    data_dir="1_AI_Processing_Edge/data",
    source_xe_keo="1_AI_Processing_Edge/data/data_xe_keo",
    max_dim=1280,
    dry_run=False
):
    splits = ["train", "valid", "test"]
    class_names = ['bicycle', 'bus', 'car', 'motorcycle', 'person', 'truck', 'xe_keo', 'xich_lo']

    print(f"[*] Bắt đầu xử lý dữ liệu xe kéo từ: {source_xe_keo}")
    
    # 1. Thu thập và kiểm tra số lượng
    xe_stats = {}
    for s in splits:
        img_dir = os.path.join(source_xe_keo, s, "images")
        lbl_dir = os.path.join(source_xe_keo, s, "labels")
        if not os.path.exists(img_dir) or not os.path.exists(lbl_dir):
            print(f"[Error] Không tìm thấy: {img_dir} hoặc {lbl_dir}")
            return
        imgs = sorted([f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
        xe_stats[s] = imgs

    total_new_imgs = sum(len(v) for v in xe_stats.values())
    print(f"[*] Tổng số ảnh xe kéo mới tìm thấy: {total_new_imgs}")
    for s in splits:
        print(f"    - {s}: {len(xe_stats[s])} ảnh")

    if dry_run:
        print("\n[!] Chế độ DRY RUN: Chưa ghi file.")
        return

    # 2. Xử lý và di chuyển ảnh + nhãn
    processed_counts = {s: 0 for s in splits}
    box_added = {s: 0 for s in splits}

    for s in splits:
        src_img_dir = os.path.join(source_xe_keo, s, "images")
        src_lbl_dir = os.path.join(source_xe_keo, s, "labels")

        dst_img_dir = os.path.join(data_dir, s, "images")
        dst_lbl_dir = os.path.join(data_dir, s, "labels")
        os.makedirs(dst_img_dir, exist_ok=True)
        os.makedirs(dst_lbl_dir, exist_ok=True)

        for idx, img_name in enumerate(xe_stats[s], start=1):
            src_img_path = os.path.join(src_img_dir, img_name)
            base_name, _ = os.path.splitext(img_name)
            src_lbl_path = os.path.join(src_lbl_dir, base_name + ".txt")

            if not os.path.exists(src_lbl_path):
                continue

            # Tên file mới chuẩn hóa
            new_file_base = f"xekeo_ext_{s}_{idx:04d}"
            dst_img_path = os.path.join(dst_img_dir, new_file_base + ".jpg")
            dst_lbl_path = os.path.join(dst_lbl_dir, new_file_base + ".txt")

            # Xử lý ảnh (Downscale nếu ảnh quá to > max_dim)
            try:
                with Image.open(src_img_path) as img:
                    img = img.convert("RGB")
                    w, h = img.size
                    if max(w, h) > max_dim:
                        if w > h:
                            new_w = max_dim
                            new_h = int(round(h * (max_dim / w)))
                        else:
                            new_h = max_dim
                            new_w = int(round(w * (max_dim / h)))
                        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    img.save(dst_img_path, "JPEG", quality=95)
            except Exception as e:
                print(f"[Warning] Lỗi khi xử lý ảnh {src_img_path}: {e}")
                continue

            # Xử lý nhãn: Chuyển class ID 0 -> 6
            new_lines = []
            with open(src_lbl_path, "r", encoding="utf-8") as fp:
                for line in fp:
                    parts = line.strip().split()
                    if parts:
                        # parts[0] là class id, đổi thành 6
                        parts[0] = "6"
                        new_lines.append(" ".join(parts))
                        box_added[s] += 1

            with open(dst_lbl_path, "w", encoding="utf-8") as fp:
                fp.write("\n".join(new_lines) + "\n")

            processed_counts[s] += 1

    print("\n[+] Đã xử lý và tích hợp thành công:")
    for s in splits:
        print(f"    - {s}: Thêm {processed_counts[s]} ảnh, {box_added[s]} bounding box xe kéo (class 6)")

    # 3. Báo cáo thống kê toàn bộ dataset sau khi tích hợp
    print("\n" + "="*75)
    print(f"{'BẢNG TỔNG HỢP TOÀN BỘ DATASET HIỆN TẠI (TRƯỚC KHI AUGMENT)':^75}")
    print("="*75)

    total_imgs = {}
    for s in splits:
        p = os.path.join(data_dir, s, "images")
        total_imgs[s] = len(os.listdir(p)) if os.path.exists(p) else 0

    all_total_imgs = sum(total_imgs.values())
    print(f"Tổng số ảnh: {all_total_imgs} ảnh")
    print(f"  - Train: {total_imgs['train']} ảnh ({total_imgs['train']/all_total_imgs*100:.1f}%)")
    print(f"  - Valid: {total_imgs['valid']} ảnh ({total_imgs['valid']/all_total_imgs*100:.1f}%)")
    print(f"  - Test:  {total_imgs['test']} ảnh ({total_imgs['test']/all_total_imgs*100:.1f}%)")
    print("-"*75)
    print(f"{'Class ID':<10}{'Tên Class':<15}{'Train':<15}{'Valid':<15}{'Test':<15}{'Tổng':<10}")
    print("-"*75)

    split_counts = {s: Counter() for s in splits}
    for s in splits:
        lbl_p = os.path.join(data_dir, s, "labels")
        if os.path.exists(lbl_p):
            for f in os.listdir(lbl_p):
                with open(os.path.join(lbl_p, f), 'r', encoding="utf-8") as fp:
                    for line in fp:
                        parts = line.strip().split()
                        if parts:
                            split_counts[s][int(parts[0])] += 1

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
    parser.add_argument("--execute", action="store_true", help="Thực thi xử lý và gộp dữ liệu")
    args = parser.parse_args()

    process_and_merge_xe_keo(dry_run=not args.execute)

