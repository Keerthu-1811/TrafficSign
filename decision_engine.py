"""
Rule-Based Driver Compliance Decision Engine for Indian Traffic Signs.
Evaluates visual traffic sign detections against multi-modal driving context:
- Speed comparison against active limit
- Stop sign duration tracking
- Turn & steering maneuver compliance (Left Turn, Right Turn, U-Turn)
- Acoustic silence zone enforcement (Horn Prohibited)
- Pedestrian crossing right-of-way yielding
"""

import time
from typing import Optional, Dict, Any
from context_manager import (
    DrivingContextManager,
    SPEED_LIMIT_MAP,
    STOP_SIGN_ID,
    TURN_SIGN_IDS,
    HORN_PROHIBITED_ID,
    PEDESTRIAN_CROSSING_ID,
)

# Complete 15-class mapping aligned with YOLOv8 model
SIGN_CLASSES = [
    "Stop",                 # 0
    "No Entry",             # 1
    "Speed Limit 20",       # 2
    "Speed Limit 40",       # 3
    "Speed Limit 60",       # 4
    "Speed Limit 80",       # 5
    "Give Way",             # 6
    "School Ahead",         # 7
    "Pedestrian Crossing",  # 8
    "Left Turn",            # 9
    "Right Turn",           # 10
    "U-Turn",               # 11
    "Horn Prohibited",      # 12
    "Parking",              # 13
    "Dangerous Curve",      # 14
]

# Remaining caution signs without direct dedicated sensors yet
ADVISORY_SIGN_DESCRIPTIONS = {
    1: ("No Entry", "Do not enter this roadway. Vehicle path/heading verification requires GPS/map context."),
    6: ("Give Way", "Yield right-of-way to oncoming traffic. Yielding compliance requires surrounding vehicle context."),
    7: ("School Ahead", "Caution: School zone. Drive attentively and watch for children."),
    13: ("Parking", "Designated parking area. Parking compliance requires stationary location context."),
    14: ("Dangerous Curve", "Caution: Sharp curve ahead. Reduce speed and stay in lane."),
}


class ComplianceStatus:
    COMPLIANT = "COMPLIANT"
    VIOLATION = "VIOLATION"
    WARNING = "WARNING"
    CHECK_REQUIRED = "CHECK_REQUIRED"
    CANNOT_VERIFY = "CANNOT_VERIFY"
    UNCERTAIN = "UNCERTAIN"
    NO_ACTION = "NO_ACTION"


class ComplianceDecisionEngine:
    """
    Evaluates driver compliance against Indian traffic signs using multi-modal driving context.
    """

    def __init__(
        self,
        context_manager: Optional[DrivingContextManager] = None,
        min_confidence: float = 0.70,
        stop_duration_required: float = 2.0,
        alert_cooldown_seconds: float = 3.0,
    ):
        self.context = context_manager or DrivingContextManager(stop_duration_required=stop_duration_required)
        self.min_confidence = min_confidence
        self.stop_duration_required = stop_duration_required
        self.alert_cooldown = alert_cooldown_seconds

        # Alert de-duplication state
        self.last_alert_message: Optional[str] = None
        self.last_alert_time: float = 0.0

    def check(
        self,
        sign_id: Optional[int] = None,
        speed_kmh: Optional[float] = None,
        confidence: float = 0.0,
        stopped_seconds: Optional[float] = None,
        heading_deg: Optional[float] = None,
        horn_active: Optional[bool] = None,
        pedestrian_present: Optional[bool] = None,
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Main multi-modal compliance evaluation entry point.
        """
        now = time.time() if timestamp is None else timestamp

        # Update telemetry in context manager
        if speed_kmh is not None:
            self.context.set_speed(speed_kmh, timestamp=now)
        if heading_deg is not None:
            self.context.set_heading(heading_deg)
        if horn_active is not None:
            self.context.set_horn(horn_active)
        if pedestrian_present is not None:
            self.context.set_pedestrian_present(pedestrian_present)

        current_speed = self.context.current_speed_kmh
        active_limit = self.context.active_speed_limit
        is_simulated = self.context.is_simulated_speed
        current_heading = self.context.current_heading_deg
        is_horn_active = self.context.horn_active
        is_ped_present = self.context.pedestrian_present

        sign_name = SIGN_CLASSES[sign_id] if (sign_id is not None and 0 <= sign_id < len(SIGN_CLASSES)) else None

        # 1. Prediction Confidence Gate
        if sign_id is not None and confidence < self.min_confidence:
            return self._build_result(
                status=ComplianceStatus.UNCERTAIN,
                message=f"Uncertain detection for sign ID {sign_id} (confidence: {confidence:.2f} < {self.min_confidence:.2f})",
                sign_id=sign_id,
                sign_name=sign_name,
                speed_kmh=current_speed,
                active_speed_limit=active_limit,
                confidence=confidence,
                is_speed_simulated=is_simulated,
                timestamp=now,
            )

        # 2. Speed Limit Signs (2, 3, 4, 5)
        if sign_id is not None and sign_id in SPEED_LIMIT_MAP and confidence >= self.min_confidence:
            active_limit = self.context.update_speed_limit(sign_id)

        # 3. Stop Sign (Class 0)
        if sign_id == STOP_SIGN_ID and confidence >= self.min_confidence:
            self.context.register_stop_sign_detection(timestamp=now)

        if self.context.stop_sign_active or (sign_id == STOP_SIGN_ID and confidence >= self.min_confidence):
            stop_duration = stopped_seconds if stopped_seconds is not None else self.context.total_stopped_duration

            if stopped_seconds is None and not self.context.speed_history and current_speed > 0:
                return self._build_result(
                    status=ComplianceStatus.CANNOT_VERIFY,
                    message="Stop sign detected; stop compliance cannot be verified without temporal speed tracking.",
                    sign_id=0,
                    sign_name="Stop",
                    speed_kmh=current_speed,
                    active_speed_limit=active_limit,
                    confidence=confidence,
                    is_speed_simulated=is_simulated,
                    timestamp=now,
                )

            if stop_duration >= self.stop_duration_required:
                self.context.stop_satisfied = True
                return self._build_result(
                    status=ComplianceStatus.COMPLIANT,
                    message=f"Stop sign requirement satisfied: vehicle stopped for {stop_duration:.1f}s (required: {self.stop_duration_required:.1f}s).",
                    sign_id=0,
                    sign_name="Stop",
                    speed_kmh=current_speed,
                    active_speed_limit=active_limit,
                    confidence=confidence,
                    is_speed_simulated=is_simulated,
                    timestamp=now,
                    context_note="Temporal speed tracker verified vehicle velocity <= 1 km/h for mandated duration.",
                )
            elif current_speed <= 1.0 and stop_duration > 0.0:
                return self._build_result(
                    status=ComplianceStatus.CHECK_REQUIRED,
                    message=f"Stop check in progress: stopped {stop_duration:.1f}s / {self.stop_duration_required:.1f}s.",
                    sign_id=0,
                    sign_name="Stop",
                    speed_kmh=current_speed,
                    active_speed_limit=active_limit,
                    confidence=confidence,
                    is_speed_simulated=is_simulated,
                    timestamp=now,
                    context_note="Vehicle halted; holding stop duration to reach required threshold.",
                )
            else:
                return self._build_result(
                    status=ComplianceStatus.CHECK_REQUIRED,
                    message=f"Stop sign active: full stop required ({self.stop_duration_required:.1f}s). Current speed: {current_speed:.0f} km/h.",
                    sign_id=0,
                    sign_name="Stop",
                    speed_kmh=current_speed,
                    active_speed_limit=active_limit,
                    confidence=confidence,
                    is_speed_simulated=is_simulated,
                    timestamp=now,
                    context_note="Stop event registered; vehicle deceleration required.",
                )

        # 4. Horn Prohibited / Silence Zone (Class 12)
        if sign_id == HORN_PROHIBITED_ID and confidence >= self.min_confidence:
            if is_horn_active:
                return self._build_result(
                    status=ComplianceStatus.VIOLATION,
                    message="VIOLATION: Illegal horn activation in Silence Zone!",
                    sign_id=12,
                    sign_name="Horn Prohibited",
                    speed_kmh=current_speed,
                    active_speed_limit=active_limit,
                    confidence=confidence,
                    is_speed_simulated=is_simulated,
                    timestamp=now,
                    context_note="Acoustic sensor detected horn honk inside restricted silence zone.",
                )
            else:
                if active_limit is not None and current_speed > active_limit:
                    return self._build_result(
                        status=ComplianceStatus.VIOLATION,
                        message=f"Speeding: {current_speed:.0f} km/h (limit: {active_limit} km/h) in Silence Zone.",
                        sign_id=12,
                        sign_name="Horn Prohibited",
                        speed_kmh=current_speed,
                        active_speed_limit=active_limit,
                        confidence=confidence,
                        is_speed_simulated=is_simulated,
                        timestamp=now,
                        context_note="Horn quiet, but speed limit exceeded.",
                    )
                return self._build_result(
                    status=ComplianceStatus.COMPLIANT,
                    message="Silence Zone: Horn prohibition compliant (no horn sounded).",
                    sign_id=12,
                    sign_name="Horn Prohibited",
                    speed_kmh=current_speed,
                    active_speed_limit=active_limit,
                    confidence=confidence,
                    is_speed_simulated=is_simulated,
                    timestamp=now,
                    context_note="Horn sensor quiet. Silence zone compliance maintained.",
                )

        # 5. Pedestrian Crossing Yielding (Class 8)
        if sign_id == PEDESTRIAN_CROSSING_ID and confidence >= self.min_confidence:
            if is_ped_present:
                if current_speed <= 5.0:
                    return self._build_result(
                        status=ComplianceStatus.COMPLIANT,
                        message=f"Yielded to pedestrian: vehicle decelerated to {current_speed:.0f} km/h.",
                        sign_id=8,
                        sign_name="Pedestrian Crossing",
                        speed_kmh=current_speed,
                        active_speed_limit=active_limit,
                        confidence=confidence,
                        is_speed_simulated=is_simulated,
                        timestamp=now,
                        context_note="Zebra crossing occupied; driver decelerated/halted to yield right-of-way.",
                    )
                else:
                    return self._build_result(
                        status=ComplianceStatus.VIOLATION,
                        message=f"VIOLATION: Failure to yield to pedestrian at crossing! (Speed: {current_speed:.0f} km/h).",
                        sign_id=8,
                        sign_name="Pedestrian Crossing",
                        speed_kmh=current_speed,
                        active_speed_limit=active_limit,
                        confidence=confidence,
                        is_speed_simulated=is_simulated,
                        timestamp=now,
                        context_note="Pedestrian present on crossing. Vehicle failed to decelerate/yield.",
                    )
            else:
                if active_limit is not None and current_speed > active_limit:
                    return self._build_result(
                        status=ComplianceStatus.VIOLATION,
                        message=f"Speeding: {current_speed:.0f} km/h (limit: {active_limit} km/h) at crossing.",
                        sign_id=8,
                        sign_name="Pedestrian Crossing",
                        speed_kmh=current_speed,
                        active_speed_limit=active_limit,
                        confidence=confidence,
                        is_speed_simulated=is_simulated,
                        timestamp=now,
                        context_note="Crossing clear of pedestrians, but vehicle exceeded speed limit.",
                    )
                return self._build_result(
                    status=ComplianceStatus.COMPLIANT,
                    message="Pedestrian Crossing clear: roadway unobstructed, speed compliant.",
                    sign_id=8,
                    sign_name="Pedestrian Crossing",
                    speed_kmh=current_speed,
                    active_speed_limit=active_limit,
                    confidence=confidence,
                    is_speed_simulated=is_simulated,
                    timestamp=now,
                    context_note="No pedestrians detected on zebra crossing. Proceeding safely.",
                )

        # 6. Turn & Heading Compliance (Classes 9, 10, 11)
        if sign_id in TURN_SIGN_IDS and confidence >= self.min_confidence:
            turn_name = TURN_SIGN_IDS[sign_id]

            if sign_id == 9:  # Left Turn
                if current_heading <= -30.0:
                    return self._build_result(
                        status=ComplianceStatus.COMPLIANT,
                        message=f"Left turn executed successfully (heading: {current_heading:.0f}°).",
                        sign_id=9,
                        sign_name=turn_name,
                        speed_kmh=current_speed,
                        active_speed_limit=active_limit,
                        confidence=confidence,
                        is_speed_simulated=is_simulated,
                        timestamp=now,
                        context_note="Vehicle steering trajectory matched mandated left turn.",
                    )
                else:
                    return self._build_result(
                        status=ComplianceStatus.CHECK_REQUIRED,
                        message=f"Mandatory Left Turn active: heading {current_heading:.0f}°. Left steer required.",
                        sign_id=9,
                        sign_name=turn_name,
                        speed_kmh=current_speed,
                        active_speed_limit=active_limit,
                        confidence=confidence,
                        is_speed_simulated=is_simulated,
                        timestamp=now,
                        context_note="Vehicle steering currently straight. Left turn maneuver pending.",
                    )

            elif sign_id == 10:  # Right Turn
                if current_heading >= 30.0:
                    return self._build_result(
                        status=ComplianceStatus.COMPLIANT,
                        message=f"Right turn executed successfully (heading: {current_heading:.0f}°).",
                        sign_id=10,
                        sign_name=turn_name,
                        speed_kmh=current_speed,
                        active_speed_limit=active_limit,
                        confidence=confidence,
                        is_speed_simulated=is_simulated,
                        timestamp=now,
                        context_note="Vehicle steering trajectory matched mandated right turn.",
                    )
                else:
                    return self._build_result(
                        status=ComplianceStatus.CHECK_REQUIRED,
                        message=f"Mandatory Right Turn active: heading {current_heading:.0f}°. Right steer required.",
                        sign_id=10,
                        sign_name=turn_name,
                        speed_kmh=current_speed,
                        active_speed_limit=active_limit,
                        confidence=confidence,
                        is_speed_simulated=is_simulated,
                        timestamp=now,
                        context_note="Vehicle steering currently straight. Right turn maneuver pending.",
                    )

            elif sign_id == 11:  # U-Turn
                if abs(current_heading) >= 140.0:
                    return self._build_result(
                        status=ComplianceStatus.COMPLIANT,
                        message=f"U-Turn completed successfully (heading: {current_heading:.0f}°).",
                        sign_id=11,
                        sign_name=turn_name,
                        speed_kmh=current_speed,
                        active_speed_limit=active_limit,
                        confidence=confidence,
                        is_speed_simulated=is_simulated,
                        timestamp=now,
                        context_note="Vehicle completed 180° heading reversal.",
                    )
                else:
                    return self._build_result(
                        status=ComplianceStatus.CHECK_REQUIRED,
                        message=f"U-Turn active: heading {current_heading:.0f}°. 180° reversal pending.",
                        sign_id=11,
                        sign_name=turn_name,
                        speed_kmh=current_speed,
                        active_speed_limit=active_limit,
                        confidence=confidence,
                        is_speed_simulated=is_simulated,
                        timestamp=now,
                        context_note="U-Turn trajectory reversal in progress.",
                    )

        # 7. Remaining Advisory Signs (1, 6, 7, 13, 14)
        if sign_id is not None and sign_id in ADVISORY_SIGN_DESCRIPTIONS and confidence >= self.min_confidence:
            name, desc = ADVISORY_SIGN_DESCRIPTIONS[sign_id]
            if active_limit is not None and current_speed > active_limit:
                return self._build_result(
                    status=ComplianceStatus.VIOLATION,
                    message=f"Speeding: {current_speed:.0f} km/h (limit: {active_limit} km/h) in {name} zone.",
                    sign_id=sign_id,
                    sign_name=name,
                    speed_kmh=current_speed,
                    active_speed_limit=active_limit,
                    confidence=confidence,
                    is_speed_simulated=is_simulated,
                    timestamp=now,
                    context_note=f"{desc} (Compliance not verified: sensor unavailable)",
                )

            return self._build_result(
                status=ComplianceStatus.WARNING,
                message=f"Caution: {name}. {desc}",
                sign_id=sign_id,
                sign_name=name,
                speed_kmh=current_speed,
                active_speed_limit=active_limit,
                confidence=confidence,
                is_speed_simulated=is_simulated,
                timestamp=now,
                context_note="Compliance not verified: context/sensor unavailable",
            )

        # 8. Speed Limit Compliance Check (active limit persists across frames)
        if active_limit is not None:
            if current_speed > active_limit:
                return self._build_result(
                    status=ComplianceStatus.VIOLATION,
                    message=f"Speeding: {current_speed:.0f} km/h (limit: {active_limit} km/h)",
                    sign_id=sign_id,
                    sign_name=sign_name,
                    speed_kmh=current_speed,
                    active_speed_limit=active_limit,
                    confidence=confidence,
                    is_speed_simulated=is_simulated,
                    timestamp=now,
                )
            else:
                return self._build_result(
                    status=ComplianceStatus.COMPLIANT,
                    message=f"Speed compliant: {current_speed:.0f} km/h (limit: {active_limit} km/h)",
                    sign_id=sign_id,
                    sign_name=sign_name,
                    speed_kmh=current_speed,
                    active_speed_limit=active_limit,
                    confidence=confidence,
                    is_speed_simulated=is_simulated,
                    timestamp=now,
                )

        # 9. Default / No active rules
        return self._build_result(
            status=ComplianceStatus.NO_ACTION,
            message="No active traffic rules or speed limits configured.",
            sign_id=sign_id,
            sign_name=sign_name,
            speed_kmh=current_speed,
            active_speed_limit=None,
            confidence=confidence,
            is_speed_simulated=is_simulated,
            timestamp=now,
        )

    def _build_result(
        self,
        status: str,
        message: str,
        sign_id: Optional[int],
        sign_name: Optional[str],
        speed_kmh: float,
        active_speed_limit: Optional[int],
        confidence: float,
        is_speed_simulated: bool,
        timestamp: float,
        context_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Constructs standardized result dictionary with alert suppression logic."""
        should_alert = False
        is_alertable = status in (ComplianceStatus.VIOLATION, ComplianceStatus.WARNING, ComplianceStatus.CHECK_REQUIRED)

        if is_alertable:
            elapsed = timestamp - self.last_alert_time
            if message != self.last_alert_message or elapsed >= self.alert_cooldown:
                should_alert = True
                self.last_alert_message = message
                self.last_alert_time = timestamp

        res = {
            "status": status,
            "message": message,
            "sign_id": sign_id,
            "sign_name": sign_name,
            "speed_kmh": round(speed_kmh, 1),
            "active_speed_limit": active_speed_limit,
            "confidence": round(confidence, 3),
            "is_speed_simulated": is_speed_simulated,
            "heading_deg": round(self.context.current_heading_deg, 1),
            "horn_active": self.context.horn_active,
            "pedestrian_present": self.context.pedestrian_present,
            "should_alert": should_alert,
        }
        if context_note:
            res["context_note"] = context_note
        return res
