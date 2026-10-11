"""
filter_scraped_data.py
======================
Automated Quality, Clipart, and Duplicate Filter for Raw Scraped TSR Images.

Filters:
1. Integrity: drops corrupt/unreadable image files.
2. Resolution: minimum 250x250 pixels (drops low-res icons/thumbnails).
3. Aspect Ratio: drops extreme aspect ratios (> 3.0 or < 0.33).
4. Clipart / Flat Background:
   - Drops transparent PNGs/stickers.
   - Drops pure white/flat canvas clipart using border luminance & variance analysis.
5. Deduplication:
   - Uses Perceptual Hashing (pHash) to remove duplicates and near-identical scrapes.
"""

import os
import shutil
import argparse
from pathlib import Path
import numpy as np
import cv2
from PIL import Image
import imagehash

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def is_flat_clipart(img_bgr: np.ndarray, border_thickness: int = 10, var_thresh: float = 12.0, lum_thresh: float = 235.0) -> bool:
    """
    Detects if an image is likely synthetic clipart rendered on a flat white/plain background.
    Examines the border pixels (top, bottom, left, right).
    """
    h, w = img_bgr.shape[:2]
    if h <= border_thickness * 2 or w <= border_thickness * 2:
        return True

    # Extract borders
    top = img_bgr[:border_thickness, :]
    bottom = img_bgr[h - border_thickness:, :]
    left = img_bgr[:, :border_thickness]
    right = img_bgr[:, w - border_thickness:]

    # Compute gray luminosity and variance for all borders
    borders = [top, bottom, left, right]
    variances = []
    means = []
    for b in borders:
        gray = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)
        variances.append(np.var(gray))
        means.append(np.mean(gray))

    avg_var = np.mean(variances)
    avg_mean = np.mean(means)

    # Clipart on solid white/near-white canvas: high luminance and very low variance
    if avg_mean >= lum_thresh and avg_var < var_thresh:
        return True

    # Also detect transparent alpha channel if converted to BGR as black canvas
    if avg_mean <= 10.0 and avg_var < 5.0:
        return True

    return False


def is_transparent_png(file_path: Path, alpha_thresh: float = 0.15) -> bool:
    """Detects if image has transparent pixels exceeding alpha_thresh ratio."""
    try:
        with Image.open(file_path) as im:
            if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
                alpha = np.array(im.convert("RGBA"))[:, :, 3]
                trans_ratio = np.mean(alpha < 240)
                if trans_ratio > alpha_thresh:
                    return True
    except Exception:
        return True
    return False


def filter_class_directory(
    input_dir: Path,
    output_dir: Path,
    min_dim: int = 250,
    max_aspect_ratio: float = 3.0,
    hash_dist_thresh: int = 5
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    image_files = [f for f in input_dir.iterdir() if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS]

    stats = {
        "total": len(image_files),
        "kept": 0,
        "corrupt": 0,
        "low_res": 0,
        "aspect_ratio": 0,
        "clipart": 0,
        "duplicate": 0
    }

    seen_hashes = []

    for fpath in image_files:
        # Check transparency
        if is_transparent_png(fpath):
            stats["clipart"] += 1
            continue

        # Load with OpenCV
        try:
            img = cv2.imread(str(fpath))
            if img is None:
                stats["corrupt"] += 1
                continue
        except Exception:
            stats["corrupt"] += 1
            continue

        h, w = img.shape[:2]

        # Resolution check
        if min(h, w) < min_dim:
            stats["low_res"] += 1
            continue

        # Aspect ratio check
        aspect = max(h / w, w / h)
        if aspect > max_aspect_ratio:
            stats["aspect_ratio"] += 1
            continue

        # Clipart / flat white background check
        if is_flat_clipart(img):
            stats["clipart"] += 1
            continue

        # Perceptual Hash deduplication
        try:
            with Image.open(fpath) as pil_img:
                current_hash = imagehash.phash(pil_img)
            
            is_dup = False
            for prev_hash in seen_hashes:
                if current_hash - prev_hash < hash_dist_thresh:
                    is_dup = True
                    break

            if is_dup:
                stats["duplicate"] += 1
                continue

            seen_hashes.append(current_hash)
        except Exception:
            stats["corrupt"] += 1
            continue

        # Passed all checks -> Copy to output directory
        dest = output_dir / fpath.name
        shutil.copy2(fpath, dest)
        stats["kept"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description="Filter raw scraped traffic sign images.")
    parser.add_argument("--input_dir", type=str, default="dataset/raw_scraped",
                        help="Input directory with raw class folders")
    parser.add_argument("--output_dir", type=str, default="dataset/filtered",
                        help="Output directory for cleaned images")
    parser.add_argument("--min_dim", type=int, default=250,
                        help="Minimum width and height in pixels (default: 250)")
    parser.add_argument("--hash_dist", type=int, default=5,
                        help="pHash Hamming distance threshold for duplicates (default: 5)")
    args = parser.parse_args()

    in_root = Path(args.input_dir)
    out_root = Path(args.output_dir)

    if not in_root.exists():
        print(f"[ERROR] Input directory '{in_root}' does not exist.")
        return

    out_root.mkdir(parents=True, exist_ok=True)
    class_folders = sorted([d for d in in_root.iterdir() if d.is_dir()])

    print("=" * 70)
    print("QUALITY & CLIPART FILTERING PIPELINE")
    print(f"Input:  {in_root.resolve()}")
    print(f"Output: {out_root.resolve()}")
    print(f"Min Resolution: {args.min_dim}x{args.min_dim} | Deduplication pHash threshold: {args.hash_dist}")
    print("=" * 70)

    grand_stats = {"total": 0, "kept": 0, "corrupt": 0, "low_res": 0, "aspect_ratio": 0, "clipart": 0, "duplicate": 0}

    for cfolder in class_folders:
        out_folder = out_root / cfolder.name
        stats = filter_class_directory(cfolder, out_folder, min_dim=args.min_dim, hash_dist_thresh=args.hash_dist)
        print(f"\n[{cfolder.name}]")
        print(f"  Total: {stats['total']} -> Kept: {stats['kept']} ({stats['kept'] / max(1, stats['total']) * 100:.1f}%)")
        print(f"  Dropped: Clipart={stats['clipart']} | Dupes={stats['duplicate']} | LowRes={stats['low_res']} | BadAspect={stats['aspect_ratio']} | Corrupt={stats['corrupt']}")

        for k in grand_stats:
            grand_stats[k] += stats[k]

    print("\n" + "=" * 70)
    print("FILTERING SUMMARY")
    print("=" * 70)
    print(f"Total Raw Images:       {grand_stats['total']}")
    print(f"High-Quality Kept:      {grand_stats['kept']}")
    print(f"Clipart/Flat Canvas:    {grand_stats['clipart']}")
    print(f"Duplicates:             {grand_stats['duplicate']}")
    print(f"Low Resolution (<250px): {grand_stats['low_res']}")
    print(f"Bad Aspect Ratio:       {grand_stats['aspect_ratio']}")
    print(f"Corrupt/Unreadable:     {grand_stats['corrupt']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
