import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/asset-production-ci.yml"
SCRIPT = ROOT / "tools/asset_lab/run_android_emulator_validation.sh"


class AndroidEmulatorWorkflowTests(unittest.TestCase):
    def test_workflow_pins_api34_emulator_image_and_runs_after_export(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("emulator", workflow)
        self.assertIn("system-images;android-34;google_apis;x86_64", workflow)
        self.assertIn("Run Android API 34 emulator validation", workflow)
        self.assertLess(workflow.index("Run complete production chain"), workflow.index("Run Android API 34 emulator validation"))
        self.assertLess(workflow.index("Run Android API 34 emulator validation"), workflow.index("Upload production evidence"))

    def test_script_distinguishes_host_blocker_from_runtime_failure(self):
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("ANDROID_EMULATOR_RUNTIME_VERIFICATION_BLOCKED", script)
        self.assertIn("ANDROID_EMULATOR_RUNTIME_VERIFICATION_FAILED", script)
        self.assertIn("ANDROID_EMULATOR_RUNTIME_VERIFICATION_PASSED", script)
        self.assertIn("adb install -r -t", script)
        self.assertIn("com.godot.game.GodotApp", script)
        self.assertIn("screencap -p", script)
        self.assertIn("KEYCODE_HOME", script)
        self.assertIn("am force-stop", script)
        self.assertIn("FATAL EXCEPTION", script)


if __name__ == "__main__":
    unittest.main()
