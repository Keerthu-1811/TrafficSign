"""
Real-Time Context-Aware Traffic Sign Recognition & Driver Compliance Prototype.
Integrates YOLOv8 detection, temporal smoothing, dynamic driving context tracking,
and rule-based driver compliance checking with interactive simulated speed.
"""

import os
import sys
import time
import argparse
from pathlib import Path
import cv2
import numpy as np

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from inference.pipeline import TwoStageTSRPipeline
from context_manager import DrivingContextManager
from decision_engine import ComplianceDecisionEngine, ComplianceStatus
from voice_alert import VoiceAlertWorker

# Visual HUD Color Scheme (BGR)
STATUS_COLORS = {
    ComplianceStatus.COMPLIANT: (34, 177, 76),       # Green
    ComplianceStatus.VIOLATION: (36, 28, 237),       # Red
    ComplianceStatus.WARNING: (0, 165, 255),         # Amber / Orange
    ComplianceStatus.CHECK_REQUIRED: (232, 162, 0),  # Cyan / Blue
    ComplianceStatus.CANNOT_VERIFY: (160, 160, 160), # Slate Gray
    ComplianceStatus.UNCERTAIN: (0, 215, 255),       # Yellow
    ComplianceStatus.NO_ACTION: (100, 100, 100),     # Dark Gray
}


def draw_hud(
    frame: np.ndarray,
    result: dict,
    fps: float,
    current_speed: float,
    active_limit: int,
    voice_enabled: bool,
    clahe_enabled: bool,
) -> np.ndarray:
    """Renders automotive style status HUD over the frame."""
    h, w, _ = frame.shape
    overlay = frame.copy()

    # 1. Top HUD Bar (Dark semi-transparent)
    top_bar_height = 56
    cv2.rectangle(overlay, (0, 0), (w, top_bar_height), (18, 18, 18), -1)

    # 2. Bottom Compliance Card (Height 68)
    bottom_bar_height = 70
    cv2.rectangle(overlay, (0, h - bottom_bar_height), (w, h), (18, 18, 18), -1)

    # Blend overlay with original frame
    frame = cv2.addWeighted(overlay, 0.75, frame, 0.25, 0)

    # --- Top Bar Info ---
    # Left: Project & FPS
    cv2.putText(
        frame,
        f"TSR India Compliance | FPS: {fps:.1f}",
        (16, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.60,
        (240, 240, 240),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        f"[W/S] Speed (+/-) | [0] Stop | [R] Reset Limit | [V] Voice: {'ON' if voice_enabled else 'OFF'} | [Q] Quit",
        (16, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (180, 180, 180),
        1,
        cv2.LINE_AA,
    )

    # Right: Telemetry (Speed & Active Limit)
    speed_tag = f"SPEED: {current_speed:.0f} km/h (SIMULATED)"
    limit_tag = f"LIMIT: {active_limit if active_limit is not None else '--'} km/h"
    
    cv2.putText(
        frame,
        limit_tag,
        (w - 220, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.60,
        (0, 220, 255) if active_limit else (150, 150, 150),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        speed_tag,
        (w - 380, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.50,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )

    # --- Bottom Bar Compliance Verdict ---
    status = result.get("status", ComplianceStatus.NO_ACTION)
    status_color = STATUS_COLORS.get(status, (200, 200, 200))
    status_text = f"[{status}]"
    message = result.get("message", "")

    # Status Badge
    cv2.putText(
        frame,
        status_text,
        (16, h - 38),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        status_color,
        2,
        cv2.LINE_AA,
    )

    # Message & Context Note
    cv2.putText(
        frame,
        message,
        (220, h - 38),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )

    context_note = result.get("context_note")
    if context_note:
        cv2.putText(
            frame,
            f"* {context_note}",
            (220, h - 14),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (170, 170, 170),
            1,
            cv2.LINE_AA,
        )

    # Detected Sign indicator pill on right of bottom bar
    sign_name = result.get("sign_name")
    if sign_name:
        conf = result.get("confidence", 0.0)
        sign_tag = f"Sign: {sign_name} ({conf*100:.0f}%)"
        (stw, _), _ = cv2.getTextSize(sign_tag, cv2.FONT_HERSHEY_SIMPLEX, 0.50, 1)
        cv2.putText(
            frame,
            sign_tag,
            (w - stw - 20, h - 38),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.50,
            (0, 255, 200),
            1,
            cv2.LINE_AA,
        )

    return frame


def run_compliance_detection(
    source: str = "0",
    yolo_weights: str = "models/best.pt",
    initial_speed: float = 30.0,
    enable_voice: bool = False,
    min_conf: float = 0.50,
    use_clahe: bool = False,
    width: int = 1280,
    height: int = 720,
):
    print("=" * 80)
    print("  INDIAN TRAFFIC SIGN RECOGNITION & DRIVER COMPLIANCE SYSTEM")
    print("=" * 80)
    print(f"Video Source: {source}")
    print(f"YOLO Weights: {yolo_weights}")
    print(f"Initial Simulated Speed: {initial_speed:.0f} km/h")
    print(f"Voice Alerts: {'ENABLED' if enable_voice else 'DISABLED'}")
    print("\nLive Controls:")
    print("  'w' / 'k'  -> Increase simulated speed (+5 km/h)")
    print("  's' / 'j'  -> Decrease simulated speed (-5 km/h)")
    print("  '0'        -> Halt vehicle (0 km/h) to simulate Stop sign compliance")
    print("  'r'        -> Reset active speed limit and stop state")
    print("  'v'        -> Toggle Voice Alerts on/off")
    print("  'c'        -> Toggle CLAHE contrast enhancement")
    print("  'p'        -> Save screenshot to results/")
    print("  'q'        -> Quit demo")
    print("=" * 80)

    # Initialize Perception Pipeline & Compliance Engine
    pipeline = TwoStageTSRPipeline(yolo_weights=yolo_weights, conf_thresh=min_conf)
    context_mgr = DrivingContextManager(is_simulated_speed=True, stop_duration_required=2.0)
    engine = ComplianceDecisionEngine(context_manager=context_mgr, min_confidence=0.65, alert_cooldown_seconds=3.0)
    voice_worker = VoiceAlertWorker(enabled=enable_voice)

    simulated_speed = initial_speed
    context_mgr.set_speed(simulated_speed)

    is_cam = source.isdigit()
    cap_source = int(source) if is_cam else source
    cap = cv2.VideoCapture(cap_source)
    if not cap.isOpened():
        print(f"[ERROR] Could not open video source: {source}")
        return

    if is_cam:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    os.makedirs("results", exist_ok=True)
    screenshot_idx = 0
    prev_time = time.time()
    fps = 0.0
    curr_clahe = use_clahe

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[INFO] Video stream ended or frame unavailable.")
            break

        now = time.time()
        fps = 0.9 * fps + 0.1 * (1.0 / max(1e-5, (now - prev_time)))
        prev_time = now

        # Run vision pipeline
        annotated_frame, detections = pipeline.process_frame(frame, conf=min_conf, use_clahe=curr_clahe)

        # Select the most prominent / highest confidence detection if available
        primary_sign_id = None
        primary_conf = 0.0
        if detections:
            # Sort by confidence descending
            top_det = max(detections, key=lambda d: d.get("conf", 0.0))
            primary_sign_id = top_det.get("class_id")
            primary_conf = top_det.get("conf", 0.0)

        # Evaluate compliance against context
        result = engine.check(
            sign_id=primary_sign_id,
            speed_kmh=simulated_speed,
            confidence=primary_conf,
            timestamp=now,
        )

        # Voice alert announcement if new alert event
        if result.get("should_alert") and enable_voice:
            voice_text = result["message"]
            voice_worker.alert(voice_text)

        # Draw Automotive HUD
        display_frame = draw_hud(
            annotated_frame,
            result=result,
            fps=fps,
            current_speed=simulated_speed,
            active_limit=context_mgr.active_speed_limit,
            voice_enabled=enable_voice,
            clahe_enabled=curr_clahe,
        )

        cv2.imshow("Indian TSR & Driver Compliance", display_frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            print("[INFO] Exiting.")
            break
        elif key in (ord('w'), ord('k')):
            simulated_speed = min(160.0, simulated_speed + 5.0)
            context_mgr.set_speed(simulated_speed, timestamp=now)
            print(f"[SPEED] Simulated speed increased: {simulated_speed:.0f} km/h")
        elif key in (ord('s'), ord('j')):
            simulated_speed = max(0.0, simulated_speed - 5.0)
            context_mgr.set_speed(simulated_speed, timestamp=now)
            print(f"[SPEED] Simulated speed decreased: {simulated_speed:.0f} km/h")
        elif key == ord('0'):
            simulated_speed = 0.0
            context_mgr.set_speed(simulated_speed, timestamp=now)
            print("[SPEED] Vehicle stopped (0 km/h).")
        elif key == ord('r'):
            context_mgr.reset()
            print("[CONTEXT] Active speed limit and stop state reset.")
        elif key == ord('v'):
            enable_voice = not enable_voice
            voice_worker.enabled = enable_voice
            print(f"[VOICE] Voice alerts: {'ENABLED' if enable_voice else 'DISABLED'}")
        elif key == ord('c'):
            curr_clahe = not curr_clahe
            print(f"[CONTRAST] CLAHE contrast: {'ENABLED' if curr_clahe else 'DISABLED'}")
        elif key == ord('p'):
            screenshot_idx += 1
            out_file = f"results/compliance_snap_{screenshot_idx:03d}.jpg"
            cv2.imwrite(out_file, display_frame)
            print(f"[SAVED] Saved frame to {out_file}")

    cap.release()
    cv2.destroyAllWindows()
    voice_worker.stop()


def main():
    parser = argparse.ArgumentParser(description="Real-Time TSR & Driver Compliance System")
    parser.add_argument("--source", type=str, default="0", help="Webcam index (0) or path to video file")
    parser.add_argument("--yolo-weights", type=str, default="models/best.pt", help="Path to YOLO weights")
    parser.add_argument("--speed", type=float, default=30.0, help="Initial simulated vehicle speed in km/h")
    parser.add_argument("--conf", type=float, default=0.50, help="Detection confidence threshold")
    parser.add_argument("--voice", action="store_true", help="Enable voice audio alerts")
    parser.add_argument("--clahe", action="store_true", help="Enable CLAHE contrast enhancement")
    args = parser.parse_args()

    run_compliance_detection(
        source=args.source,
        yolo_weights=args.yolo_weights,
        initial_speed=args.speed,
        enable_voice=args.voice,
        min_conf=args.conf,
        use_clahe=args.clahe,
    )


if __name__ == "__main__":
    main()
