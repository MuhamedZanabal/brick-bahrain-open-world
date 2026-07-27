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
    def test_halves_only_runtime_sun_shadow_distance(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "manama_souq_vertical_slice.gd"
            report = root / "report.json"
            script.write_text(
                'func _build_environment() -> void:\n'
                '\tvar sun: DirectionalLight3D = DirectionalLight3D.new()\n'
                '\tsun.name = "LateAfternoonSun"\n'
                '\tsun.shadow_enabled = true\n'
                '\tsun.directional_shadow_max_distance = 150.0\n'
                '\tadd_child(sun)\n\n'
                '\tvar fill: DirectionalLight3D = DirectionalLight3D.new()\n'
                '\tfill.name = "SkyFill"\n'
                '\tfill.shadow_enabled = false\n'
            )
            result = module.apply(script, report)
            text = script.read_text()
            self.assertIn("sun.directional_shadow_max_distance = 75.0", text)
            self.assertIn('fill.name = "SkyFill"', text)
            self.assertIn("fill.shadow_enabled = false", text)
            self.assertEqual(result["before_value"], 150.0)
            self.assertEqual(result["after_value"], 75.0)
            self.assertEqual(result["target_node"], "LateAfternoonSun")
            self.assertTrue(result["qa_override_only"])

    def test_requires_the_named_shadow_casting_sun(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "manama_souq_vertical_slice.gd"
            report = root / "report.json"
            script.write_text('var sun = DirectionalLight3D.new()\nsun.shadow_enabled = true\nsun.directional_shadow_max_distance = 150.0\n')
            with self.assertRaisesRegex(ValueError, "LateAfternoonSun"):
                module.apply(script, report)

    def test_runner_is_mobile_only_and_uses_runtime_script_override(self) -> None:
        text = RUNNER.read_text()
        self.assertIn("apply_r1_mobile_shadow_distance_fix.py", text)
        self.assertIn("scripts/manama_souq_vertical_slice.gd", text)
        self.assertIn("Godot_v4.3-stable_linux.x86_64.zip", text)
        self.assertIn("printf 'mobile_baseline'", text)
        self.assertIn("--renderer mobile", text)
        self.assertNotIn("apply_r1_mobile_shadow_size_fix.py", text)
        self.assertNotIn("gl_production", text)


if __name__ == "__main__":
    unittest.main()
