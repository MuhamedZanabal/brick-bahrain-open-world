#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STOP = ROOT / "reports/graphics/r1/R1_ENGINEERING_STOP.json"
CONTINUATION = ROOT / "reports/graphics/r1/R1_DIAGNOSTIC_CONTINUATION.json"
ENGINE = ROOT / "reports/graphics/r1/R1_ENGINE_UPGRADE_EXPERIMENT.json"
RUNNER = ROOT / "tools/graphics/run_r1_renderer_debug.sh"
WORKFLOW = ROOT / ".github/workflows/bahrain-brick-r1-renderer-runtime-debugging.yml"


class R1EngineBoundaryContinuationTest(unittest.TestCase):
    def test_historical_stop_contains_all_completed_mobile_corrections(self) -> None:
        data = json.loads(STOP.read_text())
        self.assertEqual(data["state"], "ENGINEERING_STOP_SUPERSEDED")
        self.assertFalse(data["r1_exit_criteria_met"])
        self.assertFalse(data["production_fix_authorized"])
        self.assertIsNone(data["renderer_selected"])
        self.assertFalse(data["renderer_defaults_modified"])
        self.assertFalse(data["g1_authorized"])
        mobile = data["track_b_mobile"]
        self.assertEqual(mobile["failed_correction_count"], 5)
        self.assertTrue(mobile["tonemapper_experiment_executed"])
        self.assertEqual(mobile["corrections"][-1]["run_id"], 30370527664)
        self.assertEqual(mobile["corrections"][-1]["artifact_id"], 8693475134)

    def test_active_continuation_is_engine_only_and_non_stacking(self) -> None:
        continuation = json.loads(CONTINUATION.read_text())
        authority = json.loads(ENGINE.read_text())
        self.assertEqual(continuation["active_experiment"]["id"], "GODOT_ENGINE_4_3_TO_4_7_1_STABLE")
        self.assertEqual(authority["engine_after"], "4.7.1-stable")
        self.assertEqual(authority["targets"][0]["mode"], "gl_production")
        self.assertEqual(authority["targets"][1]["mode"], "mobile_baseline")
        self.assertFalse(authority["project_corrections_stacked"])
        self.assertFalse(authority["renderer_defaults_modified"])
        self.assertFalse(authority["gameplay_modified"])
        self.assertFalse(authority["production_fix_authorized"])
        self.assertFalse(authority["g1_authorized"])

    def test_runner_and_workflow_execute_only_engine_comparison(self) -> None:
        runner = RUNNER.read_text()
        workflow = WORKFLOW.read_text()
        self.assertIn('GODOT_RELEASE="4.7.1-stable"', runner)
        self.assertIn("run_target GL gl_production", runner)
        self.assertIn("run_target MOBILE mobile_baseline", runner)
        self.assertNotIn("apply_r1_mobile_", runner)
        self.assertNotIn("apply_r1_gl_compatibility_fix.py", runner)
        self.assertIn("Bahrain Brick R1 Engine 4.7.1 Comparison", workflow)
        self.assertIn("test_r1_engine_upgrade.py", workflow)
        self.assertNotIn("Tonemapper", workflow)


if __name__ == "__main__":
    unittest.main()
