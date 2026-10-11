"""
Batch Compliance Evaluation & Demonstration Script.
Evaluates static test images across simulated driving conditions,
computes compliance verdicts with HUD overlays, and saves annotated outputs.
"""

import os
import sys
from pathlib import Path
import cv2

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from inference.pipeline import TwoStageTSRPipeline
from context_manager import DrivingContextManager
from decision_engine import ComplianceDecisionEngine
from realtime_detection import draw_hud

TEST_CASES = [
    {"image": "Test Photos/20 speed limit.jpg", "speed": 15.0, "scenario": "Within 20 km/h limit"},
    {"image": "Test Photos/20 speed limit.jpg", "speed": 35.0, "scenario": "Exceeding 20 km/h limit"},
    {"image": "Test Photos/40 speed limit.jpg", "speed": 40.0, "scenario": "At 40 km/h boundary"},
    {"image": "Test Photos/40 speed limit.jpg", "speed": 55.0, "scenario": "Exceeding 40 km/h limit"},
    {"image": "Test Photos/60 speed limit.jpg", "speed": 55.0, "scenario": "Within 60 km/h limit"},
    {"image": "Test Photos/80 speed limit.jpg", "speed": 95.0, "scenario": "Exceeding 80 km/h limit"},
    {"image": "Test Photos/stop sign.jpeg", "speed": 25.0, "scenario": "Stop sign approaching (moving)"},
    {"image": "Test Photos/stop sign.jpeg", "speed": 0.0, "stopped_seconds": 2.5, "scenario": "Stop sign satisfied (halted 2.5s)"},
    {"image": "Test Photos/pedestrian.jpg", "speed": 30.0, "scenario": "Pedestrian crossing caution"},
    {"image": "Test Photos/school ahead.png", "speed": 30.0, "scenario": "School zone caution"},
    {"image": "Test Photos/no entry.png", "speed": 20.0, "scenario": "No Entry warning"},
    {"image": "Test Photos/horn.png", "speed": 25.0, "scenario": "Horn prohibited zone"},
]


def run_batch_evaluation():
    output_dir = Path("results/compliance_eval")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("RUNNING BATCH COMPLIANCE EVALUATION ON TEST PHOTOS")
    print("=" * 80)

    pipeline = TwoStageTSRPipeline(yolo_weights="models/best.pt", conf_thresh=0.25)
    context_mgr = DrivingContextManager(is_simulated_speed=True)
    engine = ComplianceDecisionEngine(context_manager=context_mgr, min_confidence=0.50)

    print(f"{'IMAGE':<30} | {'SIM SPEED':<10} | {'STATUS':<15} | {'VERDICT MESSAGE'}")
    print("-" * 80)

    for idx, tc in enumerate(TEST_CASES, 1):
        img_path = tc["image"]
        if not os.path.exists(img_path):
            print(f"Skipping {img_path} (not found)")
            continue

        frame = cv2.imread(img_path)
        if frame is None:
            continue

        speed = tc["speed"]
        stopped_sec = tc.get("stopped_seconds")

        # For discrete test photos, reset smoother tracks to avoid carry-over
        if pipeline.smoother is not None:
            pipeline.smoother.tracks.clear()
            pipeline.smoother.next_id = 0

        # Run detection
        annotated_frame, detections = pipeline.process_frame(frame, conf=0.30)
        primary_sign_id = None
        primary_conf = 0.0
        if detections:
            top_det = max(detections, key=lambda d: d.get("conf", 0.0))
            primary_sign_id = top_det.get("class_id")
            primary_conf = top_det.get("conf", 0.0)

        # Check compliance
        result = engine.check(
            sign_id=primary_sign_id,
            speed_kmh=speed,
            confidence=primary_conf,
            stopped_seconds=stopped_sec,
        )

        status = result["status"]
        message = result["message"]
        print(f"{Path(img_path).name:<30} | {speed:>4.0f} km/h   | {status:<15} | {message}")

        # Draw HUD on frame and save
        hud_frame = draw_hud(
            annotated_frame,
            result=result,
            fps=30.0,
            current_speed=speed,
            active_limit=context_mgr.active_speed_limit,
            voice_enabled=False,
            clahe_enabled=False,
        )

        out_name = f"eval_{idx:02d}_{Path(img_path).stem}_{status.lower()}.jpg"
        cv2.imwrite(str(output_dir / out_name), hud_frame)

    print("-" * 80)
    print(f"Saved all annotated evaluation outputs with HUD overlays to: {output_dir}/")


if __name__ == "__main__":
    run_batch_evaluation()
