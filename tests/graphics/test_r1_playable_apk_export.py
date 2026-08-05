#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/graphics/patch_r1_playable_export.py"
WRAPPER = ROOT / "tools/graphics/export_r1_playable_mobile_apk.sh"
WORKFLOW = ROOT / ".github/workflows/bahrain-brick-playable-mobile-apk-export.yml"

VISUAL_UPGRADE_FILES = (
    "project.godot",
    "scenes/splash_screen.tscn",
    "scenes/loading_screen.tscn",
    "scenes/main_menu.tscn",
    "scenes/character_select.tscn",
    "scripts/ui/bahrain_theme.gd",
    "scripts/ui/safe_area_root.gd",
    "scripts/splash_screen.gd",
    "scripts/loading_screen.gd",
    "scripts/main_menu.gd",
    "scripts/character_select.gd",
    "scripts/game_manager.gd",
    "scripts/save_manager.gd",
)


def load_module():
    spec = importlib.util.spec_from_file_location("patch_r1_playable_export", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class R1PlayableApkExportTest(unittest.TestCase):
    def test_patch_preserves_production_main_scene_and_uses_playable_identity(self) -> None:
        module = load_module()
        diagnostic_override = (
            'project_text = replace_line(project_text, "run/main_scene=", '
            "'run/main_scene=\"res://tests/graphics/r1_renderer_runtime_debug.tscn\"')"
        )
        diagnostic_asset_copy = (
            'cp "$REPO_ROOT/tests/graphics/r1_renderer_runtime_debug.tscn" '
            '"$GAME/tests/graphics/"'
        )
        gpu_import = "\n".join(
            [
                "timeout --signal=TERM --kill-after=30s 1800s xvfb-run -a -s '-screen 0 1920x1080x24' \\",
                '  "$GODOT" --path "$GAME" --editor --import --quit --verbose \\',
                '  --rendering-method mobile --rendering-driver vulkan 2>&1 | tee "$OUTPUT_ROOT/import.log"',
            ]
        )
        source = "\n".join(
            [
                'MOBILE_APK="$OUTPUT_ROOT/bahrain-brick-r1-physical-mobile-arm64.apk"',
                'MOBILE_PACKAGE="com.brickbahrain.r1physical.mobile"',
                'GODOT="$(find "$GODOT_DIR" -maxdepth 1 -type f -name \'Godot*\' | head -1)"',
                diagnostic_asset_copy,
                gpu_import,
                diagnostic_override,
                'project_text = replace_line(project_text, "renderer/rendering_method=", f\'renderer/rendering_method="{renderer}"\')',
                diagnostic_override,
                '"package": "com.brickbahrain.r1physical.mobile",',
            ]
        )
        patched = module.patch_exporter_text(source)
        self.assertNotIn(diagnostic_override, patched)
        self.assertIn(diagnostic_asset_copy, patched)
        self.assertEqual(patched.count("Production main scene intentionally preserved"), 2)
        self.assertIn("bahrain-brick-playable-mobile-arm64.apk", patched)
        self.assertNotIn("com.brickbahrain.r1physical.mobile", patched)
        self.assertIn("com.brickbahrain.playable.mobile", patched)
        self.assertIn("renderer/rendering_method=", patched)
        self.assertIn("! -name '*.zip'", patched)
        self.assertIn('"$GODOT" --headless --path "$GAME" --editor --import --quit --verbose', patched)
        self.assertNotIn("xvfb-run", patched)
        self.assertNotIn("--rendering-driver vulkan", patched)

        self.assertIn("Overlay candidate visual-upgrade runtime files", patched)
        self.assertIn("VISUAL_UPGRADE_OVERLAY_SHA256SUMS.txt", patched)
        self.assertIn(
            'python3 "$REPO_ROOT/tools/graphics/verify_visual_upgrade_slice_a.py" --root "$GAME"',
            patched,
        )
        for relative in VISUAL_UPGRADE_FILES:
            self.assertIn(f'  "{relative}"', patched)
        self.assertEqual(patched.count("Overlay candidate visual-upgrade runtime files"), 1)

    def test_patch_rejects_unexpected_diagnostic_override_count(self) -> None:
        module = load_module()
        with self.assertRaisesRegex(ValueError, "exactly two diagnostic main-scene overrides"):
            module.patch_exporter_text('MOBILE_PACKAGE="com.brickbahrain.r1physical.mobile"')

    def test_wrapper_invokes_patcher_and_requires_playable_apk(self) -> None:
        text = WRAPPER.read_text(encoding="utf-8")
        self.assertIn("patch_r1_playable_export.py", text)
        self.assertIn("export_r1_physical_device_apks.sh", text)
        self.assertIn("bahrain-brick-playable-mobile-arm64.apk", text)
        self.assertIn("test -s", text)

    def test_wrapper_checks_only_the_diagnostic_main_scene_assignment(self) -> None:
        text = WRAPPER.read_text(encoding="utf-8")
        self.assertNotIn("grep -q 'r1_renderer_runtime_debug.tscn'", text)
        self.assertIn("run/main_scene=.*r1_renderer_runtime_debug", text)
        self.assertIn("diagnostic main-scene override remains", text)

    def test_workflow_uses_apkanalyzer_identity_and_preserves_handoff_diagnostics(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        identity_start = text.index("- name: Verify APK identity and handoff")
        diagnostics_start = text.index("- name: Print handoff diagnostics on failure")
        diagnostics_upload_start = text.index("- name: Upload handoff diagnostics")
        playable_upload_start = text.index("- name: Upload playable APK")
        self.assertLess(identity_start, diagnostics_start)
        self.assertLess(diagnostics_start, diagnostics_upload_start)
        self.assertLess(diagnostics_upload_start, playable_upload_start)

        identity = text[identity_start:diagnostics_start]
        self.assertIn("APKANALYZER=", identity)
        self.assertIn('apk summary "$APK"', identity)
        self.assertIn('manifest print "$APK"', identity)
        self.assertIn('manifest application-id "$APK"', identity)
        self.assertIn('manifest version-name "$APK"', identity)
        self.assertIn('manifest version-code "$APK"', identity)
        self.assertIn('manifest min-sdk "$APK"', identity)
        self.assertIn('manifest target-sdk "$APK"', identity)
        self.assertIn('manifest permissions "$APK"', identity)
        self.assertIn(
            'resources value --config default --name godot_project_name_string '
            '--type string --package com.brickbahrain.playable.mobile "$APK"',
            identity,
        )
        self.assertIn("Bahrain Brick Open World", identity)
        self.assertIn("arm64-v8a", identity)
        self.assertIn("armeabi-v7a|x86|x86_64", identity)
        self.assertIn("app_label", identity)
        self.assertIn("version_code", identity)
        self.assertIn("version_name", identity)
        self.assertIn("min_sdk", identity)
        self.assertIn("target_sdk", identity)
        self.assertIn("signing_certificate_sha256", identity)
        self.assertNotIn(
            "grep -q \"application-label:'Bahrain Brick Open World'\"",
            identity,
        )

        self.assertIn("set +e", identity)
        self.assertIn("AAPT_STATUS=$?", identity)
        self.assertIn("if (( AAPT_STATUS != 0 )); then", identity)
        self.assertIn(
            "AndroidManifest.xml:0: error: failed to read attribute 'android:required': "
            "attribute is not an integer value.",
            identity,
        )
        self.assertIn("aapt dump badging failed unexpectedly", identity)

        diagnostics = text[diagnostics_start:playable_upload_start]
        self.assertIn("if: failure()", diagnostics)
        for filename in (
            "playable-apk-badging.txt",
            "playable-apk-signing.txt",
            "PLAYABLE_APK_SHA256SUMS.txt",
            "SOURCE_TREE_EQUIVALENCE.json",
            "playable-apk-summary.txt",
            "playable-apk-manifest.xml",
            "playable-apk-application-id.txt",
            "playable-apk-app-label.txt",
            "playable-apk-version-name.txt",
            "playable-apk-version-code.txt",
            "playable-apk-min-sdk.txt",
            "playable-apk-target-sdk.txt",
            "playable-apk-permissions.txt",
            "playable-apk-inventory.txt",
        ):
            self.assertIn(filename, diagnostics)


if __name__ == "__main__":
    unittest.main()
