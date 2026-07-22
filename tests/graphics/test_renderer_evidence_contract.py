#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests" / "graphics" / "renderer_evidence.gd"
SCENE = ROOT / "tests" / "graphics" / "renderer_evidence.tscn"
FINALIZER = ROOT / "tools" / "graphics" / "finalize_renderer_evidence.py"
WORKFLOW = ROOT / ".github" / "workflows" / "bahrain-brick-graphics-g0.yml"


def load_finalizer():
    spec = importlib.util.spec_from_file_location("finalize_renderer_evidence", FINALIZER)
    if spec is None or spec.loader is None:
        raise AssertionError(f"unable to load {FINALIZER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RendererEvidenceContractTests(unittest.TestCase):
    def test_harness_has_fixed_protocol_and_required_outputs(self) -> None:
        for path in (HARNESS, SCENE, FINALIZER, WORKFLOW):
            self.assertTrue(path.is_file(), f"renderer evidence component missing: {path}")
        text = HARNESS.read_text(encoding="utf-8")
        for fragment in (
            "const VIEWPORT_SIZE := Vector2i(1920, 1080)",
            "const WARMUP_FRAMES := 180",
            "const CAPTURE_FRAME := 300",
            "const TOTAL_MEASURED_FRAMES := 360",
            "BAHRAIN_BRICK_SOUQ_SLICE_READY",
            "BAHRAIN_BRICK_KARAK_MISSION_STARTED",
            "frame_metrics.csv",
            "screenshot.png",
            "runtime.json",
            "evidence_complete",
        ):
            self.assertIn(fragment, text)
        self.assertNotIn("ProjectSettings.save", text)

    def test_workflow_reuses_one_imported_state_for_both_renderers(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        for fragment in (
            "renderer_tier_a:",
            "shared-import",
            "IMPORTED_STATE_MANIFEST.json",
            "cp -a build/g0-render/shared-import build/g0-render/gl_compatibility",
            "cp -a build/g0-render/shared-import build/g0-render/mobile_vulkan",
            "--rendering-method gl_compatibility",
            "--rendering-method mobile",
            "--rendering-driver opengl3",
            "--rendering-driver vulkan",
        ):
            self.assertIn(fragment, text)
        self.assertNotIn("sed -i", text)
        self.assertNotIn("renderer/rendering_method=", text.split("renderer_tier_a:", 1)[1])

    def test_finalizer_detects_errors_and_preserves_evidence_class(self) -> None:
        module = load_finalizer()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "runtime.log").write_text(
                "BAHRAIN_BRICK_SOUQ_SLICE_READY assets=35 pedestrians=12 traffic=6\n"
                "BAHRAIN_BRICK_KARAK_MISSION_STARTED\n"
                "ERROR: Failed loading resource: res://missing.tres\n",
                encoding="utf-8",
            )
            (root / "runtime.json").write_text(
                json.dumps({"renderer": "gl_compatibility", "evidence_tier": "A", "exit_code": 0}),
                encoding="utf-8",
            )
            result = module.finalize_evidence(root, expected_renderer="gl_compatibility")
            self.assertEqual(result["missing_resource_error_count"], 1)
            self.assertTrue(result["scene_ready_marker"])
            self.assertTrue(result["mission_start_marker"])
            self.assertFalse(result["evidence_complete"])
            self.assertEqual(result["evidence_tier"], "A")


if __name__ == "__main__":
    unittest.main(verbosity=2)
