#!/usr/bin/env python3
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "souq_population_controller.gd"
RUNTIME = ROOT / "tests" / "souq_population_runtime.gd"


class SouqPopulationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not SCRIPT.is_file():
            raise AssertionError(f"population controller missing: {SCRIPT}")
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_public_api_and_release_defaults_are_locked(self) -> None:
        self.assertIn("class_name SouqPopulationController", self.text)
        self.assertRegex(
            self.text,
            r"func configure\(bounds: AABB, traffic_route: Array\[Vector3\], pedestrian_count: int = 12, traffic_count: int = 6, seed: int = 1409\) -> bool:",
        )
        self.assertRegex(self.text, r"func spawn_all\(root: Node3D\) -> Dictionary:")
        self.assertIn("DEFAULT_PEDESTRIAN_COUNT := 12", self.text)
        self.assertIn("DEFAULT_TRAFFIC_COUNT := 6", self.text)
        self.assertIn("DEFAULT_SEED := 1409", self.text)

    def test_existing_character_and_vehicle_visual_authorities_are_reused(self) -> None:
        self.assertIn("NPCPedestrian.new()", self.text)
        self.assertIn("BrickFactory.create_brick_car", self.text)
        self.assertIn('add_to_group("souq_pedestrians")', self.text)
        self.assertIn('add_to_group("souq_traffic")', self.text)

    def test_population_is_fixed_pooled_and_deterministic(self) -> None:
        self.assertIn("RandomNumberGenerator.new()", self.text)
        self.assertIn("_rng.seed = seed", self.text)
        self.assertIn("_spawned", self.text)
        self.assertRegex(self.text, r"if _spawned:\s*return \{\}")
        self.assertNotIn("randi()", self.text)
        self.assertNotIn("randf()", self.text)

    def test_bounds_and_route_recycling_are_enforced(self) -> None:
        for fragment in (
            "_bounds.has_point",
            "_clamp_to_bounds",
            "traffic_route must be closed",
            "route_index",
            "target_index",
        ):
            self.assertIn(fragment, self.text)

    def test_spawn_report_has_exact_counts_and_groups(self) -> None:
        for key in (
            '"pedestrian_count"',
            '"traffic_count"',
            '"pedestrian_group"',
            '"traffic_group"',
            '"seed"',
        ):
            self.assertIn(key, self.text)

    def test_runtime_test_exists_and_requires_exact_counts(self) -> None:
        self.assertTrue(RUNTIME.is_file(), f"runtime test missing: {RUNTIME}")
        text = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("SOUQ_POPULATION_RUNTIME_PASS", text)
        self.assertIn("pedestrian_count", text)
        self.assertIn("traffic_count", text)
        self.assertIn("12", text)
        self.assertIn("6", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
