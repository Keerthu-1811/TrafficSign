"""
package_custom_dataset.py
=========================
Stratified Train/Val/Test Splitter and Dataset Packager for Custom Indian TSR Dataset.

Steps:
1. Reads annotated images & labels from dataset/annotated.
2. Groups by class ID and performs 70% Train, 15% Val, 15% Test stratified split.
3. Structures directory for Ultralytics YOLOv8:
   dataset/custom_indian_tsr/
     images/train, images/val, images/test
     labels/train, labels/val, labels/test
     dataset.yaml
4. Creates custom_indian_tsr.zip ready for Colab upload.
"""

import os
import shutil
import random
import argparse
import zipfile
from pathlib import Path
from collections import defaultdict
import yaml

# 15 Canonical IRC Classes
CLASS_NAMES = {
    0: "Stop",
    1: "No Entry",
    2: "Speed Limit 20",
    3: "Speed Limit 40",
    4: "Speed Limit 60",
    5: "Speed Limit 80",
    6: "Give Way",
    7: "School Ahead",
    8: "Pedestrian Crossing",
    9: "Left Turn",
    10: "Right Turn",
    11: "U-Turn",
    12: "Horn Prohibited",
    13: "Parking",
    14: "Dangerous Curve"
}

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def package_dataset(
    annotated_dir: Path,
    output_dir: Path,
    zip_path: Path,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    seed: int = 42
):
    random.seed(seed)

    images_in = annotated_dir / "images"
    labels_in = annotated_dir / "labels"

    if not images_in.exists() or not labels_in.exists():
        print(f"[ERROR] Annotated images or labels not found in {annotated_dir}")
        return

    # Find paired images and labels
    img_files = [f for f in images_in.iterdir() if f.suffix.lower() in VALID_EXTENSIONS]
    class_groups = defaultdict(list)

    for img_path in img_files:
        lbl_path = labels_in / f"{img_path.stem}.txt"
        if not lbl_path.exists():
            continue

        try:
            with open(lbl_path, "r") as f:
                first_line = f.readline().strip()
                if first_line:
                    cid = int(first_line.split()[0])
                    class_groups[cid].append((img_path, lbl_path))
        except Exception:
            continue

    print("=" * 70)
    print("STRATIFIED DATASET SPLIT & PACKAGING")
    print(f"Annotated Source: {annotated_dir.resolve()}")
    print(f"Target Directory: {output_dir.resolve()}")
    print(f"Ratios: Train={train_ratio*100:.0f}%, Val={val_ratio*100:.0f}%, Test={(1.0 - train_ratio - val_ratio)*100:.0f}%")
    print("=" * 70)

    # Clean / prepare target directories
    for split in ["train", "val", "test"]:
        (output_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (output_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

    split_counts = {"train": defaultdict(int), "val": defaultdict(int), "test": defaultdict(int)}

    for cid in sorted(CLASS_NAMES.keys()):
        pairs = class_groups.get(cid, [])
        random.shuffle(pairs)
        n = len(pairs)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        train_pairs = pairs[:n_train]
        val_pairs = pairs[n_train:n_train + n_val]
        test_pairs = pairs[n_train + n_val:]

        for split, split_data in [("train", train_pairs), ("val", val_pairs), ("test", test_pairs)]:
            for img_p, lbl_p in split_data:
                shutil.copy2(img_p, output_dir / "images" / split / img_p.name)
                shutil.copy2(lbl_p, output_dir / "labels" / split / lbl_p.name)
                split_counts[split][cid] += 1

        print(f"Class {cid:2d} ({CLASS_NAMES[cid]:<20}): Total={n:3d} | Train={len(train_pairs):3d} | Val={len(val_pairs):3d} | Test={len(test_pairs):3d}")

    # Generate dataset.yaml
    yaml_dict = {
        "path": ".",
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "nc": 15,
        "names": {k: v for k, v in CLASS_NAMES.items()}
    }

    yaml_file = output_dir / "dataset.yaml"
    with open(yaml_file, "w") as f_yaml:
        yaml.dump(yaml_dict, f_yaml, sort_keys=False)

    print(f"\n[INFO] Generated dataset configuration: {yaml_file.resolve()}")

    # Zip output dataset
    print(f"\n[INFO] Archiving dataset to {zip_path.resolve()}...")
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in output_dir.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(output_dir)
                zf.write(file, arcname)

    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"[SUCCESS] Dataset packaged successfully: {zip_path.name} ({zip_size_mb:.2f} MB)")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Split and package custom Indian TSR dataset.")
    parser.add_argument("--annotated_dir", type=str, default="dataset/annotated",
                        help="Input annotated directory")
    parser.add_argument("--output_dir", type=str, default="dataset/custom_indian_tsr",
                        help="Output structured YOLO dataset directory")
    parser.add_argument("--zip_path", type=str, default="dataset/custom_indian_tsr.zip",
                        help="Path for final zipped archive")
    parser.add_argument("--train_ratio", type=float, default=0.70, help="Train ratio (default: 0.70)")
    parser.add_argument("--val_ratio", type=float, default=0.15, help="Val ratio (default: 0.15)")
    args = parser.parse_args()

    package_dataset(
        annotated_dir=Path(args.annotated_dir),
        output_dir=Path(args.output_dir),
        zip_path=Path(args.zip_path),
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio
    )


if __name__ == "__main__":
    main()
