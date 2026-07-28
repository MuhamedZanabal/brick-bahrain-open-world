#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "reports/graphics/r1/R1_ENGINE_UPGRADE_EXPERIMENT.json"
RESULT = ROOT / "reports/graphics/r1/R1_ENGINE_UPGRADE_RESULT.json"


class R1EngineUpgradeResultTest(unittest.TestCase):
    def test_corrected_attempt_is_adjudicative_and_complete(self) -> None:
        data = json.loads(EXPERIMENT.read_text())
        attempt = data["attempts"][-1]
        self.assertEqual(attempt["run_id"], 30376596221)
        self.assertEqual(attempt["artifact_id"], 8696886506)
        self.assertTrue(attempt["adjudicative"])
        self.assertTrue(attempt["import_completed"])
        self.assertTrue(attempt["apk_exports_executed"])
        self.assertTrue(attempt["android_targets_executed"])
        self.assertFalse(data["production_engine_adoption_authorized"])
        self.assertFalse(data["r1_exit_candidate"])

    def test_mixed_engine_result_is_diagnostic_only(self) -> None:
        data = json.loads(RESULT.read_text())
        self.assertEqual(data["gl"]["link_failure_count"], 44)
        self.assertFalse(data["gl"]["exit_criterion_met"])
        self.assertEqual(data["mobile"]["last_completed_frame"], 0)
        self.assertEqual(data["mobile"]["vulkan_queue_present_failure_count"], 6)
        self.assertFalse(data["mobile"]["exit_criterion_met"])
        self.assertEqual(
            data["final_engineering_decision"],
            "RETAIN_DIAGNOSTIC_EVIDENCE_REJECT_PRODUCTION_ENGINE_ADOPTION",
        )
        self.assertFalse(data["production_engine_adoption_authorized"])
        self.assertFalse(data["production_fix_authorized"])
        self.assertFalse(data["r1_exit_candidate"])


if __name__ == "__main__":
    unittest.main()
