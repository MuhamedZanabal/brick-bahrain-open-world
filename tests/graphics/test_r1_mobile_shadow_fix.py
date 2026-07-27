#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/graphics/apply_r1_mobile_shadow_fix.py"
RUNNER = ROOT / "tools/graphics/run_r1_renderer_debug.sh"


def load_module():
    spec = importlib.util.spec_from_file_location("apply_r1_mobile_shadow_fix", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class R1MobileShadowFixTest(unittest.TestCase):
    def test_disables_only_remaining_directional_shadow_for_qa(self) -> None:
        module = load_module()
        source = '''var sun: DirectionalLight3D = DirectionalLight3D.new()\nsun.name = "LateAfternoonSun"\nsun.shadow_enabled = true\nvar fill: DirectionalLight3D = DirectionalLight3D.new()\nfill.name = "SkyFill"\nfill.shadow_enabled = false\n'''
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "manama_souq_vertical_slice.gd"
            report = root / "report.json"
            script.write_text(source, encoding="utf-8")
            result = module.apply(script, report)
            text = script.read_text(encoding="utf-8")
            self.assertNotIn("sun.shadow_enabled = true", text)
            self.assertEqual(text.count("shadow_enabled = false"), 2)
            self.assertEqual(result["experiment"], "DISABLE_ALL_DIRECTIONAL_SHADOWS")
            self.assertEqual(result["changed_shadow_count"], 1)
            self.assertTrue(result["qa_override_only"])
            self.assertFalse(result["production_source_modified"])

    def test_runner_is_mobile_only_and_uses_godot_43(self) -> None:
        text = RUNNER.read_text()
        self.assertIn("apply_r1_mobile_shadow_fix.py", text)
        self.assertIn("mobile_baseline", text)
        self.assertIn("--renderer mobile", text)
        self.assertIn("Godot_v4.3-stable_linux.x86_64.zip", text)
        self.assertNotIn("gl_production", text)
        self.assertNotIn("GL_PACKAGE", text)


if __name__ == "__main__":
    unittest.main()
