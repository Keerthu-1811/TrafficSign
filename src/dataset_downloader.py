"""
Dataset Downloader & Acquisition Helper for Indian Traffic Sign Datasets
Supports Kaggle datasets, Roboflow exports, and direct public mirrors.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

DATASET_SOURCES = {
    "itsd-kaggle": {
        "name": "Indian Traffic Sign Dataset (Kaggle)",
        "command": "kaggle datasets download -d pkdarabi/traffic-sign-dataset-classification-and-detection",
        "description": "Comprehensive Indian traffic signs with YOLO bounding box annotations."
    },
    "indian-signs-roboflow": {
        "name": "Indian Road Traffic Signs (Roboflow Universe)",
        "command": "pip install roboflow (Export via Roboflow API key in YOLOv8 format)",
        "description": "Curated Indian signs with rain, low-light, and urban road conditions."
    },
    "iitm-sample": {
        "name": "IITM Indian Traffic Sign Sample",
        "command": "Manual download from IIT Madras CV lab public release",
        "description": "Authentic south Indian road signs."
    }
}

def print_dataset_guide():
    print("=" * 80)
    print("INDIAN TRAFFIC SIGN DATASET (TSR) ACQUISITION GUIDE")
    print("=" * 80)
    print("\nSince you don't have the dataset downloaded yet, choose one of these options:\n")
    
    print("1. [Recommended for Quick Start] Generate Synthetic / Sample Verification Dataset:")
    print("   python src/create_sample_dataset.py --num-images 100")
    print("   This creates a verified 15-class mock dataset immediately so you can test")
    print("   the pipeline, upload to Google Colab, and test local inference without waiting.\n")
    
    print("2. [Kaggle CLI Method] Download open Indian TSR datasets:")
    print("   Step A: Install Kaggle CLI -> pip install kaggle")
    print("   Step B: Place your kaggle.json in ~/.kaggle/")
    print("   Step C: Run -> kaggle datasets download -d pkdarabi/traffic-sign-dataset-classification-and-detection -p dataset/raw --unzip\n")
    
    print("3. [Roboflow Method] Instant YOLOv8 download:")
    print("   Visit: https://universe.roboflow.com/search?q=indian+traffic+signs")
    print("   Click 'Download Dataset' -> Select 'YOLOv8' format -> Extract to dataset/\n")
    print("=" * 80)

def main():
    parser = argparse.ArgumentParser(description="TSR Dataset Acquisition Helper")
    parser.add_argument("--guide", action="store_true", help="Print download guide and links", default=True)
    args = parser.parse_args()
    print_dataset_guide()

if __name__ == "__main__":
    main()
