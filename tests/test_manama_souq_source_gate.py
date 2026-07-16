#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "manama-souq-vertical-slice.yml"
DRIVER = ROOT / "tools" / "vertical_slice" / "run_manama_souq_source_gate.sh"


class ManamaSouqSourceGateContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not WORKFLOW.is_file():
            raise AssertionError(f"source workflow missing: {WORKFLOW}")
        if not DRIVER.is_file():
            raise AssertionError(f"source driver missing: {DRIVER}")
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.driver = DRIVER.read_text(encoding="utf-8")

    def test_workflow_is_isolated_and_checksum_pinned(self) -> None:
        self.assertIn("work/bahrain-brick-manama-souq-vertical-slice-v1", self.workflow)
        self.assertIn("work/bahrain-brick-asset-lab-integration-v1", self.workflow)
        self.assertIn("SOURCE_ARTIFACT_ID: '8360668742'", self.workflow)
        self.assertIn("5c4d8ac4497eda7752058424062a74a97c1f6f5e0c9a1ff393abac2a2c7c828a", self.workflow)
        self.assertIn("permissions:\n  contents: read\n  actions: read", self.workflow)

    def test_workflow_recovers_exact_matrix_and_protected_authority(self) -> None:
        for fragment in (
            "FULL_ASSET_MATRIX_COMPLETION.json",
            "total_glbs']==436",
            "unique_glb_hashes']==436",
            "FROZEN_CONTROLS_SOUQ_PRE.json",
            "FROZEN_CONTROLS_SOUQ_POST.json",
            "cmp \"$REPORTS/FROZEN_CONTROLS_SOUQ_PRE.json\" \"$REPORTS/FROZEN_CONTROLS_SOUQ_POST.json\"",
        ):
            self.assertIn(fragment, self.workflow)

    def test_driver_runs_all_new_runtime_tests_and_inherited_regressions(self) -> None:
        for script in (
            "karak_delivery_mission_runtime.gd",
            "manama_souq_layout_runtime.gd",
            "souq_population_runtime.gd",
            "karak_delivery_hud_runtime.gd",
            "manama_souq_slice_runtime.gd",
        ):
            self.assertIn(script, self.driver)
        self.assertIn("run_game_regressions.sh", self.driver)
        self.assertIn("KARAK_DELIVERY_RUNTIME_PASS", self.driver)
        self.assertIn("MANAMA_SOUQ_LAYOUT_RUNTIME_PASS", self.driver)
        self.assertIn("SOUQ_POPULATION_RUNTIME_PASS", self.driver)
        self.assertIn("KARAK_DELIVERY_HUD_RUNTIME_PASS", self.driver)
        self.assertIn("MANAMA_SOUQ_SLICE_RUNTIME_PASS", self.driver)

    def test_gate_fails_on_parse_missing_resource_or_critical_runtime_error(self) -> None:
        for pattern in (
            "SCRIPT ERROR",
            "Parse Error",
            "Failed to load script",
            "Can't open dynamic library",
            "FATAL",
        ):
            self.assertIn(pattern, self.driver)
        self.assertIn("set -euo pipefail", self.driver)

    def test_evidence_upload_is_unconditional_and_no_merge_action_exists(self) -> None:
        self.assertIn("if: always()", self.workflow)
        self.assertIn("actions/upload-artifact@65462800fd760344b1a7b4382951275a0abb4808", self.workflow)
        self.assertNotIn("merge_pull_request", self.workflow)
        self.assertNotIn("gh pr merge", self.workflow)


if __name__ == "__main__":
    unittest.main(verbosity=2)
