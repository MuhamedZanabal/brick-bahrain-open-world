#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class VisualUpgradeSliceATest(unittest.TestCase):
    def test_renderer_boundary_is_unchanged(self) -> None:
        project = read("project.godot")
        self.assertIn('run/main_scene="res://scenes/splash_screen.tscn"', project)
        self.assertIn('renderer/rendering_method="gl_compatibility"', project)
        self.assertIn('renderer/rendering_method.mobile="gl_compatibility"', project)

    def test_android_orientation_is_landscape(self) -> None:
        project = read("project.godot")
        self.assertIn("window/size/viewport_width=1920", project)
        self.assertIn("window/size/viewport_height=1080", project)
        self.assertIn("window/handheld/orientation=0", project)
        self.assertNotIn("window/handheld/orientation=1", project)

    def test_shared_theme_factory_exists(self) -> None:
        theme = read("scripts/ui/bahrain_theme.gd")
        for symbol in (
            "class_name BahrainTheme",
            "static func panel_style",
            "static func button_style",
            "static func title_size",
        ):
            self.assertIn(symbol, theme)

    def test_startup_flow_uses_real_scenes(self) -> None:
        splash = read("scripts/splash_screen.gd")
        loading = read("scripts/loading_screen.gd")
        manager = read("scripts/game_manager.gd")
        self.assertIn('res://scenes/loading_screen.tscn', splash)
        self.assertIn('res://scenes/main_menu.tscn', loading)
        self.assertIn("func show_character_select", manager)

    def test_main_menu_preserves_required_actions(self) -> None:
        menu = read("scripts/main_menu.gd")
        for label in (
            '"Play"',
            '"Character Select"',
            '"Multiplayer"',
            '"Missions"',
            '"Settings"',
            '"Credits"',
            '"Exit"',
        ):
            self.assertIn(label, menu)
        self.assertIn("BahrainTheme.button_style", menu)

    def test_character_roles_and_persistence_are_explicit(self) -> None:
        selection = read("scripts/character_select.gd")
        save_manager = read("scripts/save_manager.gd")
        for role in ('"Pearl Diver"', '"Street Racer"', '"Sky Pilot"'):
            self.assertIn(role, selection)
        self.assertIn("SaveManager.set_selected_character", selection)
        self.assertIn("func set_selected_character", save_manager)

    def test_apk_identity_check_uses_manifest_analyzer_authority(self) -> None:
        workflow = read(".github/workflows/bahrain-brick-playable-mobile-apk-export.yml")
        self.assertIn('"$APKANALYZER" manifest application-id "$APK"', workflow)
        self.assertIn('test "$APPLICATION_ID" = "com.brickbahrain.playable.mobile"', workflow)
        self.assertIn("AAPT_STATUS=$?", workflow)
        self.assertIn("Known aapt AndroidManifest android:required warning accepted", workflow)
        self.assertIn("aapt dump badging failed unexpectedly", workflow)

    def test_app_label_lookup_supplies_package_without_badging_discovery(self) -> None:
        workflow = read(".github/workflows/bahrain-brick-playable-mobile-apk-export.yml")
        self.assertIn(
            'resources value --config default --name godot_project_name_string '
            '--type string --package com.brickbahrain.playable.mobile "$APK"',
            workflow,
        )


if __name__ == "__main__":
    unittest.main()
