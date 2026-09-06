"""
Lightweight YOLOv8 Detector for Traffic Sign Recognition (TSR)
Runs CPU-optimized inference on images, video files, or webcam feeds.
"""

import os
import cv2
import time
import argparse
import numpy as np
from pathlib import Path

CLASSES = [
    "Stop", "No Entry", "Speed Limit 20", "Speed Limit 40", "Speed Limit 60",
    "Speed Limit 80", "Give Way", "School Ahead", "Pedestrian Crossing",
    "Left Turn", "Right Turn", "U-Turn", "Horn Prohibited", "Parking", "Dangerous Curve"
]

# Distinct colors (BGR) for bounding box visualization
COLOR_PALETTE = [
    (0, 0, 220), (30, 30, 200), (0, 165, 255), (0, 200, 255), (0, 255, 255),
    (0, 255, 128), (0, 215, 0), (255, 191, 0), (255, 128, 0), (255, 0, 0),
    (200, 0, 128), (180, 0, 200), (128, 0, 255), (255, 0, 255), (0, 128, 255)
]

class TSRDetector:
    def __init__(self, weights_path="models/best.pt", conf_thresh=0.35, iou_thresh=0.45):
        self.weights_path = weights_path
        self.conf_thresh = conf_thresh
        self.iou_thresh = iou_thresh
        self.model = None
        self.mock_mode = False

        if os.path.exists(weights_path):
            try:
                from ultralytics import YOLO
                print(f"[INFO] Loading YOLO weights from: {weights_path}")
                self.model = YOLO(weights_path)
            except ImportError:
                print("[WARNING] Ultralytics not installed locally. Operating in mock demonstration mode.")
                self.mock_mode = True
        else:
            print(f"[INFO] Weights file '{weights_path}' not found yet.")
            print("[INFO] Operating in simulated/mock mode for pipeline verification until Colab training finishes.")
            self.mock_mode = True

    def detect(self, frame):
        """
        Runs detection on an OpenCV BGR frame.
        Returns:
            annotated_frame: np.ndarray
            detections: list of dicts [{'bbox': (x1, y1, x2, y2), 'class_id': int, 'label': str, 'conf': float}]
        """
        h, w, _ = frame.shape
        detections = []
        annotated = frame.copy()

        if self.mock_mode or self.model is None:
            # Simulated detection for pipeline testing if weights aren't trained yet
            return annotated, detections

        # Run Ultralytics inference
        results = self.model(frame, conf=self.conf_thresh, iou=self.iou_thresh, verbose=False)[0]

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            conf = float(box.conf[0].item())
            cls_id = int(box.cls[0].item())
            label = CLASSES[cls_id] if cls_id < len(CLASSES) else f"Sign_{cls_id}"

            detections.append({
                "bbox": (x1, y1, x2, y2),
                "class_id": cls_id,
                "label": label,
                "conf": conf
            })

            # Draw bounding box and label
            color = COLOR_PALETTE[cls_id % len(COLOR_PALETTE)]
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            caption = f"{label} {conf:.2f}"
            (text_w, text_h), baseline = cv2.getTextSize(caption, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated, (x1, max(0, y1 - text_h - 6)), (x1 + text_w, y1), color, -1)
            cv2.putText(annotated, caption, (x1, max(text_h, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        return annotated, detections

def main():
    parser = argparse.ArgumentParser(description="TSR YOLOv8 Inference")
    parser.add_argument("--source", type=str, default="0", help="Camera index, image path, or video path")
    parser.add_argument("--weights", type=str, default="models/best.pt", help="Path to trained weights")
    parser.add_argument("--conf", type=float, default=0.35, help="Confidence threshold")
    args = parser.parse_args()

    detector = TSRDetector(weights_path=args.weights, conf_thresh=args.conf)
    print("Detector initialized. Ready for inference.")

if __name__ == "__main__":
    main()
