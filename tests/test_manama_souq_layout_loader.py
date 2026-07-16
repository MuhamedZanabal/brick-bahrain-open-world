#!/usr/bin/env python3
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "manama_souq_layout_loader.gd"
RUNTIME = ROOT / "tests" / "manama_souq_layout_runtime.gd"


class ManamaSouqLayoutLoaderContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not SCRIPT.is_file():
            raise AssertionError(f"layout loader missing: {SCRIPT}")
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_loader_class_and_public_api_are_stable(self) -> None:
        self.assertIn("class_name ManamaSouqLayoutLoader", self.text)
        self.assertRegex(self.text, r"func load_layout\(path: String, full_manifest_path: String\) -> Dictionary:")
        self.assertRegex(self.text, r"func instantiate_layout\(root: Node3D, camera: Camera3D, profile: String\) -> Dictionary:")
        self.assertRegex(self.text, r"func get_mission_points\(\) -> Dictionary:")
        self.assertRegex(self.text, r"func get_traffic_route\(\) -> Array\[Vector3\]:")

    def test_loader_fails_closed_on_schema_membership_and_duplicates(self) -> None:
        required_fragments = (
            'EXPECTED_SCHEMA := "bahrain-brick-manama-souq-layout-v1"',
            "SUPPORTED_SCHEMA_VERSION := 1",
            "duplicate placement_id",
            "missing from full matrix manifest",
            "unsupported layout schema",
            "layout bounds are not 220m x 220m",
            "required zone missing",
            "required family count not met",
        )
        for fragment in required_fragments:
            self.assertIn(fragment, self.text)

    def test_loader_uses_existing_lod_authority_and_direct_commercial_scenes(self) -> None:
        self.assertIn("GoldenMasterLODInstance.new()", self.text)
        self.assertIn("lod_instance.configure(manifest_record, normalized_profile, camera, _hysteresis_m)", self.text)
        self.assertIn("ResourceLoader.exists(commercial_path, \"PackedScene\")", self.text)
        self.assertIn("instance.set_meta(\"placement_id\"", self.text)
        self.assertIn("instance.set_meta(\"manama_souq_zone\"", self.text)

    def test_loader_reports_deterministic_counts(self) -> None:
        for key in (
            '"placement_count"',
            '"architecture_count"',
            '"commercial_count"',
            '"zone_counts"',
            '"loaded_asset_ids"',
        ):
            self.assertIn(key, self.text)

    def test_headless_runtime_test_exists(self) -> None:
        self.assertTrue(RUNTIME.is_file(), f"runtime test missing: {RUNTIME}")
        text = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("MANAMA_SOUQ_LAYOUT_RUNTIME_PASS", text)
        self.assertIn("placement_count", text)
        self.assertIn("architecture_count", text)
        self.assertIn("commercial_count", text)
        self.assertIn("cafe_start", text)
        self.assertIn("souq_lane", text)
        self.assertIn("vehicle_route", text)
        self.assertIn("waterfront_delivery", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
