#!/usr/bin/env python3
"""
YOLO11n Pseudo-Labeler for Vietnamese Traffic Dataset.
Runs COCO-pretrained YOLO11n in batch inference over quality-filtered frames,
extracts target vehicle classes (bicycle, car, motorcycle, bus, truck),
saves bounding boxes in YOLO format, and outputs yield statistics and review warnings.
"""

import os
import sys
import csv
import argparse
import shutil
import time
from datetime import datetime
import numpy as np

# Mapping COCO class IDs to human-readable names
COCO_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

def parse_args():
    parser = argparse.ArgumentParser(
        description="Run YOLO11n Pseudo-Labeling over Kept Dataset Frames"
    )
    # Inputs & Outputs
    parser.add_argument(
        "--input-dir", "-i",
        default="1_AI_Processing_Edge/frame_extraction/extracted_frames/kept",
        help="Path to the directory containing kept/ filtered frames (default: 1_AI_Processing_Edge/frame_extraction/extracted_frames/kept)."
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="1_AI_Processing_Edge/pseudo_labeling/pseudo_labeled",
        help="Path to save pseudo-labeled output dataset (default: 1_AI_Processing_Edge/pseudo_labeling/pseudo_labeled)."
    )
    
    # Inference config
    parser.add_argument(
        "--conf", "-c",
        type=float,
        default=0.35,
        help="Confidence threshold for YOLO prediction (default: 0.35)."
    )
    parser.add_argument(
        "--device",
        default="",
        help="Device to run inference on (e.g. cpu, cuda, or 0, default: auto-detects GPU)."
    )
    
    # Image saving mode
    parser.add_argument(
        "--symlink",
        action="store_true",
        help="Create symlinks to source images instead of copying them (requires admin/developer mode on Windows)."
    )
    
    # Outlier thresholds for manual review prioritization
    parser.add_argument(
        "--high-density-limit",
        type=int,
        default=15,
        help="Detections count limit above which a frame is flagged as high-density (default: 15)."
    )
    
    return parser.parse_args()


def setup_directories(output_dir):
    """Creates the target directory structure for annotation import."""
    images_dir = os.path.join(output_dir, "images")
    labels_dir = os.path.join(output_dir, "labels")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(labels_dir, exist_ok=True)
    return images_dir, labels_dir


def handle_image_file(src_path, dest_dir, use_symlink):
    """Copies or symlinks the source image to the destination directory."""
    filename = os.path.basename(src_path)
    dest_path = os.path.join(dest_dir, filename)
    
    # Remove existing file/link to avoid errors on rerun
    if os.path.exists(dest_path) or os.path.islink(dest_path):
        try:
            os.remove(dest_path)
        except Exception as e:
            print(f"Warning: Could not remove existing file {dest_path}: {e}")
            
    if use_symlink:
        try:
            os.symlink(os.path.abspath(src_path), dest_path)
        except Exception as e:
            # Fallback to copying if symlinking fails (common on Windows without admin)
            print(f"Warning: Symlink failed for {filename} ({e}). Falling back to copy.")
            shutil.copy2(src_path, dest_path)
    else:
        shutil.copy2(src_path, dest_path)
        
    return dest_path


def main():
    args = parse_args()
    
    # 1. Verification of inputs
    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory '{args.input_dir}' does not exist.")
        print("Please run the frame extraction phase first.")
        sys.exit(1)
        
    # Check if we can import ultralytics
    try:
        from ultralytics import YOLO
    except ImportError:
        print("Error: The 'ultralytics' library is not installed.")
        print("Please install it by running: pip install ultralytics")
        sys.exit(1)
        
    # 2. Setup outputs
    images_dir, labels_dir = setup_directories(args.output_dir)
    
    # 3. Load YOLO model
    print("Loading stock YOLO11n model...")
    device = args.device if args.device else None
    try:
        model = YOLO("yolo11n.pt")
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)
        
    # 4. Find source images
    image_extensions = ('.jpg', '.jpeg', '.png')
    input_images = [
        f for f in os.listdir(args.input_dir)
        if f.lower().endswith(image_extensions)
    ]
    
    if not input_images:
        print(f"No image files found in '{args.input_dir}'.")
        sys.exit(0)
        
    print(f"Found {len(input_images)} quality-filtered frames in '{args.input_dir}'")
    print(f"Running inference at confidence threshold: {args.conf} (target classes: {list(COCO_CLASSES.values())})")
    
    # Initialize logs & stats
    prediction_log_path = os.path.join(args.output_dir, "prediction_log.csv")
    
    # Statistics counters
    stats = {
        "total_processed": 0,
        "frames_with_detections": 0,
        "frames_with_zero_detections": 0,
        "class_counts": {cid: 0 for cid in COCO_CLASSES.keys()}
    }
    
    # Lists for outlier reporting
    high_density_outliers = []
    low_confidence_outliers = []
    
    start_time = time.time()
    
    try:
        log_file = open(prediction_log_path, 'w', newline='', encoding='utf-8')
        csv_writer = csv.writer(log_file)
        # Write headers
        csv_writer.writerow([
            "Timestamp", "Image_Filename", "Detections_Count", "Avg_Confidence", "Detected_Classes"
        ])
        
        # Use stream=True to prevent loading entire batches into RAM
        # Filter for classes: 1 (bicycle), 2 (car), 3 (motorcycle), 5 (bus), 7 (truck)
        results = model.predict(
            source=args.input_dir,
            conf=args.conf,
            classes=list(COCO_CLASSES.keys()),
            stream=True,
            device=device,
            verbose=False
        )
        
        for result in results:
            stats["total_processed"] += 1
            image_path = result.path
            filename = os.path.basename(image_path)
            
            # Save/link image
            handle_image_file(image_path, images_dir, args.symlink)
            
            boxes = result.boxes
            detections_count = len(boxes)
            
            # Initialize default record fields
            avg_conf = 0.0
            classes_detected = []
            
            # Label file path
            label_filename = os.path.splitext(filename)[0] + ".txt"
            label_path = os.path.join(labels_dir, label_filename)
            
            if detections_count > 0:
                stats["frames_with_detections"] += 1
                
                # Write YOLO standard label format (.txt)
                # Format: class_idx x_center y_center width height confidence
                confs = []
                with open(label_path, 'w', encoding='utf-8') as f_lbl:
                    for box in boxes:
                        cls_id = int(box.cls[0].item())
                        conf_val = float(box.conf[0].item())
                        xywhn = box.xywhn[0].tolist()
                        
                        # Write box values
                        f_lbl.write(f"{cls_id} {xywhn[0]:.6f} {xywhn[1]:.6f} {xywhn[2]:.6f} {xywhn[3]:.6f} {conf_val:.4f}\n")
                        
                        # Collect metrics
                        confs.append(conf_val)
                        stats["class_counts"][cls_id] += 1
                        class_name = COCO_CLASSES.get(cls_id, "unknown")
                        if class_name not in classes_detected:
                            classes_detected.append(class_name)
                            
                avg_conf = float(np.mean(confs))
                
                # 5. Outlier Detection
                # Flag high-density outliers (potential false positive clusters)
                if detections_count >= args.high_density_limit:
                    high_density_outliers.append((filename, detections_count))
                    
                # Flag low-confidence outliers (average confidence close to threshold)
                # Threshold for low confidence warning: conf_threshold + 0.10
                if avg_conf < (args.conf + 0.10):
                    low_confidence_outliers.append((filename, avg_conf, detections_count))
            else:
                stats["frames_with_zero_detections"] += 1
                # If zero detections, we write an empty label file to indicate the image is empty
                # (Many training pipelines require empty txt files for images with no objects to learn background)
                with open(label_path, 'w', encoding='utf-8') as f_lbl:
                    pass
                    
            # Log record
            csv_writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                filename,
                detections_count,
                f"{avg_conf:.4f}",
                ", ".join(classes_detected) if classes_detected else "none"
            ])
            
            # Console progress update
            if stats["total_processed"] % 50 == 0:
                print(f"Processed {stats['total_processed']}/{len(input_images)} frames...")
                
    except Exception as e:
        print(f"Error during batch execution: {e}")
        sys.exit(1)
    finally:
        log_file.close()
        
    elapsed = time.time() - start_time
    print(f"\nPseudo-labeling batch complete in {elapsed:.2f} seconds.")
    
    # 6. Generate yield & review reports
    summary_path = os.path.join(args.output_dir, "pseudo_labeling_summary.txt")
    
    summary_lines = []
    summary_lines.append("=" * 65)
    summary_lines.append("PSEUDO-LABELING YIELD REPORT")
    summary_lines.append("=" * 65)
    summary_lines.append(f"Total Frames Processed:                  {stats['total_processed']}")
    summary_lines.append(f"Frames with Detections (>= 1 object):     {stats['frames_with_detections']} ({(stats['frames_with_detections']/stats['total_processed'])*100:.1f}%)")
    summary_lines.append(f"Frames with Zero Detections (Background):  {stats['frames_with_zero_detections']} ({(stats['frames_with_zero_detections']/stats['total_processed'])*100:.1f}%)")
    summary_lines.append("-" * 65)
    
    summary_lines.append("DETECTION COUNTS BY COCO CLASS:")
    for cid, name in COCO_CLASSES.items():
        count = stats["class_counts"][cid]
        summary_lines.append(f"  - {name:<15}: {count} instances")
    summary_lines.append("-" * 65)
    
    summary_lines.append(f"PRIORITIZED FOR MANUAL REVIEW:")
    summary_lines.append(f"  - High-density frames (>= {args.high_density_limit} detections): {len(high_density_outliers)}")
    summary_lines.append(f"  - Borderline low-confidence frames (< {args.conf + 0.10:.2f} avg conf): {len(low_confidence_outliers)}")
    summary_lines.append("=" * 65)
    
    # Print summary to terminal
    summary_text = "\n".join(summary_lines)
    print(summary_text)
    
    # Print details of top outliers (limit to 10 each)
    if high_density_outliers:
        print("\n[!] Top High-Density Frames (Review for false-positive clusters):")
        # Sort by count descending
        high_density_outliers.sort(key=lambda x: x[1], reverse=True)
        for fname, count in high_density_outliers[:10]:
            print(f"  - {fname} ({count} detections)")
            
    if low_confidence_outliers:
        print("\n[!] Borderline Low-Confidence Frames (Review for distorted/partial vehicles):")
        # Sort by avg confidence ascending
        low_confidence_outliers.sort(key=lambda x: x[1])
        for fname, conf, count in low_confidence_outliers[:10]:
            print(f"  - {fname} (Avg Conf: {conf:.3f}, Objects: {count})")
            
    # Write summary to file
    try:
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary_text)
            f.write("\n\n=== OUTLIER DETAILS ===\n")
            f.write("\nHIGH DENSITY OUTLIERS:\n")
            for fname, count in high_density_outliers:
                f.write(f"{fname},{count}\n")
            f.write("\nLOW CONFIDENCE OUTLIERS:\n")
            for fname, conf, count in low_confidence_outliers:
                f.write(f"{fname},{conf:.4f},{count}\n")
                
        print(f"\nSummary report saved to: {summary_path}")
        print(f"Prediction log saved to: {prediction_log_path}")
    except Exception as e:
        print(f"Error saving summary report: {e}")


if __name__ == "__main__":
    main()
