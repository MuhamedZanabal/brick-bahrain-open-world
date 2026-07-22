#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTHORITY_PATH = ROOT / "authority" / "bahrain_brick_graphics_upgrade_v1.json"
PROJECT_PATH = ROOT / "project.godot"
EXPORT_PATH = ROOT / "export_presets.cfg"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_text(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def git_bytes(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class GraphicsUpgradeG0ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        for path in (AUTHORITY_PATH, PROJECT_PATH, EXPORT_PATH):
            if not path.is_file():
                raise AssertionError(f"required G0 authority input is missing: {path}")
        cls.authority = json.loads(AUTHORITY_PATH.read_text(encoding="utf-8"))
        cls.project = PROJECT_PATH.read_text(encoding="utf-8")
        cls.export = EXPORT_PATH.read_text(encoding="utf-8")

    def test_pr59_frozen_anchor_is_exact(self) -> None:
        pr = self.authority["parent_pull_request"]
        self.assertEqual(pr["number"], 59)
        self.assertEqual(pr["expected_state"], "open")
        self.assertTrue(pr["expected_draft"])
        self.assertFalse(pr["expected_merged"])
        self.assertEqual(
            pr["expected_head_sha"],
            "5b4e2466ef84f3984f3bf336b31925d4d2e97a7f",
        )
        self.assertEqual(
            pr["expected_base_sha"],
            "fc8f00182f97c39015610d6603fa7c9c44364c5d",
        )
        self.assertEqual(pr["expected_changed_file_count"], 54)

    def test_child_branch_descends_from_frozen_pr59_head(self) -> None:
        frozen_head = self.authority["parent_pull_request"]["expected_head_sha"]
        result = git_text("merge-base", "--is-ancestor", frozen_head, "HEAD")
        if result.returncode != 0 and "not a valid object name" in result.stderr:
            self.skipTest("full git history is unavailable; CI must use fetch-depth: 0")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_protected_files_match_exact_frozen_git_objects(self) -> None:
        frozen_head = self.authority["parent_pull_request"]["expected_head_sha"]
        protected = [item["path"] for item in self.authority["protected_files"]]
        self.assertIn("scripts/world.gd", protected)
        self.assertEqual(len(protected), len(set(protected)), "duplicate protected path")
        policy = self.authority["protected_file_policy"]
        self.assertEqual(
            policy["hash_authority"],
            "exact bytes from parent_pull_request.expected_head_sha Git objects",
        )
        self.assertTrue(policy["reconstructed_hashes_are_not_git_hashes"])

        for relative_path in protected:
            frozen = git_bytes("show", f"{frozen_head}:{relative_path}")
            self.assertEqual(
                frozen.returncode,
                0,
                f"protected file missing from exact frozen tree: {relative_path}: "
                f"{frozen.stderr.decode('utf-8', errors='replace')}",
            )
            current_path = ROOT / relative_path
            self.assertTrue(current_path.is_file(), f"protected file missing at HEAD: {relative_path}")
            current = current_path.read_bytes()
            self.assertEqual(
                current,
                frozen.stdout,
                f"protected bytes changed: {relative_path}; frozen_sha256={sha256_bytes(frozen.stdout)} "
                f"current_sha256={sha256_bytes(current)}",
            )

    def test_no_protected_file_changed_since_pr59_head(self) -> None:
        frozen_head = self.authority["parent_pull_request"]["expected_head_sha"]
        result = git_text("diff", "--name-only", f"{frozen_head}...HEAD")
        if result.returncode != 0 and "unknown revision" in result.stderr:
            self.skipTest("full git history is unavailable; CI must use fetch-depth: 0")
        self.assertEqual(result.returncode, 0, result.stderr)
        changed = {line.strip() for line in result.stdout.splitlines() if line.strip()}
        protected = {item["path"] for item in self.authority["protected_files"]}
        self.assertFalse(
            changed & protected,
            f"graphics branch changed protected authorities: {sorted(changed & protected)}",
        )

    def test_renderer_conflict_remains_explicit_and_unresolved(self) -> None:
        gate = self.authority["renderer_gate"]
        self.assertEqual(gate["state"], "UNRESOLVED")
        self.assertIn('config/features=PackedStringArray("4.3", "Forward Plus")', self.project)
        self.assertIn('renderer/rendering_method="gl_compatibility"', self.project)
        self.assertIn('renderer/rendering_method.mobile="gl_compatibility"', self.project)
        self.assertEqual(gate["candidates"], ["gl_compatibility", "mobile"])

    def test_startup_brand_and_resolution_baseline_are_recorded(self) -> None:
        self.assertIn('config/name="Brick Bahrain: Open World"', self.project)
        self.assertIn('run/main_scene="res://scenes/splash_screen.tscn"', self.project)
        self.assertIn("window/size/viewport_width=1920", self.project)
        self.assertIn("window/size/viewport_height=1080", self.project)
        self.assertIn('window/stretch/aspect="expand"', self.project)

    def test_android_export_baseline_is_recorded(self) -> None:
        required = (
            'architectures/armeabi-v7a=true',
            'architectures/arm64-v8a=true',
            'architectures/x86_64=true',
            'screen/immersive_mode=true',
            'permissions/access_network_state=true',
            'permissions/internet=true',
        )
        for fragment in required:
            self.assertIn(fragment, self.export)

    def test_g0_blocks_visual_asset_ingestion_and_gameplay_edits(self) -> None:
        policy = self.authority["graphics_scope_policy"]
        self.assertFalse(policy["large_asset_ingestion_allowed"])
        self.assertFalse(policy["gameplay_changes_allowed"])
        self.assertFalse(policy["pr59_changes_allowed"])
        self.assertFalse(policy["cosmetic_work_allowed_before_g0_gate"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
