#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSPECTOR = ROOT / "tools" / "vertical_slice" / "inspect_manama_souq_android_preset.py"

ACCEPTED_PRESET = '''[preset.0]

name="Android"
platform="Android"
runnable=true
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter=""
export_path="build/bahrain_brick_v14.0.3-graphics-qa.apk"

[preset.0.options]

gradle_build/use_gradle_build=false
architectures/armeabi-v7a=true
architectures/arm64-v8a=true
architectures/x86_64=true
architectures/x86=false
keystore/debug=""
keystore/debug_password="android"
keystore/debug_user="androiddebugkey"
keystore/release=""
version/code=1404
version/name="1.4.0.4-premium-visual-qa"
package/unique_name="com.bahrainbrick.game.qa"
package/name="Bahrain Brick"
package/signed=true
apk_expansion/enable=false
permissions/custom_permissions=PackedStringArray()
permissions/access_network_state=true
permissions/internet=true
permissions/record_audio=false
'''

ACCEPTED_PROJECT = '''config_version=5
[application]
config/name="Bahrain Brick"
run/main_scene="res://scenes/splash_screen.tscn"
[display]
[display/window]
[display/window/handheld]
orientation=4
[rendering]
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
textures/vram_compression/import_etc2_astc=true
'''


class ManamaSouqGate4PresetInspectorTests(unittest.TestCase):
    def run_inspector(self, preset_text: str = ACCEPTED_PRESET) -> tuple[subprocess.CompletedProcess[str], dict]:
        self.assertTrue(INSPECTOR.is_file(), f"Gate 4 preset inspector missing: {INSPECTOR}")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            preset = root / "export_presets.cfg"
            project = root / "project.godot"
            output = root / "report.json"
            preset.write_text(preset_text, encoding="utf-8")
            project.write_text(ACCEPTED_PROJECT, encoding="utf-8")
            result = subprocess.run(
                [
                    "python3",
                    str(INSPECTOR),
                    "--preset",
                    str(preset),
                    "--project",
                    str(project),
                    "--output",
                    str(output),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            report = json.loads(output.read_text(encoding="utf-8")) if output.is_file() else {}
            return result, report

    def test_exact_accepted_composite_preset_is_valid(self) -> None:
        result, report = self.run_inspector()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(report["valid"])
        self.assertEqual(report["preset_name"], "Android")
        self.assertEqual(report["package_id"], "com.bahrainbrick.game.qa")
        self.assertEqual(report["application_label"], "Bahrain Brick")
        self.assertEqual(report["version_name"], "1.4.0.4-premium-visual-qa")
        self.assertEqual(report["version_code"], 1404)
        self.assertEqual(report["orientation_value"], 4)
        self.assertEqual(report["orientation"], "sensorLandscape")
        self.assertEqual(report["renderer"], "gl_compatibility")
        self.assertTrue(report["debuggable_export"])
        self.assertEqual(report["signing"]["debug_keystore"], "")
        self.assertEqual(report["signing"]["authority"], "external QA/debug environment override")
        self.assertEqual(
            sorted(name for name, enabled in report["architectures"].items() if enabled),
            ["arm64-v8a", "armeabi-v7a", "x86_64"],
        )

    def test_inspector_fails_closed_when_no_architecture_is_selected(self) -> None:
        malformed = ACCEPTED_PRESET.replace("architectures/armeabi-v7a=true", "architectures/armeabi-v7a=false").replace(
            "architectures/arm64-v8a=true", "architectures/arm64-v8a=false"
        ).replace("architectures/x86_64=true", "architectures/x86_64=false")
        result, report = self.run_inspector(malformed)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["valid"])
        self.assertIn("no architecture selected", {item.get("reason") for item in report["failures"]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
