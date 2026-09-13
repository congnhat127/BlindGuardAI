"""
Script: augment_minority_classes.py
Mô tả:
1. Xử lý xe kéo (xe_keo) thành chuẩn góc Fisheye mắt cá:
   - Crop xe kéo từ data ngoài, scale nhỏ về kích thước thực tế (80 - 220px)
   - Áp dụng độ méo Barrel Distortion (uốn cong theo bán kính tâm mắt cá)
   - Áp dụng độ mờ nhẹ (Lens softness / Gaussian blur) và noise phù hợp với camera 180 độ
   - Dán (Copy-Paste) lên các vị trí mặt đường/điểm mù trên frame nền fisheye thực tế
2. Augment các class ít mẫu (bicycle, bus, truck, xich_lo) bằng các phép biến đổi
   hình học và quang học chuẩn (Horizontal Flip, Scale Jitter, HSV Color, Motion Blur)
   để đạt số lượng cân bằng ~220 - 320 boxes trong tập train.
"""

import os
import random
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from collections import Counter

def apply_barrel_distortion(image_np, k=0.3):
    """Áp dụng biến dạng thùng (Barrel Distortion) mô phỏng độ cong thấu kính mắt cá"""
    h, w = image_np.shape[:2]
    # Ma trận camera giả lập
    fx = fy = max(h, w)
    cx, cy = w / 2.0, h / 2.0
    camera_matrix = np.array([[fx, 0, cx],
                              [0, fy, cy],
                              [0, 0, 1]], dtype=np.float32)
    # Hệ số méo mắt cá: k1 > 0 tạo barrel distortion (phình to giữa, cong mép)
    dist_coeffs = np.array([k, k * 0.1, 0, 0], dtype=np.float32)
    new_camera_matrix = camera_matrix.copy()
    
    map1, map2 = cv2.initUndistortRectifyMap(
        camera_matrix, dist_coeffs, np.eye(3), new_camera_matrix, (w, h), cv2.CV_32FC1
    )
    distorted = cv2.remap(image_np, map1, map2, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    return distorted

def generate_fisheye_xekeo(train_img_dir, train_lbl_dir, num_samples=130):
    """
    Tạo các mẫu xe kéo góc mắt cá thực tế (kích thước nhỏ, uốn cong, độ mờ mắt cá)
    dán lên nền đường fisheye thật của dự án.
    """
    print(f"[*] Đang sinh {num_samples} mẫu xe kéo Fisheye thực tế...")
    
    # 1. Tìm các ảnh xe kéo ngoại sinh trong train
    ext_lbl_files = [f for f in os.listdir(train_lbl_dir) if f.startswith("xekeo_ext_train_")]
    # 2. Tìm các ảnh nền fisheye thật (không phải xekeo_ext_)
    real_fisheye_imgs = [f for f in os.listdir(train_img_dir) if not f.startswith("xekeo_ext_") and not f.startswith("aug_") and not f.startswith("synth_")]

    if not ext_lbl_files or not real_fisheye_imgs:
        print("[!] Không đủ ảnh nền fisheye hoặc ảnh xe kéo mẫu.")
        return 0

    generated_count = 0
    
    for i in range(num_samples):
        # Chọn ngẫu nhiên 1 ảnh xe kéo và 1 ảnh nền fisheye thật
        lbl_file = random.choice(ext_lbl_files)
        bg_file = random.choice(real_fisheye_imgs)

        img_file = lbl_file.replace(".txt", ".jpg")
        src_img_path = os.path.join(train_img_dir, img_file)
        src_lbl_path = os.path.join(train_lbl_dir, lbl_file)
        bg_img_path = os.path.join(train_img_dir, bg_file)

        if not os.path.exists(src_img_path) or not os.path.exists(bg_img_path):
            continue

        try:
            # Đọc ảnh nguồn và đọc box xe kéo
            src_img = Image.open(src_img_path).convert("RGB")
            sw, sh = src_img.size

            boxes = []
            with open(src_lbl_path, "r") as fp:
                for line in fp:
                    p = line.strip().split()
                    if p and p[0] == "6":
                        boxes.append([float(x) for x in p[1:]])

            if not boxes:
                continue

            # Lấy 1 box xe kéo
            box = random.choice(boxes)
            bx_c, by_c, bw, bh = box
            
            # Tọa độ pixel trên ảnh nguồn
            xmin = max(0, int((bx_c - bw / 2.0) * sw))
            ymin = max(0, int((by_c - bh / 2.0) * sh))
            xmax = min(sw, int((bx_c + bw / 2.0) * sw))
            ymax = min(sh, int((by_c + bh / 2.0) * sh))

            if xmax - xmin < 20 or ymax - ymin < 20:
                continue

            crop_obj = src_img.crop((xmin, ymin, xmax, ymax))

            # --- BƯỚC 1: SCALE NHỎ VỀ KÍCH THƯỚC CAMERA MẮT CÁ ---
            # Trong frame fisheye 640x640, xe kéo ở cự ly thường rộng khoảng 90 - 200px
            target_w = random.randint(90, 210)
            aspect_ratio = (xmax - xmin) / float(ymax - ymin)
            target_h = int(target_w / aspect_ratio)
            crop_obj = crop_obj.resize((target_w, target_h), Image.Resampling.LANCZOS)

            # --- BƯỚC 2: TẠO ĐỘ MỜ (LENS SOFTNESS / MOTION BLUR) ---
            blur_radius = random.uniform(0.6, 1.4)
            crop_obj = crop_obj.filter(ImageFilter.GaussianBlur(radius=blur_radius))

            # Chuyển sang numpy để bẻ cong
            crop_np = np.array(crop_obj)

            # --- BƯỚC 3: UỐN CONG MẮT CÁ (BARREL DISTORTION) ---
            k_val = random.uniform(0.20, 0.45)
            curved_np = apply_barrel_distortion(crop_np, k=k_val)

            # --- BƯỚC 4: DÁN VÀO NỀN FISHEYE THẬT ---
            bg_img = Image.open(bg_img_path).convert("RGB")
            bg_w, bg_h = bg_img.size

            # Đọc các nhãn cũ của ảnh nền
            bg_lbl_path = os.path.join(train_lbl_dir, bg_file.replace(".jpg", ".txt"))
            existing_labels = []
            if os.path.exists(bg_lbl_path):
                with open(bg_lbl_path, "r") as fp:
                    for line in fp:
                        if line.strip():
                            existing_labels.append(line.strip())

            # Chọn vị trí dán ở vùng mặt đường (vùng điểm mù hoặc làn đường: Y từ 45% đến 80%)
            paste_y = random.randint(int(bg_h * 0.45), int(bg_h * 0.78) - target_h)
            # Chọn X: ưu tiên vùng mép sườn xe (trái: 5% - 35%, phải: 60% - 90%)
            if random.random() < 0.5:
                paste_x = random.randint(int(bg_w * 0.05), int(bg_w * 0.35))
            else:
                paste_x = random.randint(int(bg_w * 0.60), max(int(bg_w * 0.65), bg_w - target_w - 20))

            paste_x = max(0, min(paste_x, bg_w - target_w))
            paste_y = max(0, min(paste_y, bg_h - target_h))

            # Dán vật thể
            curved_pil = Image.fromarray(curved_np)
            bg_img.paste(curved_pil, (paste_x, paste_y))

            # Tính toán Bounding Box mới cho xe kéo
            new_xc = (paste_x + target_w / 2.0) / bg_w
            new_yc = (paste_y + target_h / 2.0) / bg_h
            new_w = target_w / float(bg_w)
            new_h = target_h / float(bg_h)
            new_line = f"6 {new_xc:.6f} {new_yc:.6f} {new_w:.6f} {new_h:.6f}"
            existing_labels.append(new_line)

            # Lưu ảnh mới và nhãn mới
            out_name = f"synth_fisheye_xekeo_{i+1:04d}"
            out_img_path = os.path.join(train_img_dir, out_name + ".jpg")
            out_lbl_path = os.path.join(train_lbl_dir, out_name + ".txt")

            bg_img.save(out_img_path, "JPEG", quality=95)
            with open(out_lbl_path, "w") as fp:
                fp.write("\n".join(existing_labels) + "\n")

            generated_count += 1
        except Exception as e:
            continue

    print(f"[+] Hoàn thành sinh {generated_count} ảnh xe kéo Fisheye tổng hợp.")
    return generated_count

def augment_minority_instances(train_img_dir, train_lbl_dir):
    """
    Augment các class ít mẫu:
    - bicycle (35 box) -> Nhân bản thêm ~200 box
    - bus (66 box) -> Nhân bản thêm ~180 box
    - truck (127 box) -> Nhân bản thêm ~120 box
    - xich_lo (179 box) -> Nhân bản thêm ~100 box
    Sử dụng Horizontal Flip (Lật ngang), Color/Lighting Jitter, Motion Blur
    """
    print("[*] Đang thực hiện Augmentation cho các class ít mẫu (bicycle, bus, truck, xich_lo)...")

    # Phân loại ảnh theo class có trong ảnh
    img_with_class = {cid: [] for cid in [0, 1, 5, 7]}

    for lf in os.listdir(train_lbl_dir):
        if not lf.endswith(".txt") or lf.startswith("aug_") or lf.startswith("synth_"):
            continue
        p = os.path.join(train_lbl_dir, lf)
        with open(p, "r") as fp:
            classes = set()
            for line in fp:
                parts = line.strip().split()
                if parts:
                    cid = int(parts[0])
                    if cid in img_with_class:
                        classes.add(cid)
            for cid in classes:
                img_with_class[cid].append(lf.replace(".txt", ".jpg"))

    # Kế hoạch số lượng bản sinh mới:
    # Class 0 (bicycle - 35 box): sinh 6 bản/ảnh
    # Class 1 (bus - 66 box): sinh 3 bản/ảnh
    # Class 5 (truck - 127 box): sinh 1 bản/ảnh
    # Class 7 (xich_lo - 179 box): sinh 1 bản/ảnh
    mult_rules = {
        0: 6,
        1: 3,
        5: 1,
        7: 1
    }

    aug_generated = 0
    for cid, multiplier in mult_rules.items():
        imgs = img_with_class[cid]
        print(f"    - Augment Class {cid}: {len(imgs)} ảnh gốc x {multiplier} biến thể...")
        for img_name in imgs:
            src_img_p = os.path.join(train_img_dir, img_name)
            src_lbl_p = os.path.join(train_lbl_dir, img_name.replace(".jpg", ".txt"))

            if not os.path.exists(src_img_p) or not os.path.exists(src_lbl_p):
                continue

            try:
                img = Image.open(src_img_p).convert("RGB")
                with open(src_lbl_p, "r") as fp:
                    original_lines = [l.strip() for l in fp if l.strip()]

                for m in range(multiplier):
                    new_img = img.copy()
                    new_lines = []

                    # Biến thể 1: Lật ngang (Horizontal Flip)
                    # Khi lật ngang, x_center mới = 1.0 - x_center
                    do_flip = (m % 2 == 1)
                    if do_flip:
                        new_img = new_img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

                    # Biến thể 2: Độ sáng & Tương phản (Brightness/Contrast)
                    b_factor = random.uniform(0.85, 1.20)
                    new_img = ImageEnhance.Brightness(new_img).enhance(b_factor)
                    c_factor = random.uniform(0.85, 1.15)
                    new_img = ImageEnhance.Contrast(new_img).enhance(c_factor)

                    # Biến thể 3: Làm mờ nhẹ ngẫu nhiên (Softness)
                    if random.random() < 0.35:
                        new_img = new_img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 1.2)))

                    # Cập nhật tọa độ nhãn
                    for line in original_lines:
                        parts = line.split()
                        c = parts[0]
                        xc, yc, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                        if do_flip:
                            xc = 1.0 - xc
                        new_lines.append(f"{c} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}")

                    # Lưu ảnh mới
                    base_name = os.path.splitext(img_name)[0]
                    aug_name = f"aug_cls{cid}_{base_name}_v{m+1}"
                    out_img_p = os.path.join(train_img_dir, aug_name + ".jpg")
                    out_lbl_p = os.path.join(train_lbl_dir, aug_name + ".txt")

                    new_img.save(out_img_p, "JPEG", quality=95)
                    with open(out_lbl_p, "w") as fp:
                        fp.write("\n".join(new_lines) + "\n")

                    aug_generated += 1
            except Exception as e:
                continue

    print(f"[+] Hoàn thành sinh {aug_generated} ảnh biến thể cho các class ít mẫu.")
    return aug_generated

def main():
    train_img_dir = "1_AI_Processing_Edge/data/train/images"
    train_lbl_dir = "1_AI_Processing_Edge/data/train/labels"
    data_dir = "1_AI_Processing_Edge/data"
    class_names = ['bicycle', 'bus', 'car', 'motorcycle', 'person', 'truck', 'xe_keo', 'xich_lo']

    print("="*75)
    print(f"{'QUY TRÌNH TIỀN XỬ LÝ & AUGMENTATION DỮ LIỆU ĐẶC THÙ':^75}")
    print("="*75)

    # 1. Sinh các mẫu xe kéo Fisheye thực tế
    gen_xekeo = generate_fisheye_xekeo(train_img_dir, train_lbl_dir, num_samples=130)

    # 2. Augment các class ít mẫu
    gen_minority = augment_minority_instances(train_img_dir, train_lbl_dir)

    # 3. Thống kê lại phân phối class sau khi augment
    print("\n" + "="*75)
    print(f"{'BẢNG PHÂN PHỐI TOÀN BỘ DATASET SAU KHI AUGMENT':^75}")
    print("="*75)

    total_imgs = {}
    for s in ["train", "valid", "test"]:
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

    split_counts = {s: Counter() for s in ["train", "valid", "test"]}
    for s in ["train", "valid", "test"]:
        lbl_p = os.path.join(data_dir, s, "labels")
        if os.path.exists(lbl_p):
            for f in os.listdir(lbl_p):
                with open(os.path.join(lbl_p, f), 'r') as fp:
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
    main()

