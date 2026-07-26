#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/graphics/apply_r1_gl_compatibility_fix.py"
RUNNER = ROOT / "tools/graphics/run_r1_renderer_debug.sh"


def load_module():
    spec = importlib.util.spec_from_file_location("apply_r1_gl_compatibility_fix", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class R1GLCompatibilityFixTest(unittest.TestCase):
    def test_setting_is_inserted_once_without_renderer_default_change(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project.godot"
            report = root / "report.json"
            project.write_text('[application]\nrun/main_scene="res://main.tscn"\n\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
            result = module.apply(project, report)
            text = project.read_text()
            self.assertEqual(text.count("limits/opengl/max_lights_per_object=7"), 1)
            self.assertIn('renderer/rendering_method="gl_compatibility"', text)
            self.assertFalse(result["renderer_default_modified"])

    def test_runner_is_gl_only_and_uses_43(self) -> None:
        text = RUNNER.read_text()
        self.assertIn("apply_r1_gl_compatibility_fix.py", text)
        self.assertIn("Godot_v4.3-stable_linux.x86_64.zip", text)
        self.assertIn("printf 'gl_production'", text)
        self.assertIn("R1_GL_SCENARIO_COMPLETE mode=gl_production", text)
        self.assertNotIn("MOBILE_PACKAGE", text)
        self.assertNotIn("run_target MOBILE", text)


if __name__ == "__main__":
    unittest.main()
