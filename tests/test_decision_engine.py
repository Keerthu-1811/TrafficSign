"""
Unit Tests for Indian Traffic Sign Driver Compliance Decision Engine & Context Manager.
Covers all test cases described in Section 12 of the implementation plan.
"""

import sys
import os
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from context_manager import DrivingContextManager, SPEED_LIMIT_MAP
from decision_engine import ComplianceDecisionEngine, ComplianceStatus, SIGN_CLASSES


class TestDecisionEngine(unittest.TestCase):

    def setUp(self):
        self.context = DrivingContextManager(stop_duration_required=2.0)
        self.engine = ComplianceDecisionEngine(
            context_manager=self.context,
            min_confidence=0.70,
            stop_duration_required=2.0,
            alert_cooldown_seconds=3.0,
        )

    # -------------------------------------------------------------
    # 1. Class Mapping Verification
    # -------------------------------------------------------------
    def test_class_mapping_alignment(self):
        """Verifies the 15 classes exactly align with the plan specification."""
        self.assertEqual(len(SIGN_CLASSES), 15)
        self.assertEqual(SIGN_CLASSES[0], "Stop")
        self.assertEqual(SIGN_CLASSES[1], "No Entry")
        self.assertEqual(SIGN_CLASSES[2], "Speed Limit 20")
        self.assertEqual(SIGN_CLASSES[3], "Speed Limit 40")
        self.assertEqual(SIGN_CLASSES[4], "Speed Limit 60")
        self.assertEqual(SIGN_CLASSES[5], "Speed Limit 80")
        self.assertEqual(SIGN_CLASSES[6], "Give Way")
        self.assertEqual(SIGN_CLASSES[7], "School Ahead")
        self.assertEqual(SIGN_CLASSES[8], "Pedestrian Crossing")
        self.assertEqual(SIGN_CLASSES[9], "Left Turn")
        self.assertEqual(SIGN_CLASSES[10], "Right Turn")
        self.assertEqual(SIGN_CLASSES[11], "U-Turn")
        self.assertEqual(SIGN_CLASSES[12], "Horn Prohibited")
        self.assertEqual(SIGN_CLASSES[13], "Parking")
        self.assertEqual(SIGN_CLASSES[14], "Dangerous Curve")

    # -------------------------------------------------------------
    # 2. Speed-Limit Test Cases (Implementation Plan Table)
    # -------------------------------------------------------------
    def test_speed_limit_20_compliant(self):
        """Test 1: Speed Limit 20, 15 km/h -> COMPLIANT"""
        res = self.engine.check(sign_id=2, speed_kmh=15.0, confidence=0.95)
        self.assertEqual(res["status"], ComplianceStatus.COMPLIANT)
        self.assertEqual(res["active_speed_limit"], 20)
        self.assertEqual(res["speed_kmh"], 15.0)

    def test_speed_limit_20_violation(self):
        """Test 2: Speed Limit 20, 30 km/h -> VIOLATION"""
        res = self.engine.check(sign_id=2, speed_kmh=30.0, confidence=0.92)
        self.assertEqual(res["status"], ComplianceStatus.VIOLATION)
        self.assertEqual(res["active_speed_limit"], 20)
        self.assertTrue(res["should_alert"])

    def test_speed_limit_40_at_boundary(self):
        """Test 3: Speed Limit 40, 40 km/h -> COMPLIANT (within configured limit)"""
        res = self.engine.check(sign_id=3, speed_kmh=40.0, confidence=0.88)
        self.assertEqual(res["status"], ComplianceStatus.COMPLIANT)
        self.assertEqual(res["active_speed_limit"], 40)

    def test_speed_limit_40_violation(self):
        """Test 4: Speed Limit 40, 45 km/h -> VIOLATION"""
        res = self.engine.check(sign_id=3, speed_kmh=45.0, confidence=0.85)
        self.assertEqual(res["status"], ComplianceStatus.VIOLATION)
        self.assertEqual(res["active_speed_limit"], 40)

    def test_speed_limit_60_compliant(self):
        """Test 5: Speed Limit 60, 55 km/h -> COMPLIANT"""
        res = self.engine.check(sign_id=4, speed_kmh=55.0, confidence=0.90)
        self.assertEqual(res["status"], ComplianceStatus.COMPLIANT)
        self.assertEqual(res["active_speed_limit"], 60)

    def test_speed_limit_80_violation(self):
        """Test 6: Speed Limit 80, 90 km/h -> VIOLATION"""
        res = self.engine.check(sign_id=5, speed_kmh=90.0, confidence=0.93)
        self.assertEqual(res["status"], ComplianceStatus.VIOLATION)
        self.assertEqual(res["active_speed_limit"], 80)

    def test_low_confidence_uncertain(self):
        """Test 7: No reliable prediction (confidence < 0.70) -> UNCERTAIN, limit not changed"""
        res = self.engine.check(sign_id=3, speed_kmh=50.0, confidence=0.55)
        self.assertEqual(res["status"], ComplianceStatus.UNCERTAIN)
        self.assertIsNone(res["active_speed_limit"])

    def test_limit_persistence_after_sign_leaves_frame(self):
        """Test 8: Sign leaves frame (sign_id=None); speed above retained limit is still checked"""
        # First frame: Detect Speed Limit 60
        self.engine.check(sign_id=4, speed_kmh=50.0, confidence=0.95)
        self.assertEqual(self.context.active_speed_limit, 60)

        # Later frames: Sign no longer visible (sign_id=None), vehicle speeds up to 75 km/h
        res = self.engine.check(sign_id=None, speed_kmh=75.0, confidence=0.0)
        self.assertEqual(res["status"], ComplianceStatus.VIOLATION)
        self.assertEqual(res["active_speed_limit"], 60)

    def test_limit_update_sequence(self):
        """Verifies encountering a new speed limit updates the active limit properly."""
        self.engine.check(sign_id=2, speed_kmh=20.0, confidence=0.90)
        self.assertEqual(self.context.active_speed_limit, 20)

        # Transition to Speed Limit 40 zone
        self.engine.check(sign_id=3, speed_kmh=35.0, confidence=0.90)
        self.assertEqual(self.context.active_speed_limit, 40)

    # -------------------------------------------------------------
    # 3. Stop Sign Test Cases
    # -------------------------------------------------------------
    def test_stop_sign_no_speed_context(self):
        """Stop sign detected without speed/temporal context -> CANNOT_VERIFY or CHECK_REQUIRED"""
        fresh_engine = ComplianceDecisionEngine()
        # Speed is 30 km/h, no history or stop duration provided
        res = fresh_engine.check(sign_id=0, speed_kmh=30.0, confidence=0.95)
        self.assertIn(res["status"], [ComplianceStatus.CANNOT_VERIFY, ComplianceStatus.CHECK_REQUIRED])

    def test_stop_sign_external_duration(self):
        """Stop sign evaluated with external stopped_seconds."""
        # 1. Stopped for 1.0s (less than 2.0s required) -> CHECK_REQUIRED
        res1 = self.engine.check(sign_id=0, speed_kmh=0.0, confidence=0.95, stopped_seconds=1.0)
        self.assertEqual(res1["status"], ComplianceStatus.CHECK_REQUIRED)

        # 2. Stopped for 2.2s (>= 2.0s required) -> COMPLIANT
        res2 = self.engine.check(sign_id=0, speed_kmh=0.0, confidence=0.95, stopped_seconds=2.2)
        self.assertEqual(res2["status"], ComplianceStatus.COMPLIANT)

    def test_stop_sign_temporal_tracking_in_context(self):
        """Context manager accumulates stopped duration over timestamps."""
        t0 = 1000.0
        # Frame 1: Stop sign detected, car decelerating to 0 km/h
        self.engine.check(sign_id=0, speed_kmh=0.0, confidence=0.95, timestamp=t0)
        
        # Frame 2: 1.0 second stopped
        res_mid = self.engine.check(sign_id=0, speed_kmh=0.0, confidence=0.95, timestamp=t0 + 1.0)
        self.assertEqual(res_mid["status"], ComplianceStatus.CHECK_REQUIRED)

        # Frame 3: 2.2 seconds stopped -> Satisfied
        res_done = self.engine.check(sign_id=0, speed_kmh=0.0, confidence=0.95, timestamp=t0 + 2.2)
        self.assertEqual(res_done["status"], ComplianceStatus.COMPLIANT)

    # -------------------------------------------------------------
    # 4. Multi-Modal Context Rules: Horn, Pedestrian, Turn Signs
    # -------------------------------------------------------------
    def test_horn_prohibited_violation_when_honked(self):
        """Horn Prohibited (ID 12) + horn active -> VIOLATION"""
        res = self.engine.check(sign_id=12, speed_kmh=30.0, confidence=0.90, horn_active=True)
        self.assertEqual(res["status"], ComplianceStatus.VIOLATION)
        self.assertIn("Illegal horn", res["message"])

    def test_horn_prohibited_compliant_when_silent(self):
        """Horn Prohibited (ID 12) + horn silent -> COMPLIANT"""
        res = self.engine.check(sign_id=12, speed_kmh=30.0, confidence=0.90, horn_active=False)
        self.assertEqual(res["status"], ComplianceStatus.COMPLIANT)
        self.assertIn("Horn prohibition compliant", res["message"])

    def test_pedestrian_crossing_yield_compliant(self):
        """Pedestrian Crossing (ID 8) + pedestrian present + speed <= 5 km/h -> COMPLIANT"""
        res = self.engine.check(sign_id=8, speed_kmh=0.0, confidence=0.92, pedestrian_present=True)
        self.assertEqual(res["status"], ComplianceStatus.COMPLIANT)
        self.assertIn("Yielded to pedestrian", res["message"])

    def test_pedestrian_crossing_failure_to_yield_violation(self):
        """Pedestrian Crossing (ID 8) + pedestrian present + speed > 5 km/h -> VIOLATION"""
        res = self.engine.check(sign_id=8, speed_kmh=35.0, confidence=0.92, pedestrian_present=True)
        self.assertEqual(res["status"], ComplianceStatus.VIOLATION)
        self.assertIn("Failure to yield", res["message"])

    def test_pedestrian_crossing_clear_roadway(self):
        """Pedestrian Crossing (ID 8) + no pedestrian -> COMPLIANT"""
        res = self.engine.check(sign_id=8, speed_kmh=30.0, confidence=0.92, pedestrian_present=False)
        self.assertEqual(res["status"], ComplianceStatus.COMPLIANT)
        self.assertIn("clear", res["message"])

    def test_left_turn_compliance(self):
        """Left Turn (ID 9): heading <= -30° -> COMPLIANT; heading 0° -> CHECK_REQUIRED"""
        # Heading 0° (straight)
        res1 = self.engine.check(sign_id=9, speed_kmh=25.0, confidence=0.90, heading_deg=0.0)
        self.assertEqual(res1["status"], ComplianceStatus.CHECK_REQUIRED)

        # Heading -45° (turned left)
        res2 = self.engine.check(sign_id=9, speed_kmh=20.0, confidence=0.90, heading_deg=-45.0)
        self.assertEqual(res2["status"], ComplianceStatus.COMPLIANT)

    def test_right_turn_compliance(self):
        """Right Turn (ID 10): heading >= 30° -> COMPLIANT"""
        res = self.engine.check(sign_id=10, speed_kmh=20.0, confidence=0.90, heading_deg=60.0)
        self.assertEqual(res["status"], ComplianceStatus.COMPLIANT)

    def test_u_turn_compliance(self):
        """U-Turn (ID 11): heading 180° -> COMPLIANT"""
        res = self.engine.check(sign_id=11, speed_kmh=15.0, confidence=0.90, heading_deg=180.0)
        self.assertEqual(res["status"], ComplianceStatus.COMPLIANT)

    def test_caution_sign_with_active_speed_violation(self):
        """In a 20 km/h zone, School Ahead at 45 km/h -> VIOLATION."""
        self.engine.check(sign_id=2, speed_kmh=18.0, confidence=0.90)  # active limit = 20
        res = self.engine.check(sign_id=7, speed_kmh=45.0, confidence=0.90)  # School ahead at 45
        self.assertEqual(res["status"], ComplianceStatus.VIOLATION)
        self.assertIn("School Ahead", res["message"])

    # -------------------------------------------------------------
    # 5. Alert Cooldown / Suppression
    # -------------------------------------------------------------
    def test_alert_suppression_cooldown(self):
        """Verifies repeated alerts within cooldown window are suppressed."""
        t0 = 2000.0
        # First violation triggers alert
        res1 = self.engine.check(sign_id=2, speed_kmh=35.0, confidence=0.95, timestamp=t0)
        self.assertTrue(res1["should_alert"])

        # Identical violation 1 second later should be suppressed
        res2 = self.engine.check(sign_id=2, speed_kmh=35.0, confidence=0.95, timestamp=t0 + 1.0)
        self.assertFalse(res2["should_alert"])

        # Identical violation after cooldown (4 seconds later) triggers alert
        res3 = self.engine.check(sign_id=2, speed_kmh=35.0, confidence=0.95, timestamp=t0 + 4.0)
        self.assertTrue(res3["should_alert"])


if __name__ == "__main__":
    unittest.main()
