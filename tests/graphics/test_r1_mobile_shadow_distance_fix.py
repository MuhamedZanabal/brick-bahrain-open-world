#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/graphics/apply_r1_mobile_shadow_distance_fix.py"
RUNNER = ROOT / "tools/graphics/run_r1_renderer_debug.sh"


def load_module():
    spec = importlib.util.spec_from_file_location("apply_r1_mobile_shadow_distance_fix", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class R1MobileShadowDistanceFixTest(unittest.TestCase):
    def test_halves_only_active_sun_shadow_distance(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scene = root / "scene.tscn"
            report = root / "report.json"
            scene.write_text(
                '[gd_scene format=3]\n\n'
                '[node name="LateAfternoonSun" type="DirectionalLight3D"]\n'
                'shadow_enabled = true\n'
                'directional_shadow_max_distance = 100.0\n\n'
                '[node name="DirectionalFill" type="DirectionalLight3D"]\n'
                'shadow_enabled = false\n'
                'directional_shadow_max_distance = 100.0\n'
            )
            result = module.apply(scene, report)
            text = scene.read_text()
            target = text.split('[node name="LateAfternoonSun"', 1)[1].split('[node name="DirectionalFill"', 1)[0]
            fill = text.split('[node name="DirectionalFill"', 1)[1]
            self.assertIn("directional_shadow_max_distance = 50.0", target)
            self.assertIn("directional_shadow_max_distance = 100.0", fill)
            self.assertEqual(result["before_value"], 100.0)
            self.assertEqual(result["after_value"], 50.0)
            self.assertEqual(result["target_node"], "LateAfternoonSun")
            self.assertTrue(result["qa_override_only"])

    def test_inserts_half_default_when_property_is_absent(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scene = root / "scene.tscn"
            report = root / "report.json"
            scene.write_text('[node name="LateAfternoonSun" type="DirectionalLight3D"]\nshadow_enabled = true\n')
            result = module.apply(scene, report)
            self.assertIn("directional_shadow_max_distance = 50.0", scene.read_text())
            self.assertEqual(result["before_value"], 100.0)

    def test_runner_is_mobile_only_and_uses_distance_override(self) -> None:
        text = RUNNER.read_text()
        self.assertIn("apply_r1_mobile_shadow_distance_fix.py", text)
        self.assertIn("Godot_v4.3-stable_linux.x86_64.zip", text)
        self.assertIn("printf 'mobile_baseline'", text)
        self.assertIn("--renderer mobile", text)
        self.assertNotIn("apply_r1_mobile_shadow_size_fix.py", text)
        self.assertNotIn("gl_production", text)


if __name__ == "__main__":
    unittest.main()
