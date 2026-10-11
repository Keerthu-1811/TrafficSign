import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2
from inference.detector import TSRDetector

def evaluate_all():
    detector = TSRDetector(weights_path="models/best.pt", conf_thresh=0.20)
    test_dir = Path("Test Photos")
    out_dir = Path("results/test_eval")
    out_dir.mkdir(parents=True, exist_ok=True)

    image_files = sorted([p for p in test_dir.iterdir() if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]])

    print("=" * 95)
    print(f"EVALUATING {len(image_files)} TEST PHOTOS WITH models/best.pt")
    print("=" * 95)

    summary = []

    for img_path in image_files:
        frame = cv2.imread(str(img_path))
        if frame is None:
            print(f"[ERROR] Could not read {img_path.name}")
            continue

        annotated, detections = detector.detect(frame)
        out_path = out_dir / f"eval_{img_path.stem}.jpg"
        cv2.imwrite(str(out_path), annotated)

        ground_truth = img_path.stem
        if detections:
            top_det = max(detections, key=lambda d: d["conf"])
            pred_label = top_det["label"]
            conf = top_det["conf"]
            all_dets = ", ".join([f"{d['label']} ({d['conf']:.2f})" for d in detections])
        else:
            pred_label = "No Detection"
            conf = 0.0
            all_dets = "None"

        # Check match
        gt_norm = ground_truth.lower().replace("_", " ").replace("-", " ")
        pred_norm = pred_label.lower().replace("_", " ").replace("-", " ")
        
        is_match = False
        if pred_label != "No Detection":
            # Match keywords
            keywords = ["20", "40", "60", "80", "stop", "no entry", "give way", "pedestrian", "school", "left turn", "right turn", "u turn", "horn", "curve"]
            for kw in keywords:
                if kw in gt_norm and kw in pred_norm:
                    is_match = True
                    break
            if not is_match and (gt_norm in pred_norm or pred_norm in gt_norm):
                is_match = True

        status = "MATCH" if is_match else ("NO_DETECTION" if pred_label == "No Detection" else "MISMATCH")

        summary.append({
            "file": img_path.name,
            "expected": ground_truth,
            "predicted": pred_label,
            "conf": conf,
            "status": status,
            "all": all_dets
        })

        tag = "[OK]  " if is_match else ("[MISS]" if status == "NO_DETECTION" else "[DIFF]")
        print(f"{tag} {img_path.name:<25} | Expected: {ground_truth:<18} | Detected: {pred_label:<20} ({conf:.2f}) | {all_dets}")

    print("=" * 95)
    matches = sum(1 for s in summary if s["status"] == "MATCH")
    total = len(summary)
    print(f"\nFinal Accuracy: {matches}/{total} ({matches/total*100:.1f}%)")
    print(f"All annotated images saved to: {out_dir.resolve()}")

if __name__ == "__main__":
    evaluate_all()
