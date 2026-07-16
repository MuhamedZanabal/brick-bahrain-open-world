#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "vertical_slice" / "composite_source_authority.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CompositeAuthorityToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.game = self.root / "game"
        self.out = self.root / "out"
        self.repo.mkdir()
        self.game.mkdir()
        self.out.mkdir()
        (self.game / "project.godot").write_text("config_version=5\n", encoding="utf-8")
        (self.game / "scripts").mkdir()
        (self.game / "scripts" / "example.gd").write_text("extends Node\n", encoding="utf-8")
        (self.repo / "tool.py").write_text("print('tool')\n", encoding="utf-8")
        self.contract = self.root / "authority.json"
        self.origins = self.root / "origins.json"
        self.write_contract()
        self.write_origins()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_contract(self, **overrides: object) -> None:
        data: dict[str, object] = {
            "schema_version": 1,
            "authority_classification": "deterministically_reconstructable_composite",
            "candidate_branch": "work/bahrain-brick-manama-souq-vertical-slice-v1",
            "base_authority": "fc8f00182f97c39015610d6603fa7c9c44364c5d",
            "frozen_premium_authority": "e26ec912db5c10d071a8e120010bdb5a9a136f17",
            "external_inputs": [
                {
                    "id": "assets436",
                    "immutable_locator": "https://example.invalid/assets.zip",
                    "sha256": "a" * 64,
                    "bytes": 10,
                    "provenance_authority": "ba31e620bdcbc2e8def98e2b888362620c26c4db",
                    "extraction_destination": "source",
                },
                {
                    "id": "historical_source",
                    "immutable_locator": "https://example.invalid/game.zip",
                    "sha256": "b" * 64,
                    "bytes": 20,
                    "provenance_authority": "v1.4.0.3-graphics-qa",
                    "extraction_destination": "game",
                },
            ],
            "toolchain": {
                "runner_image": "ubuntu-24.04@20260714.240.1",
                "os_release": "Ubuntu 24.04.4 LTS",
                "python": "3.12.3",
                "pillow": "12.3.0",
                "librsvg2_bin": "2.58.0+dfsg-1build1",
                "godot_version": "4.3.stable.official.77dcf97d8",
                "godot_archive_sha512": "c" * 128,
            },
            "reconstruction_scripts": [
                {"path": "tool.py", "sha256": sha256(self.repo / "tool.py")}
            ],
            "protected_files": [],
            "expected_final": {
                "manifest_sha256": None,
                "aggregate_tree_sha256": None,
                "file_count": None,
                "total_bytes": None,
            },
        }
        data.update(overrides)
        self.contract.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def write_origins(self, records: list[dict[str, str]] | None = None) -> None:
        if records is None:
            records = [
                {"path": "project.godot", "origin": "historical source"},
                {"path": "scripts/example.gd", "origin": "PR #59 checkout"},
            ]
        self.origins.write_text(
            json.dumps({"schema_version": 1, "files": records}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def run_tool(self, *args: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
        process = subprocess.run(
            [sys.executable, str(TOOL), *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        self.assertEqual(process.returncode, expect, process.stdout)
        return process

    def generate_manifest(self, label: str = "A") -> tuple[Path, Path]:
        manifest = self.out / f"manifest-{label}.json"
        report = self.out / f"report-{label}.json"
        self.run_tool(
            "manifest",
            "--contract", str(self.contract),
            "--repo-root", str(self.repo),
            "--game-root", str(self.game),
            "--origin-ledger", str(self.origins),
            "--candidate-commit", "1" * 40,
            "--output", str(manifest),
            "--report", str(report),
        )
        return manifest, report

    def test_contract_rejects_unpinned_toolchain_identity(self) -> None:
        data = json.loads(self.contract.read_text(encoding="utf-8"))
        data["toolchain"]["python"] = ""
        self.contract.write_text(json.dumps(data), encoding="utf-8")
        result = self.run_tool(
            "validate-contract", "--contract", str(self.contract), "--repo-root", str(self.repo), expect=2
        )
        self.assertIn("toolchain.python", result.stdout)

    def test_contract_rejects_reconstruction_script_change(self) -> None:
        (self.repo / "tool.py").write_text("print('changed')\n", encoding="utf-8")
        result = self.run_tool(
            "validate-contract", "--contract", str(self.contract), "--repo-root", str(self.repo), expect=2
        )
        self.assertIn("reconstruction script checksum mismatch", result.stdout)

    def test_verify_input_fails_on_checksum_or_size_change(self) -> None:
        payload = self.root / "payload.zip"
        payload.write_bytes(b"authority")
        result = self.run_tool(
            "verify-input",
            "--file", str(payload),
            "--expected-sha256", "0" * 64,
            "--expected-bytes", str(payload.stat().st_size),
            "--id", "assets436",
            "--output", str(self.out / "input.json"),
            expect=2,
        )
        self.assertIn("checksum mismatch", result.stdout)
        result = self.run_tool(
            "verify-input",
            "--file", str(payload),
            "--expected-sha256", sha256(payload),
            "--expected-bytes", str(payload.stat().st_size + 1),
            "--id", "assets436",
            "--output", str(self.out / "input.json"),
            expect=2,
        )
        self.assertIn("byte-size mismatch", result.stdout)

    def test_manifest_rejects_symbolic_links(self) -> None:
        os.symlink(self.game / "project.godot", self.game / "linked.godot")
        self.write_origins([
            {"path": "project.godot", "origin": "historical source"},
            {"path": "scripts/example.gd", "origin": "PR #59 checkout"},
            {"path": "linked.godot", "origin": "historical source"},
        ])
        result = self.run_tool(
            "manifest",
            "--contract", str(self.contract),
            "--repo-root", str(self.repo),
            "--game-root", str(self.game),
            "--origin-ledger", str(self.origins),
            "--candidate-commit", "1" * 40,
            "--output", str(self.out / "manifest.json"),
            "--report", str(self.out / "report.json"),
            expect=2,
        )
        self.assertIn("symbolic link", result.stdout)

    def test_manifest_rejects_case_collisions_and_unsafe_origin_paths(self) -> None:
        (self.game / "Scripts").mkdir()
        (self.game / "Scripts" / "EXAMPLE.gd").write_text("collision\n", encoding="utf-8")
        self.write_origins([
            {"path": "project.godot", "origin": "historical source"},
            {"path": "scripts/example.gd", "origin": "PR #59 checkout"},
            {"path": "Scripts/EXAMPLE.gd", "origin": "premium overlay"},
        ])
        result = self.run_tool(
            "manifest", "--contract", str(self.contract), "--repo-root", str(self.repo),
            "--game-root", str(self.game), "--origin-ledger", str(self.origins),
            "--candidate-commit", "1" * 40, "--output", str(self.out / "m.json"),
            "--report", str(self.out / "r.json"), expect=2,
        )
        self.assertIn("case-colliding", result.stdout)
        (self.game / "Scripts" / "EXAMPLE.gd").unlink()
        (self.game / "Scripts").rmdir()
        self.write_origins([
            {"path": "project.godot", "origin": "historical source"},
            {"path": "scripts/example.gd", "origin": "PR #59 checkout"},
            {"path": "../escape", "origin": "premium overlay"},
        ])
        result = self.run_tool(
            "manifest", "--contract", str(self.contract), "--repo-root", str(self.repo),
            "--game-root", str(self.game), "--origin-ledger", str(self.origins),
            "--candidate-commit", "1" * 40, "--output", str(self.out / "m.json"),
            "--report", str(self.out / "r.json"), expect=2,
        )
        self.assertIn("unsafe normalized path", result.stdout)

    def test_manifest_rejects_missing_unexpected_and_duplicate_origin_records(self) -> None:
        self.write_origins([{"path": "project.godot", "origin": "historical source"}])
        result = self.run_tool(
            "manifest", "--contract", str(self.contract), "--repo-root", str(self.repo),
            "--game-root", str(self.game), "--origin-ledger", str(self.origins),
            "--candidate-commit", "1" * 40, "--output", str(self.out / "m.json"),
            "--report", str(self.out / "r.json"), expect=2,
        )
        self.assertIn("unexpected files without origin", result.stdout)
        self.write_origins([
            {"path": "project.godot", "origin": "historical source"},
            {"path": "scripts/example.gd", "origin": "PR #59 checkout"},
            {"path": "missing.txt", "origin": "validation correction"},
        ])
        result = self.run_tool(
            "manifest", "--contract", str(self.contract), "--repo-root", str(self.repo),
            "--game-root", str(self.game), "--origin-ledger", str(self.origins),
            "--candidate-commit", "1" * 40, "--output", str(self.out / "m.json"),
            "--report", str(self.out / "r.json"), expect=2,
        )
        self.assertIn("origin records for missing files", result.stdout)
        self.write_origins([
            {"path": "project.godot", "origin": "historical source"},
            {"path": "project.godot", "origin": "premium overlay"},
            {"path": "scripts/example.gd", "origin": "PR #59 checkout"},
        ])
        result = self.run_tool(
            "manifest", "--contract", str(self.contract), "--repo-root", str(self.repo),
            "--game-root", str(self.game), "--origin-ledger", str(self.origins),
            "--candidate-commit", "1" * 40, "--output", str(self.out / "m.json"),
            "--report", str(self.out / "r.json"), expect=2,
        )
        self.assertIn("duplicate normalized origin path", result.stdout)

    def test_file_change_missing_file_and_unexpected_file_change_tree_authority(self) -> None:
        manifest_a, report_a = self.generate_manifest("A")
        a = json.loads(report_a.read_text(encoding="utf-8"))
        (self.game / "scripts" / "example.gd").write_text("extends Node2D\n", encoding="utf-8")
        manifest_b, report_b = self.generate_manifest("B")
        b = json.loads(report_b.read_text(encoding="utf-8"))
        self.assertNotEqual(a["aggregate_tree_sha256"], b["aggregate_tree_sha256"])
        self.assertNotEqual(sha256(manifest_a), sha256(manifest_b))
        (self.game / "scripts" / "example.gd").unlink()
        result = self.run_tool(
            "manifest", "--contract", str(self.contract), "--repo-root", str(self.repo),
            "--game-root", str(self.game), "--origin-ledger", str(self.origins),
            "--candidate-commit", "1" * 40, "--output", str(self.out / "m.json"),
            "--report", str(self.out / "r.json"), expect=2,
        )
        self.assertIn("origin records for missing files", result.stdout)
        (self.game / "scripts" / "example.gd").write_text("extends Node\n", encoding="utf-8")
        (self.game / "unexpected.txt").write_text("x", encoding="utf-8")
        result = self.run_tool(
            "manifest", "--contract", str(self.contract), "--repo-root", str(self.repo),
            "--game-root", str(self.game), "--origin-ledger", str(self.origins),
            "--candidate-commit", "1" * 40, "--output", str(self.out / "m.json"),
            "--report", str(self.out / "r.json"), expect=2,
        )
        self.assertIn("unexpected files without origin", result.stdout)

    def test_deterministic_archive_and_evidence_inventory(self) -> None:
        manifest, _ = self.generate_manifest("archive")
        archive_a = self.out / "source-a.zip"
        archive_b = self.out / "source-b.zip"
        report_a = self.out / "archive-a.json"
        report_b = self.out / "archive-b.json"
        for archive, report in ((archive_a, report_a), (archive_b, report_b)):
            self.run_tool(
                "archive", "--game-root", str(self.game), "--manifest", str(manifest),
                "--output", str(archive), "--report", str(report)
            )
        self.assertEqual(sha256(archive_a), sha256(archive_b))
        with zipfile.ZipFile(archive_a) as zf:
            self.assertEqual(sorted(zf.namelist()), ["project.godot", "scripts/example.gd"])
        retained = self.root / "retained"
        retained.mkdir()
        (retained / "manifest.json").write_bytes(manifest.read_bytes())
        (retained / "source.zip").write_bytes(archive_a.read_bytes())
        inventory = retained / "EVIDENCE_INVENTORY.json"
        self.run_tool("inventory", "--root", str(retained), "--output", str(inventory))
        self.run_tool("verify-inventory", "--root", str(retained), "--inventory", str(inventory))
        (retained / "source.zip").write_bytes(b"tampered")
        result = self.run_tool(
            "verify-inventory", "--root", str(retained), "--inventory", str(inventory), expect=2
        )
        self.assertIn("evidence inventory mismatch", result.stdout)

    def test_compare_rejects_different_reconstructions_and_accepts_identical_ones(self) -> None:
        run_a = self.root / "run-a"
        run_b = self.root / "run-b"
        run_a.mkdir()
        run_b.mkdir()
        for run in (run_a, run_b):
            (run / "FINAL_TREE_MANIFEST.json").write_text("{}\n", encoding="utf-8")
            (run / "FINAL_TREE_AUTHORITY.json").write_text(
                json.dumps({"file_count": 2, "total_bytes": 20, "aggregate_tree_sha256": "d" * 64}) + "\n",
                encoding="utf-8",
            )
            (run / "FROZEN_CONTROLS_PRE.json").write_text("{}\n", encoding="utf-8")
            (run / "FROZEN_CONTROLS_POST.json").write_text("{}\n", encoding="utf-8")
        self.run_tool(
            "compare", "--run-a", str(run_a), "--run-b", str(run_b),
            "--output", str(self.out / "comparison.json")
        )
        (run_b / "FINAL_TREE_MANIFEST.json").write_text('{"changed":true}\n', encoding="utf-8")
        result = self.run_tool(
            "compare", "--run-a", str(run_a), "--run-b", str(run_b),
            "--output", str(self.out / "comparison.json"), expect=2
        )
        self.assertIn("reconstruction mismatch", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
