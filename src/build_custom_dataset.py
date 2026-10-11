"""
build_custom_dataset.py
=======================
Master Pipeline Runner for Authentic Indian Traffic Sign Recognition Dataset.

Stages:
  Step 1: Multi-threaded Web Scraping (~220 images/class across 15 IRC classes)
  Step 2: Quality, Clipart & pHash Deduplication Filter
  Step 3: Automated Bounding Box Proposals & YOLO Labels
  Step 4: Stratified Split (70/15/15) & Packaging (.zip + dataset.yaml)
  Step 5: Visual Inspection HTML Gallery Generation
"""

import sys
import time
import argparse
from pathlib import Path
import subprocess

def run_step(step_name: str, cmd: list):
    print(f"\n{'='*75}")
    print(f"STAGE: {step_name}")
    print(f"COMMAND: {' '.join(cmd)}")
    print(f"{'='*75}\n")
    t0 = time.time()
    res = subprocess.run([sys.executable] + cmd, check=True)
    t1 = time.time()
    print(f"\n[DONE] {step_name} completed in {t1 - t0:.1f} seconds.")


def main():
    parser = argparse.ArgumentParser(description="Build complete custom Indian TSR dataset.")
    parser.add_argument("--classes", type=str, default="all",
                        help="Classes to build (default: 'all' -> 0 to 14)")
    parser.add_argument("--limit", type=int, default=220,
                        help="Target raw images per class (default: 220)")
    parser.add_argument("--skip_scrape", action="store_true",
                        help="Skip scraping if raw images already exist")
    args = parser.parse_args()

    total_start = time.time()
    print("=" * 75)
    print("INDIAN TRAFFIC SIGN RECOGNITION (TSR) - END-TO-END DATASET PIPELINE")
    print(f"Target: ~{args.limit} images per class for 15 IRC classes")
    print("=" * 75)

    # Step 1: Scrape
    if not args.skip_scrape:
        run_step(
            "1. Multi-Threaded Scraping",
            ["src/dataset_collector.py", "--classes", args.classes, "--limit", str(args.limit), "--workers", "10"]
        )
    else:
        print("\n[SKIP] Skipping scraping stage as requested.")

    # Step 2: Filter
    run_step(
        "2. Quality, Clipart & Deduplication Filtering",
        ["src/filter_scraped_data.py", "--input_dir", "dataset/raw_scraped", "--output_dir", "dataset/filtered", "--min_dim", "250", "--hash_dist", "5"]
    )

    # Step 3: Auto-Annotate
    run_step(
        "3. Bounding Box Auto-Annotation & YOLO Label Generation",
        ["src/auto_annotator.py", "--input_dir", "dataset/filtered", "--output_dir", "dataset/annotated", "--weights", "models/best.pt", "--conf", "0.15"]
    )

    # Step 4: Package & Split
    run_step(
        "4. Stratified Split (70/15/15) & Packaging to Zip",
        ["src/package_custom_dataset.py", "--annotated_dir", "dataset/annotated", "--output_dir", "dataset/custom_indian_tsr", "--zip_path", "dataset/custom_indian_tsr.zip"]
    )

    # Step 5: Inspection Gallery
    run_step(
        "5. Interactive HTML Inspection Gallery",
        ["src/generate_inspection_gallery.py", "--preview_dir", "dataset/annotated/preview", "--output_html", "results/annotation_gallery.html"]
    )

    total_time = time.time() - total_start
    print("\n" + "=" * 75)
    print("ALL PIPELINE STAGES COMPLETED SUCCESSFULLY!")
    print(f"Total time elapsed: {total_time / 60:.1f} minutes")
    print("Deliverables:")
    print("  1. Custom Structured Dataset : dataset/custom_indian_tsr/")
    print("  2. Packaged Training Archive : dataset/custom_indian_tsr.zip")
    print("  3. Visual Inspection Gallery : results/annotation_gallery.html")
    print("=" * 75)


if __name__ == "__main__":
    main()
