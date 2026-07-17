#!/usr/bin/env python3
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "tools" / "vertical_slice" / "run_manama_souq_gate4_export_diagnostic.sh"

SAMPLE = '''Installed packages:
  Path                               | Version       | Description
  -------                            | -------       | -------
  build-tools;34.0.0                 | 34.0.0        | Android SDK Build-Tools 34
  platform-tools                     | 37.0.0        | Android SDK Platform-Tools
  platforms;android-34               | 3             | Android SDK Platform 34
'''


class ManamaSouqGate4SdkLedgerContractTests(unittest.TestCase):
    def test_installed_package_parser_accepts_sdkmanager_table_indentation(self) -> None:
        wrapper = WRAPPER.read_text(encoding="utf-8")
        self.assertIn("SDK package identity parser indentation defect", wrapper)
        self.assertIn(r"^\\s*{re.escape(name)}", wrapper)
        pattern = re.compile(r"^\s*build\-tools;34\.0\.0\s+\|\s+([^|\s]+)", re.M)
        match = pattern.search(SAMPLE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "34.0.0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
