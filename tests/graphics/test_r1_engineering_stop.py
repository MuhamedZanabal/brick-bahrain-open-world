#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STOP = ROOT / "reports/graphics/r1/R1_ENGINEERING_STOP.json"
CONTINUATION = ROOT / "reports/graphics/r1/R1_DIAGNOSTIC_CONTINUATION.json"
RUNNER = ROOT / "tools/graphics/run_r1_renderer_debug.sh"
RETRY = ROOT / "tools/graphics/run_r1_engine_retry.sh"
WORKFLOW = ROOT / ".github/workflows/bahrain-brick-r1-renderer-runtime-debugging.yml"


class R1FinalEngineeringStopTest(unittest.TestCase):
    def test_final_stop_preserves_all_stage_boundaries(self) -> None:
        data = json.loads(STOP.read_text())
        self.assertEqual(data["state"], "ENGINEERING_STOP")
        self.assertFalse(data["r1_exit_criteria_met"])
        self.assertFalse(data["production_fix_authorized"])
        self.assertIsNone(data["renderer_selected"])
        self.assertFalse(data["renderer_defaults_modified"])
        self.assertFalse(data["g1_authorized"])
        self.assertTrue(data["emulator_side_experiment_boundary_exhausted"])
        self.assertEqual(data["track_a_gl"]["engine_4_7_1_link_failures"], 44)
        self.assertEqual(data["track_b_mobile"]["engine_4_7_1_last_completed_frame"], 0)
        self.assertEqual(data["engine_comparison"]["adjudicative_attempt"]["run_id"], 30376596221)

    def test_continuation_is_closed_without_active_experiment(self) -> None:
        data = json.loads(CONTINUATION.read_text())
        self.assertEqual(data["state"], "COMPLETED_ENGINEERING_STOP")
        self.assertIsNone(data["active_experiment"])
        self.assertEqual(
            data["completed_experiment"]["decision"],
            "RETAIN_DIAGNOSTIC_EVIDENCE_REJECT_PRODUCTION_ENGINE_ADOPTION",
        )
        self.assertFalse(data["production_fix_authorized"])
        self.assertFalse(data["g1_authorized"])

    def test_execution_entrypoints_are_archived_guards(self) -> None:
        runner = RUNNER.read_text()
        retry = RETRY.read_text()
        self.assertIn("R1_ENGINEERING_STOP", runner)
        self.assertIn("exit 64", runner)
        self.assertIn("R1_ENGINE_RETRY_ARCHIVED", retry)
        self.assertIn("exit 64", retry)
        for text in (runner, retry):
            self.assertNotIn("emulator", text.lower().replace("emulator-side", ""))
            self.assertNotIn("Godot_v4", text)
            self.assertNotIn("apply_r1_", text)

    def test_workflow_is_static_and_non_android(self) -> None:
        text = WORKFLOW.read_text()
        self.assertIn("Bahrain Brick R1 Final Engineering Stop", text)
        self.assertIn("test_r1_engine_upgrade.py", text)
        self.assertIn("test_r1_engineering_stop.py", text)
        self.assertIn("R1_ENGINEERING_STOP", text)
        self.assertNotIn("actions/setup-java", text)
        self.assertNotIn("android-actions/setup-android", text)
        self.assertNotIn("upload-artifact", text)
        self.assertNotIn("Build and launch", text)


if __name__ == "__main__":
    unittest.main()
