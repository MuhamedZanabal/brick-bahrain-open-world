#!/usr/bin/env python3
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "manama_souq_vertical_slice.gd"
SCENE = ROOT / "scenes" / "manama_souq_vertical_slice.tscn"
RUNTIME = ROOT / "tests" / "manama_souq_slice_runtime.gd"


class ManamaSouqVerticalSliceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        for path in (SCRIPT, SCENE, RUNTIME):
            if not path.is_file():
                raise AssertionError(f"vertical-slice authority missing: {path}")
        cls.script = SCRIPT.read_text(encoding="utf-8")
        cls.scene = SCENE.read_text(encoding="utf-8")
        cls.runtime = RUNTIME.read_text(encoding="utf-8")

    def test_scene_root_and_named_runtime_nodes_are_locked(self) -> None:
        self.assertIn('name="ManamaSouqVerticalSlice"', self.scene)
        self.assertIn('path="res://scripts/manama_souq_vertical_slice.gd"', self.scene)
        for node_name in ("District", "PlayerSpawn", "MissionVehicleSpawn", "Population", "Mission", "HUD"):
            self.assertIn(f'"{node_name}"', self.script)

    def test_orchestrator_reuses_existing_player_vehicle_and_matrix_authorities(self) -> None:
        self.assertIn("class_name ManamaSouqVerticalSlice", self.script)
        self.assertIn('preload("res://scripts/player_controller.gd")', self.script)
        self.assertIn('preload("res://scripts/vehicle.gd")', self.script)
        self.assertIn("ManamaSouqLayoutLoader.new()", self.script)
        self.assertIn("SouqPopulationController.new()", self.script)
        self.assertIn('preload("res://scenes/karak_delivery_hud.tscn")', self.script)
        self.assertIn("KarakDeliveryMission.new()", self.script)

    def test_environment_spawn_and_mission_methods_are_explicit(self) -> None:
        for method in (
            "_build_environment",
            "_spawn_player",
            "_spawn_mission_vehicle",
            "_spawn_population",
            "_start_mission",
            "_update_mission_from_world",
            "_reset_for_replay",
            "_emit_ready",
        ):
            self.assertRegex(self.script, rf"func {method}\(")

    def test_touch_and_vehicle_state_are_integrated_without_control_rewrite(self) -> None:
        self.assertIn("TouchInput.consume_interact()", self.script)
        self.assertIn("_player.current_vehicle", self.script)
        self.assertIn("notify_vehicle_entered", self.script)
        self.assertIn("notify_vehicle_exited", self.script)
        self.assertIn("Input.is_action_just_pressed(\"enter_vehicle\")", self.script)

    def test_readiness_and_qa_markers_are_exact(self) -> None:
        self.assertIn('print("BAHRAIN_BRICK_SOUQ_SLICE_READY assets=%d pedestrians=12 traffic=6" % asset_count)', self.script)
        self.assertIn('print("BAHRAIN_BRICK_SOUQ_QA_TRAVERSAL_COMPLETE")', self.script)
        self.assertIn('"bahrain_brick/qa_auto_mission"', self.script)

    def test_runtime_contract_requires_real_composition(self) -> None:
        for fragment in (
            "MANAMA_SOUQ_SLICE_RUNTIME_PASS",
            "ManamaSouqVerticalSlice",
            "KarakDeliveryMission",
            "MissionVehicle",
            "souq_pedestrians",
            "souq_traffic",
            "35",
            "12",
            "6",
        ):
            self.assertIn(fragment, self.runtime)


if __name__ == "__main__":
    unittest.main(verbosity=2)
