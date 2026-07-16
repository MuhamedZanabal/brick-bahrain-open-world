import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "asset_lab/runtime/full_asset_matrix_manifest.json"
RUNTIME = ROOT / "scripts/full_asset_matrix_runtime.gd"
WORLD = ROOT / "scenes/world.tscn"


class FullAssetMatrixRuntimeTests(unittest.TestCase):
    def test_runtime_is_manifest_driven_and_uses_lod_hysteresis(self):
        text = RUNTIME.read_text(encoding="utf-8")
        for required in (
            "FULL_MATRIX_MANIFEST",
            "GoldenMasterLODInstance.new()",
            "GoldenMasterQuality.normalize_profile",
            "lod_hysteresis_m",
            "BAHRAIN_BRICK_FULL_MATRIX_READY",
            "BAHRAIN BRICK GAME ASSET LAB READY",
        ):
            self.assertIn(required, text)
        for protected in ("touch_input", "player_controller", "joystick", "camera_touch"):
            self.assertNotIn(protected, text.lower())

    def test_world_uses_full_matrix_runtime(self):
        text = WORLD.read_text(encoding="utf-8")
        self.assertIn("res://scripts/full_asset_matrix_runtime.gd", text)
        self.assertNotIn('path="res://scripts/asset_lab_runtime.gd" id="2_asset_lab"', text)

    def test_generated_manifest_has_exact_closure_when_present(self):
        if not MANIFEST.exists():
            self.skipTest("runtime manifest is generated in the production workflow")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["architecture_asset_count"], 48)
        self.assertEqual(manifest["commercial_asset_count"], 4)
        self.assertEqual(len(manifest["assets"]), 48)
        self.assertEqual(len(manifest["commercial"]), 4)
        paths = []
        for record in manifest["assets"]:
            for profile in ("low", "balanced", "high"):
                paths.extend(record["paths"][profile])
        paths.extend(record["path"] for record in manifest["commercial"])
        self.assertEqual(len(paths), 436)
        self.assertEqual(len(set(paths)), 436)


if __name__ == "__main__":
    unittest.main()
