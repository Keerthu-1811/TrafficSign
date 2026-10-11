"""
Streamlit Dashboard for Indian Traffic Sign Recognition & Driver Compliance.
Provides an interactive web UI with:
- Video / Image / Webcam input source selection
- Interactive simulated speed slider (0 to 120 km/h)
- Dynamic Active Speed Limit tracking display
- Real-time Compliance Status indicator & Alert cards
- Evaluation gallery of test photos
"""

import os
import sys
from pathlib import Path
import cv2
import numpy as np

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import streamlit as st
except ImportError:
    print("[ERROR] Streamlit is not installed. Run 'pip install streamlit' to launch the web dashboard.")
    sys.exit(1)

from inference.pipeline import TwoStageTSRPipeline
from context_manager import DrivingContextManager
from decision_engine import ComplianceDecisionEngine, ComplianceStatus, SIGN_CLASSES
from realtime_detection import draw_hud

st.set_page_config(
    page_title="Indian TSR & Driver Compliance",
    page_icon="🚦",
    layout="wide",
)

# Custom Styling
st.markdown("""
<style>
.badge-compliant { background-color: #28a745; color: white; padding: 4px 12px; border-radius: 6px; font-weight: bold; }
.badge-violation { background-color: #dc3545; color: white; padding: 4px 12px; border-radius: 6px; font-weight: bold; }
.badge-warning { background-color: #fd7e14; color: white; padding: 4px 12px; border-radius: 6px; font-weight: bold; }
.badge-check { background-color: #17a2b8; color: white; padding: 4px 12px; border-radius: 6px; font-weight: bold; }
.badge-uncertain { background-color: #ffc107; color: black; padding: 4px 12px; border-radius: 6px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_pipeline():
    return TwoStageTSRPipeline(yolo_weights="models/best.pt", conf_thresh=0.25)


pipeline = load_pipeline()

# Session State for Context Manager
if "context_mgr" not in st.session_state:
    st.session_state.context_mgr = DrivingContextManager(is_simulated_speed=True)
if "engine" not in st.session_state:
    st.session_state.engine = ComplianceDecisionEngine(
        context_manager=st.session_state.context_mgr,
        min_confidence=0.55,
    )

context_mgr = st.session_state.context_mgr
engine = st.session_state.engine

# Header
st.title("🚦 Context-Aware Indian TSR & Driver Compliance")
st.caption("Academic Prototype: Rule-based driver compliance checking on top of YOLOv8 sign detection.")

# Sidebar Controls
st.sidebar.header("🕹️ Simulation Controls")

simulated_speed = st.sidebar.slider(
    "Vehicle Speed (km/h) [SIMULATED]",
    min_value=0,
    max_value=120,
    value=35,
    step=5,
    help="Adjust vehicle speed to test compliance against detected signs.",
)

stop_duration_sec = st.sidebar.number_input(
    "Stopped Duration (seconds)",
    min_value=0.0,
    max_value=10.0,
    value=0.0,
    step=0.5,
    help="Simulate how long the vehicle has been stationary at a Stop sign.",
)

conf_threshold = st.sidebar.slider(
    "Detection Confidence Threshold",
    min_value=0.10,
    max_value=0.95,
    value=0.50,
    step=0.05,
)

if st.sidebar.button("🔄 Reset Active Speed Limit & Context"):
    context_mgr.reset()
    st.sidebar.success("Context state reset!")

# Input Selection
mode = st.radio(
    "Select Input Mode:",
    ["Sample Test Photo", "Upload Image", "Evaluation Gallery"],
    horizontal=True,
)

sample_photos = sorted([str(p) for p in Path("Test Photos").glob("*.*")])

if mode == "Sample Test Photo":
    col1, col2 = st.columns([1, 1])

    with col1:
        chosen_photo = st.selectbox("Choose a sample sign image:", sample_photos, index=0)
        img_bgr = cv2.imread(chosen_photo)
        if img_bgr is not None:
            # Run detection
            if pipeline.smoother is not None:
                pipeline.smoother.tracks.clear()
            annotated_frame, detections = pipeline.process_frame(img_bgr, conf=conf_threshold)

            primary_sign_id = None
            primary_conf = 0.0
            if detections:
                top_det = max(detections, key=lambda d: d.get("conf", 0.0))
                primary_sign_id = top_det.get("class_id")
                primary_conf = top_det.get("conf", 0.0)

            # Evaluate compliance
            result = engine.check(
                sign_id=primary_sign_id,
                speed_kmh=float(simulated_speed),
                confidence=primary_conf,
                stopped_seconds=stop_duration_sec if stop_duration_sec > 0 else None,
            )

            # Render HUD
            hud_frame = draw_hud(
                annotated_frame,
                result=result,
                fps=30.0,
                current_speed=float(simulated_speed),
                active_limit=context_mgr.active_speed_limit,
                voice_enabled=False,
                clahe_enabled=False,
            )

            hud_rgb = cv2.cvtColor(hud_frame, cv2.COLOR_BGR2RGB)
            st.image(hud_rgb, caption="Annotated Vision & HUD Feed", use_container_width=True)

    with col2:
        st.subheader("📊 Compliance Status")
        status = result["status"]
        status_color_map = {
            ComplianceStatus.COMPLIANT: "badge-compliant",
            ComplianceStatus.VIOLATION: "badge-violation",
            ComplianceStatus.WARNING: "badge-warning",
            ComplianceStatus.CHECK_REQUIRED: "badge-check",
            ComplianceStatus.UNCERTAIN: "badge-uncertain",
        }
        badge_class = status_color_map.get(status, "badge-uncertain")
        st.markdown(f"### Status: <span class='{badge_class}'>{status}</span>", unsafe_allow_html=True)
        st.info(result["message"])

        m1, m2, m3 = st.columns(3)
        m1.metric("Simulated Speed", f"{simulated_speed} km/h")
        m2.metric("Active Limit", f"{context_mgr.active_speed_limit or '--'} km/h")
        m3.metric("Sign Conf", f"{primary_conf*100:.0f}%" if primary_conf else "--")

        if result.get("context_note"):
            st.warning(f"Note: {result['context_note']}")

elif mode == "Upload Image":
    uploaded = st.file_uploader("Upload an image of a traffic sign:", type=["jpg", "jpeg", "png", "webp"])
    if uploaded:
        file_bytes = np.asarray(bytearray(uploaded.read()), dtype=np.uint8)
        img_bgr = cv2.imdecode(file_bytes, 1)

        if pipeline.smoother is not None:
            pipeline.smoother.tracks.clear()
        annotated_frame, detections = pipeline.process_frame(img_bgr, conf=conf_threshold)

        primary_sign_id = None
        primary_conf = 0.0
        if detections:
            top_det = max(detections, key=lambda d: d.get("conf", 0.0))
            primary_sign_id = top_det.get("class_id")
            primary_conf = top_det.get("conf", 0.0)

        result = engine.check(
            sign_id=primary_sign_id,
            speed_kmh=float(simulated_speed),
            confidence=primary_conf,
            stopped_seconds=stop_duration_sec if stop_duration_sec > 0 else None,
        )

        hud_frame = draw_hud(
            annotated_frame,
            result=result,
            fps=30.0,
            current_speed=float(simulated_speed),
            active_limit=context_mgr.active_speed_limit,
            voice_enabled=False,
            clahe_enabled=False,
        )

        col1, col2 = st.columns(2)
        with col1:
            st.image(cv2.cvtColor(hud_frame, cv2.COLOR_BGR2RGB), use_container_width=True)
        with col2:
            st.markdown(f"### Verdict: **{result['status']}**")
            st.write(result["message"])

elif mode == "Evaluation Gallery":
    st.subheader("Batch Evaluation Results Gallery")
    eval_images = sorted(list(Path("results/compliance_eval").glob("*.jpg")))
    if not eval_images:
        st.write("No batch outputs found. Run `python evaluate_compliance_batch.py` to generate.")
    else:
        cols = st.columns(3)
        for i, img_p in enumerate(eval_images):
            with cols[i % 3]:
                st.image(str(img_p), caption=img_p.name, use_container_width=True)
