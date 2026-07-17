#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "manama-souq-gate4-android-export.yml"


class ManamaSouqGate4CompactDiagnosticsContractTests(unittest.TestCase):
    def test_each_export_uploads_compact_failure_diagnostics_separately(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for slot in ("primary", "secondary"):
            self.assertIn(f"Upload {slot} compact failure diagnostics", workflow)
            self.assertIn(
                f"bahrain-brick-pr59-gate4-{slot}-diagnostics-${{{{ github.run_id }}}}",
                workflow,
            )
            self.assertIn(
                f"build/gate4-{slot}-evidence/reports/GATE4_FAILURE.json",
                workflow,
            )
            self.assertIn(
                f"build/gate4-{slot}-evidence/reports/GATE4_PREREQUISITES.json",
                workflow,
            )
            self.assertIn(
                f"build/gate4-{slot}-evidence/logs/gate4-runner-xtrace.log",
                workflow,
            )
        self.assertIn("if-no-files-found: warn", workflow)
        self.assertIn("compression-level: 9", workflow)


if __name__ == "__main__":
    unittest.main(verbosity=2)
