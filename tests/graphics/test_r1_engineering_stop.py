#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STOP = ROOT / "reports/graphics/r1/R1_ENGINEERING_STOP.json"
RUNNER = ROOT / "tools/graphics/run_r1_renderer_debug.sh"
WORKFLOW = ROOT / ".github/workflows/bahrain-brick-r1-renderer-runtime-debugging.yml"


class R1EngineeringStopTest(unittest.TestCase):
    def test_stop_report_preserves_stage_boundaries(self) -> None:
        data = json.loads(STOP.read_text())
        self.assertEqual(data["state"], "ENGINEERING_STOP")
        self.assertFalse(data["r1_exit_criteria_met"])
        self.assertFalse(data["production_fix_authorized"])
        self.assertIsNone(data["renderer_selected"])
        self.assertFalse(data["renderer_defaults_modified"])
        self.assertFalse(data["g1_authorized"])
        self.assertEqual(data["track_b_mobile"]["failed_correction_count"], 3)
        self.assertFalse(data["track_b_mobile"]["render_scale_experiment_executed"])

    def test_runner_is_an_explicit_non_executing_guard(self) -> None:
        text = RUNNER.read_text()
        self.assertIn("R1_ENGINEERING_STOP", text)
        self.assertIn("exit 64", text)
        self.assertNotIn("apply_r1_mobile_", text)
        self.assertNotIn("emulator", text.lower())
        self.assertNotIn("Godot_v4", text)

    def test_workflow_is_static_and_has_no_android_execution(self) -> None:
        text = WORKFLOW.read_text()
        self.assertIn("Bahrain Brick R1 Engineering Stop", text)
        self.assertIn("test_r1_engineering_stop.py", text)
        self.assertIn("python3 -m json.tool", text)
        self.assertNotIn("actions/setup-java", text)
        self.assertNotIn("android-actions/setup-android", text)
        self.assertNotIn("Build and launch Mobile", text)
        self.assertNotIn("upload-artifact", text)


if __name__ == "__main__":
    unittest.main()
