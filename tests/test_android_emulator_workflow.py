import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/asset-production-ci.yml"
SCRIPT = ROOT / "tools/asset_lab/run_android_emulator_validation.sh"
MATERIALIZER = ROOT / "tools/asset_lab/materialize_android_emulator_wallclock.py"


class AndroidEmulatorWorkflowTests(unittest.TestCase):
    def test_workflow_pins_api34_emulator_image_and_allows_extended_runtime(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("emulator", workflow)
        self.assertIn("system-images;android-34;google_apis;x86_64", workflow)
        self.assertIn("Run Android API 34 emulator validation", workflow)
        self.assertIn("EXPECTED_APK_SHA256", workflow)
        self.assertIn("timeout-minutes: 65", workflow)
        self.assertIn("materialize_android_emulator_wallclock.py", workflow)
        self.assertIn("run_android_emulator_validation_effective.sh", workflow)
        self.assertLess(workflow.index("Run complete production chain"), workflow.index("Run Android API 34 emulator validation"))
        self.assertLess(workflow.index("Run Android API 34 emulator validation"), workflow.index("Upload production evidence"))

    def test_script_proves_host_dependencies_and_virtualization_state(self):
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("libpulse0", script)
        self.assertIn('ldd "$EMULATOR"', script)
        self.assertIn("ANDROID_EMULATOR_UNRESOLVED_LIBRARIES", script)
        self.assertIn("libpulse.so.0 did not resolve after libpulse0 installation", script)
        self.assertIn("ANDROID_EMULATOR_KVM.txt", script)
        self.assertIn("emulator process exited before Android completed boot", script)
        self.assertIn("-no-window", script)
        self.assertIn("-no-audio", script)
        self.assertIn("-no-boot-anim", script)
        self.assertIn("-no-snapshot", script)
        self.assertIn("-gpu swiftshader_indirect", script)
        self.assertIn("adb wait-for-device", script)
        self.assertIn("sys.boot_completed", script)

    def test_script_runs_exact_apk_world_lifecycle_traversal_and_soak(self):
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("EXPECTED_APK_SHA256", script)
        self.assertIn("APK SHA-256 did not match", script)
        self.assertIn("com.godot.game.GodotApp", script)
        self.assertIn("BAHRAIN BRICK GAME ASSET LAB READY", script)
        self.assertIn("android-emulator-startup.png", script)
        self.assertIn("android-emulator-gameplay.png", script)
        self.assertIn("android-emulator-traversal-midpoint.png", script)
        self.assertIn("android-emulator-final.png", script)
        self.assertIn("KEYCODE_HOME", script)
        self.assertIn("am force-stop", script)
        self.assertIn("TRAVERSAL_SECONDS=600", script)
        self.assertIn("SOAK_SECONDS=1800", script)
        self.assertIn("dumpsys meminfo", script)
        self.assertIn("ANDROID_EMULATOR_RUNTIME_METRICS.csv", script)
        self.assertIn("android-emulator-logcat-continuous.txt", script)
        self.assertIn("FATAL EXCEPTION", script)
        self.assertIn("Invalid get index", script)
        self.assertIn("Navigation", script)

    def test_wallclock_materializer_is_fail_closed_and_emits_valid_shell(self):
        materializer = MATERIALIZER.read_text(encoding="utf-8")
        self.assertIn("expected exactly one reviewed source block", materializer)
        self.assertIn("TRAVERSAL_DEADLINE", materializer)
        self.assertIn("SOAK_DEADLINE", materializer)
        self.assertIn("ACTUAL_TRAVERSAL_SECONDS", materializer)
        self.assertIn("ACTUAL_SOAK_SECONDS", materializer)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "effective.sh"
            report = Path(tmp) / "materialization.json"
            subprocess.run(["python3", str(MATERIALIZER), str(SCRIPT), str(output), str(report)], check=True)
            subprocess.run(["bash", "-n", str(output)], check=True)
            effective = output.read_text(encoding="utf-8")
            self.assertIn("TRAVERSAL_DEADLINE", effective)
            self.assertIn("SOAK_DEADLINE", effective)
            self.assertTrue(report.is_file())


if __name__ == "__main__":
    unittest.main()
