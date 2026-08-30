
# 180° Wide-Angle Dash Cam Frame Extraction & Quality Filter

This sub-module provides high-performance, quality-filtered frame extraction from video footage for building a high-quality Vietnamese Traffic Dataset suitable for training YOLO11n object detection models.

## Structure

- **`frame_extractor.py`**: Batch processing script that extracts frames from videos at configurable frame rates, assesses frame quality using blur and brightness parameters, and organizes frames into `kept/` and `rejected_*` folders.
- **`recover_frame.py`**: Utility script to manually move a rejected frame back to `kept/` and update its audit log status.

## Directory Layout

Place your raw video files in the `raw_videos/` folder. The output folders will be generated under `extracted_frames/`:
```
1_AI_Processing_Edge/frame_extraction/
├── frame_extractor.py
├── recover_frame.py
├── raw_videos/              ← Place your raw .mp4 videos here
└── extracted_frames/        ← Outputs folder (created automatically)
    ├── kept/                ← High-quality frames ready for dataset inclusion/labeling
    ├── rejected_blurry/     ← Extracted frames that failed the blur threshold
    ├── rejected_overexposed/← Extracted frames that failed brightness/glare thresholds
    ├── filter_log.csv       ← Complete audit log of every frame's metrics and status
    └── extraction_summary.txt← Copy of the batch process summary report
```

---

## 1. Frame Extraction Rates Strategy

Consecutive frames in traffic video can be highly redundant. To balance dataset size with data diversity, we support two extraction rate tiers:

*   **Standard Rate (Default: 0.3333 FPS):** Extracts 1 frame every 3 seconds. At typical driving speeds (e.g. 40 km/h or ~11 m/s), a vehicle travels 33 meters between frames, providing clean viewpoint transitions and background diversity.
*   **Rare/High-Value Rate (Default: 5.0 FPS):** Extracts 5 frames per second for specific footage flagged as containing rare traffic participants (e.g., *xich lo*, hand carts, agricultural trailers). This allows capturing rare classes in multiple perspectives and distances inside the wide-angle camera's field of view without overloading annotators with redundant highway frames.

### Configuring Custom Rates
You can specify custom frame rates for specific files in two ways:
1.  **Prefix matching:** Any video file starting with `rare_` (e.g., `rare_xich_lo_hanoi.mp4`) automatically uses the high-value rate.
2.  **JSON Config File:** Pass a JSON configuration map defining FPS per video using the `--config-file` argument.
    
    *Example `rare_videos.json`:*
    ```json
    {
      "highway_trip_01.mp4": 0.5,
      "rare_cyclos_district_1.mp4": 10.0,
      "xe_keo_market_rush.mp4": 5.0
    }
    ```

---

## 2. Naming Convention
Extracted frames are named to ensure absolute traceability:
```
{video_basename}_f{frame_index}_t{timestamp_ms}ms.jpg
```
*Example:* `trip024_f000180_t00006000ms.jpg` represents frame index 180, extracted at exactly 6000ms (6.0 seconds) into `trip024.mp4`.

---

## 3. Quality Filtering Algorithms

Wide-angle dash cams face severe radial distortion at the borders (edge blur) and are frequently subjected to strong sunlight glare or high-contrast shadows. The tool implements the following check parameters:

1.  **Blur (Laplacian Variance):** Evaluates the variance of the Laplacian of the grayscale frame. A high variance indicates sharp transitions (edges), whereas low variance indicates blur. Frames below the `--blur-threshold` (default `50.0`) are moved to `rejected_blurry/`.
2.  **Overexposure (Glare):** High average brightness ($> 248$) or too many white/clipped pixels ($> 30\%$ of pixels at $> 250$ brightness) triggers rejection. These are moved to `rejected_overexposed/`.
3.  **Underexposure:** Average brightness $< 35$ or extreme darkness ($> 70\%$ of pixels at $< 15$ brightness) triggers rejection. These are moved to `rejected_overexposed/`.

---

## 4. Usage

### Prerequisites
Make sure you have `opencv-python` and `numpy` installed:
```bash
pip install opencv-python numpy
```

### Running Batch Frame Extraction
If you put your videos in `1_AI_Processing_Edge/frame_extraction/raw_videos/`, you can run it from the root of the workspace without any arguments:
```bash
python 1_AI_Processing_Edge/frame_extraction/frame_extractor.py
```

### Advanced Customization Example
Customize quality thresholds and frame rates:
```bash
python 1_AI_Processing_Edge/frame_extraction/frame_extractor.py \
  --input-dir ./different_input_folder \
  --output-dir ./different_output_folder \
  --default-fps 0.5 \
  --rare-fps 8.0 \
  --blur-threshold 120.0 \
  --min-brightness 40.0 \
  --max-brightness 210.0 \
  --config-file rare_configs.json
```

### Reverting/Recovering Rejected Frames
If you manually review `rejected_blurry/` or `rejected_overexposed/` and find a frame that is actually acceptable, you can move it back to `kept/` and update the logs using `recover_frame.py`:

```bash
# Recover a single frame (using defaults)
python 1_AI_Processing_Edge/frame_extraction/recover_frame.py frame_name_f00030_t00001000ms.jpg

# Recover multiple frames in batch
python 1_AI_Processing_Edge/frame_extraction/recover_frame.py frame_1.jpg frame_2.jpg frame_3.jpg
```
