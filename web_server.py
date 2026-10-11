"""
Lightweight Web Server for Indian Traffic Sign Recognition & Driver Compliance Cockpit.
Built using standard library http.server (zero extra web framework dependencies required).
Serves the digital cockpit UI and handles real-time YOLOv8 detection & compliance evaluation API requests.
"""

import os
import sys
import json
import time
import base64
import mimetypes
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import cv2
import numpy as np

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from inference.pipeline import TwoStageTSRPipeline
from context_manager import DrivingContextManager
from decision_engine import ComplianceDecisionEngine

# Global instances for the web session
pipeline = TwoStageTSRPipeline(yolo_weights="models/best.pt", conf_thresh=0.25)
context_mgr = DrivingContextManager(is_simulated_speed=True)
engine = ComplianceDecisionEngine(context_manager=context_mgr, min_confidence=0.50)


class ADASCockpitHandler(SimpleHTTPRequestHandler):

    def translate_path(self, path):
        """Map web root and asset paths."""
        parsed = urlparse(path).path
        if parsed == "/" or parsed == "/index.html":
            return str(PROJECT_ROOT / "web" / "index.html")
        elif parsed.startswith("/Test Photos/"):
            rel_path = parsed.lstrip("/")
            return str(PROJECT_ROOT / rel_path)
        elif parsed.startswith("/results/"):
            rel_path = parsed.lstrip("/")
            return str(PROJECT_ROOT / rel_path)
        elif parsed.startswith("/web/"):
            rel_path = parsed.lstrip("/")
            return str(PROJECT_ROOT / rel_path)
        return super().translate_path(path)

    def do_GET(self):
        parsed = urlparse(self.path).path
        if parsed == "/api/photos":
            photo_dir = PROJECT_ROOT / "Test Photos"
            photos = sorted([p.name for p in photo_dir.glob("*.*") if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]])
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(photos).encode("utf-8"))
            return
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path).path

        if parsed == "/api/detect":
            # Image upload & YOLOv8 perception endpoint
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len)
            try:
                data = json.loads(post_body.decode("utf-8"))
                img_data = data.get("image", "")
                speed_kmh = float(data.get("speed_kmh", context_mgr.current_speed_kmh))
                conf_thresh = float(data.get("confidence_threshold", 0.30))

                if "," in img_data:
                    img_data = img_data.split(",", 1)[1]

                img_bytes = base64.b64decode(img_data)
                np_arr = np.frombuffer(img_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                if frame is None:
                    raise ValueError("Failed to decode image data.")

                h, w, _ = frame.shape

                # Reset smoother tracks for static photo detection
                if pipeline.smoother is not None:
                    pipeline.smoother.tracks.clear()
                    pipeline.smoother.next_id = 0

                # Process through YOLOv8 vision pipeline
                annotated_frame, detections = pipeline.process_frame(frame, conf=conf_thresh)

                primary_sign_id = None
                primary_sign_name = None
                primary_conf = 0.0
                bbox = None

                if detections:
                    top_det = max(detections, key=lambda d: d.get("conf", 0.0))
                    primary_sign_id = top_det.get("class_id")
                    primary_sign_name = top_det.get("label")
                    primary_conf = float(top_det.get("conf", 0.0))
                    bbox = [int(v) for v in top_det.get("bbox", [])]

                heading_deg = data.get("heading_deg")
                horn_active = data.get("horn_active")
                pedestrian_present = data.get("pedestrian_present")

                # Run compliance check
                compliance_result = engine.check(
                    sign_id=primary_sign_id,
                    speed_kmh=speed_kmh,
                    confidence=primary_conf,
                    heading_deg=heading_deg,
                    horn_active=horn_active,
                    pedestrian_present=pedestrian_present,
                )

                response_payload = {
                    "detected": len(detections) > 0,
                    "detections": detections,
                    "primary_sign_id": primary_sign_id,
                    "primary_sign_name": primary_sign_name,
                    "confidence": primary_conf,
                    "bbox": bbox,
                    "image_width": w,
                    "image_height": h,
                    "active_speed_limit": context_mgr.active_speed_limit,
                    "compliance": compliance_result,
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(response_payload).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        elif parsed == "/api/check":
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len)
            try:
                data = json.loads(post_body.decode("utf-8"))
                sign_id = data.get("sign_id")
                speed_kmh = data.get("speed_kmh")
                confidence = float(data.get("confidence", 0.90))
                stopped_sec = data.get("stopped_seconds")
                heading_deg = data.get("heading_deg")
                horn_active = data.get("horn_active")
                pedestrian_present = data.get("pedestrian_present")

                result = engine.check(
                    sign_id=sign_id,
                    speed_kmh=speed_kmh,
                    confidence=confidence,
                    stopped_seconds=stopped_sec,
                    heading_deg=heading_deg,
                    horn_active=horn_active,
                    pedestrian_present=pedestrian_present,
                )

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        elif parsed == "/api/reset":
            context_mgr.reset()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "RESET_SUCCESS"}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def run_server(port=8080):
    server_address = ("", port)
    httpd = HTTPServer(server_address, ADASCockpitHandler)
    print("=" * 75)
    print("🚦 INDIAN ADAS & DRIVER COMPLIANCE DIGITAL COCKPIT IS LIVE")
    print(f"👉 Open in your web browser: http://localhost:{port}")
    print("=" * 75)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Server shutting down.")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
