"""
sync_dataset.py
===============
Helper script to sync labels and refresh custom_indian_tsr.zip after manual deletion.

Features:
- Removes orphan label (.txt) files if you deleted their corresponding images.
- Re-archives custom_indian_tsr.zip so your Colab upload is immediately up-to-date.
- Prints updated class distributions.
"""

import os
import zipfile
from pathlib import Path
from collections import defaultdict
import yaml

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

def sync_and_repack(dataset_dir: str = "dataset/custom_indian_tsr", zip_path: str = "dataset/custom_indian_tsr.zip"):
    root = Path(dataset_dir)
    zip_p = Path(zip_path)

    if not root.exists():
        print(f"[ERROR] Directory '{root}' not found.")
        return

    print("=" * 65)
    print("SYNCING DATASET & CLEANING ORPHAN LABELS")
    print(f"Target Directory: {root.resolve()}")
    print("=" * 65)

    removed_labels = 0
    remaining_counts = defaultdict(lambda: defaultdict(int))

    for split in ["train", "val", "test"]:
        img_dir = root / "images" / split
        lbl_dir = root / "labels" / split

        if not img_dir.exists() or not lbl_dir.exists():
            continue

        existing_stems = {f.stem for f in img_dir.iterdir() if f.suffix.lower() in VALID_EXTENSIONS}
        label_files = list(lbl_dir.glob("*.txt"))

        for lbl in label_files:
            if lbl.stem not in existing_stems:
                lbl.unlink()
                removed_labels += 1
            else:
                # Count classes
                try:
                    with open(lbl, "r") as f:
                        line = f.readline().strip()
                        if line:
                            cid = int(line.split()[0])
                            remaining_counts[split][cid] += 1
                except Exception:
                    pass

    print(f"[INFO] Removed {removed_labels} orphan label files where images were deleted.")

    # Re-zip
    print(f"\n[INFO] Updating {zip_p.name}...")
    if zip_p.exists():
        zip_p.unlink()

    with zipfile.ZipFile(zip_p, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in root.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(root)
                zf.write(file, arcname)

    size_mb = zip_p.stat().st_size / (1024 * 1024)
    print(f"[SUCCESS] Updated {zip_p.name} ({size_mb:.2f} MB)")

    # Print summary
    yaml_file = root / "dataset.yaml"
    if yaml_file.exists():
        with open(yaml_file) as f:
            cfg = yaml.safe_load(f)
        names = cfg.get("names", {})
        print("\n" + "=" * 65)
        print("UPDATED DATASET SUMMARY")
        print("=" * 65)
        total_all = 0
        for cid in sorted(names.keys()):
            tr = remaining_counts["train"][cid]
            vl = remaining_counts["val"][cid]
            ts = remaining_counts["test"][cid]
            subtot = tr + vl + ts
            total_all += subtot
            print(f"  Class {cid:2d} ({names[cid]:<20}): Total={subtot:3d} | Train={tr:3d} | Val={vl:2d} | Test={ts:2d}")
        print(f"\nTotal Clean Images Remaining: {total_all}")
    print("=" * 65)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_dir", default="dataset/custom_indian_tsr")
    parser.add_argument("--zip_path", default="dataset/custom_indian_tsr.zip")
    args = parser.parse_args()
    sync_and_repack(args.dataset_dir, args.zip_path)
