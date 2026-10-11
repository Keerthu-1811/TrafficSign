"""
Two-Stage TSR Inference Pipeline:
Stage 1: YOLOv8 sign localization with Temporal Smoothing & Tracking
Stage 2: EfficientNet-B0 (or MobileNetV3) crop classification
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2
import numpy as np
from PIL import Image
try:
    import torch
except ImportError:
    torch = None

from inference.detector import TSRDetector, CLASSES, COLOR_PALETTE

class TemporalSmoother:
    """
    IoU-based rolling tracker for video streams.
    Smooths bounding box jitter and applies confidence-weighted majority voting
    over a sliding window of frames to eliminate flicker between similar signs
    (e.g. Pedestrian Crossing vs School Ahead).
    """
    def __init__(self, history_len=5, iou_thresh=0.35, max_missing=3):
        self.history_len = history_len
        self.iou_thresh = iou_thresh
        self.max_missing = max_missing
        self.tracks = {}
        self.next_id = 0

    def _iou(self, b1, b2):
        xA, yA = max(b1[0], b2[0]), max(b1[1], b2[1])
        xB, yB = min(b1[2], b2[2]), min(b1[3], b2[3])
        inter = max(0, xB - xA) * max(0, yB - yA)
        area1 = max(1, (b1[2] - b1[0]) * (b1[3] - b1[1]))
        area2 = max(1, (b2[2] - b2[0]) * (b2[3] - b2[1]))
        return inter / float(area1 + area2 - inter)

    def update(self, detections):
        matched = set()
        unmatched_dets = []

        for det in detections:
            bbox = det["bbox"]
            best_iou, best_id = 0.0, None
            for tid, track in self.tracks.items():
                if tid in matched:
                    continue
                iou = self._iou(bbox, track["bbox"])
                if iou > best_iou:
                    best_iou, best_id = iou, tid

            if best_id is not None and best_iou >= self.iou_thresh:
                matched.add(best_id)
                tr = self.tracks[best_id]
                # EMA smooth coordinates
                alpha = 0.65
                tr["bbox"] = (
                    int(alpha * bbox[0] + (1 - alpha) * tr["bbox"][0]),
                    int(alpha * bbox[1] + (1 - alpha) * tr["bbox"][1]),
                    int(alpha * bbox[2] + (1 - alpha) * tr["bbox"][2]),
                    int(alpha * bbox[3] + (1 - alpha) * tr["bbox"][3])
                )
                tr["history"].append((det["label"], det["conf"]))
                if len(tr["history"]) > self.history_len:
                    tr["history"].pop(0)
                tr["missing"] = 0
            else:
                unmatched_dets.append(det)

        # Drop dead tracks
        dead_ids = [tid for tid, tr in self.tracks.items() if tid not in matched and tr["missing"] >= self.max_missing]
        for tid in dead_ids:
            del self.tracks[tid]
        for tid, tr in self.tracks.items():
            if tid not in matched:
                tr["missing"] += 1

        # Register new tracks
        for det in unmatched_dets:
            self.tracks[self.next_id] = {
                "bbox": det["bbox"],
                "history": [(det["label"], det["conf"])],
                "missing": 0
            }
            self.next_id += 1

        # Format smoothed detections
        smoothed = []
        for tid, tr in self.tracks.items():
            if tr["missing"] > 1:
                continue
            votes = {}
            for label, conf in tr["history"]:
                votes[label] = votes.get(label, 0.0) + conf
            best_label = max(votes, key=votes.get)
            matching_confs = [c for l, c in tr["history"] if l == best_label]
            avg_conf = sum(matching_confs) / max(1, len(matching_confs))
            
            # Find class_id
            cls_id = CLASSES.index(best_label) if best_label in CLASSES else 0

            smoothed.append({
                "track_id": tid,
                "bbox": tr["bbox"],
                "class_id": cls_id,
                "label": best_label,
                "conf": avg_conf
            })

        return smoothed

class TwoStageTSRPipeline:
    def __init__(self, yolo_weights="models/best.pt", classifier_weights="models/efficientnet_tsr.pth", conf_thresh=0.25, device=None, enable_smoothing=True):
        self.device = device or ("cuda" if (torch is not None and torch.cuda.is_available()) else "cpu")
        self.conf_thresh = conf_thresh
        self.detector = TSRDetector(weights_path=yolo_weights, conf_thresh=conf_thresh)
        self.classifier = None
        self.has_classifier = False
        self.smoother = TemporalSmoother() if enable_smoothing else None
        self.clahe_obj = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))

        if os.path.exists(classifier_weights):
            try:
                import torchvision.models as models
                import torch.nn as nn
                
                print(f"[INFO] Loading EfficientNet-B0 classifier from: {classifier_weights}")
                net = models.efficientnet_b0(weights=None)
                in_feats = net.classifier[1].in_features
                net.classifier[1] = nn.Linear(in_feats, len(CLASSES))
                net.load_state_dict(torch.load(classifier_weights, map_location=self.device))
                net.to(self.device)
                net.eval()
                self.classifier = net
                self.has_classifier = True
            except Exception as e:
                print(f"[WARNING] Could not load classifier: {e}. Falling back to single-stage YOLO.")
        else:
            print(f"[INFO] Stage 2 classifier weights '{classifier_weights}' not present. Operating in direct YOLO detection mode.")

    def enhance_contrast(self, frame):
        """Enhances contrast on the Lightness channel while preserving authentic sign colors."""
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = self.clahe_obj.apply(l)
        return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)

    def process_frame(self, frame, conf=None, use_clahe=False):
        """
        Runs Stage 1 detection, optional Stage 2 refinement, and temporal smoothing.
        """
        input_frame = self.enhance_contrast(frame) if use_clahe else frame
        annotated_frame, raw_detections = self.detector.detect(input_frame, conf=conf)

        # Stage 2 crop classification if weights exist
        detections = raw_detections
        if self.has_classifier and len(detections) > 0:
            refined_detections = []
            h, w, _ = frame.shape
            for det in detections:
                x1, y1, x2, y2 = det["bbox"]
                crop_bgr = frame[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
                if crop_bgr.size == 0 or crop_bgr.shape[0] < 5 or crop_bgr.shape[1] < 5:
                    refined_detections.append(det)
                    continue

                crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
                crop_resized = cv2.resize(crop_rgb, (224, 224))
                tensor = torch.from_numpy(crop_resized).permute(2, 0, 1).float().unsqueeze(0) / 255.0
                mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
                std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
                tensor = ((tensor - mean) / std).to(self.device)

                with torch.no_grad():
                    logits = self.classifier(tensor)
                    probs = torch.softmax(logits, dim=1)
                    conf, pred_id = torch.max(probs, dim=1)

                pred_id = int(pred_id.item())
                conf = float(conf.item())
                label = CLASSES[pred_id] if pred_id < len(CLASSES) else f"Sign_{pred_id}"
                det["class_id"] = pred_id
                det["label"] = label
                det["conf"] = conf
                refined_detections.append(det)
            detections = refined_detections

        # Apply temporal smoothing for video stability
        if self.smoother is not None:
            detections = self.smoother.update(detections)
            # Re-draw smoothed boxes
            annotated_frame = frame.copy()
            for det in detections:
                x1, y1, x2, y2 = det["bbox"]
                cls_id = det.get("class_id", 0)
                color = COLOR_PALETTE[cls_id % len(COLOR_PALETTE)]
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                caption = f"{det['label']} {det['conf']:.2f}"
                (tw, th), _ = cv2.getTextSize(caption, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(annotated_frame, (x1, max(0, y1 - th - 6)), (x1 + tw, y1), color, -1)
                cv2.putText(annotated_frame, caption, (x1, max(th, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        return annotated_frame, detections
