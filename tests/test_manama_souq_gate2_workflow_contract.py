#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE1 = ROOT / ".github" / "workflows" / "manama-souq-vertical-slice.yml"
GATE2 = ROOT / ".github" / "workflows" / "manama-souq-gate2-source-runtime.yml"
BASE_RUNNER = ROOT / "tools" / "vertical_slice" / "run_manama_souq_gate2_source_runtime.sh"
RUNNER = ROOT / "tools" / "vertical_slice" / "run_manama_souq_gate2_source_runtime_v2.sh"
PROJECT_SCRIPT = ROOT / "tests" / "gate2" / "souq_population_project_context_runtime.gd"
PROJECT_SCENE = ROOT / "tests" / "gate2" / "souq_population_project_context_runtime.tscn"
SLICE_PROJECT_SCRIPT = ROOT / "tests" / "gate2" / "manama_souq_slice_project_context_runtime.gd"
SLICE_PROJECT_SCENE = ROOT / "tests" / "gate2" / "manama_souq_slice_project_context_runtime.tscn"
HISTORICAL_RUNTIME = ROOT / "tests" / "souq_population_runtime.gd"
HISTORICAL_SLICE_RUNTIME = ROOT / "tests" / "manama_souq_slice_runtime.gd"

ACCEPTED_GATE1_SHA256 = "ada88cb2d6a19282124f2e836f574dc59d1d61c85348e27f61fb42a59712fdbd"
ACCEPTED_HEAD = "b12e1e012e256036e71066260a4c6392d26c3839"
ACCEPTED_MANIFEST = "ba937afa335170ccaa726297fc23712a44e3295689a86640e1c1dbe6165701ab"
ACCEPTED_TREE = "e0cfa6604569c13e1d75b2439d6936b7e2423ad5ba3715f033200335e864bc4e"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ManamaSouqGate2WorkflowContractTests(unittest.TestCase):
    def test_closed_gate1_workflow_is_byte_identical_to_accepted_authority(self) -> None:
        self.assertTrue(GATE1.is_file())
        self.assertEqual(sha256(GATE1), ACCEPTED_GATE1_SHA256)

    def test_gate2_workflow_and_harness_are_separate_components(self) -> None:
        for path in (
            GATE2,
            BASE_RUNNER,
            RUNNER,
            PROJECT_SCRIPT,
            PROJECT_SCENE,
            SLICE_PROJECT_SCRIPT,
            SLICE_PROJECT_SCENE,
            HISTORICAL_RUNTIME,
            HISTORICAL_SLICE_RUNTIME,
        ):
            self.assertTrue(path.is_file(), f"Gate 2 component missing: {path}")
        self.assertNotEqual(GATE1, GATE2)

    def test_gate2_consumes_the_accepted_gate1_authority(self) -> None:
        workflow = GATE2.read_text(encoding="utf-8")
        runner = BASE_RUNNER.read_text(encoding="utf-8") + RUNNER.read_text(encoding="utf-8")
        combined = workflow + runner
        for value in (ACCEPTED_HEAD, ACCEPTED_MANIFEST, ACCEPTED_TREE, "1502", "369162800"):
            self.assertIn(value, combined)
        self.assertIn("reconstruct_manama_souq_composite.sh", combined)
        self.assertIn("FROZEN_CONTROLS_PRE.json", combined)
        self.assertIn("FROZEN_CONTROLS_POST.json", combined)
        self.assertIn("run_manama_souq_gate2_source_runtime_v2.sh", workflow)

    def test_runner_uses_the_accepted_frozen_control_report_schema(self) -> None:
        runner = BASE_RUNNER.read_text(encoding="utf-8")
        self.assertIn("item['pass']", runner)
        self.assertNotIn("item['passed']", runner)

    def test_both_population_execution_contexts_are_bounded_and_retained(self) -> None:
        runner = BASE_RUNNER.read_text(encoding="utf-8")
        self.assertIn(
            '--script "res://tests/souq_population_runtime.gd"',
            runner,
        )
        self.assertIn(
            'res://tests/gate2/souq_population_project_context_runtime.tscn',
            runner,
        )
        for fragment in (
            "timeout --signal=TERM --kill-after=20s",
            "HISTORICAL_SCRIPT_MODE_EXIT_CODE.txt",
            "PROJECT_CONTEXT_EXIT_CODE.txt",
            "HISTORICAL_SCRIPT_MODE_TIMEOUT.txt",
            "PROJECT_CONTEXT_TIMEOUT.txt",
            "BRICK_FACTORY_CLASSIFICATION.json",
        ):
            self.assertIn(fragment, runner)

    def test_project_context_harness_preserves_population_assertions_and_real_factory_call(self) -> None:
        script = PROJECT_SCRIPT.read_text(encoding="utf-8")
        historical = HISTORICAL_RUNTIME.read_text(encoding="utf-8")
        for fragment in (
            "controller.configure(bounds, route, 12, 6, 1409)",
            "controller.spawn_all(population_root)",
            'get_nodes_in_group("souq_pedestrians").size() == 12',
            'get_nodes_in_group("souq_traffic").size() == 6',
            "duplicate population spawn was accepted",
            "bounds.has_point",
            "SOUQ_POPULATION_PROJECT_CONTEXT_PASS",
        ):
            self.assertIn(fragment, script)
        self.assertIn("BrickFactory.create_brick_car", (ROOT / "scripts" / "souq_population_controller.gd").read_text(encoding="utf-8"))
        self.assertNotIn("mock", script.lower())
        self.assertNotIn("placeholder", script.lower())
        self.assertIn("SOUQ_POPULATION_RUNTIME_PASS", historical)

    def test_complete_slice_autoload_boundary_has_script_and_project_context_evidence(self) -> None:
        runner = RUNNER.read_text(encoding="utf-8")
        script = SLICE_PROJECT_SCRIPT.read_text(encoding="utf-8")
        historical = HISTORICAL_SLICE_RUNTIME.read_text(encoding="utf-8")
        self.assertIn(
            '--script "res://tests/manama_souq_slice_runtime.gd"',
            runner,
        )
        self.assertIn(
            'res://tests/gate2/manama_souq_slice_project_context_runtime.tscn',
            runner,
        )
        for fragment in (
            "MANAMA_SOUQ_SLICE_HARNESS_CLASSIFICATION.json",
            "MANAMA_SOUQ_SLICE_PROJECT_CONTEXT_PASS",
            "slice.is_slice_ready()",
            'get_nodes_in_group("souq_pedestrians").size() == 12',
            'get_nodes_in_group("souq_traffic").size() == 6',
            'mission_vehicle.name == "MissionVehicle"',
            'player.name == "Player"',
        ):
            self.assertIn(fragment, runner + script)
        self.assertIn("MANAMA_SOUQ_SLICE_RUNTIME_PASS", historical)
        self.assertNotIn("mock", script.lower())
        self.assertNotIn("placeholder", script.lower())

    def test_gate2_does_not_perform_android_or_product_source_mutations(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (GATE2, BASE_RUNNER, RUNNER, PROJECT_SCRIPT, PROJECT_SCENE, SLICE_PROJECT_SCRIPT, SLICE_PROJECT_SCENE)
        )
        self.assertNotIn("android", combined.lower())
        for prohibited in (
            "project.godot <<",
            "scripts/brick_factory.gd <<",
            "scripts/souq_population_controller.gd <<",
            "scripts/manama_souq_vertical_slice.gd <<",
            "gh pr merge",
            "git push --force",
        ):
            self.assertNotIn(prohibited, combined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
