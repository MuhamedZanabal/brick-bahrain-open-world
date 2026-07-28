#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/graphics/apply_r1_mobile_tonemapper_fix.py"
RUNNER = ROOT / "tools/graphics/run_r1_renderer_debug.sh"
WORKFLOW = ROOT / ".github/workflows/bahrain-brick-r1-renderer-runtime-debugging.yml"


def load_module():
    spec = importlib.util.spec_from_file_location("apply_r1_mobile_tonemapper_fix", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class R1MobileTonemapperFixTest(unittest.TestCase):
    def test_changes_only_filmic_tonemapper_in_named_environment(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "manama_souq_vertical_slice.gd"
            report = root / "report.json"
            script.write_text(
                'environment_node.name = "SouqWorldEnvironment"\n'
                'environment.background_mode = Environment.BG_COLOR\n'
                'environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC\n'
                'sun.name = "LateAfternoonSun"\n'
                'sun.shadow_enabled = true\n'
                'sun.directional_shadow_max_distance = 150.0\n'
                'fill.name = "SkyFill"\n'
                'fill.shadow_enabled = false\n'
            )
            result = module.apply(script, report)
            text = script.read_text()
            self.assertEqual(text.count("Environment.TONE_MAPPER_LINEAR"), 1)
            self.assertNotIn("Environment.TONE_MAPPER_FILMIC", text)
            self.assertIn("sun.shadow_enabled = true", text)
            self.assertIn("sun.directional_shadow_max_distance = 150.0", text)
            self.assertIn("fill.shadow_enabled = false", text)
            self.assertEqual(result["before_value"], "Environment.TONE_MAPPER_FILMIC")
            self.assertEqual(result["after_value"], "Environment.TONE_MAPPER_LINEAR")
            self.assertFalse(result["renderer_default_modified"])
            self.assertFalse(result["gameplay_modified"])
            self.assertTrue(result["qa_override_only"])

    def test_fails_when_exact_environment_signature_is_absent(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "manama_souq_vertical_slice.gd"
            report = root / "report.json"
            script.write_text("environment.tonemap_mode = Environment.TONE_MAPPER_ACES\n")
            with self.assertRaises(ValueError):
                module.apply(script, report)

    def test_runner_and_workflow_are_mobile_only_and_non_stacking(self) -> None:
        runner = RUNNER.read_text()
        workflow = WORKFLOW.read_text()
        self.assertIn("apply_r1_mobile_tonemapper_fix.py", runner)
        self.assertIn("R1_MOBILE_TONEMAPPER_RESULT.json", runner)
        self.assertIn("Godot_v4.3-stable_linux.x86_64.zip", runner)
        self.assertIn("printf 'mobile_baseline'", runner)
        self.assertIn("--renderer mobile", runner)
        for forbidden in (
            "apply_r1_mobile_secondary_light_fix.py",
            "apply_r1_mobile_shadow_size_fix.py",
            "apply_r1_mobile_shadow_distance_fix.py",
            "apply_r1_mobile_render_scale_fix.py",
            "apply_r1_gl_compatibility_fix.py",
            "gl_production",
        ):
            self.assertNotIn(forbidden, runner)
        self.assertIn("Bahrain Brick R1 Mobile Tonemapper", workflow)
        self.assertIn("test_r1_mobile_tonemapper_fix.py", workflow)
        self.assertIn("apply_r1_mobile_tonemapper_fix.py", workflow)
        self.assertIn("Build and launch Mobile only", workflow)
        self.assertNotIn("Engineering Stop", workflow)


if __name__ == "__main__":
    unittest.main()
