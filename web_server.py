"""
Lightweight Web Server for Indian Traffic Sign Recognition & Driver Compliance Cockpit.
Built using standard library http.server (zero extra web framework dependencies required).
Serves the digital cockpit UI and handles real-time compliance evaluation API requests.
"""

import os
import sys
import json
import time
import mimetypes
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from context_manager import DrivingContextManager
from decision_engine import ComplianceDecisionEngine

# Global instances for the web session
context_mgr = DrivingContextManager(is_simulated_speed=True)
engine = ComplianceDecisionEngine(context_manager=context_mgr, min_confidence=0.55)


class ADASCockpitHandler(SimpleHTTPRequestHandler):

    def translate_path(self, path):
        """Map web root and asset paths."""
        parsed = urlparse(path).path
        if parsed == "/" or parsed == "/index.html":
            return str(PROJECT_ROOT / "web" / "index.html")
        elif parsed.startswith("/Test Photos/"):
            # Serve Test Photos
            rel_path = parsed.lstrip("/")
            return str(PROJECT_ROOT / rel_path)
        elif parsed.startswith("/results/"):
            rel_path = parsed.lstrip("/")
            return str(PROJECT_ROOT / rel_path)
        elif parsed.startswith("/web/"):
            rel_path = parsed.lstrip("/")
            return str(PROJECT_ROOT / rel_path)
        return super().translate_path(path)

    def do_POST(self):
        parsed = urlparse(self.path).path

        if parsed == "/api/check":
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len)
            try:
                data = json.loads(post_body.decode("utf-8"))
                sign_id = data.get("sign_id")
                speed_kmh = data.get("speed_kmh")
                confidence = float(data.get("confidence", 0.90))
                stopped_sec = data.get("stopped_seconds")

                result = engine.check(
                    sign_id=sign_id,
                    speed_kmh=speed_kmh,
                    confidence=confidence,
                    stopped_seconds=stopped_sec,
                )

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
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
    print(f"🚦 INDIAN ADAS & DRIVER COMPLIANCE DIGITAL COCKPIT IS LIVE")
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
