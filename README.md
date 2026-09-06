# Indian Traffic Sign Recognition (TSR)

An India-focused deep learning perception system for detecting and classifying Indian traffic signs under challenging real-world road conditions (weather variations, sun glare, shadows, physical deterioration, and chaotic traffic).

Designed for **low-end local hardware** (development, scripting, CPU real-time inference) paired with **free Cloud GPUs** (Google Colab / Kaggle) for deep learning training.

---

## 🚦 Project Highlights
- **Target Classes**: 15 key Indian traffic sign classes (Stop, No Entry, Speed Limits 20/40/60/80, Give Way, School Ahead, Pedestrian Crossing, Turns, Horn Prohibited, Parking, Dangerous Curve).
- **Architecture**:
  - **Stage 1 (Detection)**: Ultralytics YOLOv8n (Lightweight, 3.2M parameters, anchor-free).
  - **Stage 2 (Classification - Optional)**: PyTorch EfficientNet-B0 (Compound scaling for fine-grained sign recognition).
- **Indian Road Conditions Augmentation**: Simulates monsoon rain streaks, harsh shadows, tropical glare, dust haze, and motion blur.
- **Compute Efficiency**: Model training runs seamlessly on Google Colab (Tesla T4/L4 GPU). Inference is optimized for local CPU execution via OpenCV.

---

## 📁 Repository Structure

```text
TrafficSign/
├── dataset/                    # Dataset directory
│   ├── train/                  # 70% Train split (images & labels)
│   ├── valid/                  # 15% Validation split
│   └── test/                   # 15% Test split
├── docs/                       # Project specifications & plans
├── inference/                  # Local CPU inference & demo scripts
│   ├── detector.py             # YOLOv8 inference wrapper
│   ├── pipeline.py             # Two-stage YOLO + EfficientNet pipeline
│   └── realtime_demo.py        # Live webcam / video OpenCV demo
├── models/                     # Saved model weights (best.pt, efficientnet_tsr.pth)
├── notebooks/                  # Cloud GPU training notebooks
│   ├── 01_yolov8_training_colab.ipynb
│   └── 02_efficientnet_classifier_colab.ipynb
├── reports/                    # Phase reports & literature survey
│   └── literature_survey.md    # Phase 1 Literature Survey & Gap Analysis
├── results/                    # Validation metrics, plots, and screenshots
├── src/                        # Data processing & augmentation utilities
│   ├── augmentations.py        # Indian weather & lighting transforms
│   ├── create_sample_dataset.py# Synthetic dataset generator for pipeline dry-run
│   ├── dataset_downloader.py   # Dataset acquisition helper & guide
│   └── dataset_prep.py         # Dataset validator and 70/15/15 splitter
├── training/
│   └── dataset.yaml            # YOLOv8 dataset configuration
├── requirements.txt            # Python dependencies
└── README.md
```

---

## ⚡ Quick Start

### 1. Installation
Ensure Python 3.10+ is installed. Install local dependencies:
```bash
pip install -r requirements.txt
```

### 2. Dataset Setup
Since you may not have the full dataset downloaded yet, you can choose either:

#### Option A: Instant Synthetic Verification Set (No Downloads Needed)
Generate a verified 15-class dataset locally to test all scripts:
```bash
python src/create_sample_dataset.py --num-samples 150
```

#### Option B: Download Full Datasets (ITSD / Roboflow)
View dataset acquisition instructions:
```bash
python src/dataset_downloader.py
```

### 3. Verify Dataset Formatting
Validate bounding boxes, coordinates, and class distributions:
```bash
python src/dataset_prep.py --verify
```

---

## ☁️ Google Colab Cloud Training Workflow

1. Open **[Google Colab](https://colab.research.google.com/)**.
2. Upload `notebooks/01_yolov8_training_colab.ipynb`.
3. Set runtime to **GPU (T4 or L4)**: `Runtime` $\rightarrow$ `Change runtime type` $\rightarrow$ `T4 GPU`.
4. Upload or mount your `dataset/` directory.
5. Run the notebook to train YOLOv8n for 100 epochs.
6. When training finishes, download `best.pt` and place it in the local `models/` directory:
   ```text
   models/best.pt
   ```

---

## 🖥️ Local Inference & Real-Time Demo

Once weights are placed in `models/best.pt`:

### Webcam Live Feed:
```bash
python inference/realtime_demo.py --source 0
```

### Process Video File:
```bash
python inference/realtime_demo.py --source path/to/dashcam_video.mp4
```

### Single Image Inference:
```bash
python inference/detector.py --source path/to/image.jpg
```

---

## 📊 Phase Progress Checklist

- [x] **Phase 1: Literature Survey & Formulation** (`reports/literature_survey.md`)
- [x] **Phase 2 & 3: Dataset Ingestion & Validation** (`src/dataset_downloader.py`, `src/dataset_prep.py`, `src/create_sample_dataset.py`)
- [x] **Phase 4 & 5: Indian Road Augmentations** (`src/augmentations.py`, `training/dataset.yaml`)
- [x] **Phase 6 & 7: Cloud Training Pipelines** (`notebooks/01_yolov8_training_colab.ipynb`)
- [x] **Phase 8: Stage 2 Classifier Pipeline** (`notebooks/02_efficientnet_classifier_colab.ipynb`)
- [x] **Phase 9: Evaluation Metrics Framework** (mAP@50, mAP@50-95, Precision, Recall, F1)
- [x] **Phase 10 & 11: Real-Time Local Demo** (`inference/pipeline.py`, `inference/realtime_demo.py`)
