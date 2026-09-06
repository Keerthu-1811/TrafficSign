"""
Dataset Preparation & Verification Utility for YOLOv8 TSR
Validates bounding box geometry, class distributions, and creates 70/15/15 train/val/test splits.
"""

import os
import sys
import shutil
import random
import argparse
from pathlib import Path
from collections import Counter

CLASSES = [
    "Stop", "No Entry", "Speed Limit 20", "Speed Limit 40", "Speed Limit 60",
    "Speed Limit 80", "Give Way", "School Ahead", "Pedestrian Crossing",
    "Left Turn", "Right Turn", "U-Turn", "Horn Prohibited", "Parking", "Dangerous Curve"
]

def validate_annotation_file(label_path, num_classes=15):
    """
    Validates that a YOLO annotation file conforms to format:
    <class_id> <x_center> <y_center> <width> <height>
    with all values normalized between 0.0 and 1.0.
    """
    valid = True
    errors = []
    class_counts = Counter()

    if not os.path.exists(label_path):
        return False, ["File not found"], class_counts

    with open(label_path, 'r') as f:
        lines = f.readlines()

    for idx, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 5:
            valid = False
            errors.append(f"Line {idx}: Expected 5 fields, got {len(parts)} -> '{line}'")
            continue
        
        try:
            cls_id = int(parts[0])
            xc, yc, w, h = map(float, parts[1:])
        except ValueError:
            valid = False
            errors.append(f"Line {idx}: Non-numeric values in line -> '{line}'")
            continue

        if not (0 <= cls_id < num_classes):
            valid = False
            errors.append(f"Line {idx}: Class ID {cls_id} out of bounds [0, {num_classes-1}]")
        else:
            class_counts[cls_id] += 1

        for name, val in [("xc", xc), ("yc", yc), ("w", w), ("h", h)]:
            if not (0.0 <= val <= 1.0):
                valid = False
                errors.append(f"Line {idx}: Normalized coordinate {name}={val} outside [0.0, 1.0]")

    return valid, errors, class_counts

def verify_dataset(dataset_root="dataset", num_classes=15):
    """
    Scans dataset/train, dataset/valid, and dataset/test to ensure matching
    images and labels, validating coordinates and computing class distributions.
    """
    root = Path(dataset_root)
    splits = ["train", "valid", "test"]
    overall_counts = Counter()
    total_images = 0
    total_labels = 0
    total_errors = 0

    print("=" * 80)
    print(f"VERIFYING DATASET STRUCTURE AT: {root.resolve()}")
    print("=" * 80)

    for split in splits:
        img_dir = root / split / "images"
        lbl_dir = root / split / "labels"

        if not img_dir.exists() or not lbl_dir.exists():
            print(f"[WARNING] Split '{split}' missing images or labels directory.")
            continue

        images = [p for p in img_dir.glob("*") if p.suffix.lower() in [".jpg", ".jpeg", ".png"]]
        labels = list(lbl_dir.glob("*.txt"))

        print(f"\n-> Split: {split.upper()}")
        print(f"   Images found: {len(images)}")
        print(f"   Labels found: {len(labels)}")

        total_images += len(images)
        total_labels += len(labels)

        split_counts = Counter()
        for img in images:
            corresponding_lbl = lbl_dir / f"{img.stem}.txt"
            if not corresponding_lbl.exists():
                print(f"   [MISSING LABEL] Image {img.name} has no corresponding .txt")
                total_errors += 1
                continue

            valid, errs, counts = validate_annotation_file(corresponding_lbl, num_classes)
            if not valid:
                print(f"   [INVALID ANNOTATION] {corresponding_lbl.name}: {errs[:2]}")
                total_errors += len(errs)
            split_counts.update(counts)
            overall_counts.update(counts)

        print(f"   Class Distribution in {split}:")
        for cid in range(num_classes):
            cname = CLASSES[cid] if cid < len(CLASSES) else f"Class_{cid}"
            cnt = split_counts.get(cid, 0)
            print(f"     [{cid:2d}] {cname:<22}: {cnt}")

    print("\n" + "=" * 80)
    print(f"VERIFICATION SUMMARY:")
    print(f"Total Images: {total_images}")
    print(f"Total Labels: {total_labels}")
    print(f"Total Errors / Anomalies: {total_errors}")
    print("=" * 80)
    return total_errors == 0

def split_raw_dataset(raw_dir, output_dir="dataset", train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, seed=42):
    """
    Partitions raw unorganized images and labels into standard 70/15/15 YOLO format.
    """
    random.seed(seed)
    raw_path = Path(raw_dir)
    out_path = Path(output_dir)

    raw_images = [p for p in raw_path.glob("**/*") if p.suffix.lower() in [".jpg", ".jpeg", ".png"]]
    print(f"Found {len(raw_images)} raw images in {raw_dir}")

    # Pair with labels
    paired = []
    for img in raw_images:
        lbl = img.with_suffix(".txt")
        if lbl.exists():
            paired.append((img, lbl))

    print(f"Successfully paired {len(paired)} image-label pairs.")
    random.shuffle(paired)

    n_total = len(paired)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)

    splits = {
        "train": paired[:n_train],
        "valid": paired[n_train:n_train + n_val],
        "test": paired[n_train + n_val:]
    }

    for split_name, pairs in splits.items():
        img_dest = out_path / split_name / "images"
        lbl_dest = out_path / split_name / "labels"
        img_dest.mkdir(parents=True, exist_ok=True)
        lbl_dest.mkdir(parents=True, exist_ok=True)

        for img, lbl in pairs:
            shutil.copy2(img, img_dest / img.name)
            shutil.copy2(lbl, lbl_dest / lbl.name)
        print(f"Copied {len(pairs)} samples to {split_name}/")

    print("\nDataset split complete!")

def main():
    parser = argparse.ArgumentParser(description="YOLOv8 TSR Dataset Prep and Validation Tool")
    parser.add_argument("--verify", action="store_true", help="Verify existing dataset structure and annotations")
    parser.add_argument("--split-raw", type=str, help="Directory containing raw images & .txt files to split into 70/15/15")
    parser.add_argument("--output", type=str, default="dataset", help="Output directory for split dataset")
    args = parser.parse_args()

    if args.split_raw:
        split_raw_dataset(args.split_raw, args.output)
    else:
        verify_dataset(args.output)

if __name__ == "__main__":
    main()
