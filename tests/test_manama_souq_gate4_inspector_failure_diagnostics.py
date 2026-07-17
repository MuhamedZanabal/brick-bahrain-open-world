#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from test_manama_souq_gate4_apk_inspector_direct_assets import InspectorFixture  # noqa: E402


class ManamaSouqGate4InspectorFailureDiagnosticsTests(unittest.TestCase):
    def test_failed_inspection_emits_exact_failure_categories_to_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = InspectorFixture(Path(temporary))
            fixture.write_inventory(files=set(), raw_files=set(), aliases=[])
            result, _, _, record = fixture.inspect()
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(record["passed"])
            self.assertIn('"archive_failures"', result.stderr)
            self.assertIn('"packaged_resource_failures"', result.stderr)
            self.assertIn('"signing_failures"', result.stderr)
            self.assertIn("empty normalized project-resource inventory", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
