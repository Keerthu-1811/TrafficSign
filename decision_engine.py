"""
Rule-Based Driver Compliance Decision Engine for Indian Traffic Signs.
Evaluates visual traffic sign detections against driving context (speed, stop duration)
and produces structured compliance verdicts.
"""

import time
from typing import Optional, Dict, Any
from context_manager import DrivingContextManager, SPEED_LIMIT_MAP, STOP_SIGN_ID

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

# Sign IDs requiring caution warnings with context notes
CAUTION_SIGN_DESCRIPTIONS = {
    1: ("No Entry", "Do not enter this roadway. Vehicle path/heading verification requires GPS/map context."),
    6: ("Give Way", "Yield right-of-way to oncoming traffic. Yielding compliance requires surrounding vehicle context."),
    7: ("School Ahead", "Caution: School zone. Drive attentively and watch for children."),
    8: ("Pedestrian Crossing", "Caution: Pedestrian crossing. Yield to pedestrians; verification requires pedestrian detection."),
    9: ("Left Turn", "Mandatory / impending Left Turn. Trajectory compliance requires steering/heading sensor."),
    10: ("Right Turn", "Mandatory / impending Right Turn. Trajectory compliance requires steering/heading sensor."),
    11: ("U-Turn", "U-Turn advisory. Maneuver compliance requires vehicle trajectory context."),
    12: ("Horn Prohibited", "Silence zone. Horn prohibition compliance requires acoustic/CAN-bus horn sensor."),
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
    Evaluates driver compliance against Indian traffic signs using dynamic context.
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
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Main evaluation entry point.
        Args:
            sign_id: Detected class index (0-14) or None if no sign detected in current frame.
            speed_kmh: Current vehicle speed in km/h. If None, uses context manager speed.
            confidence: Model classification confidence (0.0 to 1.0).
            stopped_seconds: Explicit stop duration in seconds, if supplied by external tracker.
            timestamp: Processing timestamp (defaults to current time).
        Returns:
            Dictionary with structured compliance decision.
        """
        now = time.time() if timestamp is None else timestamp

        # Update speed in context manager if supplied
        if speed_kmh is not None:
            self.context.set_speed(speed_kmh, timestamp=now)

        current_speed = self.context.current_speed_kmh
        active_limit = self.context.active_speed_limit
        is_simulated = self.context.is_simulated_speed

        sign_name = SIGN_CLASSES[sign_id] if (sign_id is not None and 0 <= sign_id < len(SIGN_CLASSES)) else None

        # 1. Check Prediction Confidence if a sign is supplied
        if sign_id is not None and confidence < self.min_confidence:
            # Low confidence sign: do not activate new rules or update speed limits
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

        # 2. If confident speed limit sign detected, update active limit
        if sign_id is not None and sign_id in SPEED_LIMIT_MAP and confidence >= self.min_confidence:
            active_limit = self.context.update_speed_limit(sign_id)

        # 3. Handle Stop Sign (Class 0)
        if sign_id == STOP_SIGN_ID and confidence >= self.min_confidence:
            self.context.register_stop_sign_detection(timestamp=now)

        if self.context.stop_sign_active or (sign_id == STOP_SIGN_ID and confidence >= self.min_confidence):
            stop_duration = stopped_seconds if stopped_seconds is not None else self.context.total_stopped_duration

            if stopped_seconds is None and not self.context.speed_history and current_speed > 0:
                # No speed history and no external duration data provided
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
                )

        # 4. Handle Caution / Advisory Signs (1, 6-14)
        if sign_id is not None and sign_id in CAUTION_SIGN_DESCRIPTIONS and confidence >= self.min_confidence:
            name, desc = CAUTION_SIGN_DESCRIPTIONS[sign_id]
            # Speed check still applies if limit is active
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

        # 5. Speed Limit Compliance Check (active limit persists even when no sign is in frame)
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

        # 6. Default / No active rules
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
        # Alert cooldown handling
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
            "should_alert": should_alert,
        }
        if context_note:
            res["context_note"] = context_note
        return res
