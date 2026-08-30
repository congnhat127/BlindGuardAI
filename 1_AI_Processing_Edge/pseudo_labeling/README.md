# YOLO11n Pseudo-Labeling Module (COCO classes)

This sub-module runs a stock, COCO-pretrained YOLO11n model over quality-filtered images to auto-generate initial bounding boxes for standard vehicle classes. These auto-generated labels drastically reduce manual annotation time.

## Target COCO Classes
We only extract detections for classes present in both standard COCO datasets and our target class list:
*   **`1`**: bicycle (mapping to final target class `xe_dap`)
*   **`2`**: car (mapping to final target class `oto`)
*   **`3`**: motorcycle (mapping to final target class `xe_may`)
*   **`5`**: bus (mapping to final target class `xe_buyt`)
*   **`7`**: truck (mapping to final target class `xe_tai`)

*Note: Vietnam-specific classes `xich_lo` (cyclo) and `xe_keo` (cart/trailer) cannot be detected by this stock model and must be manually labeled in the next phase.*

---

## Directory Layout (Generated)
After executing the script, files are saved in an annotation-tool-ready structure:
```
1_AI_Processing_Edge/pseudo_labeling/
├── pseudo_labeler.py
└── pseudo_labeled/
    ├── images/                    ← Image copies/symlinks
    ├── labels/                    ← YOLO standard format .txt files (6 columns: class x y w h conf)
    ├── prediction_log.csv         ← Audit trail detailing detections per image
    └── pseudo_labeling_summary.txt← Performance/yield report, listing outliers to review first
```

---

## Usage

### Prerequisites
Make sure you have `ultralytics` (YOLO) and `numpy` installed:
```bash
pip install ultralytics numpy
```

### Running Batch Inference
Run the script using default paths (assumes your frames are in `1_AI_Processing_Edge/frame_extraction/extracted_frames/kept/`):
```bash
python 1_AI_Processing_Edge/pseudo_labeling/pseudo_labeler.py
```

### Configuring Parameters
You can customize the confidence threshold and use GPU if available:
```bash
python 1_AI_Processing_Edge/pseudo_labeling/pseudo_labeler.py \
  --input-dir /path/to/kept/frames \
  --output-dir /path/to/output_pseudo_labeled \
  --conf 0.40 \
  --device 0 \
  --symlink
```

---

## Yield & Outlier Reporting

The batch process outputs a summary report to prioritize your manual annotation work:

1.  **High-density frames:** Any frame containing $\ge 15$ detections is flagged. These are typical points of interest (complex intersections) or warning areas containing false-positive clusters (e.g. reflections or water droplets on the camera glass classified as multiple motorcycles).
2.  **Borderline low-confidence frames:** Frames where the average detection confidence is close to the threshold (e.g. $< 0.45$ for a threshold of $0.35$). These often contain partially obscured vehicles or vehicles far from the camera.

Reviewing these highlighted frames first helps identify config issues early.

---

## [!] Important Caveat: Fisheye (Radial) Distortion
The stock `yolo11n.pt` model was trained on standard flat (rectilinear) images. 

A 180° wide-angle dash cam introduces extreme **barrel distortion**, which stretches and squishes objects near the borders of the frame. Because of this:
*   Detection accuracy, recall, and bounding box snugness will be **significantly lower near the image edges** compared to the center.
*   **Human review is mandatory.** All generated label files (`.txt`) must be reviewed and corrected by an annotator before this dataset can be used to fine-tune the final target model. Do not treat these pseudo-labels as ground truth without review.
