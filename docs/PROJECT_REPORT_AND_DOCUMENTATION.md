# Context-Aware Indian Traffic Sign Recognition & Intelligent Driver Compliance System
## Comprehensive Project Report & System Documentation

**Academic Project Report:** Autonomous Perception & Advanced Driver Assistance Systems (ADAS)  
**Repository:** [https://github.com/Keerthu-1811/TrafficSign](https://github.com/Keerthu-1811/TrafficSign)  
**Target Architecture:** Lightweight Edge/CPU Real-Time Inference + Cloud GPU Training (Google Colab)  
**Status:** Completed, Fully Tested (23/23 Passing Tests), Deployed with Interactive ADAS Digital Cockpit  

---

## Executive Summary

Standard Traffic Sign Recognition (TSR) systems focus strictly on perception—classifying and localizing signs within camera frames. However, **perception alone does not guarantee road safety or driver compliance**. Detecting a *Stop* sign or a *Speed Limit 40* sign provides zero utility unless the vehicle's driving behavior is actively evaluated against that sign.

This project delivers an end-to-end, two-tier ADAS prototype designed for Indian roadway conditions:
1. **Tier 1 (Perception Layer):** A deep learning object detection model (Ultralytics YOLOv8n) fine-tuned on **15 Indian Road Congress (IRC-67)** traffic sign classes with multi-frame temporal smoothing.
2. **Tier 2 (Context-Aware Decision Engine):** A deterministic, rule-based compliance engine that fuses sign detections with dynamic vehicle telemetry (speed, heading, horn activation, stop duration, pedestrian presence) to evaluate compliance, detect violations, and emit non-blocking driver alerts.

The system is delivered with an interactive, web-based **ADAS Digital Cockpit** inspired by modern EV instrument clusters, accompanied by a 23-case unit test suite and a batch evaluation pipeline across real-world Indian road scenes.

---

## Table of Contents

1. [Problem Statement & Objectives](#1-problem-statement--objectives)
2. [Traffic Sign Ontology (15 IRC Classes)](#2-traffic-sign-ontology-15-irc-classes)
3. [End-to-End System Architecture](#3-end-to-end-system-architecture)
4. [Phase 1: Dataset Engineering & Synthetic Augmentation](#4-phase-1-dataset-engineering--synthetic-augmentation)
5. [Phase 2: Vision Model Training & Temporal Smoothing](#5-phase-2-vision-model-training--temporal-smoothing)
6. [Phase 3: The Driving Context Manager](#6-phase-3-the-driving-context-manager)
7. [Phase 4: Rule-Based Compliance Decision Engine](#7-phase-4-rule-based-compliance-decision-engine)
8. [Phase 5: Multi-Modal Driver Feedback & ADAS Web Cockpit](#8-phase-5-multi-modal-driver-feedback--adas-web-cockpit)
9. [Phase 6: Testing, Verification & Experimental Results](#9-phase-6-testing-verification--experimental-results)
10. [Limitations & Academic Integrity](#10-limitations--academic-integrity)
11. [System Operation & Reproducibility Guide](#11-system-operation--reproducibility-guide)

---

## 1. Problem Statement & Objectives

### 1.1 The Domain Gap in Indian Traffic Scenarios
Deploying Western ADAS models in India leads to critical performance degradation due to:
* **Non-Standard & Weathered Signage:** Peeling paint, dust accumulation, vandalism, non-standard mounting elevations.
* **Chaotic Traffic & Visual Clutter:** Unregulated roadside vegetation, commercial advertising billboards, mixed traffic (two-wheelers, auto-rickshaws, pedestrians, stray cattle).
* **Environmental Variance:** Monsoon rain streaks, tropical sun glare, high ambient dust levels.

### 1.2 The Compliance Gap (Why Perception Alone is Insufficient)
* A vehicle observing a **Speed Limit 60** sign does not know if the driver is speeding unless the vehicle velocity is tracked.
* A **Stop** sign requires coming to a complete halt ($v \le 1\text{ km/h}$) for a sustained interval ($t \ge 2.0\text{ s}$), which cannot be evaluated from a single video frame.
* A **Left Turn** or **Right Turn** sign requires verifying vehicle heading trajectory ($\Delta \theta$).
* A **Horn Prohibited** sign requires acoustic silence zone monitoring.
* A **Pedestrian Crossing** sign requires right-of-way yielding if pedestrians occupy the zebra crossing.

### 1.3 Project Deliverables
* Fine-tune a lightweight YOLOv8 detector for 15 IRC sign classes.
* Implement a multi-frame temporal tracker (`TemporalSmoother`) to eliminate classification flicker.
* Design a persistent `DrivingContextManager` to maintain active road rules across video frames.
* Build a deterministic `ComplianceDecisionEngine` implementing multi-modal compliance logic.
* Implement a non-blocking voice alert worker (`VoiceAlertWorker`) with alert suppression cooldowns.
* Develop an interactive web application (**ADAS Digital Cockpit**) with digital speedometer, IRC sign badges, multi-modal vehicle controls, and real-time YOLOv8 scanning.
* Validate all edge cases through automated unit tests.

---

## 2. Traffic Sign Ontology (15 IRC Classes)

The system aligns strictly with the Indian Road Congress (IRC: 67-2012) Code of Practice for Road Signs:

| Class ID | Sign Name | Category | Compliance Check Mode | Required Context Data |
|:---:|:---|:---|:---|:---|
| **0** | Stop | Regulatory / Mandatory | Temporal Halt Verification | Speed over time ($v \le 1\text{ km/h}$, $t \ge 2.0\text{ s}$) |
| **1** | No Entry | Prohibitory | Warning / Advisory | Road direction & vehicle trajectory vector |
| **2** | Speed Limit 20 | Regulatory / Mandatory | Speed Ceiling Enforcement | Current velocity ($v \le 20\text{ km/h}$) |
| **3** | Speed Limit 40 | Regulatory / Mandatory | Speed Ceiling Enforcement | Current velocity ($v \le 40\text{ km/h}$) |
| **4** | Speed Limit 60 | Regulatory / Mandatory | Speed Ceiling Enforcement | Current velocity ($v \le 60\text{ km/h}$) |
| **5** | Speed Limit 80 | Regulatory / Mandatory | Speed Ceiling Enforcement | Current velocity ($v \le 80\text{ km/h}$) |
| **6** | Give Way | Regulatory / Yield | Warning / Right-of-Way | Intersecting traffic context |
| **7** | School Ahead | Cautionary / Warning | Caution Advisory | School zone proximity context |
| **8** | Pedestrian Crossing | Cautionary / Regulatory | Right-of-Way Yielding | Pedestrian occupancy + vehicle speed |
| **9** | Left Turn | Mandatory Direction | Steering Trajectory Check | Vehicle heading angle ($\theta \le -30^\circ$) |
| **10** | Right Turn | Mandatory Direction | Steering Trajectory Check | Vehicle heading angle ($\theta \ge +30^\circ$) |
| **11** | U-Turn | Mandatory / Advisory | Heading Reversal Check | Vehicle heading reversal ($|\theta| \ge 140^\circ$) |
| **12** | Horn Prohibited | Regulatory / Silence Zone | Acoustic Actuation Check | CAN-bus / acoustic horn activation state |
| **13** | Parking | Informatory | Parking Zone Verification | Stationary location context |
| **14** | Dangerous Curve | Cautionary / Warning | Deceleration & Lateral G | Curve geometry & deceleration rate |

---

## 3. End-to-End System Architecture

The project is structured into a clean, decoupled perception-to-compliance pipeline:

```text
+-------------------------------------------------------------------------------+
|                             PERCEPTION TIER                                   |
|                                                                               |
|   Camera / Video Stream / Image Upload                                        |
|                     |                                                         |
|                     v                                                         |
|           [CLAHE Contrast Enhancement]                                        |
|                     |                                                         |
|                     v                                                         |
|         Ultralytics YOLOv8n Detector (weights: models/best.pt)                |
|                     |  Raw Bounding Boxes, Class IDs, Confidences             |
|                     v                                                         |
|      TemporalSmoother (IoU Tracking + EMA Coordinates + Sliding Vote Window)  |
|                     |  Stabilized primary sign ID & confidence                |
+---------------------|---------------------------------------------------------+
                      v
+-------------------------------------------------------------------------------+
|                            COMPLIANCE TIER                                    |
|                                                                               |
|   Vehicle Telemetry Inputs:                                                   |
|   - Speed (km/h)      - Heading (deg)      - Horn Signal      - Pedestrian    |
|                     \        |                  /             /               |
|                      v       v                 v             v                |
|                +-----------------------------------------------+              |
|                |             DrivingContextManager             |              |
|                |  - Retains Active Speed Limit across frames   |              |
|                |  - Measures Stop Duration Stopwatch           |              |
|                |  - Tracks Rolling Speed History Window        |              |
|                +-----------------------------------------------+              |
|                                      |                                        |
|                                      v                                        |
|                +-----------------------------------------------+              |
|                |          ComplianceDecisionEngine             |              |
|                |  - Confidence Gating (< 0.70 -> UNCERTAIN)    |              |
|                |  - Speed Ceiling Evaluation                   |              |
|                |  - Stop Sign Duration Evaluation              |              |
|                |  - Steering / Heading Trajectory Evaluation   |              |
|                |  - Acoustic Silence Zone Evaluation           |              |
|                |  - Pedestrian Right-of-Way Evaluation         |              |
|                |  - Alert De-duplication Cooldown (3.0s)       |              |
|                +-----------------------------------------------+              |
|                                      |                                        |
|                     +----------------+----------------+                       |
|                     |                                 |                       |
|                     v                                 v                       |
|             [VoiceAlertWorker]              [ADAS Digital Cockpit]            |
|          Threaded TTS Voice Alerts         - SVG Speedometer Gauge            |
|          with Queue & Suppression          - IRC Road Sign Badge              |
|                                            - Glowing Compliance Cards         |
|                                            - Telemetry Stream Log             |
+-------------------------------------------------------------------------------+
```

---

## 4. Phase 1: Dataset Engineering & Synthetic Augmentation

### 4.1 Dataset Acquisition
The training corpus was assembled using a multi-pronged approach:
* **Custom Dataset (`dataset/custom_indian_tsr/`):** 2,657 annotated images partitioned into train (70%), validation (15%), and test (15% - 227 images).
* **Multi-Threaded Targeted Web Scraper (`src/dataset_collector.py`):** Automated acquisition of authentic Indian street scenes using Bing Image API targeting exact IRC queries.
* **Auto-Annotation Tool (`src/auto_annotator.py`):** Semi-supervised bootstrapping utilizing pre-trained model proposals with human verification.

### 4.2 Indian Road Weather & Lighting Augmentation (`src/augmentations.py`)
To prevent domain overfitting and simulate harsh Indian conditions, custom Albumentations pipelines were built:
* **Monsoon Rain Streaks:** Directional synthetic translucent streaks simulating severe rainfall.
* **Harsh Glare & Shadows:** Gamma contrast shifts and localized bright ellipsoids simulating tropical noon sun glare.
* **Haze & Dust:** Additive Gaussian atmospheric noise simulating urban smog and highway dust clouds.
* **Motion Blur:** Linear motion convolution kernels simulating vehicular vibrations on unpaved roads.

---

## 5. Phase 2: Vision Model Training & Temporal Smoothing

### 5.1 Model Selection & Training
* **Model:** Ultralytics YOLOv8n (Nano variant, ~3.2M parameters).
* **Training Platform:** Google Colab utilizing Tesla T4 GPU (`notebooks/01_yolov8_training_colab.ipynb` and `notebooks/03_train_custom_dataset_colab.ipynb`).
* **Input Resolution:** $640 \times 640$ pixels.
* **Weights Exported:** [`models/best.pt`](file:///d:/Antigravity/TrafficSign/models/best.pt) (22.5 MB).

### 5.2 Multi-Frame Temporal Smoothing (`inference/pipeline.py`)
In live video feeds, raw per-frame object detections suffer from edge jitter and classification flickering (e.g., oscillating between *Pedestrian Crossing* and *School Ahead* due to similar triangular hazard borders).

The `TemporalSmoother` class eliminates this via:
1. **IoU Track Matching:** Matches candidate bounding boxes against existing tracks using Intersection over Union (threshold: 0.35).
2. **Exponential Moving Average (EMA) Coordinates:** Smooths bounding box jitter ($\alpha = 0.65$):
   $$\text{box}_{\text{smoothed}} = \alpha \cdot \text{box}_{\text{new}} + (1 - \alpha) \cdot \text{box}_{\text{track}}$$
3. **Sliding Window Majority Voting:** Maintains a rolling history buffer ($N = 5$) and calculates confidence-weighted voting across the window to determine the stable label.
4. **Dead Track Pruning:** Drops tracks after 3 consecutive missing frames.

---

## 6. Phase 3: The Driving Context Manager

Implemented in [`context_manager.py`](file:///d:/Antigravity/TrafficSign/context_manager.py), the `DrivingContextManager` provides temporal state persistence:

### 6.1 State Attributes
```python
active_speed_limit: Optional[int]    # Persisted speed limit (20, 40, 60, 80 km/h)
current_speed_kmh: float             # Vehicle speed telemetry
current_heading_deg: float           # Steering angle (-180° to +180°; 0° = straight)
horn_active: bool                    # CAN-bus / acoustic horn actuation state
pedestrian_present: bool             # Zebra crossing occupancy status
stop_sign_active: bool               # Flag indicating active Stop sign zone
total_stopped_duration: float        # Accumulated stationary time
stop_satisfied: bool                 # True when duration >= required threshold
speed_history: List[Tuple[t, v]]     # 15-second rolling velocity history buffer
```

### 6.2 Key Context Behaviors
* **Speed Limit Retention:** Once a speed limit sign is confirmed, the limit remains actively enforced across frames even after the sign moves out of the camera's field of view.
* **Stop Event Stopwatch:** When a Stop sign (Class 0) is encountered, the manager begins tracking vehicle velocity. If $v \le 1.0\text{ km/h}$, it measures stationary duration. Once $t \ge 2.0\text{ s}$, it marks `stop_satisfied = True`.
* **Discrete Image Reset:** When processing standalone test photos (e.g. from the web upload tool), track history is explicitly flushed to prevent previous images from contaminating new inferences.

---

## 7. Phase 4: Rule-Based Compliance Decision Engine

Implemented in [`decision_engine.py`](file:///d:/Antigravity/TrafficSign/decision_engine.py), the engine executes deterministic rules and returns standardized decision payloads.

### 7.1 Compliance Verdict Vocabulary
* **`COMPLIANT`:** Vehicle telemetry satisfies the active rule.
* **`VIOLATION`:** Vehicle telemetry violates the active rule (speed exceeded, horn in silence zone, failure to yield).
* **`WARNING`:** Cautionary hazard sign detected (School Ahead, Dangerous Curve); driver alerted.
* **`CHECK_REQUIRED`:** A multi-step maneuver is currently pending (vehicle approaching Stop sign, mandatory turn pending).
* **`CANNOT_VERIFY`:** Mandatory sign detected, but required context sensors are unobservable.
* **`UNCERTAIN`:** Model detection confidence is below the confidence threshold ($< 0.70$).
* **`NO_ACTION`:** Roadway clear with no restrictive signs active.

### 7.2 Decision Logic Matrix

```python
# Rule 1: Confidence Gating
if confidence < min_confidence (0.70):
    return UNCERTAIN (do not update speed limits or trigger state changes)

# Rule 2: Speed Limit Enforcement (Classes 2, 3, 4, 5)
if sign_id in [2, 3, 4, 5]:
    update active_speed_limit
if active_speed_limit is not None:
    if current_speed > active_speed_limit:
        return VIOLATION ("Speeding: X km/h (Limit: Y km/h)")
    else:
        return COMPLIANT ("Speed compliant: X km/h (Limit: Y km/h)")

# Rule 3: Stop Sign Enforcement (Class 0)
if stop_duration >= 2.0 seconds:
    return COMPLIANT ("Stop requirement satisfied: vehicle stopped for 2.X s")
elif current_speed <= 1.0 km/h:
    return CHECK_REQUIRED ("Stop check in progress: stopped X s / 2.0 s")
else:
    return CHECK_REQUIRED ("Stop sign active: full stop required")

# Rule 4: Directional Turn Enforcement (Classes 9, 10, 11)
if sign_id == 9 (Left Turn):
    return COMPLIANT if heading <= -30° else CHECK_REQUIRED ("Left steer required")
if sign_id == 10 (Right Turn):
    return COMPLIANT if heading >= +30° else CHECK_REQUIRED ("Right steer required")
if sign_id == 11 (U-Turn):
    return COMPLIANT if |heading| >= 140° else CHECK_REQUIRED ("180° reversal pending")

# Rule 5: Acoustic Silence Zone (Class 12: Horn Prohibited)
if sign_id == 12:
    if horn_active:
        return VIOLATION ("Illegal horn activation in Silence Zone!")
    else:
        return COMPLIANT ("Silence Zone: Horn prohibition compliant")

# Rule 6: Pedestrian Right-of-Way (Class 8: Pedestrian Crossing)
if sign_id == 8:
    if pedestrian_present:
        return COMPLIANT if current_speed <= 5 km/h else VIOLATION ("Failed to yield to pedestrian!")
    else:
        return COMPLIANT ("Pedestrian crossing clear")
```

### 7.3 Alert Suppression Engine
To prevent auditory fatigue and video lag, an alert cooldown timer ($3.0\text{ s}$) suppresses repeated triggers for identical messages while keeping the visual HUD updated in real time.

---

## 8. Phase 5: Multi-Modal Driver Feedback & ADAS Web Cockpit

### 8.1 Non-Blocking Audio Alert Worker ([`voice_alert.py`](file:///d:/Antigravity/TrafficSign/voice_alert.py))
* Uses a background daemon worker thread and a bounded thread-safe queue (`queue.Queue(maxsize=5)`).
* Wraps `pyttsx3` text-to-speech engine. Calls to speech synthesis execute independently of OpenCV inference loops, maintaining 30–60 FPS camera frame rates.

### 8.2 Real-Time OpenCV Video HUD ([`realtime_detection.py`](file:///d:/Antigravity/TrafficSign/realtime_detection.py))
* Renders an automotive-grade dark semi-transparent HUD banner:
  * Top Bar: FPS, Confidence, Telemetry controls hint, Simulated Speed badge, Active Speed Limit.
  * Bottom Card: Color-coded status badge (Emerald for `COMPLIANT`, Crimson for `VIOLATION`, Amber for `WARNING`, Cyan for `CHECK_REQUIRED`), advisory text, and sensor gap notes.

### 8.3 Modern ADAS Digital Cockpit Web App ([`web/index.html`](file:///d:/Antigravity/TrafficSign/web/index.html) & [`web_server.py`](file:///d:/Antigravity/TrafficSign/web_server.py))
Built using HTML5, Tailwind CSS, Web Audio API, and standard library Python `http.server`:
* **Circular SVG Speedometer:** Animated glowing arc displaying 0–140 km/h with digital readout.
* **IRC-67 Road Sign Badge:** European/Indian circular white disk with 9px red border and bold black numeral.
* **Stop Sign Stopwatch Bar:** Visual progress fill indicating stationary duration ($0.0\text{ s} \to 2.0\text{ s}$).
* **Multi-Modal Vehicle Controls:**
  * Interactive throttle slider and quick buttons (`-5`, `STOP`, `+5`).
  * 4-Way Steering Selector (`Straight 0°`, `Left -60°`, `Right +60°`, `U-Turn 180°`).
  * Acoustic Horn Button triggering a dual-tone Web Audio car horn synthesizer (435 Hz + 345 Hz).
  * Pedestrian Crossing presence toggle switch.
* **Test Photos Library Dropdown:** Instant one-click selection of 59 categorized test photos.
* **REST Endpoints:**
  * `GET /api/photos`: Lists all available library test photos.
  * `POST /api/detect`: Receives base64 image data, clears static tracks, runs YOLOv8 inference, repositions the bounding box proportionally, and returns compliance decisions.
  * `POST /api/check`: Telemetry-only decision evaluation.

---

## 9. Phase 6: Testing, Verification & Experimental Results

### 9.1 Automated Unit Test Suite ([`tests/test_decision_engine.py`](file:///d:/Antigravity/TrafficSign/tests/test_decision_engine.py))
A comprehensive test suite containing **23 unit test cases** was executed using Python's `unittest` framework:

```text
Ran 23 tests in 0.001s
OK
```

#### Test Suite Breakdown
1. **Class Mapping Alignment (1 test):** Validates all 15 IRC class names and zero-indexed ordering.
2. **Speed-Limit Scenarios (7 tests):**
   * Limit 20 with 15 km/h $\to$ `COMPLIANT`
   * Limit 20 with 30 km/h $\to$ `VIOLATION`
   * Limit 40 at boundary (40 km/h) $\to$ `COMPLIANT`
   * Limit 40 with 45 km/h $\to$ `VIOLATION`
   * Limit 60 with 55 km/h $\to$ `COMPLIANT`
   * Limit 80 with 90 km/h $\to$ `VIOLATION`
   * Low confidence ($0.55 < 0.70$) $\to$ `UNCERTAIN` (no limit mutation)
3. **Limit Persistence Across Frames (2 tests):** Confirms limit remains active when signs leave camera view.
4. **Stop Sign Workflow (3 tests):**
   * Stop sign without temporal history $\to$ `CANNOT_VERIFY` / `CHECK_REQUIRED`
   * Stationary stop held for 1.0s ($< 2.0\text{s}$) $\to$ `CHECK_REQUIRED`
   * Stationary stop held for 2.2s ($\ge 2.0\text{s}$) $\to$ `COMPLIANT`
5. **Multi-Modal Context Tests (7 tests):**
   * Horn honked in Silence Zone $\to$ `VIOLATION`
   * Horn silent in Silence Zone $\to$ `COMPLIANT`
   * Pedestrian present + speed 0 km/h $\to$ `COMPLIANT` (yielded)
   * Pedestrian present + speed 35 km/h $\to$ `VIOLATION` (failure to yield)
   * Pedestrian crossing clear $\to$ `COMPLIANT`
   * Left Turn: heading $-45^\circ \to$ `COMPLIANT`; heading $0^\circ \to$ `CHECK_REQUIRED`
   * Right Turn: heading $+60^\circ \to$ `COMPLIANT`
   * U-Turn: heading $180^\circ \to$ `COMPLIANT`
6. **Alert Suppression Cooldown (2 tests):** Identical alerts within 3.0s suppressed; re-triggered after cooldown.

---

### 9.2 Static Image Batch Evaluation ([`evaluate_compliance_batch.py`](file:///d:/Antigravity/TrafficSign/evaluate_compliance_batch.py))
Evaluated static photos from [`Test Photos/`](file:///d:/Antigravity/TrafficSign/Test%20Photos/) across simulated driving conditions, saving annotated HUD outputs to [`results/compliance_eval/`](file:///d:/Antigravity/TrafficSign/results/compliance_eval/):

| Test Image | Ground Truth Sign | Simulated Speed | Detected Status | System Verdict Message |
|:---|:---|:---:|:---:|:---|
| `20 speed limit.jpg` | Speed Limit 20 | 15 km/h | **`COMPLIANT`** | Speed compliant: 15 km/h (limit: 20 km/h) |
| `20 speed limit.jpg` | Speed Limit 20 | 35 km/h | **`VIOLATION`** | Speeding: 35 km/h (limit: 20 km/h) |
| `40 speed limit.jpg` | Speed Limit 40 | 40 km/h | **`COMPLIANT`** | Speed compliant: 40 km/h (limit: 40 km/h) |
| `40 speed limit.jpg` | Speed Limit 40 | 55 km/h | **`VIOLATION`** | Speeding: 55 km/h (limit: 40 km/h) |
| `60 speed limit.jpg` | Speed Limit 60 | 55 km/h | **`COMPLIANT`** | Speed compliant: 55 km/h (limit: 60 km/h) |
| `80 speed limit.jpg` | Speed Limit 80 | 95 km/h | **`VIOLATION`** | Speeding: 95 km/h (limit: 80 km/h) |
| `stop sign.jpeg` | Stop | 25 km/h | **`CHECK_REQUIRED`** | Stop sign active: full stop required (2.0s) |
| `stop sign.jpeg` | Stop (halted 2.5s) | 0 km/h | **`COMPLIANT`** | Stop sign requirement satisfied: vehicle stopped for 2.5s |
| `pedestrian.jpg` | Pedestrian Crossing | 30 km/h | **`COMPLIANT`** | Pedestrian Crossing clear: roadway unobstructed |
| `horn.png` | Horn Prohibited | 25 km/h | **`COMPLIANT`** | Silence Zone: Horn prohibition compliant (no horn sounded) |
| `school ahead.png` | School Ahead | 30 km/h | **`WARNING`** | Caution: School Ahead. Drive attentively |
| `no entry.png` | No Entry | 20 km/h | **`WARNING`** | Caution: No Entry. Path verification requires map context |

---

## 10. Limitations & Academic Integrity

In compliance with the project specifications, the prototype's operational boundaries must be explicitly reported:
1. **Academic Prototype Status:** This system is an academic proof-of-concept designed to illustrate context-aware ADAS architectures. It is **not** a validated automotive safety system certified for autonomous vehicle actuation.
2. **Simulated Context vs. Real In-Vehicle Telemetry:** In the current prototype, vehicle velocity, steering angle, horn actuation, and pedestrian presence are simulated via cockpit UI controls rather than connected vehicle hardware (OBD-II CAN-bus, steering angle sensors, RTK GPS).
3. **Absence of HD Map Localization:** For signs such as *No Entry* and *Give Way*, true compliance requires localized road topology vectors and intersection priority maps. The system transparently flags these signs with `context_note: "Compliance not verified: sensor unavailable"`.
4. **Lighting Extremes:** While CLAHE contrast enhancement aids dark conditions, detection recall drops under extreme headlight glare and heavy nighttime unlit rural roads.

---

## 11. System Operation & Reproducibility Guide

### 11.1 Prerequisites
```powershell
# Clone the repository
git clone https://github.com/Keerthu-1811/TrafficSign.git
cd TrafficSign

# Install core dependencies
pip install -r requirements.txt
```

### 11.2 Running the Automated Test Suite
```powershell
python -m unittest discover -s tests
```

### 11.3 Launching the ADAS Digital Cockpit Web Application (Recommended)
```powershell
python web_server.py 8080
```
Open **`http://localhost:8080`** in any web browser:
* Select any of the **59 pre-loaded sign photos** from the *Test Photos Library* dropdown.
* Or drag and drop any custom traffic sign image into the upload box.
* Adjust simulated speed, test the **HONK HORN** button in silence zones, toggle pedestrian crossings, or adjust steering angles to observe real-time rule evaluations.

### 11.4 Running the Real-Time Webcam / Video Pipeline
```powershell
python realtime_detection.py --source 0 --speed 30
```
* Use `W` / `S` keys to accelerate or decelerate ($\pm 5\text{ km/h}$).
* Press `0` to halt the vehicle ($0\text{ km/h}$) at Stop signs.
* Press `R` to reset context state.
* Press `V` to toggle voice audio announcements.

### 11.5 Running the Batch Test Evaluation
```powershell
python evaluate_compliance_batch.py
```
Outputs are written with full HUD overlays to [`results/compliance_eval/`](file:///d:/Antigravity/TrafficSign/results/compliance_eval/).

---

## Summary of Completed Milestones

| Milestone | Deliverable | Status |
|:---|:---|:---:|
| **M1: Perception Layer** | YOLOv8n fine-tuned on 15 IRC classes (`models/best.pt`) | **Completed** |
| **M2: Temporal Tracking** | Sliding window smoothing & EMA tracker (`TemporalSmoother`) | **Completed** |
| **M3: Driving Context Manager** | Persistent state engine for limits, stop timing & telemetry | **Completed** |
| **M4: Rule Decision Engine** | Speed, stop, turn, horn & pedestrian rules (`decision_engine.py`) | **Completed** |
| **M5: Audio Alert System** | Non-blocking voice worker with cooldown suppression | **Completed** |
| **M6: Verification Suite** | 23 automated unit tests with 100% pass rate | **Completed** |
| **M7: ADAS Web Cockpit** | Interactive digital cockpit UI with SVG gauge, IRC badges & controls | **Completed** |
| **M8: Dataset Expansion** | 59 categorized test images covering all 15 IRC classes | **Completed** |
| **M9: Version Control** | All source code, assets & documentation pushed to GitHub | **Completed** |

*Report generated and approved for project documentation and academic review.*
