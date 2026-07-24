#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "graphics" / "g0_source_tree_census.py"


def load_module():
    spec = importlib.util.spec_from_file_location("g0_source_tree_census", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"unable to load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class G0SourceTreeCensusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def test_classification_covers_required_graphics_categories(self) -> None:
        classify = self.module.classify_file
        self.assertIn("scene", classify("scenes/ui/menu.tscn", b"[node type=\"Control\"]"))
        self.assertIn("ui_scene", classify("scenes/ui/menu.tscn", b"[node type=\"Control\"]"))
        self.assertIn("ui_script", classify("scripts/ui/menu.gd", b"extends Control\n"))
        self.assertIn("shader", classify("shaders/water.gdshader", b"shader_type spatial;\n"))
        self.assertIn("material", classify("assets/materials/road.tres", b"[resource type=\"StandardMaterial3D\"]\n"))
        self.assertIn("texture", classify("assets/ui/icon.png", b"\x89PNG"))
        self.assertIn("font", classify("assets/fonts/interface.ttf", b"font"))
        self.assertIn("environment_resource", classify("assets/environment/late_afternoon.tres", b"Environment"))
        self.assertIn("source_controlled_import", classify("assets/car.glb.import", b"[remap]\n"))
        self.assertIn("godot_dependency", classify(".godot/imported/car.ctex", b"binary"))

    def test_census_and_comparison_are_exact_git_object_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q", repo], check=True)
            subprocess.run(["git", "-C", repo, "config", "user.email", "g0@example.invalid"], check=True)
            subprocess.run(["git", "-C", repo, "config", "user.name", "G0 Test"], check=True)
            (repo / "project.godot").write_text('[autoload]\nGame="*res://scripts/game.gd"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n', encoding="utf-8")
            (repo / "scripts").mkdir()
            (repo / "scripts" / "game.gd").write_text("extends Node\n", encoding="utf-8")
            subprocess.run(["git", "-C", repo, "add", "."], check=True)
            subprocess.run(["git", "-C", repo, "commit", "-qm", "base"], check=True)
            base = subprocess.check_output(["git", "-C", repo, "rev-parse", "HEAD"], text=True).strip()
            (repo / "reports" / "graphics" / "g0").mkdir(parents=True)
            (repo / "reports" / "graphics" / "g0" / "evidence.json").write_text("{}\n", encoding="utf-8")
            subprocess.run(["git", "-C", repo, "add", "."], check=True)
            subprocess.run(["git", "-C", repo, "commit", "-qm", "g0"], check=True)
            head = subprocess.check_output(["git", "-C", repo, "rev-parse", "HEAD"], text=True).strip()

            frozen = self.module.build_census(repo, base)
            graphics = self.module.build_census(repo, head)
            comparison = self.module.compare_censuses(frozen, graphics)

            self.assertEqual(frozen["commit"], base)
            self.assertEqual(graphics["commit"], head)
            self.assertEqual(frozen["file_count"], 2)
            self.assertEqual(len(frozen["files"]), frozen["file_count"])
            self.assertTrue(all(len(item["sha256"]) == 64 for item in frozen["files"]))
            self.assertEqual(comparison["removed_paths"], [])
            self.assertEqual(comparison["modified_paths"], [])
            self.assertEqual(comparison["added_paths"], ["reports/graphics/g0/evidence.json"])
            self.assertTrue(comparison["differences_authorized"])
            self.assertEqual(frozen["autoloads"]["Game"], "res://scripts/game.gd")
            self.assertEqual(frozen["renderer_settings"]["renderer/rendering_method"], "gl_compatibility")

    def test_world_adjudication_never_invents_exit_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q", repo], check=True)
            subprocess.run(["git", "-C", repo, "config", "user.email", "g0@example.invalid"], check=True)
            subprocess.run(["git", "-C", repo, "config", "user.name", "G0 Test"], check=True)
            (repo / "scripts").mkdir()
            (repo / "scripts" / "world.gd").write_text("extends Node3D\nfunc _ready():\n\tpass\n", encoding="utf-8")
            (repo / "design.md").write_text("Protect scripts/world.gd::_exit_tree.\n", encoding="utf-8")
            subprocess.run(["git", "-C", repo, "add", "."], check=True)
            subprocess.run(["git", "-C", repo, "commit", "-qm", "authority"], check=True)
            commit = subprocess.check_output(["git", "-C", repo, "rev-parse", "HEAD"], text=True).strip()

            report = self.module.adjudicate_world_gd(repo, commit, [])
            self.assertTrue(report["frozen_tree"]["exists"])
            self.assertFalse(report["frozen_tree"]["exit_tree_function_exists"])
            self.assertGreaterEqual(len(report["design_references"]), 1)
            self.assertEqual(report["resulting_protection_rule"], "BYTE_PROTECT_EXACT_FROZEN_WORLD_GD")
            self.assertEqual(report["symbol_claim"], "NOT_PRESENT_IN_EXACT_FROZEN_FILE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
