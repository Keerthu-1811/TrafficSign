# Traffic Sign Recognition - Dataset Specification & Training Guide
## India-Focused TSR Project

---

# 1. Project Overview

This document defines:

- Dataset structure
- Traffic sign classes
- Annotation format
- YOLO dataset configuration
- Preprocessing workflow
- Google Colab training pipeline
- Evaluation workflow

This serves as the implementation reference for the project.

---

# 2. Recommended Traffic Sign Classes

Start with 10–15 classes.

Example:

| Class ID | Traffic Sign |
|-----------|-------------|
| 0 | Stop |
| 1 | No Entry |
| 2 | Speed Limit 20 |
| 3 | Speed Limit 40 |
| 4 | Speed Limit 60 |
| 5 | Speed Limit 80 |
| 6 | Give Way |
| 7 | School Ahead |
| 8 | Pedestrian Crossing |
| 9 | Left Turn |
| 10 | Right Turn |
| 11 | U-Turn |
| 12 | Horn Prohibited |
| 13 | Parking |
| 14 | Dangerous Curve |

Start small.

Classes can be increased later.

---

# 3. Dataset Sources

## Primary

Indian Traffic Sign Dataset (ITSD)

---

## Secondary

Mapillary Traffic Sign Dataset

---

## Optional

Self-collected Indian road images.

---

# 4. Dataset Folder Structure

```text
dataset/
│
├── train/
│   ├── images/
│   └── labels/
│
├── valid/
│   ├── images/
│   └── labels/
│
└── test/
    ├── images/
    └── labels/
```

---

# 5. YOLO Annotation Format

Example:

```text
0 0.521 0.442 0.122 0.140
```

Format:

```text
class_id x_center y_center width height
```

All values are normalized.

---

# 6. Annotation Tools

Recommended:

- LabelImg
- CVAT
- Roboflow

Export:

```text
YOLO TXT Format
```

---

# 7. Dataset Split

Recommended:

```text
Train      70%
Validation 15%
Test       15%
```

Example:

10,000 Images

```text
7000 Train
1500 Validation
1500 Test
```

---

# 8. Image Preprocessing

## Resize

Training:

```text
640 × 640
```

---

## Normalization

```python
image = image / 255.0
```

---

## Data Augmentation

Apply:

- Rotation
- Blur
- Brightness variation
- Contrast variation
- Noise
- Rain effect
- Shadow effect

Important for Indian roads.

---

# 9. YOLO Dataset Configuration

Create:

```text
dataset.yaml
```

Example:

```yaml
path: /content/dataset

train: train/images
val: valid/images
test: test/images

names:
  0: Stop
  1: No Entry
  2: Speed Limit 20
  3: Speed Limit 40
  4: Speed Limit 60
  5: Speed Limit 80
  6: Give Way
  7: School Ahead
  8: Pedestrian Crossing
  9: Left Turn
  10: Right Turn
  11: U-Turn
  12: Horn Prohibited
  13: Parking
  14: Dangerous Curve
```

---

# 10. Google Colab Setup

## Install YOLO

```python
!pip install ultralytics
```

---

## Verify Installation

```python
from ultralytics import YOLO
```

---

## Mount Google Drive

```python
from google.colab import drive
drive.mount('/content/drive')
```

---

# 11. Model Training

## Load Model

```python
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
```

---

## Train

```python
model.train(
    data="dataset.yaml",
    epochs=100,
    imgsz=640,
    batch=16
)
```

---

# 12. Recommended Hyperparameters

| Parameter | Value |
|------------|---------|
| Model | YOLOv8n |
| Epochs | 100 |
| Image Size | 640 |
| Batch Size | 16 |
| Optimizer | AdamW |
| Learning Rate | 0.001 |

---

# 13. Evaluation

Run:

```python
metrics = model.val()
```

Important metrics:

- Precision
- Recall
- mAP50
- mAP50-95

---

# 14. Testing

Single image:

```python
results = model("test.jpg")
```

---

Video:

```python
results = model("video.mp4")
```

---

# 15. Output Files

Training creates:

```text
runs/
 └── detect/
      └── train/
            ├── best.pt
            ├── last.pt
            ├── results.png
            └── confusion_matrix.png
```

Important:

```text
best.pt
```

This is the final model.

---

# 16. Local Deployment

Install:

```bash
pip install ultralytics opencv-python
```

---

Inference:

```python
from ultralytics import YOLO

model = YOLO("best.pt")

results = model("image.jpg")

results[0].show()
```

---

# 17. Project Deliverables

1. Literature Survey
2. Dataset Analysis
3. Data Preprocessing
4. Model Training
5. Evaluation
6. Real-Time Demo
7. Comparison with Existing Papers
8. Final Report
9. Presentation

---

# 18. Future Enhancements

- YOLOv11 migration
- Mobile deployment
- Edge AI deployment
- Traffic violation monitoring
- Driver assistance integration
- Real-time dashboard

---

# Final Recommended MVP

Phase 1:
- 10–15 sign classes
- 5,000–10,000 images
- YOLOv8n

Phase 2:
- 20–30 classes
- 15,000+ images

Phase 3:
- Real-time deployment using OpenCV

This roadmap minimizes hardware requirements while maximizing the chances of completing a robust final-year project successfully.
