from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "asset_lab"
sys.path.insert(0, str(TOOLS_DIR))

from check_repository_binaries import scan_repository  # noqa: E402
from validate_manifest_schema import validate_manifest_tree  # noqa: E402


class BinaryPolicyTests(unittest.TestCase):
    def test_rejects_oversized_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "asset_lab" / "exports" / "glb" / "too_large.glb"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"x" * 32)
            report = scan_repository(root, limits={".glb": 16}, duplicate_min_bytes=8)
            self.assertFalse(report["passed"])
            self.assertEqual(report["oversized"][0]["path"], "asset_lab/exports/glb/too_large.glb")

    def test_rejects_duplicate_binary_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = b"same-binary-payload"
            for name in ("a.glb", "b.glb"):
                path = root / "asset_lab" / "exports" / "glb" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
            report = scan_repository(root, limits={".glb": 1024}, duplicate_min_bytes=8)
            self.assertFalse(report["passed"])
            self.assertEqual(len(report["duplicates"]), 1)
            self.assertEqual(report["duplicates"][0]["paths"], [
                "asset_lab/exports/glb/a.glb",
                "asset_lab/exports/glb/b.glb",
            ])

    def test_small_binary_duplicates_do_not_trip_duplicate_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("a.png", "b.png"):
                path = root / "asset_lab" / "evidence" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"tiny")
            report = scan_repository(root, limits={".png": 1024}, duplicate_min_bytes=8)
            self.assertTrue(report["passed"])


class ManifestBootstrapTests(unittest.TestCase):
    def test_empty_phase2_manifest_tree_passes_when_allow_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "asset_lab" / "manifests").mkdir(parents=True)
            report = validate_manifest_tree(root, allow_empty=True)
            self.assertTrue(report["passed"])
            self.assertEqual(report["state"], "EMPTY_BOOTSTRAP")

    def test_manifest_without_schema_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = root / "asset_lab" / "manifests" / "assets"
            assets.mkdir(parents=True)
            (assets / "candidate.json").write_text("{}\n", encoding="utf-8")
            report = validate_manifest_tree(root, allow_empty=True)
            self.assertFalse(report["passed"])
            self.assertEqual(report["state"], "SCHEMA_MISSING")

    def test_invalid_json_fails_before_semantic_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema_dir = root / "asset_lab" / "manifests" / "schema"
            assets = root / "asset_lab" / "manifests" / "assets"
            schema_dir.mkdir(parents=True)
            assets.mkdir(parents=True)
            (schema_dir / "asset-manifest.schema.json").write_text(json.dumps({"type": "object"}), encoding="utf-8")
            (assets / "candidate.json").write_text("{not-json", encoding="utf-8")
            report = validate_manifest_tree(root, allow_empty=True)
            self.assertFalse(report["passed"])
            self.assertEqual(report["state"], "INVALID_JSON")


if __name__ == "__main__":
    unittest.main()
