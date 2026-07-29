#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/graphics/finalize_r1_renderer_debug.py"


def load_module():
    spec = importlib.util.spec_from_file_location("finalize_r1_renderer_debug", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("module spec unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class R1FinalizerTest(unittest.TestCase):
    def test_gl_empty_overflow_proves_engine_generated_baseline_problem(self) -> None:
        module = load_module()
        scenarios = {
            "gl_unshaded": {"link_failures": 0, "uniform_overflow_failures": 0},
            "gl_empty": {"link_failures": 3, "uniform_overflow_failures": 3, "active_uniform_vectors": [261]},
            "gl_sun": {"link_failures": 3, "uniform_overflow_failures": 3, "active_uniform_vectors": [261]},
            "gl_sun_shadow": {"link_failures": 3, "uniform_overflow_failures": 3, "active_uniform_vectors": [261]},
            "gl_two_directional": {"link_failures": 3, "uniform_overflow_failures": 3, "active_uniform_vectors": [261]},
            "gl_two_directional_shadow": {"link_failures": 3, "uniform_overflow_failures": 3, "active_uniform_vectors": [261]},
            "gl_production": {"link_failures": 45, "uniform_overflow_failures": 45, "active_uniform_vectors": [261]},
        }
        result = module.classify_gl(scenarios)
        self.assertTrue(result["diagnosis_proven"])
        self.assertEqual(result["earliest_failing_mode"], "gl_empty")
        self.assertEqual(result["root_cause"], "GLES3_SHADED_SCENE_SHADER_UNIFORM_VECTOR_OVERFLOW")
        self.assertFalse(result["production_fix_authorized"])

    def test_mobile_render_disabled_control_proves_render_pipeline_stall(self) -> None:
        module = load_module()
        baseline = {
            "records": [
                {"local_frame": 0, "wall_ms": 0, "frames_drawn": 0},
                {"local_frame": 20, "wall_ms": 180000, "frames_drawn": 20},
            ],
            "complete": False,
        }
        control = {
            "records": [
                {"local_frame": 0, "wall_ms": 0, "frames_drawn": 0},
                {"local_frame": 300, "wall_ms": 1800, "frames_drawn": 0},
            ],
            "complete": True,
        }
        result = module.classify_mobile(baseline, control, baseline_log="", baseline_backtrace="")
        self.assertEqual(result["classification"], "RENDER_PIPELINE_STALL")
        self.assertTrue(result["diagnosis_proven"])
        self.assertFalse(result["production_fix_authorized"])

    def test_mobile_without_unique_control_result_is_unknown(self) -> None:
        module = load_module()
        baseline = {"records": [{"local_frame": 0, "wall_ms": 0}], "complete": False}
        control = {"records": [{"local_frame": 0, "wall_ms": 0}], "complete": False}
        result = module.classify_mobile(baseline, control, baseline_log="", baseline_backtrace="")
        self.assertEqual(result["classification"], "UNKNOWN_RUNTIME_BLOCK")
        self.assertFalse(result["diagnosis_proven"])

    def test_main_writes_governing_gate_and_no_fix_authority(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw"
            output = Path(tmp) / "reports"
            for mode in module.GL_MODES:
                scenario = raw / "track_a" / mode
                scenario.mkdir(parents=True)
                (scenario / "logcat_full.txt").write_text("R1_GL_SCENARIO_COMPLETE mode=%s\n" % mode)
            for mode in module.MOBILE_MODES:
                scenario = raw / "track_b" / mode
                scenario.mkdir(parents=True)
                (scenario / "logcat_full.txt").write_text("")
                (scenario / "r1_mobile_progress.json").write_text(json.dumps({"records": [], "complete": False}))
            result = module.finalize(raw, output)
            self.assertEqual(result["governing_gate"], "G0_EVIDENCE_INSUFFICIENT")
            self.assertFalse(result["production_fix_authorized"])
            self.assertTrue((output / "R1_DIAGNOSTIC_REPORT.json").is_file())


if __name__ == "__main__":
    unittest.main()
