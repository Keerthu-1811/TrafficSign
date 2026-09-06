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

# Comprehensive mapping for standard GTSRB & Indian Traffic Sign (IRC) numerical IDs
SIGN_NAME_MAP = {
    # Speed Limits
    "0": "Speed Limit 20",
    "1": "Speed Limit 30",
    "2": "Speed Limit 50",
    "3": "Speed Limit 60",
    "4": "Speed Limit 70",
    "5": "Speed Limit 80",
    "6": "End of Speed Limit 80",
    "7": "Speed Limit 100",
    "8": "Speed Limit 120",
    "20": "Speed Limit 20",
    "30": "Speed Limit 30",
    "40": "Speed Limit 40",
    "50": "Speed Limit 50",
    "60": "Speed Limit 60",
    "70": "Speed Limit 70",
    "80": "Speed Limit 80",
    "90": "Speed Limit 90",
    "100": "Speed Limit 100",
    "120": "Speed Limit 120",

    # Priority & Prohibitory
    "9": "No Passing / Overtaking",
    "10": "No Heavy Vehicles",
    "11": "Priority at Intersection",
    "12": "Priority Road",
    "13": "Give Way / Yield",
    "14": "Stop Sign",
    "15": "No Vehicles",
    "16": "No Commercial Trucks",
    "17": "No Entry",
    "18": "General Caution Ahead",

    # Hazards & Curves
    "19": "Dangerous Left Curve",
    "20": "Dangerous Right Curve",
    "21": "Double Curve Ahead",
    "22": "Bumpy / Rough Road",
    "23": "Slippery Road",
    "24": "Road Narrows on Right",
    "25": "Road Work Ahead",
    "26": "Traffic Light Ahead",
    "27": "Pedestrian Crossing",
    "28": "School Ahead / Children",
    "29": "Bicycle Crossing",
    "30": "Snow / Ice Caution",
    "31": "Wild Animals Crossing",
    "32": "End of Restrictions",

    # Mandatory Direction Signs (Arrows & Turns)
    "33": "Turn Right Ahead",
    "34": "Turn Left Ahead",
    "35": "Ahead Only",
    "36": "Straight or Right Turn",
    "37": "Straight or Left Turn",
    "38": "Keep Right",
    "39": "Keep Left",
    "40": "Roundabout Mandatory",
    "41": "End of No Passing",
    "42": "End of No Passing (Trucks)",

    # Extended Indian Road Signs (43 - 73)
    "43": "Left Curve",
    "44": "Right Curve",
    "45": "Left Hairpin Bend",
    "46": "Right Hairpin Bend",
    "47": "Left Reverse Bend",
    "48": "Right Reverse Bend",
    "49": "Steep Ascent",
    "50": "Steep Descent",
    "51": "Narrow Road Ahead",
    "52": "Narrow Bridge Ahead",
    "53": "U-Turn / Median Opening",
    "54": "Side Road Right",
    "55": "Side Road Left",
    "56": "Roundabout Ahead",
    "57": "Dangerous Dip",
    "58": "Speed Breaker Ahead",
    "59": "Barrier Ahead",
    "60": "Horn Prohibited",
    "61": "No Parking",
    "62": "No Stopping",
    "63": "Right Turn",
    "64": "Left Turn",
    "65": "Parking Area",
    "66": "Hospital Ahead",
    "67": "First Aid Post",
    "68": "Restaurant Ahead",
    "69": "Refreshments Ahead",
    "70": "Resting Place",
    "71": "Petrol Pump",
    "72": "Compulsory Left Turn",
    "73": "Compulsory Right Turn",
}

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
            raw_label = ""
            if hasattr(self.model, "names") and isinstance(self.model.names, dict) and cls_id in self.model.names:
                raw_label = str(self.model.names[cls_id]).strip()
            elif hasattr(self.model, "names") and isinstance(self.model.names, list) and cls_id < len(self.model.names):
                raw_label = str(self.model.names[cls_id]).strip()
            elif cls_id < len(CLASSES):
                raw_label = CLASSES[cls_id]
            else:
                raw_label = f"Sign_{cls_id}"

            # Filter out non-sign Roboflow metadata artifact labels
            if any(raw_label.startswith(pfx) for pfx in ["*", "=", "Roboflow", "The ", "For ", "To ", "Traffic-sign are", "traffic sign -", "visit ", "annotate"]):
                continue

            # Format label cleanly using comprehensive SIGN_NAME_MAP
            clean_key = raw_label.strip()
            if clean_key in SIGN_NAME_MAP:
                label = SIGN_NAME_MAP[clean_key]
            elif clean_key.isdigit() and str(int(clean_key)) in SIGN_NAME_MAP:
                label = SIGN_NAME_MAP[str(int(clean_key))]
            elif clean_key.lower() in ["traffic-sign", "traffic sign"]:
                label = "Traffic Sign"
            elif cls_id < len(CLASSES):
                label = CLASSES[cls_id]
            else:
                label = f"Sign {raw_label}"

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
    parser.add_argument("--source", type=str, default="dataset/test/images/syn_tsr_test_0001.jpg", help="Camera index, image path, or video path")
    parser.add_argument("--weights", type=str, default="models/best.pt", help="Path to trained weights")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--output", type=str, default="results/detected_output.jpg", help="Output path for annotated image")
    args = parser.parse_args()

    detector = TSRDetector(weights_path=args.weights, conf_thresh=args.conf)
    
    if os.path.exists(args.source):
        print(f"[INFO] Processing image: {args.source}")
        frame = cv2.imread(args.source)
        if frame is None:
            print(f"[ERROR] Could not read image at: {args.source}")
            return
        
        annotated, detections = detector.detect(frame)
        print(f"[RESULT] Detected {len(detections)} traffic sign(s):")
        for i, det in enumerate(detections, 1):
            print(f"  {i}. {det['label']} (Confidence: {det['conf']:.2f}, Box: {det['bbox']})")
        
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        cv2.imwrite(args.output, annotated)
        print(f"[SAVED] Annotated image saved to: {args.output}")
    else:
        print(f"[INFO] Source '{args.source}' is not a local file. For webcam or video stream, use realtime_demo.py.")

if __name__ == "__main__":
    main()
