"""
auto_annotator.py
=================
Automated Bounding Box Proposal & YOLO Label Generator for Scraped Traffic Signs.

Logic:
1. Ground Truth Class ID is extracted directly from the class folder name (e.g., '0_Stop' -> class 0).
2. Primary Bounding Box Detection:
   - Evaluates image using models/best.pt with low confidence threshold (conf=0.15) and class-agnostic NMS.
   - If detector finds candidate boxes, prefers the highest confidence box matching the sign shape.
3. Fallback Heuristic (if detector misses):
   - Multi-color HSV thresholding (Red, Blue, Yellow) for Indian traffic sign shapes.
   - Finds largest closed geometric contour with sign-like aspect ratio (0.65 to 1.5) and reasonable area (1.5% to 85%).
4. Close-Up Default:
   - If image is a close-up cropped sign with no background, uses a tight centered bounding box.
5. Saves clean normalized YOLO format labels:
   <class_id> <x_center> <y_center> <width> <height>
"""

import os
import argparse
from pathlib import Path
import numpy as np
import cv2
from ultralytics import YOLO

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def find_sign_by_contour(img_bgr: np.ndarray):
    """
    Fallback color-contour locator for Indian traffic signs in HSV space.
    Detects red, blue, or yellow signboards.
    Returns normalized [x_center, y_center, w, h] or None.
    """
    h_img, w_img = img_bgr.shape[:2]
    img_area = h_img * w_img
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    # Red masks (wraps around 0 and 180)
    lower_red1 = np.array([0, 70, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 70, 50])
    upper_red2 = np.array([180, 255, 255])
    mask_red = cv2.bitwise_or(
        cv2.inRange(hsv, lower_red1, upper_red1),
        cv2.inRange(hsv, lower_red2, upper_red2)
    )

    # Blue mask (e.g. Parking, Turn signs)
    lower_blue = np.array([100, 80, 50])
    upper_blue = np.array([135, 255, 255])
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)

    # Yellow/Amber mask (cautionary signs)
    lower_yellow = np.array([15, 80, 80])
    upper_yellow = np.array([35, 255, 255])
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)

    combined_mask = cv2.bitwise_or(mask_red, mask_blue)
    combined_mask = cv2.bitwise_or(combined_mask, mask_yellow)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    morph = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_box = None
    max_area = 0

    for c in contours:
        area = cv2.contourArea(c)
        if area < 0.015 * img_area or area > 0.88 * img_area:
            continue
        x, y, w, h = cv2.boundingRect(c)
        aspect = w / max(1, h)
        if 0.60 <= aspect <= 1.65:
            if area > max_area:
                max_area = area
                best_box = (x, y, w, h)

    if best_box:
        bx, by, bw, bh = best_box
        # Add slight 4% padding around contour
        pad_x = int(bw * 0.04)
        pad_y = int(bh * 0.04)
        x1 = max(0, bx - pad_x)
        y1 = max(0, by - pad_y)
        x2 = min(w_img, bx + bw + pad_x)
        y2 = min(h_img, by + bh + pad_y)

        x_center = ((x1 + x2) / 2.0) / w_img
        y_center = ((y1 + y2) / 2.0) / h_img
        norm_w = (x2 - x1) / w_img
        norm_h = (y2 - y1) / h_img
        return [x_center, y_center, norm_w, norm_h]

    return None


def annotate_dataset(
    input_dir: Path,
    output_dir: Path,
    model_weights: str = "models/best.pt",
    conf_thresh: float = 0.15,
    save_debug_vis: bool = True
):
    print("=" * 70)
    print("AUTOMATED BOUNDING BOX ANNOTATION PIPELINE")
    print(f"Input:       {input_dir.resolve()}")
    print(f"Output:      {output_dir.resolve()}")
    print(f"Weights:     {model_weights}")
    print(f"Confidence:  {conf_thresh}")
    print("=" * 70)

    # Load YOLO model
    detector = None
    if Path(model_weights).exists():
        print(f"[INFO] Loading YOLO detector from {model_weights}...")
        detector = YOLO(model_weights)
    else:
        print(f"[WARNING] Model weights '{model_weights}' not found. Using heuristic contour detector.")

    # Setup directories
    images_out = output_dir / "images"
    labels_out = output_dir / "labels"
    debug_out = output_dir / "preview" if save_debug_vis else None

    images_out.mkdir(parents=True, exist_ok=True)
    labels_out.mkdir(parents=True, exist_ok=True)
    if debug_out:
        debug_out.mkdir(parents=True, exist_ok=True)

    class_folders = sorted([d for d in input_dir.iterdir() if d.is_dir()])
    total_annotated = 0
    stats = {"detector_hits": 0, "contour_hits": 0, "closeup_fallback": 0}

    for cfolder in class_folders:
        try:
            class_id = int(cfolder.name.split("_")[0])
        except ValueError:
            print(f"[SKIP] Cannot parse class ID from folder: {cfolder.name}")
            continue

        img_files = [f for f in cfolder.iterdir() if f.suffix.lower() in VALID_EXTENSIONS]
        print(f"\n[Processing Class {class_id}: {cfolder.name}] ({len(img_files)} images)")

        for img_path in img_files:
            img = cv2.imread(str(img_path))
            if img is None:
                continue

            h_img, w_img = img.shape[:2]
            chosen_box = None
            method = "none"

            # 1. Primary: Try YOLO detector
            if detector is not None:
                try:
                    res = detector(img, conf=conf_thresh, agnostic_nms=True, verbose=False)[0]
                    if len(res.boxes) > 0:
                        # Extract boxes
                        boxes = res.boxes.xywhn.cpu().numpy()  # [x_center, y_center, w, h] normalized
                        confs = res.boxes.conf.cpu().numpy()
                        classes = res.boxes.cls.cpu().numpy().astype(int)

                        # Prefer box that matched the target class
                        match_idxs = [i for i, c in enumerate(classes) if c == class_id]
                        if len(match_idxs) > 0:
                            best_idx = match_idxs[np.argmax(confs[match_idxs])]
                        else:
                            best_idx = int(np.argmax(confs))

                        chosen_box = boxes[best_idx].tolist()
                        method = "detector"
                        stats["detector_hits"] += 1
                except Exception as e:
                    pass

            # 2. Fallback: Color/contour heuristic
            if chosen_box is None:
                contour_box = find_sign_by_contour(img)
                if contour_box is not None:
                    chosen_box = contour_box
                    method = "contour"
                    stats["contour_hits"] += 1

            # 3. Fallback: Close-up / centered crop
            if chosen_box is None:
                chosen_box = [0.5, 0.5, 0.90, 0.90]
                method = "closeup"
                stats["closeup_fallback"] += 1

            # Write label file
            base_stem = f"{class_id:02d}_{img_path.stem}"
            dest_img = images_out / f"{base_stem}{img_path.suffix.lower()}"
            dest_lbl = labels_out / f"{base_stem}.txt"

            cv2.imwrite(str(dest_img), img)

            xc, yc, bw, bh = chosen_box
            with open(dest_lbl, "w") as f_lbl:
                f_lbl.write(f"{class_id} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}\n")

            total_annotated += 1

            # Optional visual preview overlay
            if debug_out:
                preview_img = img.copy()
                x1 = int((xc - bw / 2.0) * w_img)
                y1 = int((yc - bh / 2.0) * h_img)
                x2 = int((xc + bw / 2.0) * w_img)
                y2 = int((yc + bh / 2.0) * h_img)

                color = (0, 255, 0) if method == "detector" else ((0, 165, 255) if method == "contour" else (0, 0, 255))
                cv2.rectangle(preview_img, (x1, y1), (x2, y2), color, 2)
                cv2.putText(preview_img, f"ID:{class_id} ({method})", (x1, max(20, y1 - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
                cv2.imwrite(str(debug_out / f"{base_stem}.jpg"), preview_img)

    print("\n" + "=" * 70)
    print("ANNOTATION PIPELINE COMPLETE")
    print("=" * 70)
    print(f"Total Images Annotated:    {total_annotated}")
    print(f"  - Detected by Model:     {stats['detector_hits']}")
    print(f"  - Detected by Contours:  {stats['contour_hits']}")
    print(f"  - Close-up Fallback:     {stats['closeup_fallback']}")
    print(f"Images saved to:  {images_out.resolve()}")
    print(f"Labels saved to:  {labels_out.resolve()}")
    if debug_out:
        print(f"Previews saved:   {debug_out.resolve()}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Auto-annotate scraped traffic sign images.")
    parser.add_argument("--input_dir", type=str, default="dataset/filtered",
                        help="Input directory with filtered class folders")
    parser.add_argument("--output_dir", type=str, default="dataset/annotated",
                        help="Output directory for images and labels")
    parser.add_argument("--weights", type=str, default="models/best.pt",
                        help="Path to YOLO weights")
    parser.add_argument("--conf", type=float, default=0.15,
                        help="Confidence threshold for bounding box detection")
    parser.add_argument("--no_preview", action="store_true",
                        help="Disable saving preview images")
    args = parser.parse_args()

    annotate_dataset(
        input_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir),
        model_weights=args.weights,
        conf_thresh=args.conf,
        save_debug_vis=not args.no_preview
    )


if __name__ == "__main__":
    main()
