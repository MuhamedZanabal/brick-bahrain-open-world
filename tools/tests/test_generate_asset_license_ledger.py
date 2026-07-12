from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

TOOLS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_DIR))

from generate_asset_license_ledger import generate_ledger, summary  # noqa: E402

MIT_TEXT = """MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy.
THE SOFTWARE IS PROVIDED \"AS IS\".
"""


class AssetLicenseLedgerTests(unittest.TestCase):
    def test_unlicensed_third_party_component_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            component = root / "addons" / "unknown_pack"
            component.mkdir(parents=True)
            (component / "model.obj").write_text("o model\n", encoding="utf-8")
            rows = generate_ledger(root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].status, "BLOCKED")
            self.assertEqual(rows[0].replacement_required, "yes")

    def test_recognized_mit_evidence_marks_component_verified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            component = root / "addons" / "mit_pack"
            component.mkdir(parents=True)
            (component / "LICENSE").write_text(MIT_TEXT, encoding="utf-8")
            (component / "shader.gdshader").write_text("shader_type spatial;\n", encoding="utf-8")
            rows = generate_ledger(root)
            by_path = {row.path: row for row in rows}
            shader = by_path["addons/mit_pack/shader.gdshader"]
            self.assertEqual(shader.license, "MIT")
            self.assertEqual(shader.status, "VERIFIED_EVIDENCE")
            self.assertEqual(shader.redistribution_allowed, "yes")
            self.assertEqual(shader.license_text_path, "addons/mit_pack/LICENSE")

    def test_project_asset_requires_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            asset = root / "assets" / "icon.png"
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b"synthetic")
            rows = generate_ledger(root)
            self.assertEqual(rows[0].status, "PROJECT_PROVENANCE_REQUIRED")
            self.assertEqual(rows[0].replacement_required, "review")

    def test_paths_are_unique_and_summary_counts_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            component = root / "vendor" / "pack"
            component.mkdir(parents=True)
            (component / "a.png").write_bytes(b"a")
            (component / "b.png").write_bytes(b"b")
            rows = generate_ledger(root)
            self.assertEqual(len({row.path for row in rows}), len(rows))
            self.assertEqual(summary(rows)["status_counts"]["BLOCKED"], 2)


if __name__ == "__main__":
    unittest.main()
