#!/usr/bin/env python3
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "karak_delivery_mission.gd"
RUNTIME = ROOT / "tests" / "karak_delivery_mission_runtime.gd"


class KarakDeliveryMissionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not SCRIPT.is_file():
            raise AssertionError(f"mission implementation missing: {SCRIPT}")
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_class_states_and_signals_are_explicit(self) -> None:
        self.assertIn("class_name KarakDeliveryMission", self.text)
        for state in (
            "NOT_STARTED",
            "WALK_TO_CAFE",
            "COLLECT_ORDER",
            "ENTER_VEHICLE",
            "DRIVE_TO_WATERFRONT",
            "EXIT_VEHICLE",
            "DELIVER_ORDER",
            "COMPLETED",
            "FAILED",
        ):
            self.assertRegex(self.text, rf"\b{state}\b")
        for signal in (
            "objective_changed",
            "state_changed",
            "mission_completed",
            "mission_failed",
        ):
            self.assertRegex(self.text, rf"signal\s+{signal}\b")

    def test_public_transition_api_is_complete(self) -> None:
        signatures = (
            r"func start\(player: Node3D, vehicle: Node3D\) -> bool:",
            r"func configure\(points: Dictionary, reward_coins: int = 250, time_limit_seconds: float = 300\.0\) -> bool:",
            r"func advance_from_player_position\(position: Vector3\) -> bool:",
            r"func notify_order_collected\(\) -> bool:",
            r"func notify_vehicle_entered\(vehicle: Node3D\) -> bool:",
            r"func notify_vehicle_exited\(\) -> bool:",
            r"func restart\(\) -> bool:",
        )
        for signature in signatures:
            self.assertRegex(self.text, signature)

    def test_reward_time_limit_and_runtime_markers_are_locked(self) -> None:
        self.assertIn("DEFAULT_REWARD_COINS := 250", self.text)
        self.assertIn("DEFAULT_TIME_LIMIT_SECONDS := 300.0", self.text)
        self.assertIn('print("BAHRAIN_BRICK_KARAK_MISSION_STARTED")', self.text)
        self.assertIn('print("BAHRAIN_BRICK_KARAK_MISSION_COMPLETED reward=%d" % _reward_coins)', self.text)

    def test_transition_guards_and_duplicate_event_immunity_are_present(self) -> None:
        self.assertIn("const LEGAL_TRANSITIONS :=", self.text)
        self.assertRegex(self.text, r"if current_state == next_state:\s*return false")
        self.assertRegex(self.text, r"if not next_state in allowed:\s*return false")
        self.assertIn("_order_collected", self.text)
        self.assertIn("_active_vehicle", self.text)
        self.assertIn("_completed_once", self.text)

    def test_state_specific_objectives_are_defined(self) -> None:
        expected = (
            "Walk to the karak café",
            "Collect the sealed karak order",
            "Enter the delivery vehicle",
            "Drive to the waterfront customer",
            "Exit the vehicle at the delivery court",
            "Deliver the karak order",
            "Delivery complete",
        )
        for objective in expected:
            self.assertIn(objective, self.text)

    def test_headless_runtime_test_exists_and_covers_every_state(self) -> None:
        self.assertTrue(RUNTIME.is_file(), f"runtime test missing: {RUNTIME}")
        text = RUNTIME.read_text(encoding="utf-8")
        for state in (
            "WALK_TO_CAFE",
            "COLLECT_ORDER",
            "ENTER_VEHICLE",
            "DRIVE_TO_WATERFRONT",
            "EXIT_VEHICLE",
            "DELIVER_ORDER",
            "COMPLETED",
        ):
            self.assertIn(state, text)
        self.assertIn("duplicate transition emitted", text)
        self.assertIn("KARAK_DELIVERY_RUNTIME_PASS", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
