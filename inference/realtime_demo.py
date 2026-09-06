"""
Real-Time Traffic Sign Recognition (TSR) Demo
Supports Webcam, Video File, or Image Directory with FPS and latency display.
Optimized for low-end laptop CPU execution.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2
import time
import argparse
from inference.pipeline import TwoStageTSRPipeline

def run_demo(source="0", yolo_weights="models/best.pt", classifier_weights="models/efficientnet_tsr.pth"):
    print("=" * 70)
    print("REAL-TIME INDIAN TRAFFIC SIGN RECOGNITION (TSR) DEMO")
    print("=" * 70)
    print(f"Source: {source}")
    print("Controls:")
    print("  'q' -> Quit demo")
    print("  's' -> Save screenshot to results/demo_screenshot.jpg")
    print("=" * 70)

    pipeline = TwoStageTSRPipeline(yolo_weights=yolo_weights, classifier_weights=classifier_weights)

    # Determine input type
    is_cam = source.isdigit()
    cap_source = int(source) if is_cam else source

    cap = cv2.VideoCapture(cap_source)
    if not cap.isOpened():
        print(f"[ERROR] Could not open video source: {source}")
        return

    # Frame timing
    prev_time = time.time()
    last_log_time = 0.0
    fps = 0.0

    os.makedirs("results", exist_ok=True)
    screenshot_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[INFO] Stream ended or frame not received.")
            break

        # Inference
        start_inf = time.time()
        annotated_frame, detections = pipeline.process_frame(frame)
        latency_ms = (time.time() - start_inf) * 1000.0

        curr_time = time.time()
        if len(detections) > 0 and (curr_time - last_log_time > 1.0):
            last_log_time = curr_time
            det_summary = ", ".join([f"{d['label']} ({d['conf']*100:.0f}%)" for d in detections])
            print(f"[LIVE DETECT] {det_summary}")

        # Calculate FPS
        fps = 0.9 * fps + 0.1 * (1.0 / max(1e-5, (curr_time - prev_time)))
        prev_time = curr_time

        # UI Overlay: Status banner
        overlay = annotated_frame.copy()
        cv2.rectangle(overlay, (0, 0), (annotated_frame.shape[1], 45), (20, 20, 20), -1)
        annotated_frame = cv2.addWeighted(overlay, 0.7, annotated_frame, 0.3, 0)

        info_text = f"TSR India | FPS: {fps:.1f} | Latency: {latency_ms:.1f}ms | Signs: {len(detections)}"
        cv2.putText(annotated_frame, info_text, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 200), 2, cv2.LINE_AA)

        # Show window
        cv2.imshow("Indian Traffic Sign Recognition - Live Demo", annotated_frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            print("[INFO] Quitting demo.")
            break
        elif key == ord('s'):
            screenshot_idx += 1
            save_path = f"results/screenshot_{screenshot_idx:03d}.jpg"
            cv2.imwrite(save_path, annotated_frame)
            print(f"[SAVED] Screenshot saved to {save_path}")

    cap.release()
    cv2.destroyAllWindows()

def main():
    parser = argparse.ArgumentParser(description="TSR Real-Time OpenCV Demo")
    parser.add_argument("--source", type=str, default="0", help="Camera index (0) or path to video file")
    parser.add_argument("--yolo-weights", type=str, default="models/best.pt", help="Path to YOLOv8 weights")
    parser.add_argument("--classifier-weights", type=str, default="models/efficientnet_tsr.pth", help="Path to EfficientNet weights")
    args = parser.parse_args()

    run_demo(source=args.source, yolo_weights=args.yolo_weights, classifier_weights=args.classifier_weights)

if __name__ == "__main__":
    main()
