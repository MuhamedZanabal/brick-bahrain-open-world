#!/usr/bin/env python3
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "karak_delivery_hud.gd"
SCENE = ROOT / "scenes" / "karak_delivery_hud.tscn"
RUNTIME = ROOT / "tests" / "karak_delivery_hud_runtime.gd"


class KarakDeliveryHUDContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not SCRIPT.is_file():
            raise AssertionError(f"HUD script missing: {SCRIPT}")
        if not SCENE.is_file():
            raise AssertionError(f"HUD scene missing: {SCENE}")
        cls.script = SCRIPT.read_text(encoding="utf-8")
        cls.scene = SCENE.read_text(encoding="utf-8")

    def test_public_binding_and_replay_interfaces_are_stable(self) -> None:
        self.assertIn("class_name KarakDeliveryHUD", self.script)
        self.assertRegex(self.script, r"signal replay_requested\(\)")
        self.assertRegex(self.script, r"func bind_mission\(mission: KarakDeliveryMission, player: Node3D\) -> void:")
        self.assertRegex(self.script, r"func set_interaction_prompt\(text: String, visible: bool\) -> void:")
        self.assertRegex(self.script, r"func set_status_message\(text: String, duration_seconds: float = 2\.0\) -> void:")

    def test_required_nodes_exist_in_scene(self) -> None:
        for node_name in (
            "MissionTitle",
            "ObjectiveText",
            "DistanceText",
            "OrderIndicator",
            "RewardText",
            "InteractionPrompt",
            "ReplayButton",
        ):
            self.assertIn(f'name="{node_name}"', self.scene)

    def test_hud_consumes_mission_signals_and_distance(self) -> None:
        for signal in ("objective_changed", "state_changed", "mission_completed", "mission_failed"):
            self.assertIn(signal, self.script)
        self.assertIn("global_position.distance_to", self.script)
        self.assertIn('"Order: Collected"', self.script)
        self.assertIn('"Order: Not collected"', self.script)
        self.assertIn('"Reward: %d coins"', self.script)

    def test_hud_is_top_anchored_and_preserves_touch_control_space(self) -> None:
        self.assertIn("anchor_left = 0.2", self.scene)
        self.assertIn("anchor_right = 0.8", self.scene)
        self.assertIn("anchor_top = 0.0", self.scene)
        self.assertIn("anchor_bottom = 0.0", self.scene)
        self.assertIn("mouse_filter = 2", self.scene)

    def test_runtime_signal_test_exists(self) -> None:
        self.assertTrue(RUNTIME.is_file(), f"HUD runtime test missing: {RUNTIME}")
        text = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("KARAK_DELIVERY_HUD_RUNTIME_PASS", text)
        self.assertIn("MissionTitle", text)
        self.assertIn("ObjectiveText", text)
        self.assertIn("ReplayButton", text)
        self.assertIn("replay_requested", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
