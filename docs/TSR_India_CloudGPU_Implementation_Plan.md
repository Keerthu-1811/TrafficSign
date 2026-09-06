# Traffic Sign Recognition Project Plan (India-Focused, Low-End Laptop + Cloud GPU Approach)

## Project Goal

Develop a Traffic Sign Recognition (TSR) system capable of detecting and classifying Indian traffic signs using deep learning while training primarily on free cloud GPU platforms such as Google Colab and Kaggle.

---

# Why This Approach?

### Hardware Constraint

Current system:

- Low-end laptop
- Integrated graphics
- Limited RAM and compute capability

Training modern deep learning models locally would be:

- Extremely slow
- Potentially impossible for larger datasets
- Inefficient

Therefore:

- Development and coding → Laptop
- Training and experimentation → Cloud GPU

---

# Recommended Technology Stack

## Programming Language

- Python

## Libraries

- PyTorch
- OpenCV
- NumPy
- Pandas
- Matplotlib
- Albumentations
- Scikit-Learn
- Ultralytics YOLO

---

# System Architecture

```text
Dataset
   |
   v
Preprocessing
   |
   v
YOLOv8n Detector
   |
   v
Detected Traffic Sign
   |
   v
EfficientNet-B0 Classifier
   |
   v
Traffic Sign Label
```

---

# Phase 1: Literature Survey

## Objectives

Study:

- Traffic Sign Recognition systems
- Traffic Sign Detection methods
- CNN-based classification
- YOLO-based detection
- Indian traffic sign datasets

## Deliverables

- Literature review table
- Gap analysis
- Problem statement
- Methodology selection

---

# Phase 2: Dataset Collection

## Primary Focus

Use Indian datasets.

### Recommended Datasets

#### 1. Indian Traffic Sign Dataset (ITSD)

Use for:

- Classification
- Detection

#### 2. IITM Indian Traffic Sign Dataset

Use for:

- Real-world Indian road conditions

#### 3. Mapillary Traffic Sign Dataset

Use for:

- Additional detection data
- Data diversity

#### 4. Self-Collected Images (Optional)

Capture:

- Chennai roads
- Highway signs
- Warning signs
- Mandatory signs

This improves project originality.

---

# Phase 3: Dataset Preparation

## Folder Structure

```text
dataset/
│
├── train/
├── valid/
└── test/
```

Split:

- Train = 70%
- Validation = 15%
- Test = 15%

---

# Phase 4: Annotation

## Tools

- LabelImg
- CVAT
- Roboflow

Export format:

```text
YOLO Format
```

---

# Phase 5: Data Preprocessing

## Resize

YOLO:

```text
640 × 640
```

Classifier:

```text
224 × 224
```

---

## Normalization

```python
image = image / 255.0
```

---

## Augmentation

Apply:

- Rotation
- Brightness changes
- Contrast changes
- Blur
- Noise
- Shadow simulation
- Rain simulation

Important for Indian road conditions.

---

# Phase 6: Cloud Training Environment

## Option 1 (Recommended)

Google Colab

GPU:

- Tesla T4
- L4

Workflow:

```text
Google Drive
     |
     v
Google Colab
     |
     v
Train Model
     |
     v
Save Weights
```

---

## Option 2

Kaggle Notebooks

Benefits:

- Free GPU
- Easy dataset management
- Long sessions

---

# Phase 7: Detection Model Training

## Model Choice

YOLOv8n

Reason:

- Lightweight
- Fast
- Low GPU requirement
- Suitable for student projects

---

## Installation

```bash
pip install ultralytics
```

---

## Training Command

```bash
yolo detect train data=dataset.yaml model=yolov8n.pt epochs=100 imgsz=640
```

---

## Output

```text
best.pt
```

This becomes the detector.

---

# Phase 8: Classification Model Training

## Recommended Model

EfficientNet-B0

Advantages:

- High accuracy
- Lightweight
- Faster training

---

Alternative:

- MobileNetV3

---

## Input

Traffic sign crops from detector.

## Output

Traffic sign class.

---

# Phase 9: Evaluation

## Detection Metrics

- Precision
- Recall
- mAP@50
- mAP@50-95

---

## Classification Metrics

- Accuracy
- Precision
- Recall
- F1 Score
- Confusion Matrix

---

# Phase 10: Integration

Combine:

```text
YOLOv8n
      +
EfficientNet-B0
```

Pipeline:

```text
Image
  |
  v
YOLO Detection
  |
  v
Crop Sign
  |
  v
Classifier
  |
  v
Predicted Class
```

---

# Phase 11: Local Deployment

After training:

Download:

- best.pt
- classifier weights

Run locally using CPU.

Even low-end laptops can perform inference.

---

# Project Folder Structure

```text
Traffic-Sign-Recognition/
│
├── dataset/
├── notebooks/
├── models/
├── training/
├── inference/
├── results/
├── reports/
└── README.md
```

---

# Suggested Timeline

## Week 1

Literature Survey

## Week 2

Dataset Collection

## Week 3

Annotation

## Week 4

Preprocessing

## Week 5–6

YOLOv8n Training

## Week 7

EfficientNet-B0 Training

## Week 8

Hyperparameter Tuning

## Week 9

Evaluation

## Week 10

Deployment and Documentation

---

# Final Recommended Pipeline

1. Collect Indian traffic sign datasets.
2. Annotate in YOLO format.
3. Upload dataset to Google Drive.
4. Train YOLOv8n using Google Colab.
5. Train EfficientNet-B0 using Google Colab.
6. Evaluate results.
7. Build OpenCV-based demo.
8. Compare with literature survey papers.
9. Prepare project report and presentation.

This pipeline is optimized for students using low-end laptops while still achieving strong research-quality results.
