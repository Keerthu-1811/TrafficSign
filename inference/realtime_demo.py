"""
Real-Time Traffic Sign Recognition (TSR) Demo
Supports Webcam, Video File, or Image Directory with FPS and latency display.
Optimized for low-end laptop CPU execution with dynamic confidence adjustment,
HD webcam resolution support, and real-time contrast enhancement (CLAHE).
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

def run_demo(source="0", yolo_weights="models/best.pt", classifier_weights="models/efficientnet_tsr.pth",
             conf=0.25, use_clahe=False, width=1280, height=720):
    print("=" * 75)
    print("REAL-TIME INDIAN TRAFFIC SIGN RECOGNITION (TSR) DEMO")
    print("=" * 75)
    print(f"Source: {source}")
    print(f"Initial Confidence Threshold: {conf:.2f}")
    print(f"Initial Contrast Boost (CLAHE): {'ENABLED' if use_clahe else 'DISABLED'}")
    print("\nLive Interactive Controls:")
    print("  '+' or ']'  -> Increase confidence threshold (+0.05)")
    print("  '-' or '['  -> Decrease confidence threshold (-0.05)")
    print("  'c'         -> Toggle Contrast Enhancement (CLAHE) on/off")
    print("  's'         -> Save screenshot to results/")
    print("  'q'         -> Quit demo")
    print("=" * 75)

    pipeline = TwoStageTSRPipeline(yolo_weights=yolo_weights, classifier_weights=classifier_weights, conf_thresh=conf)

    # Determine input type
    is_cam = source.isdigit()
    cap_source = int(source) if is_cam else source

    cap = cv2.VideoCapture(cap_source)
    if not cap.isOpened():
        print(f"[ERROR] Could not open video source: {source}")
        return

    # Request HD resolution if using webcam
    if is_cam:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    # Frame timing
    prev_time = time.time()
    last_log_time = 0.0
    fps = 0.0

    os.makedirs("results", exist_ok=True)
    screenshot_idx = 0
    curr_conf = conf
    curr_clahe = use_clahe

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[INFO] Stream ended or frame not received.")
            break

        # Inference
        start_inf = time.time()
        annotated_frame, detections = pipeline.process_frame(frame, conf=curr_conf, use_clahe=curr_clahe)
        latency_ms = (time.time() - start_inf) * 1000.0

        curr_time = time.time()
        if len(detections) > 0 and (curr_time - last_log_time > 1.0):
            last_log_time = curr_time
            det_summary = ", ".join([f"{d['label']} ({d['conf']*100:.0f}%)" for d in detections])
            print(f"[LIVE DETECT] {det_summary}")

        # Calculate FPS
        fps = 0.9 * fps + 0.1 * (1.0 / max(1e-5, (curr_time - prev_time)))
        prev_time = curr_time

        # UI Overlay: Top HUD banner
        overlay = annotated_frame.copy()
        cv2.rectangle(overlay, (0, 0), (annotated_frame.shape[1], 48), (20, 20, 20), -1)
        annotated_frame = cv2.addWeighted(overlay, 0.75, annotated_frame, 0.25, 0)

        clahe_str = "ON" if curr_clahe else "OFF"
        info_text = f"TSR India | FPS: {fps:.1f} | Conf: {int(curr_conf*100)}% | CLAHE: {clahe_str} | Signs: {len(detections)}"
        cv2.putText(annotated_frame, info_text, (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 200), 2, cv2.LINE_AA)

        hint_text = "[+/-] Conf  |  [c] Toggle Contrast  |  [s] Screenshot  |  [q] Quit"
        cv2.putText(annotated_frame, hint_text, (15, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1, cv2.LINE_AA)

        # Show window
        cv2.imshow("Indian Traffic Sign Recognition - Live Demo", annotated_frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            print("[INFO] Quitting demo.")
            break
        elif key in (ord('+'), ord('='), ord(']')):
            curr_conf = min(0.95, round(curr_conf + 0.05, 2))
            print(f"[HUD] Confidence threshold set to: {curr_conf:.2f}")
        elif key in (ord('-'), ord('_'), ord('[')):
            curr_conf = max(0.10, round(curr_conf - 0.05, 2))
            print(f"[HUD] Confidence threshold set to: {curr_conf:.2f}")
        elif key == ord('c'):
            curr_clahe = not curr_clahe
            print(f"[HUD] Contrast enhancement (CLAHE): {'ENABLED' if curr_clahe else 'DISABLED'}")
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
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold (default: 0.25)")
    parser.add_argument("--clahe", action="store_true", help="Enable CLAHE contrast boost on startup")
    parser.add_argument("--width", type=int, default=1280, help="Webcam capture width (default: 1280)")
    parser.add_argument("--height", type=int, default=720, help="Webcam capture height (default: 720)")
    args = parser.parse_args()

    run_demo(
        source=args.source,
        yolo_weights=args.yolo_weights,
        classifier_weights=args.classifier_weights,
        conf=args.conf,
        use_clahe=args.clahe,
        width=args.width,
        height=args.height
    )

if __name__ == "__main__":
    main()
