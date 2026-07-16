#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "manama-souq-vertical-slice.yml"
DRIVER = ROOT / "tools" / "vertical_slice" / "reconstruct_manama_souq_composite.sh"
TOOL = ROOT / "tools" / "vertical_slice" / "composite_source_authority.py"
CONTRACT = ROOT / "authority" / "manama_souq_composite_source.json"


class ManamaSouqSourceGateContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        for path in (WORKFLOW, DRIVER, TOOL, CONTRACT):
            if not path.is_file():
                raise AssertionError(f"authority component missing: {path}")
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.driver = DRIVER.read_text(encoding="utf-8")
        cls.tool = TOOL.read_text(encoding="utf-8")
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_workflow_is_read_only_and_uses_durable_checksum_pinned_inputs(self) -> None:
        self.assertIn("work/bahrain-brick-manama-souq-vertical-slice-v1", self.workflow)
        self.assertIn("work/bahrain-brick-asset-lab-integration-v1", self.workflow)
        self.assertIn("permissions:\n  contents: read", self.workflow)
        self.assertNotIn("contents: write", self.workflow)
        self.assertNotIn("SOURCE_ARTIFACT_ID", self.workflow)
        self.assertNotIn("8360668742", self.workflow)
        self.assertIn("bahrain-brick-full-asset-matrix-authority-76964c58c283caca.zip", self.workflow)
        self.assertIn("76964c58c283cacaee137152189727d678aa83230d7211dc6a15aa9af9d4a67a", self.workflow)
        self.assertIn("5c4d8ac4497eda7752058424062a74a97c1f6f5e0c9a1ff393abac2a2c7c828a", self.workflow)

    def test_workflow_runs_two_independent_reconstructions_and_compares_them(self) -> None:
        for fragment in (
            "authority_run_a:",
            "authority_run_b:",
            "authority_compare:",
            "reconstruct_manama_souq_composite.sh A",
            "reconstruct_manama_souq_composite.sh B",
            "composite_source_authority.py compare",
        ):
            self.assertIn(fragment, self.workflow)
        for fragment in (
            "FINAL_TREE_MANIFEST.json",
            "FINAL_TREE_AUTHORITY.json",
            "MANAMA_SOUQ_COMPOSITE_SOURCE.zip",
            "EVIDENCE_INVENTORY.json",
        ):
            self.assertIn(fragment, self.driver)
        self.assertNotIn("Run full Manama Souq source and Godot gate", self.workflow)
        self.assertNotIn("run_manama_souq_source_gate.sh", self.workflow)
        self.assertNotIn("--editor --import", self.workflow)
        self.assertNotIn("android", self.workflow.lower())

    def test_contract_pins_every_required_authority_and_tool_identity(self) -> None:
        self.assertEqual(
            self.contract["base_authority"], "fc8f00182f97c39015610d6603fa7c9c44364c5d"
        )
        self.assertEqual(
            self.contract["frozen_premium_authority"], "e26ec912db5c10d071a8e120010bdb5a9a136f17"
        )
        inputs = {item["id"]: item for item in self.contract["external_inputs"]}
        self.assertEqual(
            inputs["assets436"]["sha256"],
            "76964c58c283cacaee137152189727d678aa83230d7211dc6a15aa9af9d4a67a",
        )
        self.assertEqual(inputs["assets436"]["bytes"], 469706251)
        self.assertEqual(
            inputs["historical_source"]["sha256"],
            "5c4d8ac4497eda7752058424062a74a97c1f6f5e0c9a1ff393abac2a2c7c828a",
        )
        toolchain = self.contract["toolchain"]
        self.assertEqual(toolchain["runner_image"], "ubuntu-24.04@20260714.240.1")
        self.assertEqual(toolchain["os_release"], "Ubuntu 24.04.4 LTS")
        self.assertEqual(toolchain["python"], "3.12.3")
        self.assertEqual(toolchain["pillow"], "12.3.0")
        self.assertEqual(toolchain["librsvg2_bin"], "2.58.0+dfsg-1build1")
        self.assertEqual(toolchain["godot_version"], "4.3.stable.official.77dcf97d8")
        self.assertRegex(toolchain["godot_archive_sha512"], r"^[0-9a-f]{128}$")

    def test_driver_fails_closed_before_assembly_and_retains_complete_evidence(self) -> None:
        for fragment in (
            "validate-contract",
            "verify-input",
            "dpkg-query",
            "Pillow",
            "ORIGIN_LEDGER.json",
            "FROZEN_CONTROLS_PRE.json",
            "FROZEN_CONTROLS_POST.json",
            "manifest",
            "archive",
            "inventory",
            "verify-inventory",
        ):
            self.assertIn(fragment, self.driver)
        self.assertIn("set -euo pipefail", self.driver)
        self.assertNotIn("godot --headless", self.driver.lower())
        self.assertIn(
            'cp "$REPO_ROOT/tools/vertical_slice/run_manama_souq_source_gate.sh"',
            self.driver,
        )
        self.assertNotIn(
            "bash tools/vertical_slice/run_manama_souq_source_gate.sh",
            self.driver,
        )

    def test_authority_tool_rejects_unsafe_or_untracked_source_states(self) -> None:
        for fragment in (
            "case-colliding",
            "symbolic link",
            "unsafe normalized path",
            "unexpected files without origin",
            "origin records for missing files",
            "duplicate normalized origin path",
            "reconstruction script checksum mismatch",
            "evidence inventory mismatch",
            "reconstruction mismatch",
        ):
            self.assertIn(fragment, self.tool)

    def test_no_merge_release_creation_or_gameplay_modification_action_exists(self) -> None:
        prohibited = (
            "merge_pull_request",
            "gh pr merge",
            "gh release create",
            "git push --force",
            "scripts/souq_population_controller.gd <<",
            "tests/souq_population_runtime.gd <<",
        )
        for fragment in prohibited:
            self.assertNotIn(fragment, self.workflow + self.driver + self.tool)


if __name__ == "__main__":
    unittest.main(verbosity=2)
