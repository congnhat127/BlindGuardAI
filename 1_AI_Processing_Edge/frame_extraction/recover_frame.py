#!/usr/bin/env python3
"""
Recovery tool for Vietnamese Traffic Dataset Frame Extractor.
Allows manual override to move a frame from either rejected folder back to the 'kept/' folder,
and updates the status of that frame in 'filter_log.csv'.
"""

import os
import sys
import csv
import argparse
import shutil

def parse_args():
    parser = argparse.ArgumentParser(
        description="Recover rejected frames by moving them back to the kept/ folder."
    )
    parser.add_argument(
        "frame_names",
        nargs="+",
        help="One or more frame filenames (e.g. cam01_f0030_t0001000ms.jpg) to recover."
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="1_AI_Processing_Edge/frame_extraction/extracted_frames",
        help="Path to the output directory containing kept/ and rejected/ folders (default: 1_AI_Processing_Edge/frame_extraction/extracted_frames)."
    )
    return parser.parse_args()


def update_log_status(log_path, frame_name, new_status="recovered"):
    """Reads the CSV log, updates the status of the specified frame, and writes it back."""
    if not os.path.exists(log_path):
        print(f"Warning: log file not found at {log_path}. Frame moved but log not updated.")
        return False
        
    temp_path = log_path + ".tmp"
    updated = False
    
    try:
        with open(log_path, 'r', newline='', encoding='utf-8') as infile, \
             open(temp_path, 'w', newline='', encoding='utf-8') as outfile:
            
            reader = csv.reader(infile)
            writer = csv.writer(outfile)
            
            header = next(reader, None)
            if header:
                writer.writerow(header)
                # Find index of Frame_Filename and Status
                try:
                    frame_idx = header.index("Frame_Filename")
                    status_idx = header.index("Status")
                except ValueError:
                    # Fallback if headers changed
                    frame_idx = 2
                    status_idx = 3
            else:
                frame_idx = 2
                status_idx = 3
                
            for row in reader:
                if len(row) > max(frame_idx, status_idx):
                    if row[frame_idx] == frame_name:
                        row[status_idx] = new_status
                        updated = True
                writer.writerow(row)
                
        if updated:
            shutil.move(temp_path, log_path)
        else:
            os.remove(temp_path)
            
    except Exception as e:
        print(f"Error updating CSV log file: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False
        
    return updated


def main():
    args = parse_args()
    
    output_dir = args.output_dir
    kept_dir = os.path.join(output_dir, "kept")
    rejected_dirs = [
        os.path.join(output_dir, "rejected_blurry"),
        os.path.join(output_dir, "rejected_overexposed")
    ]
    
    if not os.path.exists(kept_dir):
        print(f"Error: Kept directory '{kept_dir}' does not exist. Make sure --output-dir is correct.")
        sys.exit(1)
        
    log_path = os.path.join(output_dir, "filter_log.csv")
    
    success_count = 0
    
    for frame_name in args.frame_names:
        # Normalize in case a path was passed instead of just the basename
        frame_name = os.path.basename(frame_name)
        
        found = False
        source_path = None
        
        for rej_dir in rejected_dirs:
            potential_path = os.path.join(rej_dir, frame_name)
            if os.path.exists(potential_path):
                found = True
                source_path = potential_path
                break
                
        if not found:
            # Check if it is already in the kept folder
            if os.path.exists(os.path.join(kept_dir, frame_name)):
                print(f"Info: Frame '{frame_name}' is already in the 'kept/' folder.")
            else:
                print(f"Error: Frame '{frame_name}' was not found in any rejected folders.")
            continue
            
        # Perform move
        dest_path = os.path.join(kept_dir, frame_name)
        try:
            shutil.move(source_path, dest_path)
            print(f"Successfully recovered: {frame_name} -> kept/")
            
            # Update log
            log_updated = update_log_status(log_path, frame_name, new_status="recovered")
            if log_updated:
                print(f"  Log status updated in CSV.")
            success_count += 1
        except Exception as e:
            print(f"Error moving file {frame_name}: {e}")
            
    print(f"\nRecovery complete. Successfully recovered {success_count} of {len(args.frame_names)} frames.")


if __name__ == "__main__":
    main()
