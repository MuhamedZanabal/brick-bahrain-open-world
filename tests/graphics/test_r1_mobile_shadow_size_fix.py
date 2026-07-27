#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/graphics/apply_r1_mobile_shadow_size_fix.py"
RUNNER = ROOT / "tools/graphics/run_r1_renderer_debug.sh"


def load_module():
    spec = importlib.util.spec_from_file_location("apply_r1_mobile_shadow_size_fix", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class R1MobileShadowSizeFixTest(unittest.TestCase):
    def test_reduces_directional_shadow_size_without_renderer_default_change(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project.godot"
            report = root / "report.json"
            project.write_text('[application]\nrun/main_scene="res://main.tscn"\n\n[rendering]\nrenderer/rendering_method="mobile"\n')
            result = module.apply(project, report)
            text = project.read_text()
            self.assertEqual(text.count("lights_and_shadows/directional_shadow/size=2048"), 1)
            self.assertIn('renderer/rendering_method="mobile"', text)
            self.assertEqual(result["before_value"], 4096)
            self.assertEqual(result["after_value"], 2048)
            self.assertFalse(result["renderer_default_modified"])
            self.assertTrue(result["qa_override_only"])

    def test_replaces_existing_value_once_and_is_idempotent(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project.godot"
            report = root / "report.json"
            project.write_text('[rendering]\nlights_and_shadows/directional_shadow/size=4096\n')
            module.apply(project, report)
            module.apply(project, report)
            self.assertEqual(project.read_text().count("lights_and_shadows/directional_shadow/size=2048"), 1)

    def test_runner_is_mobile_only_and_uses_godot_43(self) -> None:
        text = RUNNER.read_text()
        self.assertIn("apply_r1_mobile_shadow_size_fix.py", text)
        self.assertIn("Godot_v4.3-stable_linux.x86_64.zip", text)
        self.assertIn("printf 'mobile_baseline'", text)
        self.assertIn("--renderer mobile", text)
        self.assertNotIn("gl_production", text)
        self.assertNotIn("apply_r1_gl_compatibility_fix.py", text)


if __name__ == "__main__":
    unittest.main()
