"""
Two-Stage TSR Inference Pipeline:
Stage 1: YOLOv8 sign localization
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
from inference.detector import TSRDetector, CLASSES, COLOR_PALETTE

class TwoStageTSRPipeline:
    def __init__(self, yolo_weights="models/best.pt", classifier_weights="models/efficientnet_tsr.pth", device=None):
        if device:
            self.device = device
        else:
            try:
                import torch
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self.device = "cpu"
        self.detector = TSRDetector(weights_path=yolo_weights)
        self.classifier = None
        self.has_classifier = False

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

    def process_frame(self, frame):
        """
        Runs Stage 1 detection, crops signs, refines classes via Stage 2 if available,
        and annotates the output frame.
        """
        annotated_frame, detections = self.detector.detect(frame)

        if not self.has_classifier or len(detections) == 0:
            return annotated_frame, detections

        # Refine detections with Stage 2 classifier
        refined_detections = []
        h, w, _ = frame.shape

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            crop_bgr = frame[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
            
            if crop_bgr.size == 0 or crop_bgr.shape[0] < 5 or crop_bgr.shape[1] < 5:
                refined_detections.append(det)
                continue

            # Preprocess crop for EfficientNet (224x224, ImageNet normalization)
            crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
            crop_resized = cv2.resize(crop_rgb, (224, 224))
            tensor = torch.from_numpy(crop_resized).permute(2, 0, 1).float().unsqueeze(0) / 255.0
            
            # Normalize
            mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
            std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
            tensor = (tensor - mean) / std
            tensor = tensor.to(self.device)

            with torch.no_grad():
                logits = self.classifier(tensor)
                probs = torch.softmax(logits, dim=1)
                conf, pred_id = torch.max(probs, dim=1)
                
            pred_id = int(pred_id.item())
            conf = float(conf.item())
            label = CLASSES[pred_id] if pred_id < len(CLASSES) else f"Sign_{pred_id}"

            det["stage2_class_id"] = pred_id
            det["stage2_label"] = label
            det["stage2_conf"] = conf
            refined_detections.append(det)

        return annotated_frame, refined_detections
