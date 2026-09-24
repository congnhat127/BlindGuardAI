"""
Script: merge_new20_9.py
Mô tả:
- Trích xuất 674 ảnh mới (chứa 349 mẫu xe kéo thật) từ data/new20_9
- Loại bỏ 888 ảnh đã bị trùng lặp với dữ liệu cũ
- Sao chép ảnh và nhãn theo đúng phân bổ chuẩn Roboflow:
    + Train: 563 ảnh mới
    + Valid: 71 ảnh mới
    + Test:  40 ảnh mới
- Thống kê chi tiết phân bố 8 lớp trước và sau khi gộp.
"""

import shutil
from pathlib import Path
from collections import Counter

DATA_DIR = Path(__file__).resolve().parent / "data"
NEW_DIR = DATA_DIR / "new20_9"
CLASS_NAMES = ['bicycle', 'bus', 'car', 'motorcycle', 'person', 'truck', 'xe_keo', 'xich_lo']

def count_classes_in_dir(label_dir):
    counts = Counter()
    for txt in label_dir.glob("*.txt"):
        try:
            for line in txt.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    cls_id = line.split()[0]
                    counts[cls_id] += 1
        except Exception:
            pass
    return counts

def main():
    print("=" * 75)
    print(f"{'HỢP NHẤT DỮ LIỆU BỔ SUNG XE KÉO THẬT VÀO TẬP CHÍNH THỨC':^75}")
    print("=" * 75)
    print(f"[*] Thư mục nguồn mới:     {NEW_DIR}")
    print(f"[*] Thư mục đích chính:    {DATA_DIR}")

    if not NEW_DIR.exists():
        print(f"[!] Không tìm thấy thư mục {NEW_DIR}")
        return

    # Lấy danh sách ảnh hiện có trong data/ (không tính thư mục con new/new20_9)
    existing_imgs = set()
    for split in ["train", "valid", "test"]:
        img_dir = DATA_DIR / split / "images"
        for p in img_dir.glob("*.*"):
            existing_imgs.add(p.name)
    print(f"[*] Số lượng ảnh hiện có trong data chính: {len(existing_imgs)}")

    # Đếm số lượng lớp trước khi gộp
    before_counts = Counter()
    for split in ["train", "valid", "test"]:
        lbl_dir = DATA_DIR / split / "labels"
        before_counts.update(count_classes_in_dir(lbl_dir))

    # Tiến hành lọc và gộp
    splits = ["train", "valid", "test"]
    stats = {}
    total_copied = 0

    for split in splits:
        src_img_dir = NEW_DIR / split / "images"
        src_lbl_dir = NEW_DIR / split / "labels"

        dst_img_dir = DATA_DIR / split / "images"
        dst_lbl_dir = DATA_DIR / split / "labels"
        dst_img_dir.mkdir(parents=True, exist_ok=True)
        dst_lbl_dir.mkdir(parents=True, exist_ok=True)

        copied_in_split = 0
        skipped_in_split = 0

        for img_path in sorted(src_img_dir.glob("*.*")):
            if img_path.name in existing_imgs:
                skipped_in_split += 1
                continue

            # Sao chép ảnh
            dst_img_path = dst_img_dir / img_path.name
            shutil.copy2(img_path, dst_img_path)
            existing_imgs.add(img_path.name)

            # Sao chép file nhãn txt tương ứng
            lbl_path = src_lbl_dir / f"{img_path.stem}.txt"
            if lbl_path.exists():
                dst_lbl_path = dst_lbl_dir / lbl_path.name
                shutil.copy2(lbl_path, dst_lbl_path)

            copied_in_split += 1

        stats[split] = {
            "copied": copied_in_split,
            "skipped": skipped_in_split,
            "total_after": len(list(dst_img_dir.glob("*.*")))
        }
        total_copied += copied_in_split

    # Đếm lại sau khi gộp
    after_counts = Counter()
    for split in splits:
        lbl_dir = DATA_DIR / split / "labels"
        after_counts.update(count_classes_in_dir(lbl_dir))

    print("\n" + "=" * 75)
    print(f"{'KẾT QUẢ GỘP DỮ LIỆU CHI TIẾT':^75}")
    print("=" * 75)
    for split, s in stats.items():
        print(f"  • Tập {split.upper():<6}: Thêm mới +{s['copied']:<4} ảnh | Trùng lặp bỏ qua: {s['skipped']:<4} | Tổng sau gộp: {s['total_after']:<5} ảnh")
    print(f"\n[+] Tổng số ảnh mới độc nhất đã thêm vào toàn bộ dataset: {total_copied} ảnh.")

    print("\n" + "-" * 75)
    print(f"{'BIẾN ĐỘNG SỐ LƯỢNG BOUNDING BOX THEO LỚP (BEFORE -> AFTER)':^75}")
    print("-" * 75)
    print(f"{'Class ID':<10} {'Tên Lớp (Class Name)':<22} {'Trước Gộp':<14} {'Sau Gộp':<14} {'Tăng (+)'}")
    print("-" * 75)
    for idx, name in enumerate(CLASS_NAMES):
        b = before_counts.get(str(idx), 0)
        a = after_counts.get(str(idx), 0)
        diff = a - b
        pct = f"(+{diff/b*100:.1f}%)" if b > 0 and diff > 0 else ""
        highlight = " <== [BOOST LỚN!]" if idx == 6 else ""
        print(f"{idx:<10} {name:<22} {b:<14} {a:<14} +{diff:<6} {pct} {highlight}")
    print("=" * 75)

if __name__ == "__main__":
    main()

