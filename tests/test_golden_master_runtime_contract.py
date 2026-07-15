import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "asset_lab/runtime/golden_master_manifest.json"
QUALITY_PATH = ROOT / "scripts/golden_master_quality.gd"
LOD_PATH = ROOT / "scripts/golden_master_lod_instance.gd"
PREVIEW_SCRIPT_PATH = ROOT / "scripts/golden_master_preview_district.gd"
PREVIEW_SCENE_PATH = ROOT / "scenes/golden_master_preview_district.tscn"

EXPECTED_ASSETS = {
    "bh_traditional_projecting_window_01": "traditional",
    "bh_souq_shop_gold_01": "souq",
    "bh_waterfront_tower_a_01": "waterfront",
    "bh_supermarket_storefront_a_01": "commercial",
    "bh_cr_skyscraper_tower_01": "hero_skyline",
}
EXPECTED_PROFILES = ("low", "balanced", "high")


class GoldenMasterRuntimeContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_manifest_declares_exact_batch_one_authorities(self):
        self.assertEqual(self.manifest["schema_version"], 1)
        self.assertEqual(tuple(self.manifest["profiles"]), EXPECTED_PROFILES)
        self.assertEqual(self.manifest["default_profile"], "balanced")
        records = self.manifest["assets"]
        self.assertEqual(len(records), 5)
        self.assertEqual(
            {record["asset_id"]: record["family"] for record in records},
            EXPECTED_ASSETS,
        )

    def test_manifest_resolves_exactly_45_unique_runtime_paths(self):
        paths = []
        for record in self.manifest["assets"]:
            self.assertGreater(record["lod0_max_m"], 0)
            self.assertGreater(record["lod1_max_m"], record["lod0_max_m"])
            self.assertEqual(len(record["position"]), 3)
            self.assertEqual(len(record["scale"]), 3)
            for profile in EXPECTED_PROFILES:
                profile_paths = record["paths"][profile]
                self.assertEqual(len(profile_paths), 3)
                for lod, path in enumerate(profile_paths):
                    expected = (
                        f"res://assets/asset_lab/golden_masters/{profile}/"
                        f"{record['family']}/{record['asset_id']}_lod{lod}.glb"
                    )
                    self.assertEqual(path, expected)
                    paths.append(path)
        self.assertEqual(len(paths), 45)
        self.assertEqual(len(set(paths)), 45)

    def test_quality_selector_contains_bidirectional_hysteresis(self):
        source = QUALITY_PATH.read_text(encoding="utf-8")
        self.assertIn("class_name GoldenMasterQuality", source)
        self.assertIn("lod0_max_m + hysteresis", source)
        self.assertIn("lod0_max_m - hysteresis", source)
        self.assertIn("lod1_max_m + hysteresis", source)
        self.assertIn("lod1_max_m - hysteresis", source)
        self.assertNotIn("rand", source.lower())

    def test_lod_instance_loads_manifest_paths_without_material_override(self):
        source = LOD_PATH.read_text(encoding="utf-8")
        self.assertIn("class_name GoldenMasterLODInstance", source)
        self.assertIn("ResourceLoader.exists", source)
        self.assertIn("GoldenMasterQuality.select_lod", source)
        self.assertIn("PackedScene", source)
        self.assertNotRegex(source, re.compile(r"material_override\s*="))

    def test_preview_scene_isolated_and_manifest_driven(self):
        script = PREVIEW_SCRIPT_PATH.read_text(encoding="utf-8")
        scene = PREVIEW_SCENE_PATH.read_text(encoding="utf-8")
        self.assertIn("golden_master_manifest.json", script)
        self.assertIn("GoldenMasterLODInstance", script)
        self.assertIn("GOLDEN_MASTER_PREVIEW_READY", script)
        self.assertIn("golden_master_preview_district.gd", scene)
        self.assertNotIn("world.gd", scene)
        self.assertNotIn("player_controller.gd", scene)


if __name__ == "__main__":
    unittest.main()
