#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTHORITY = ROOT / "authority/bahrain_brick_r1_renderer_runtime_debugging.json"
HARNESS = ROOT / "tests/graphics/r1_renderer_runtime_debug.gd"
RUNNER = ROOT / "tools/graphics/run_r1_renderer_debug.sh"
FINALIZER = ROOT / "tools/graphics/finalize_r1_renderer_debug.py"
WORKFLOW = ROOT / ".github/workflows/bahrain-brick-r1-renderer-runtime-debugging.yml"

GL_MODES = (
    "gl_unshaded",
    "gl_empty",
    "gl_sun",
    "gl_sun_shadow",
    "gl_two_directional",
    "gl_two_directional_shadow",
    "gl_production",
)
MOBILE_MODES = ("mobile_baseline", "mobile_render_disabled_control")
MOBILE_CLASSIFICATIONS = (
    "FRAME_LOOP_STALLED",
    "ASYNC_RESOURCE_WAIT",
    "SCENE_TRANSITION_WAIT",
    "SCRIPT_RUNTIME_ERROR",
    "GPU_DRIVER_TIMEOUT",
    "RENDER_PIPELINE_STALL",
    "UNKNOWN_RUNTIME_BLOCK",
)


class R1ContractTest(unittest.TestCase):
    def test_authority_is_exact(self) -> None:
        data = json.loads(AUTHORITY.read_text())
        self.assertEqual(data["branch"], "work/bahrain-brick-renderer-runtime-debugging-r1")
        self.assertEqual(data["parent_g0_2_head"], "6c7d49dbfb00aaaa2f90d63f47fa76af7a0f910e")
        self.assertEqual(data["renderer_authority"], "6ade72ed02084791128dcf4a91223e695d802c15")
        self.assertEqual(data["governing_gate"], "G0_EVIDENCE_INSUFFICIENT")
        self.assertFalse(data["renderer_defaults_may_change"])
        self.assertFalse(data["g1_authorized"])
        self.assertEqual(tuple(data["tracks"]["mobile_vulkan"]["classifications"]), MOBILE_CLASSIFICATIONS)

    def test_harness_declares_full_diagnostic_matrix(self) -> None:
        text = HARNESS.read_text()
        for mode in GL_MODES + MOBILE_MODES:
            self.assertIn(mode, text)
        for marker in (
            "R1_GL_SCENARIO_BEGIN",
            "R1_GL_SCENARIO_COMPLETE",
            "R1_GL_MATERIAL_INVENTORY_WRITTEN",
            "R1_MOBILE_HEARTBEAT",
            "R1_MOBILE_CAPTURE_FRAME",
            "R1_MOBILE_CONTROL_COMPLETE",
        ):
            self.assertIn(marker, text)
        self.assertIn("RenderingServer.render_loop_enabled = false", text)
        self.assertIn("Engine.get_process_frames()", text)
        self.assertIn("Engine.get_physics_frames()", text)
        self.assertIn("Engine.get_frames_drawn()", text)

    def test_runner_is_diagnostic_only_and_uses_shared_import(self) -> None:
        text = RUNNER.read_text()
        self.assertIn("IMPORTED_STATE_MANIFEST.json", text)
        self.assertIn("CLONE_IDENTITY.json", text)
        self.assertIn("GL_MAX_FRAGMENT_UNIFORM_VECTORS", text)
        for mode in GL_MODES + MOBILE_MODES:
            self.assertIn(mode, text)
        self.assertIn("debuggerd -b", text)
        self.assertIn("dumpsys gfxinfo", text)
        self.assertNotIn('renderer/rendering_method="', text)
        self.assertNotIn("G1", text)

    def test_finalizer_requires_unique_evidence_backed_classification(self) -> None:
        text = FINALIZER.read_text()
        for value in MOBILE_CLASSIFICATIONS:
            self.assertIn(value, text)
        self.assertIn("Fragment shader active uniforms exceed GL_MAX_FRAGMENT_UNIFORM_VECTORS", text)
        self.assertIn("diagnosis_proven", text)
        self.assertIn("production_fix_authorized", text)
        self.assertIn("G0_EVIDENCE_INSUFFICIENT", text)

    def test_workflow_is_bounded_to_r1(self) -> None:
        text = WORKFLOW.read_text()
        self.assertIn("work/bahrain-brick-renderer-runtime-debugging-r1", text)
        self.assertIn("run_r1_renderer_debug.sh", text)
        self.assertIn("finalize_r1_renderer_debug.py", text)
        self.assertNotIn("project.godot", text)
        self.assertNotIn("renderer default", text.lower())


if __name__ == "__main__":
    unittest.main()
