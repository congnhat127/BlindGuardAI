#!/usr/bin/env python3
"""
Frame Extractor and Quality Filter for Vietnamese Traffic Dataset.
Extracts frames from video files at configurable rates (standard vs rare/high FPS),
evaluates image quality (blur detection via Laplacian variance, and over/underexposure
via average brightness & pixel clipping), and automatically sorts frames into kept/rejected directories.
"""

import os
import sys
import csv
import json
import argparse
import time
from datetime import datetime
import cv2
import numpy as np

def parse_args():
    parser = argparse.ArgumentParser(
        description="Frame Extractor & Quality Filter for 180° Wide-Angle Traffic Footage"
    )
    # Inputs & Outputs
    parser.add_argument(
        "--input-dir", "-i",
        default="1_AI_Processing_Edge/frame_extraction/raw_videos",
        help="Path to the directory containing input .mp4 files (default: 1_AI_Processing_Edge/frame_extraction/raw_videos)."
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="1_AI_Processing_Edge/frame_extraction/extracted_frames",
        help="Path to the output directory (default: 1_AI_Processing_Edge/frame_extraction/extracted_frames)."
    )
    
    # Extraction Rates
    parser.add_argument(
        "--default-fps",
        type=float,
        default=0.3333,
        help="Default frame extraction rate (frames per second) for standard footage (default: 0.3333)."
    )
    parser.add_argument(
        "--rare-fps",
        type=float,
        default=5.0,
        help="High frame extraction rate (frames per second) for videos containing rare/valuable content (default: 5.0)."
    )
    parser.add_argument(
        "--config-file",
        help="Optional path to a JSON configuration file specifying custom FPS rates per video."
    )
    
    # Blur Detection Parameters
    parser.add_argument(
        "--blur-threshold",
        type=float,
        default=50.0,
        help="Laplacian variance threshold for blur detection. Below this is rejected (default: 50.0)."
    )
    
    # Exposure/Glare Parameters
    parser.add_argument(
        "--min-brightness",
        type=float,
        default=35.0,
        help="Minimum average brightness (0-255). Below this is rejected as underexposed (default: 35.0)."
    )
    parser.add_argument(
        "--max-brightness",
        type=float,
        default=248.0,
        help="Maximum average brightness (0-255). Above this is rejected as overexposed/glare (default: 248.0)."
    )
    parser.add_argument(
        "--clip-high-threshold",
        type=float,
        default=0.30,
        help="Maximum ratio of white pixels (brightness > 250) allowed before rejecting as overexposed/glare (default: 0.30)."
    )
    parser.add_argument(
        "--clip-low-threshold",
        type=float,
        default=0.70,
        help="Maximum ratio of dark pixels (brightness < 15) allowed before rejecting as underexposed (default: 0.70)."
    )
    
    return parser.parse_args()


def load_fps_config(config_path):
    """Loads a JSON configuration mapping video basenames to custom FPS rates."""
    if not config_path:
        return {}
    
    if not os.path.exists(config_path):
        print(f"Warning: Configuration file not found at {config_path}. Using default rates.")
        return {}
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Normalize keys to be basenames just in case full paths were given
            return {os.path.basename(k): float(v) for k, v in data.items()}
    except Exception as e:
        print(f"Error reading config file {config_path}: {e}. Proceeding with default rates.")
        return {}


def assess_quality(frame, args):
    """
    Evaluates frame quality for blur and exposure.
    Returns: (status, metrics_dict)
      status: 'kept', 'rejected_blurry', or 'rejected_overexposed'
      metrics_dict: dict of computed metrics
    """
    # Convert to grayscale for analysis
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # 1. Blur Check (Laplacian Variance)
    blur_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    is_blurry = blur_var < args.blur_threshold
    
    # 2. Exposure Checks
    avg_brightness = float(np.mean(gray))
    
    # High clipping ratio (pixels near white: > 250)
    clip_high_count = np.sum(gray > 250)
    clip_high_ratio = float(clip_high_count / gray.size)
    
    # Low clipping ratio (pixels near black: < 15)
    clip_low_count = np.sum(gray < 15)
    clip_low_ratio = float(clip_low_count / gray.size)
    
    is_overexposed = (avg_brightness > args.max_brightness) or (clip_high_ratio > args.clip_high_threshold)
    is_underexposed = (avg_brightness < args.min_brightness) or (clip_low_ratio > args.clip_low_threshold)
    
    metrics = {
        "blur_var": blur_var,
        "avg_brightness": avg_brightness,
        "clip_high_ratio": clip_high_ratio,
        "clip_low_ratio": clip_low_ratio
    }
    
    # Filter decision hierarchy: blur takes precedence, then exposure issues
    if is_blurry:
        return "rejected_blurry", metrics
    elif is_overexposed or is_underexposed:
        return "rejected_overexposed", metrics
    else:
        return "kept", metrics


def process_video(video_path, output_dirs, args, target_fps, csv_writer):
    """Processes a single video file, extracts frames, filters them, and logs results."""
    video_name = os.path.basename(video_path)
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        return {
            "video_name": video_name,
            "target_fps": target_fps,
            "total_extracted": 0,
            "kept": 0,
            "rejected_blurry": 0,
            "rejected_overexposed": 0
        }
    
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    if video_fps <= 0:
        video_fps = 30.0  # Fallback to standard 30 FPS if metadata is corrupt
        
    duration_sec = total_frames / video_fps
    
    # Determine the step size in frame indices
    step = max(1, round(video_fps / target_fps))
    
    stats = {
        "video_name": video_name,
        "target_fps": target_fps,
        "total_extracted": 0,
        "kept": 0,
        "rejected_blurry": 0,
        "rejected_overexposed": 0
    }
    
    current_frame_idx = 0
    
    print(f"Processing '{video_name}' | Source FPS: {video_fps:.2f} | Extracting at: {target_fps} FPS (Step: every {step} frames) | Est. duration: {duration_sec:.1f}s")
    
    while True:
        # Use cap.grab() to skip decoding frames we don't need (optimized reader pattern)
        success = cap.grab()
        if not success:
            break
            
        if current_frame_idx % step == 0:
            success, frame = cap.retrieve()
            if not success:
                break
                
            stats["total_extracted"] += 1
            
            # Approximate timestamp of the frame in milliseconds
            timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
            # Fallback if CAP_PROP_POS_MSEC returns 0 or negative
            if timestamp_ms <= 0:
                timestamp_ms = int((current_frame_idx / video_fps) * 1000)
                
            timestamp_sec = timestamp_ms / 1000.0
            
            # Assess quality
            status, metrics = assess_quality(frame, args)
            stats[status] += 1
            
            # Name convention: [video_basename_no_ext]_f[frame_index]_t[timestamp_ms]ms.jpg
            video_base, _ = os.path.splitext(video_name)
            frame_filename = f"{video_base}_f{current_frame_idx:06d}_t{timestamp_ms:08d}ms.jpg"
            
            # Determine save path
            save_path = os.path.join(output_dirs[status], frame_filename)
            cv2.imwrite(save_path, frame)
            
            # Log to CSV
            csv_writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                video_name,
                frame_filename,
                status,
                f"{metrics['blur_var']:.2f}",
                f"{metrics['avg_brightness']:.2f}",
                f"{metrics['clip_high_ratio']:.4f}",
                f"{metrics['clip_low_ratio']:.4f}",
                f"{args.blur_threshold:.2f}",
                f"{args.max_brightness:.2f}/{args.min_brightness:.2f}",
                f"{args.clip_high_threshold:.2f}/{args.clip_low_threshold:.2f}"
            ])
            
        current_frame_idx += 1
        
    cap.release()
    return stats


def print_summary(video_stats, summary_path):
    """Prints a structured summary table and saves it to a file."""
    header = f"{'Video Name':<35} | {'FPS':<6} | {'Total':<7} | {'Kept':<7} | {'Blurry':<7} | {'Exposure':<8}"
    divider = "-" * 83
    
    summary_lines = []
    summary_lines.append("=" * 83)
    summary_lines.append("FRAME EXTRACTION & FILTERING SUMMARY")
    summary_lines.append("=" * 83)
    summary_lines.append(header)
    summary_lines.append(divider)
    
    total_extracted = 0
    total_kept = 0
    total_blurry = 0
    total_exposure = 0
    
    for stat in video_stats:
        line = (f"{stat['video_name']:<35} | "
                f"{stat['target_fps']:<6.1f} | "
                f"{stat['total_extracted']:<7d} | "
                f"{stat['kept']:<7d} | "
                f"{stat['rejected_blurry']:<7d} | "
                f"{stat['rejected_overexposed']:<8d}")
        summary_lines.append(line)
        
        total_extracted += stat['total_extracted']
        total_kept += stat['kept']
        total_blurry += stat['rejected_blurry']
        total_exposure += stat['rejected_overexposed']
        
    summary_lines.append(divider)
    total_line = (f"{'TOTALS':<35} | "
                  f"{'-':<6} | "
                  f"{total_extracted:<7d} | "
                  f"{total_kept:<7d} | "
                  f"{total_blurry:<7d} | "
                  f"{total_exposure:<8d}")
    summary_lines.append(total_line)
    summary_lines.append("=" * 83)
    
    # Output to console
    print("\n".join(summary_lines))
    
    # Save to file
    try:
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(summary_lines))
        print(f"\nSummary report saved to: {summary_path}")
    except Exception as e:
        print(f"Error saving summary report: {e}")


def main():
    args = parse_args()
    
    # 1. Verify and create directories
    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory '{args.input_dir}' does not exist.")
        sys.exit(1)
        
    output_dir = args.output_dir
    output_dirs = {
        "kept": os.path.join(output_dir, "kept"),
        "rejected_blurry": os.path.join(output_dir, "rejected_blurry"),
        "rejected_overexposed": os.path.join(output_dir, "rejected_overexposed")
    }
    
    for path in output_dirs.values():
        os.makedirs(path, exist_ok=True)
        
    # 2. Find video files
    video_extensions = ('.mp4', '.avi', '.mov', '.mkv')
    video_files = []
    for file in os.listdir(args.input_dir):
        if file.lower().endswith(video_extensions):
            video_files.append(os.path.join(args.input_dir, file))
            
    if not video_files:
        print(f"No video files found in '{args.input_dir}'.")
        sys.exit(0)
        
    print(f"Found {len(video_files)} video files in '{args.input_dir}'")
    
    # 3. Load rare/custom FPS config
    fps_config = load_fps_config(args.config_file)
    
    # 4. Initialize CSV log
    log_csv_path = os.path.join(output_dir, "filter_log.csv")
    csv_file_exists = os.path.exists(log_csv_path)
    
    # Open CSV in append mode to support successive runs
    try:
        log_file = open(log_csv_path, 'a', newline='', encoding='utf-8')
        csv_writer = csv.writer(log_file)
        if not csv_file_exists:
            # Write Header
            csv_writer.writerow([
                "Timestamp", "Video", "Frame_Filename", "Status", 
                "Blur_Var", "Avg_Brightness", "Clip_High", "Clip_Low",
                "Blur_Threshold", "Brightness_Thresholds(Max/Min)", "Clipping_Thresholds(High/Low)"
            ])
    except Exception as e:
        print(f"Error initializing CSV log file at {log_csv_path}: {e}")
        sys.exit(1)
        
    # 5. Process Videos
    video_stats = []
    start_time = time.time()
    
    try:
        for video_path in video_files:
            video_name = os.path.basename(video_path)
            
            # Determine FPS rate for this video
            target_fps = args.default_fps
            if video_name in fps_config:
                target_fps = fps_config[video_name]
                print(f"Configured custom FPS for {video_name}: {target_fps}")
            elif video_name.startswith("rare_"):
                target_fps = args.rare_fps
                print(f"Detected prefix 'rare_' for {video_name}. Using rare FPS: {target_fps}")
                
            stats = process_video(video_path, output_dirs, args, target_fps, csv_writer)
            video_stats.append(stats)
            # Flush log to disk after each video
            log_file.flush()
    finally:
        log_file.close()
        
    elapsed = time.time() - start_time
    print(f"\nProcessing complete in {elapsed:.2f} seconds.")
    
    # 6. Generate and save summary reports
    summary_path = os.path.join(output_dir, "extraction_summary.txt")
    print_summary(video_stats, summary_path)


if __name__ == "__main__":
    main()
