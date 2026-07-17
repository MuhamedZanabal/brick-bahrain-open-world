#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "tools" / "vertical_slice" / "run_manama_souq_gate4_export_diagnostic.sh"


class ManamaSouqGate4PatchMaterializationContractTests(unittest.TestCase):
    def test_patch_generator_fails_immediately_and_uses_unique_markers(self) -> None:
        text = WRAPPER.read_text(encoding="utf-8")
        self.assertIn("set -euo pipefail", text)
        self.assertIn("asset_start_marker", text)
        self.assertIn("asset_end_marker", text)
        self.assertIn("asset_start=text.find(asset_start_marker)", text)
        self.assertIn("asset_end=text.find(asset_end_marker, asset_start)", text)
        self.assertIn("if asset_start < 0 or asset_end < 0", text)
        self.assertIn("target.is_file()", text)
        self.assertNotIn("asset_count=text.count(asset_packaging_old)", text)
        self.assertNotIn(".replace(asset_packaging_old,asset_packaging_new,1)", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
