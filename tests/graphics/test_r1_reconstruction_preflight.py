#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/graphics/patch_r1_reconstruction_preflight.py"


def load_module():
    spec = importlib.util.spec_from_file_location("patch_r1_reconstruction_preflight", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("module spec unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def record(path: str, data: bytes) -> dict[str, object]:
    return {
        "path": path,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "origin": "PR #59 checkout",
    }


class ReconstructionPreflightTest(unittest.TestCase):
    def test_exact_manifest_tree_passes(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            game = root / "game"
            game.mkdir()
            files = {"project.godot": b"config_version=5\n", "scripts/example.gd": b"extends Node\n"}
            for rel, data in files.items():
                path = game / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            manifest = {
                "schema_version": 1,
                "file_count": len(files),
                "total_bytes": sum(len(data) for data in files.values()),
                "aggregate_tree_sha256": "a" * 64,
                "files": [record(rel, data) for rel, data in sorted(files.items())],
            }
            manifest_path = root / "FINAL_TREE_MANIFEST.json"
            manifest_path.write_text(json.dumps(manifest))
            output = root / "SOURCE_TREE_EQUIVALENCE.json"
            result = module.verify_reconstruction_manifest(manifest_path, game, output)
            self.assertTrue(result["passed"])
            self.assertTrue(result["production_source_byte_equivalent"])
            self.assertEqual(result["expected_file_count"], 2)
            self.assertEqual(result["actual_file_count"], 2)
            self.assertEqual(result["authority_class"], "RECONSTRUCTION_FINAL_TREE_MANIFEST")

    def test_modified_missing_and_unexpected_paths_fail(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            game = root / "game"
            game.mkdir()
            expected = {"project.godot": b"expected\n", "scripts/missing.gd": b"missing\n"}
            (game / "project.godot").write_bytes(b"modified\n")
            (game / "unexpected.txt").write_text("unexpected\n")
            manifest = {
                "schema_version": 1,
                "file_count": len(expected),
                "total_bytes": sum(len(data) for data in expected.values()),
                "aggregate_tree_sha256": "b" * 64,
                "files": [record(rel, data) for rel, data in sorted(expected.items())],
            }
            manifest_path = root / "FINAL_TREE_MANIFEST.json"
            manifest_path.write_text(json.dumps(manifest))
            output = root / "SOURCE_TREE_EQUIVALENCE.json"
            with self.assertRaises(ValueError):
                module.verify_reconstruction_manifest(manifest_path, game, output)
            report = json.loads(output.read_text())
            self.assertFalse(report["passed"])
            self.assertEqual(report["missing_paths"], ["scripts/missing.gd"])
            self.assertEqual(report["unexpected_paths"], ["unexpected.txt"])
            self.assertIn("project.godot", report["mismatched_paths"])

    def test_patched_runner_uses_final_tree_manifest_not_post_import_inventory(self) -> None:
        module = load_module()
        runner = Path("/tmp/nonexistent")
        self.assertIn("FINAL_TREE_MANIFEST.json", module.NEW_BLOCK)
        self.assertIn("SOURCE_TREE_EQUIVALENCE.json", module.NEW_BLOCK)
        self.assertNotIn("shared_import_equivalence.json", module.NEW_BLOCK)
        self.assertIn("R1_ACTUAL_IMAGE_VERSION", module.NEW_BLOCK)
        self.assertFalse(runner.exists())


if __name__ == "__main__":
    unittest.main()
