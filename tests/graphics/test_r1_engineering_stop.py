#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STOP = ROOT / "reports/graphics/r1/R1_ENGINEERING_STOP.json"
CONTINUATION = ROOT / "reports/graphics/r1/R1_DIAGNOSTIC_CONTINUATION.json"
RUNNER = ROOT / "tools/graphics/run_r1_renderer_debug.sh"
WORKFLOW = ROOT / ".github/workflows/bahrain-brick-r1-renderer-runtime-debugging.yml"


class R1DiagnosticContinuationTest(unittest.TestCase):
    def test_historical_stop_is_reconciled_with_render_scale_evidence(self) -> None:
        data = json.loads(STOP.read_text())
        self.assertEqual(data["state"], "ENGINEERING_STOP_SUPERSEDED")
        self.assertTrue(data["superseded_by_user_continuation"])
        self.assertFalse(data["r1_exit_criteria_met"])
        self.assertFalse(data["production_fix_authorized"])
        self.assertIsNone(data["renderer_selected"])
        self.assertFalse(data["renderer_defaults_modified"])
        self.assertFalse(data["g1_authorized"])
        mobile = data["track_b_mobile"]
        self.assertEqual(mobile["failed_correction_count"], 4)
        self.assertTrue(mobile["render_scale_experiment_executed"])
        self.assertEqual(mobile["corrections"][-1]["run_id"], 30313623186)
        self.assertEqual(mobile["corrections"][-1]["artifact_id"], 8671766622)

    def test_continuation_is_diagnostic_only_and_single_variable(self) -> None:
        data = json.loads(CONTINUATION.read_text())
        self.assertEqual(data["state"], "IN_PROGRESS")
        self.assertFalse(data["production_fix_authorized"])
        self.assertIsNone(data["renderer_selected"])
        self.assertFalse(data["renderer_defaults_modified"])
        self.assertFalse(data["g1_authorized"])
        active = data["active_experiment"]
        self.assertEqual(active["id"], "MOBILE_ENVIRONMENT_TONEMAPPER_FILMIC_TO_LINEAR")
        self.assertFalse(active["prior_shadow_changes_stacked"])
        self.assertFalse(active["render_scale_change_stacked"])
        self.assertFalse(active["gl_change_stacked"])
        self.assertFalse(active["gameplay_modified"])
        self.assertFalse(active["renderer_default_modified"])

    def test_runner_and_workflow_execute_only_the_active_mobile_experiment(self) -> None:
        runner = RUNNER.read_text()
        workflow = WORKFLOW.read_text()
        self.assertIn("apply_r1_mobile_tonemapper_fix.py", runner)
        self.assertNotIn("R1_ENGINEERING_STOP", runner)
        self.assertIn("Bahrain Brick R1 Mobile Tonemapper", workflow)
        self.assertIn("Build and launch Mobile only", workflow)
        self.assertNotIn("gl_production", runner)


if __name__ == "__main__":
    unittest.main()
