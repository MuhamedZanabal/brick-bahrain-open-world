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
PATCHER = ROOT / "tools/graphics/patch_r1_reconstruction_preflight.py"
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
        patch = PATCHER.read_text()
        combined = text + "\n" + patch
        self.assertIn("IMPORTED_STATE_MANIFEST.json", text)
        self.assertIn("CLONE_IDENTITY.json", text)
        self.assertIn("GL_MAX_FRAGMENT_UNIFORM_VECTORS", text)
        self.assertIn("R1_RECONSTRUCTION_ENVIRONMENT.json", combined)
        self.assertIn("SOURCE_TREE_EQUIVALENCE.json", combined)
        self.assertIn("FINAL_TREE_MANIESTä¹©Í½¸ˆ°½µ‰¥¹•¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ9½Ñ%¸ ‰É•Á½ÉÑÌ½É…Á¡¥Ì½œÁ|È½Í¡…É•‘}¥µÁ½ÉÑ}•ÅÕ¥Ù…±•¹”¹©Í½¸ˆ°Á…Ñ ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ%¸ ‰HÅ}QU1}%5}YIM%=8ˆ°½µ‰¥¹•¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ9½Ñ%¸ %µ…•Y•ÉÍ¥½¸ôÈÀÈØÀÜÄÐ¸ÈÐÀ¸Äœ°Ñ•áÐ¤(€€€€€€€™½Èµ½‘”¥¸1}5=L€¬5=	%1}5=Lè(€€€€€€€€€€€Í•±˜¹…ÍÍ•ÉÑ%¸¡µ½‘”°Ñ•áÐ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ%¸ ‰‘•‰Õ•É€µˆˆ°Ñ•áÐ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ%¸ ‰‘ÕµÁÍåÌ™á¥¹™¼ˆ°Ñ•áÐ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ9½Ñ%¸ ‰É•¹‘•É•È½É•¹‘•É¥¹}µ•Ñ¡½õpˆˆ°Ñ•áÐ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ9½Ñ%¸ ‰Äˆ°Ñ•áÐ¤((€€€‘•˜Ñ•ÍÑ}™¥¹…±¥é•É}É•ÅÕ¥É•Í}Õ¹¥ÅÕ•}•Ù¥‘•¹•}‰…­•‘}±…ÍÍ¥™¥…Ñ¥½¸¡Í•±˜¤€´ø9½¹”è(€€€€€€€Ñ•áÐ€ô%91%iH¹É•…‘}Ñ•áÐ ¤(€€€€€€€™½ÈÙ…±Õ”¥¸5=	%1}1MM%%Q%=9Lè(€€€€€€€€€€€Í•±˜¹…ÍÍ•ÉÑ%¸¡Ù…±Õ”°Ñ•áÐ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ%¸ ‰É…µ•¹ÐÍ¡…‘•È…Ñ¥Ù”Õ¹¥™½ÉµÌ•á••1}5a}I59Q}U9%=I5}YQ=ILˆ°Ñ•áÐ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ%¸ ‰‘¥…¹½Í¥Í}ÁÉ½Ù•¸ˆ°Ñ•áÐ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ%¸ ‰ÁÉ½‘ÕÑ¥½¹}™¥á}…ÕÑ¡½É¥é•ˆ°Ñ•áÐ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ%¸ ‰Á}Y%9}%9MU%%9Pˆ°Ñ•áÐ¤((€€€‘•˜Ñ•ÍÑ}Ý½É­™±½Ý}¥Í}‰½Õ¹‘•‘}Ñ½}ÈÄ¡Í•±˜¤€´ø9½¹”è(€€€€€€€Ñ•áÐ€ô]=I-1=\¹É•…‘}Ñ•áÐ ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ%¸ ‰Ý½É¬½‰…¡É…¥¸µ‰É¥¬µÉ•¹‘•É•ÈµÉÕ¹Ñ¥µ”µ‘•‰Õ¥¹œµÈÄˆ°Ñ•áÐ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ%¸ ‰ÑåÁ•Ìèm½Á•¹•°Íå¹¡É½¹¥é•tˆ°Ñ•áÐ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ%¸ ‰Á…Ñ¡Ìéq¸€€€€€€´€¹¥Ñ¡Õˆ½Ý½É­™±½ÝÌ½‰…¡É…¥¸µ‰É¥¬µÈÄµÉ•¹‘•É•ÈµÉÕ¹Ñ¥µ”µ‘•‰Õ¥¹œ¹åµ°ˆ°Ñ•áÐ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ%¸ ‰ÉÕ¹}ÈÅ}É•¹‘•É•É}‘•‰Õœ¹Í ˆ°Ñ•áÐ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ%¸ ‰™¥¹…±¥é•}ÈÅ}É•¹‘•É•É}‘•‰Õœ¹Áäˆ°Ñ•áÐ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ9½Ñ%¸ ‰ÁÉ½©•Ð¹½‘½Ðˆ°Ñ•áÐ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ9½Ñ%¸ ‰É•¹‘•É•È‘•™…Õ±Ðˆ°Ñ•áÐ¹±½Ý•È ¤¤(()¥˜}}¹…µ•}|€ôô€‰}}µ…¥¹}|ˆè(€€€Õ¹¥ÑÑ•ÍÐ¹µ…¥¸ ¤(