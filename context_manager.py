"""
Context Manager for Indian Traffic Sign Driver Compliance Prototype.
Maintains state across video frames:
- Active speed limit
- Current vehicle speed (simulated or sensor-based)
- Stop sign event tracking and stopped duration
- Vehicle heading & steering angle (Left Turn, Right Turn, U-Turn)
- Acoustic horn state (Silence Zone / Horn Prohibited)
- Pedestrian crossing presence & yielding status
- History window for speed and timing
"""

import time
from typing import Optional, List, Tuple

SPEED_LIMIT_MAP = {
    2: 20,
    3: 40,
    4: 60,
    5: 80,
}

STOP_SIGN_ID = 0
STOP_SPEED_THRESHOLD_KMH = 1.0  # Speeds <= 1.0 km/h are considered stopped

TURN_SIGN_IDS = {
    9: "Left Turn",
    10: "Right Turn",
    11: "U-Turn",
}

HORN_PROHIBITED_ID = 12
PEDESTRIAN_CROSSING_ID = 8


class DrivingContextManager:
    """
    Tracks dynamic driving context over time, including speed limits,
    vehicle speed, stop duration, heading angle, horn state, and pedestrian presence.
    """

    def __init__(
        self,
        default_speed_limit: Optional[int] = None,
        is_simulated_speed: bool = True,
        stop_duration_required: float = 2.0,
        stop_event_timeout: float = 10.0,
    ):
        self.active_speed_limit: Optional[int] = default_speed_limit
        self.current_speed_kmh: float = 0.0
        self.is_simulated_speed: bool = is_simulated_speed
        self.stop_duration_required: float = stop_duration_required
        self.stop_event_timeout: float = stop_event_timeout

        # Vehicle Heading / Steering Angle (-180 to +180 deg; 0 = straight)
        self.current_heading_deg: float = 0.0

        # Horn Activation State (Silence Zone)
        self.horn_active: bool = False

        # Pedestrian Crossing Presence
        self.pedestrian_present: bool = False

        # Stop sign state tracking
        self.stop_sign_active: bool = False
        self.stop_sign_first_seen_time: Optional[float] = None
        self.stop_sign_last_seen_time: Optional[float] = None
        self.stopped_start_time: Optional[float] = None
        self.total_stopped_duration: float = 0.0
        self.stop_satisfied: bool = False

        # Recent speed history [(timestamp, speed_kmh)]
        self.speed_history: List[Tuple[float, float]] = []
        self.history_max_age: float = 15.0

    def set_speed(self, speed_kmh: float, timestamp: Optional[float] = None):
        """Updates the current vehicle speed and updates stop duration tracking."""
        now = time.time() if timestamp is None else timestamp
        self.current_speed_kmh = max(0.0, float(speed_kmh))
        self._record_speed(now, self.current_speed_kmh)
        self._update_stop_tracking(now)

    def set_heading(self, heading_deg: float):
        """Updates the current vehicle steering / heading angle in degrees."""
        # Normalize to [-180, 180]
        deg = float(heading_deg) % 360
        if deg > 180:
            deg -= 360
        self.current_heading_deg = deg

    def set_horn(self, active: bool):
        """Sets the current horn activation status (pressed/released)."""
        self.horn_active = bool(active)

    def set_pedestrian_present(self, present: bool):
        """Sets whether a pedestrian is currently on or entering the crossing."""
        self.pedestrian_present = bool(present)

    def _record_speed(self, timestamp: float, speed_kmh: float):
        self.speed_history.append((timestamp, speed_kmh))
        cutoff = timestamp - self.history_max_age
        while self.speed_history and self.speed_history[0][0] < cutoff:
            self.speed_history.pop(0)

    def update_speed_limit(self, sign_id: int) -> Optional[int]:
        """
        Updates the active speed limit if the given sign ID is a valid speed limit sign.
        Returns the new active limit if updated, else None.
        """
        if sign_id in SPEED_LIMIT_MAP:
            new_limit = SPEED_LIMIT_MAP[sign_id]
            self.active_speed_limit = new_limit
            return new_limit
        return None

    def register_stop_sign_detection(self, timestamp: Optional[float] = None):
        """Registers a detection of a Stop sign, initiating or continuing a Stop event."""
        now = time.time() if timestamp is None else timestamp
        if not self.stop_sign_active:
            self.stop_sign_active = True
            self.stop_sign_first_seen_time = now
            self.stop_satisfied = False
            self.total_stopped_duration = 0.0
            self.stopped_start_time = None
        self.stop_sign_last_seen_time = now
        self._update_stop_tracking(now)

    def _update_stop_tracking(self, now: float):
        """Calculates stopped duration if a Stop sign event is currently active."""
        if not self.stop_sign_active:
            return

        # Check if the stop sign event timed out
        if self.stop_sign_last_seen_time is not None:
            if (now - self.stop_sign_last_seen_time) > self.stop_event_timeout and not self.stop_satisfied:
                self.stop_sign_active = False
                self.stopped_start_time = None
                return

        # If vehicle is stopped
        if self.current_speed_kmh <= STOP_SPEED_THRESHOLD_KMH:
            if self.stopped_start_time is None:
                self.stopped_start_time = now
            else:
                self.total_stopped_duration = now - self.stopped_start_time
                if self.total_stopped_duration >= self.stop_duration_required:
                    self.stop_satisfied = True
        else:
            # Vehicle is moving
            if self.stop_satisfied:
                self.stop_sign_active = False
                self.stopped_start_time = None
            else:
                self.stopped_start_time = None

    def reset_stop_state(self):
        """Clears the active Stop sign tracking."""
        self.stop_sign_active = False
        self.stop_sign_first_seen_time = None
        self.stop_sign_last_seen_time = None
        self.stopped_start_time = None
        self.total_stopped_duration = 0.0
        self.stop_satisfied = False

    def clear_active_limit(self):
        """Clears the currently retained speed limit (e.g. at end of trip)."""
        self.active_speed_limit = None

    def reset(self):
        """Full reset of all context state."""
        self.clear_active_limit()
        self.reset_stop_state()
        self.current_speed_kmh = 0.0
        self.current_heading_deg = 0.0
        self.horn_active = False
        self.pedestrian_present = False
        self.speed_history.clear()
