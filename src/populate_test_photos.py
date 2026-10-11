"""
Populate Test Photos Library
Extracts representative test images for each of the 15 classes from the test split
into 'Test Photos/' so you have a rich set of photos to test in the Web Cockpit.
"""

import os
import shutil
from pathlib import Path
from collections import defaultdict

CLASSES = [
    "Stop", "No Entry", "Speed Limit 20", "Speed Limit 40", "Speed Limit 60",
    "Speed Limit 80", "Give Way", "School Ahead", "Pedestrian Crossing",
    "Left Turn", "Right Turn", "U-Turn", "Horn Prohibited", "Parking", "Dangerous Curve"
]


def populate_library(images_per_class=3):
    img_dir = Path("dataset/custom_indian_tsr/images/test")
    lbl_dir = Path("dataset/custom_indian_tsr/labels/test")
    dest_dir = Path("Test Photos")
    dest_dir.mkdir(parents=True, exist_ok=True)

    if not img_dir.exists() or not lbl_dir.exists():
        print(f"[ERROR] Test directory {img_dir} not found.")
        return

    # Map class_id to list of image paths
    class_images = defaultdict(list)

    for lbl_file in sorted(lbl_dir.glob("*.txt")):
        stem = lbl_file.stem
        # Find corresponding image
        img_candidates = list(img_dir.glob(f"{stem}.*"))
        if not img_candidates:
            continue
        img_path = img_candidates[0]

        with open(lbl_file, "r") as f:
            for line in f:
                parts = line.strip().split()
                if parts:
                    cls_id = int(parts[0])
                    if cls_id < len(CLASSES):
                        class_images[cls_id].append(img_path)
                    break

    copied_total = 0
    print("=" * 70)
    print("EXTRACTING SAMPLES FROM TEST DATASET INTO 'Test Photos/'")
    print("=" * 70)

    for cls_id, cls_name in enumerate(CLASSES):
        imgs = class_images[cls_id][:images_per_class]
        sanitized_name = cls_name.lower().replace(" ", "_")
        for i, src_img in enumerate(imgs, 1):
            dst_name = f"{sanitized_name}_{i:02d}{src_img.suffix}"
            dst_path = dest_dir / dst_name
            shutil.copy2(src_img, dst_path)
            copied_total += 1
            print(f"  [{cls_id:>2}] {cls_name:<20} -> {dst_name}")

    print("=" * 70)
    print(f"Successfully added {copied_total} new test photos to {dest_dir}/")


if __name__ == "__main__":
    populate_library(images_per_class=3)
