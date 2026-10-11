# Implementation Plan: Context-Aware Indian Traffic Sign Recognition and Driver Compliance

## 1. Project objective

Extend the existing Indian traffic-sign recognition model with a simple driver-compliance module. The system should:

1. Detect/classify a traffic sign using the existing trained model.
2. Track the currently applicable speed limit.
3. compare the supplied vehicle speed against that limit.
4. Check a Stop sign using vehicle-stop duration when suitable context is available.
5. Display compliance status and issue alerts.
6. Clearly report when compliance cannot be verified because the required sensor/context is unavailable.

**Recommended first implementation:** a camera/video + existing model + simulated vehicle-speed input + rule-based decision engine + dashboard/voice alert. Real GPS/OBD-II speed and advanced behavior checks can be added later.

This is an academic prototype, not a validated road-safety system.

---

## 2. Existing traffic-sign classes

Keep the class IDs and order exactly aligned with the trained model:

| ID | Class |
|---:|---|
| 0 | Stop |
| 1 | No Entry |
| 2 | Speed Limit 20 |
| 3 | Speed Limit 40 |
| 4 | Speed Limit 60 |
| 5 | Speed Limit 80 |
| 6 | Give Way |
| 7 | School Ahead |
| 8 | Pedestrian |
| 9 | Left Turn |
| 10 | Right Turn |
| 11 | U-Turn |
| 12 | Horn Prohibited |
| 13 | Parking |
| 14 | Dangerous Curve |

Before integration, verify the model's output index-to-class mapping. A correct model with a mismatched class list will produce incorrect rules.

---

## 3. High-level architecture

```text
Camera / Video
      |
      v
Existing Traffic-Sign Model
(class ID + confidence)
      |
      v
Prediction Stabilization
(confirm a sign across multiple frames)
      |
      v
Context Manager
(active speed limit, vehicle speed, stop duration,
 sign event/time and optional vehicle direction)
      |
      v
Rule-Based Compliance Engine
      |
      +----> COMPLIANT
      +----> VIOLATION
      +----> WARNING
      +----> CHECK_REQUIRED
      +----> CANNOT_VERIFY / UNCERTAIN
      |
      v
Dashboard + Optional Voice Alert
```

### Main design principle

Traffic-sign recognition alone does not prove driver compliance. Each rule needs the appropriate driving-context input. Do not label behavior as a violation if the system cannot observe or infer it reliably.

---

## 4. Scope: what to implement for each class

| Class ID(s) | Sign(s) | Initial implementation |
|---|---|---|
| 2, 3, 4, 5 | Speed Limit 20/40/60/80 | Compare vehicle speed with the active limit. |
| 0 | Stop | Measure speed over time; report a stop as satisfied only if the vehicle stopped near the relevant sign for the chosen duration. |
| 1 | No Entry | Warning only. Verifying entry needs location, road direction and vehicle-path context. |
| 6 | Give Way | Warning only. Verifying yielding requires right-of-way and traffic context. |
| 7 | School Ahead | Caution warning. Any configured speed rule must be documented as a project assumption, not inferred from the sign alone. |
| 8 | Pedestrian | Caution warning. Verifying yielding requires pedestrian detection and motion/context analysis. |
| 9, 10, 11 | Left Turn, Right Turn, U-Turn | Warning first. Later compare intended/required direction with vehicle heading or path. |
| 12 | Horn Prohibited | Warning first. Later check horn activation within a known restricted zone. |
| 13 | Parking | Warning first. Later define the sign's exact meaning and use location/vehicle state to check it. |
| 14 | Dangerous Curve | Caution warning. Actual compliance checks need road geometry and vehicle behavior. |

**Minimum viable project:** speed-limit compliance, a basic Stop-sign workflow, a visual dashboard and optional voice alerts. The remaining classes should still be recognized and displayed, but marked as warning-only or not verified.

---

## 5. Suggested project structure

Adapt names to the current repository rather than duplicating files unnecessarily.

```text
traffic-sign-project/
├── model/
│   └── existing trained model and class mapping
├── realtime_detection.py       # Existing camera/video inference entry point
├── decision_engine.py           # Compliance rules
├── context_manager.py           # Active limit and vehicle-context state
├── dashboard.py                 # Optional Streamlit dashboard
├── voice_alert.py                # Optional text-to-speech
├── tests/
│   └── test_decision_engine.py
├── requirements.txt
└── README.md
```

For a very small prototype, the context manager can initially live inside `decision_engine.py`. Split it out only when the integration becomes difficult to maintain.

---

## 6. Phase 1 — Verify existing model output

### Tasks

1. Run the trained model on a few known images or a short video.
2. Confirm that the output is a class ID from 0 to 14.
3. Obtain the prediction confidence.
4. Verify that output index 2 means Speed Limit 20, index 3 means Speed Limit 40, and so on.
5. Record how preprocessing is performed: image size, colour order, normalization and any other model-specific requirements.

### Expected interface

The model integration should produce values similar to:

```python
predicted_class = 2
confidence = 0.95
```

If the model returns a probability array:

```python
predicted_class = int(predictions.argmax())
confidence = float(predictions.max())
```

This example assumes `predictions` contains probabilities for the 15 classes. If it returns logits, apply the appropriate softmax first. Preserve the preprocessing and output conventions used during training.

### Important

Do not retrain the model just to add compliance checking. Reuse the trained model unless testing reveals a separate recognition problem.

---

## 7. Phase 2 — Build the rule-based decision engine

Create `decision_engine.py`. Its job is to receive the detected sign, confidence, vehicle speed and any available stop-duration/context data, then return a structured result.

### Required rules

#### A. Speed limits

```python
SPEED_LIMITS = {
    2: 20,
    3: 40,
    4: 60,
    5: 80,
}
```

- When a stable speed-limit sign is confirmed, update the active limit.
- Compare speed in km/h with the active limit on every processing cycle.
- If speed is greater than the active limit, return `VIOLATION`.
- Otherwise return `COMPLIANT` for the speed rule.
- Keep the active limit after the sign leaves the camera view. For the prototype, reset it at the end of a test/drive or when a clearly defined reset condition occurs.
- Do not clear the active limit merely because a frame has no sign prediction.

#### B. Stop sign

- Detect class 0 and create a Stop-sign event.
- Obtain vehicle speed over time from a simulator or speed source.
- Check whether the vehicle reaches approximately zero speed for a configured duration (for example, 2 seconds).
- Associate the stop with the relevant sign/approach if possible.
- If only a sign classification is available, do not claim the driver complied or violated; return `CHECK_REQUIRED` or `CANNOT_VERIFY`.

The example duration is a configurable demo assumption, not a universal legal definition.

#### C. Other classes

Return a caution `WARNING` and say that compliance is not verified. Do not make unsupported claims about No Entry, Give Way, pedestrian yielding, turning, horn use or parking without the corresponding context input.

#### D. Prediction confidence

- Start with a configurable threshold such as 0.70.
- If confidence is below the threshold, return `UNCERTAIN`.
- Treat the threshold as an initial value to test, not a proven optimum.

#### E. Alert suppression

- Avoid repeating the same voice warning on every video frame.
- Suppress identical alerts for a short cooldown (for example, 3 seconds), or trigger only when a new violation event begins.
- Keep dashboard status updated even while voice repeats are suppressed.

### Suggested result format

```python
{
    "status": "VIOLATION",
    "message": "Speeding: 30 km/h (limit: 20 km/h)",
    "sign_id": 2,
    "speed_kmh": 30,
    "active_speed_limit": 20
}
```

Possible statuses:

- `COMPLIANT`
- `VIOLATION`
- `WARNING`
- `CHECK_REQUIRED`
- `CANNOT_VERIFY`
- `UNCERTAIN`
- `NO_ACTION`

Keep the result fields consistent so the dashboard can display them without parsing message text.

---

## 8. Phase 3 — Add a simulated speed input

Start with a simulated speed because it is simple, reproducible and does not require vehicle hardware.

### Options

- **Fastest:** set `vehicle_speed` manually in a test script.
- **Interactive demo:** use a Streamlit slider from 0 to 120 km/h.
- **Keyboard demo:** use keys to increase/decrease speed during a video.
- **Later hardware:** use GPS speed or a suitable OBD-II adapter.

Example:

```python
vehicle_speed = 30.0

result = checker.check(
    sign_id=2,
    speed_kmh=vehicle_speed,
    confidence=0.95
)
```

Expected result: a 20 km/h limit with a simulated speed of 30 km/h should produce `VIOLATION`.

A simulated input demonstrates the decision logic, not real-world sensing accuracy. Label it as simulated in the dashboard and project report.

---

## 9. Phase 4 — Integrate with the live model

In the existing camera/video inference loop:

1. Read a frame.
2. Run the existing preprocessing and model inference.
3. Obtain predicted class and confidence.
4. Stabilize the prediction across multiple frames.
5. Update the active sign/context state only when a new sign is confirmed.
6. Obtain the current vehicle speed from the simulator or actual source.
7. Call the compliance engine on every cycle so the active limit continues to be checked.
8. Display the sign, confidence, speed, active limit and compliance result.
9. Trigger voice alerts only for new alert events.

Example integration pattern:

```python
result = checker.check(
    sign_id=stable_sign_id,
    speed_kmh=current_speed_kmh,
    confidence=stable_confidence,
    stopped_seconds=stopped_seconds
)
```

The parameter names must match the final `decision_engine.py` implementation.

### Prediction stabilization

A sign can be recognized across many consecutive frames. Do not treat each frame as a brand-new sign event.

Simple method:
- Keep the last 5 predictions.
- Use the most frequent class or require the same class in a configured number of frames.
- Require sufficient confidence.
- Create a new sign event when the stable class changes or a new sign is detected after a suitable gap.

For a prototype, a short rolling window is sufficient. More advanced tracking is optional.

---

## 10. Phase 5 — Dashboard

A Streamlit dashboard is a practical option if the project is Python-based. Alternatively, display the status directly in the existing OpenCV video window.

### Show these fields

- Camera/video frame
- Detected sign name and class ID
- Model confidence
- Vehicle speed, clearly labelled as simulated or real
- Active speed limit
- Compliance status
- Alert message
- Whether the result is verified, warning-only or uncertain

### Suggested status presentation

- `COMPLIANT` — speed is within the configured limit.
- `VIOLATION` — speed exceeds the active configured limit.
- `WARNING` — sign detected, but no behavior verdict is available.
- `CHECK_REQUIRED` — a context check is in progress.
- `CANNOT_VERIFY` — necessary data is unavailable.
- `UNCERTAIN` — model confidence is too low.

Avoid showing `COMPLIANT` for the entire driving situation when only the speed rule has been checked. Make the scope explicit, for example: “Speed rule: compliant.”

---

## 11. Phase 6 — Voice alerts (optional)

Install `pyttsx3` if offline text-to-speech is suitable:

```bash
pip install pyttsx3
```

Example:

```python
import pyttsx3

engine = pyttsx3.init()

def speak_alert(message):
    engine.say(message)
    engine.runAndWait()
```

Call it only when a new violation or warning event occurs. Repeatedly calling `runAndWait()` from the camera loop can block video processing, so use a non-blocking queue or a separate worker if the live feed becomes slow.

Voice alerts should be concise, for example:
- “Speed limit 20. Reduce speed.”
- “Stop sign ahead.”
- “Pedestrian warning.”

These are demonstration alerts; they should not be treated as validated safety instructions.

---

## 12. Phase 7 — Testing

Write unit tests for the decision engine separately from the camera and model.

### Speed-limit test cases

| Test | Active sign/limit | Simulated speed | Expected |
|---|---|---:|---|
| 1 | Speed Limit 20 | 15 km/h | `COMPLIANT` |
| 2 | Speed Limit 20 | 30 km/h | `VIOLATION` |
| 3 | Speed Limit 40 | 40 km/h | Within configured limit |
| 4 | Speed Limit 40 | 45 km/h | `VIOLATION` |
| 5 | Speed Limit 60 | 55 km/h | `COMPLIANT` |
| 6 | Speed Limit 80 | 90 km/h | `VIOLATION` |
| 7 | No reliable prediction | Any speed | `UNCERTAIN` for the prediction; do not invent a new limit |
| 8 | No new sign in frame | Speed above retained limit | Still check the active limit |

Define the comparison policy clearly. The simple example uses `speed > limit`; it does not add a tolerance margin.

### Stop-sign test cases

- Stop sign detected, no speed-duration input: `CANNOT_VERIFY` or `CHECK_REQUIRED`.
- Vehicle speed reaches zero for less than the configured duration: still checking.
- Vehicle stops for the configured duration near the relevant sign: mark the Stop requirement satisfied.
- Vehicle stops far away or the sign is no longer relevant: do not count it as compliance without suitable event/location association.

### General tests

- Every class ID maps to the correct name.
- Low-confidence predictions do not activate new rules.
- Repeated detections do not repeatedly trigger voice alerts.
- A newly confirmed speed-limit sign updates the active limit.
- The active limit remains in effect when the sign is no longer visible.
- The dashboard clearly labels simulated inputs.

---

## 13. Phase 8 — Optional extensions after the MVP works

Implement these only after the speed and Stop-sign workflows are reliable.

1. **GPS speed:** replace the simulated speed with speed from a GPS receiver/device. Consider latency and measurement noise.
2. **OBD-II:** obtain vehicle speed from a compatible adapter and vehicle.
3. **Stop detection:** use speed history plus sign-event timing and, if possible, sign/vehicle distance.
4. **Turn compliance:** estimate vehicle heading/path and compare it with the required maneuver.
5. **Pedestrian yielding:** add pedestrian detection/tracking and define a meaningful yielding criterion.
6. **No Entry:** use road direction, location/map context and vehicle trajectory.
7. **Horn prohibited:** use a valid horn-activation signal and a defined restricted zone.
8. **Parking:** define the exact sign semantics and restricted-zone boundaries before checking behavior.
9. **Dangerous curve:** use road geometry and vehicle speed; do not infer compliance from the sign alone.

Do not add these extensions just to claim all 15 signs are compliance-checked. A transparent warning-only result is better than an unsupported verdict.

---

## 14. Recommended development order

### Milestone 1 — Rule engine
- Create `decision_engine.py`.
- Implement the four speed limits and confidence handling.
- Test with manually supplied class IDs and speed values.

### Milestone 2 — Simulation
- Add a slider or keyboard input for speed.
- Demonstrate compliant and violation cases.

### Milestone 3 — Model integration
- Connect the trained model's class ID/confidence to the engine.
- Add multi-frame prediction stabilization.
- Keep the active speed limit across frames.

### Milestone 4 — Stop workflow
- Add speed history and stop-duration tracking.
- Clearly handle missing spatial/context data.

### Milestone 5 — Interface and alerts
- Display all required fields.
- Add optional voice alerts and cooldown logic.

### Milestone 6 — Evaluation and documentation
- Run the test cases.
- Record results, limitations and assumptions.
- Prepare screenshots/video of the demo.

---

## 15. Demonstration scenario for the project review

1. Start the camera/video and show the model detecting Speed Limit 20.
2. Set simulated speed to 15 km/h; show `COMPLIANT`.
3. Increase speed to 30 km/h; show `VIOLATION` and optionally play a voice alert.
4. Let the sign leave the frame; verify the active limit remains 20 km/h.
5. Detect Speed Limit 40; verify the active limit changes.
6. Detect a Stop sign; show that the system starts a stop check and does not claim success until the available speed/context data supports it.
7. Detect another sign, such as Pedestrian or No Entry; show a warning and `Compliance not verified`.

This demonstrates perception, context tracking, a decision engine and driver feedback in one coherent pipeline.

---

## 16. Definition of done

The minimum implementation is complete when:

- [ ] The existing model still recognizes all 15 classes.
- [ ] The class mapping is verified.
- [ ] Speed-limit signs update the active limit.
- [ ] The engine correctly reports compliant/violation for the four limits using simulated speed.
- [ ] The limit remains active after the sign leaves the frame.
- [ ] Low-confidence predictions are handled safely.
- [ ] Stop-sign behavior is checked only when sufficient context is available.
- [ ] Other classes produce honest warnings rather than false compliance verdicts.
- [ ] The dashboard shows sign, confidence, speed, active limit and status.
- [ ] Repeated voice alerts are controlled if voice is enabled.
- [ ] Test results and limitations are documented.

## 17. What to explain in the report

Describe the contribution as a **context-aware, rule-based driver-compliance layer on top of an existing traffic-sign recognition model**. Explain that the ML model handles visual sign classification while the decision engine uses driving context to evaluate selected rules.

Report separately:
- Classification performance of the existing model.
- Compliance-engine test results under simulated inputs.
- End-to-end demonstration results.
- Limitations: simulated speed, missing road localization, incomplete sign-context tracking, and unimplemented checks for some classes.

Do not report simulated compliance tests as real-road validation.
