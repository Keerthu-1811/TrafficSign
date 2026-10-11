"""
Modern ADAS Digital Cockpit - Indian Traffic Sign Recognition & Driver Compliance Dashboard.
Built with Streamlit, styled with custom glassmorphism CSS, circular IRC sign badges,
and live driver telemetry for an automotive digital cockpit experience.
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
    page_title="Indian ADAS Digital Cockpit",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# High-Tech Automotive Styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@600;800;900&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: radial-gradient(circle at 50% 10%, #111827 0%, #030712 100%);
    color: #f3f4f6;
}

/* Glassmorphism Cards */
.cockpit-card {
    background: rgba(17, 24, 39, 0.75);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.7);
    margin-bottom: 16px;
}

/* HUD Font */
.font-hud {
    font-family: 'Orbitron', monospace;
}

.font-mono-val {
    font-family: 'JetBrains Mono', monospace;
}

/* IRC Circular Road Sign Badge */
.irc-sign-badge {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    background: #ffffff;
    border: 9px solid #ef4444;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 25px rgba(239, 68, 68, 0.45);
    font-family: 'Orbitron', sans-serif;
    font-weight: 900;
    font-size: 26px;
    color: #0f172a;
    margin: 0 auto;
}

/* Compliance Status Glow Badges */
.badge-compliant {
    background: rgba(16, 185, 129, 0.15);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.5);
    padding: 6px 16px;
    border-radius: 9999px;
    font-family: 'Orbitron', monospace;
    font-weight: 800;
    display: inline-block;
    letter-spacing: 0.05em;
    box-shadow: 0 0 20px rgba(16, 185, 129, 0.3);
}

.badge-violation {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.6);
    padding: 6px 16px;
    border-radius: 9999px;
    font-family: 'Orbitron', monospace;
    font-weight: 800;
    display: inline-block;
    letter-spacing: 0.05em;
    box-shadow: 0 0 25px rgba(239, 68, 68, 0.4);
    animation: pulse 1.8s infinite;
}

.badge-warning {
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.5);
    padding: 6px 16px;
    border-radius: 9999px;
    font-family: 'Orbitron', monospace;
    font-weight: 800;
    display: inline-block;
    letter-spacing: 0.05em;
    box-shadow: 0 0 20px rgba(245, 158, 11, 0.3);
}

.badge-check {
    background: rgba(6, 182, 212, 0.15);
    color: #06b6d4;
    border: 1px solid rgba(6, 182, 212, 0.5);
    padding: 6px 16px;
    border-radius: 9999px;
    font-family: 'Orbitron', monospace;
    font-weight: 800;
    display: inline-block;
    letter-spacing: 0.05em;
    box-shadow: 0 0 20px rgba(6, 182, 212, 0.3);
}

.digital-speedometer {
    text-align: center;
    padding: 15px;
    background: rgba(15, 23, 42, 0.6);
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.06);
}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_pipeline():
    return TwoStageTSRPipeline(yolo_weights="models/best.pt", conf_thresh=0.25)


pipeline = load_pipeline()

# Session State
if "context_mgr" not in st.session_state:
    st.session_state.context_mgr = DrivingContextManager(is_simulated_speed=True)
if "engine" not in st.session_state:
    st.session_state.engine = ComplianceDecisionEngine(
        context_manager=st.session_state.context_mgr,
        min_confidence=0.55,
    )

context_mgr = st.session_state.context_mgr
engine = st.session_state.engine

# Top Cockpit Header
st.markdown("""
<div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #1f2937; padding-bottom: 14px; margin-bottom: 20px;">
    <div>
        <h1 style="margin: 0; font-size: 26px; font-weight: 800; color: #f9fafb;">
            🚦 AI TSR & Driver Compliance Cockpit
        </h1>
        <p style="margin: 2px 0 0 0; font-size: 13px; color: #9ca3af;">
            Context-Aware Indian Road Safety & Rule Enforcement Engine
        </p>
    </div>
    <div style="text-align: right;">
        <span style="font-size: 11px; background: rgba(6, 182, 212, 0.15); color: #06b6d4; padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(6, 182, 212, 0.3); font-weight: 600;">
            ● YOLOV8 PERCEPTION ENGINE ACTIVE
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar: Controls
st.sidebar.markdown("### 🕹️ Vehicle Telemetry Simulator")
simulated_speed = st.sidebar.slider(
    "Vehicle Speed (km/h)",
    min_value=0,
    max_value=140,
    value=35,
    step=5,
    help="Adjust vehicle speed to test compliance against detected signs.",
)

stop_duration_sec = st.sidebar.number_input(
    "Stationary Stop Duration (seconds)",
    min_value=0.0,
    max_value=10.0,
    value=0.0,
    step=0.5,
    help="Simulates stationary vehicle duration at a Stop sign.",
)

conf_threshold = st.sidebar.slider(
    "Vision Confidence Gate",
    min_value=0.10,
    max_value=0.95,
    value=0.50,
    step=0.05,
)

if st.sidebar.button("🔄 Reset Active Speed Limit & Context"):
    context_mgr.reset()
    st.sidebar.success("Context & limits reset!")

# Main Layout: 2 Columns
col_left, col_right = st.columns([5, 7])

with col_left:
    st.markdown("#### 📷 Perception & Vision Feed")

    source_mode = st.radio("Select Input Mode:", ["📁 Upload Sign Photo", "🖼️ Sample Test Photo Presets"], horizontal=True)

    img_bgr = None
    if source_mode == "📁 Upload Sign Photo":
        uploaded_file = st.file_uploader("Upload a traffic sign photo:", type=["jpg", "jpeg", "png", "webp"])
        if uploaded_file is not None:
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            img_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        else:
            st.info("👆 Please upload an image of an Indian traffic sign to run detection.")
    else:
        sample_photos = sorted([str(p) for p in Path("Test Photos").glob("*.*")])
        input_choice = st.selectbox("Select Traffic Sign Test Scene:", sample_photos, index=0)
        img_bgr = cv2.imread(input_choice)

    if img_bgr is not None:
        # Reset smoother tracks for discrete static photo to prevent carry-over from previous images
        if pipeline.smoother is not None:
            pipeline.smoother.tracks.clear()
            pipeline.smoother.next_id = 0

        annotated_frame, detections = pipeline.process_frame(img_bgr, conf=conf_threshold)

        primary_sign_id = None
        primary_conf = 0.0
        if detections:
            top_det = max(detections, key=lambda d: d.get("conf", 0.0))
            primary_sign_id = top_det.get("class_id")
            primary_conf = top_det.get("conf", 0.0)
        else:
            st.warning("⚠️ No traffic sign detected at current confidence threshold. Try lowering the 'Vision Confidence Gate' slider in the sidebar.")

        # Decision Engine
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
        st.image(cv2.cvtColor(hud_frame, cv2.COLOR_BGR2RGB), use_container_width=True)
    else:
        # Placeholder result when no image is uploaded
        result = engine.check(
            sign_id=None,
            speed_kmh=float(simulated_speed),
            confidence=0.0,
        )
        primary_conf = 0.0

with col_right:
    st.markdown("#### 🏎️ Digital Instrument Cluster")

    # Cluster Cards
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class="digital-speedometer">
            <span style="font-size: 11px; text-transform: uppercase; color: #9ca3af; font-weight: 600;">Current Speed</span>
            <div class="font-hud" style="font-size: 52px; font-weight: 800; color: #ffffff; line-height: 1.1;">
                {simulated_speed}
            </div>
            <span style="font-size: 12px; color: #06b6d4; font-weight: 600;">KM/H (SIMULATED)</span>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        active_lim_val = context_mgr.active_speed_limit if context_mgr.active_speed_limit is not None else "--"
        st.markdown(f"""
        <div class="digital-speedometer" style="display: flex; flex-direction: column; align-items: center; justify-content: center;">
            <span style="font-size: 11px; text-transform: uppercase; color: #9ca3af; font-weight: 600; margin-bottom: 4px;">IRC Speed Ceiling</span>
            <div class="irc-sign-badge">
                {active_lim_val}
            </div>
            <span style="font-size: 11px; color: #10b981; font-weight: 500; margin-top: 4px;">Active Limit Retained</span>
        </div>
        """, unsafe_allow_html=True)

    # Compliance Verdict Card
    status = result["status"]
    status_classes = {
        ComplianceStatus.COMPLIANT: "badge-compliant",
        ComplianceStatus.VIOLATION: "badge-violation",
        ComplianceStatus.WARNING: "badge-warning",
        ComplianceStatus.CHECK_REQUIRED: "badge-check",
        ComplianceStatus.UNCERTAIN: "badge-warning",
    }
    badge_cls = status_classes.get(status, "badge-warning")

    st.markdown(f"""
    <div class="cockpit-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span style="font-size: 12px; font-weight: 700; text-transform: uppercase; color: #9ca3af; letter-spacing: 0.05em;">
                Compliance Decision Status
            </span>
            <span class="{badge_cls}">
                {status}
            </span>
        </div>
        <div style="font-size: 18px; font-weight: 700; color: #ffffff; margin-bottom: 8px;">
            {result['message']}
        </div>
        <div style="font-size: 12px; color: #9ca3af; line-height: 1.6; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 10px; margin-top: 10px;">
            <strong>Sensor & Context Audit:</strong> {result.get('context_note', 'Speed comparison against active Indian Road Congress limit ceiling verified.')}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Telemetry breakdown
    m1, m2, m3 = st.columns(3)
    m1.metric("IRC Sign ID", str(result["sign_id"]) if result["sign_id"] is not None else "--")
    m2.metric("Sign Label", result["sign_name"] if result["sign_name"] is not None else "None")
    m3.metric("Detection Confidence", f"{primary_conf*100:.0f}%" if primary_conf else "--")
