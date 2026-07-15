import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/asset-production-ci.yml"
DRIVER = ROOT / "tools/asset_lab/run_asset_production_ci.sh"


class AssetProductionWorkflowTests(unittest.TestCase):
    def test_workflow_pins_authorities_and_toolchains(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        for value in (
            "e26ec912db5c10d071a8e120010bdb5a9a136f17",
            "5383c376df40f2a427fc5f739cac0ad23584de35",
            "7aed2cf05f63e0c3c607a98acde454ff103584eb",
            "BLENDER_VERSION: 4.3.2",
            "GODOT_VERSION: 4.3",
            "GODOT_BUILD: 77dcf97d8",
            "ANDROID_PLATFORM: android-34",
            "ANDROID_BUILD_TOOLS: 34.0.0",
            "GLTF_VALIDATOR_VERSION: 2.0.0-dev.3.10",
            "PACKAGE_NAME: com.bahrainbrick.game.qa",
            "VERSION_CODE: '1404'",
            "VERSION_NAME: 1.4.0.4-premium-visual-qa",
            "librsvg2-bin",
            "Pillow==12.3.0",
            "Stage checksum-pinned generator dependencies",
        ):
            self.assertIn(value, text)

    def test_driver_contains_required_execution_chain(self):
        text = DRIVER.read_text(encoding="utf-8")
        ordered = [
            "Verify exact integration ancestry", "Recover checksum-locked game source",
            "Protected-control pre-check", "Verify corrected asset source integrity",
            "Run corrected asset repository tests", "Generate deterministic validation cube twice",
            "Require deterministic cube GLB bytes", "Run Khronos glTF Validator",
            "Run independent cube contract validator", "Run production asset generators",
            "Validate generated asset families", "Run Khronos validation for every generated GLB",
            "Run clean Godot import", "Apply verified premium validation overlay",
            "Run post-overlay Godot import", "Run gameplay regression suites",
            "Protected-control post-check", "Export Android APK", "Validate Android APK",
        ]
        positions = [text.index(item) for item in ordered]
        self.assertEqual(positions, sorted(positions))


    def test_driver_refreshes_godot_class_cache_after_overlay(self):
        text = DRIVER.read_text(encoding="utf-8")
        self.assertIn("class_name PremiumWorldMaterials", text)
        self.assertIn("godot-post-overlay-import.log", text)
        self.assertLess(text.index("Apply verified premium validation overlay"), text.index("Run post-overlay Godot import"))
        self.assertLess(text.index("Run post-overlay Godot import"), text.index("Run gameplay regression suites"))

    def test_generated_validation_evidence_paths_are_unique(self):
        text = DRIVER.read_text(encoding="utf-8")
        self.assertIn('report_name="${relative//\//__}"', text)
        self.assertIn('test "$validated" -eq 436', text)
        self.assertIn("GENERATED_ASSET_BATCH_VALIDATION.json", text)

    def test_workflow_and_driver_do_not_mutate_or_merge(self):
        text = WORKFLOW.read_text(encoding="utf-8") + DRIVER.read_text(encoding="utf-8")
        self.assertIn("contents: read", text)
        for forbidden in ("git push", "gh pr merge", "force: true", "contents: write"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
