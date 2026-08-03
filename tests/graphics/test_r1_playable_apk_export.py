#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/graphics/patch_r1_playable_export.py"
BASE_EXPORTER = ROOT / "tools/graphics/export_r1_physical_device_apks.sh"
WRAPPER = ROOT / "tools/graphics/export_r1_playable_mobile_apk.sh"


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
        source = "\n".join(
            [
                'MOBILE_APK="$OUTPUT_ROOT/bahrain-brick-r1-physical-mobile-arm64.apk"',
                'MOBILE_PACKAGE="com.brickbahrain.r1physical.mobile"',
                'GODOT="$(find "$GODOT_DIR" -maxdepth 1 -type f -name \'Godot*\' | head -1)"',
                diagnostic_override,
                'project_text = replace_line(project_text, "renderer/rendering_method=", f\'renderer/rendering_method="{renderer}"\')',
                diagnostic_override,
                '"package": "com.brickbahrain.r1physical.mobile",',
            ]
        )
        patched = module.patch_exporter_text(source)
        self.assertNotIn(diagnostic_override, patched)
        self.assertEqual(patched.count("Production main scene intentionally preserved"), 2)
        self.assertIn("bahrain-brick-playable-mobile-arm64.apk", patched)
        self.assertNotIn("com.brickbahrain.r1physical.mobile", patched)
        self.assertIn("com.brickbahrain.playable.mobile", patched)
        self.assertIn("renderer/rendering_method=", patched)
        self.assertIn("! -name '*.zip'", patched)

    def test_patch_accepts_current_authoritative_exporter(self) -> None:
        module = load_module()
        source = BASE_EXPORTER.read_text(encoding="utf-8")

        patched = module.patch_exporter_text(source)

        self.assertNotIn(module.DIAGNOSTIC_MAIN_SCENE_OVERRIDE, patched)
        self.assertEqual(patched.count(module.PRODUCTION_MAIN_SCENE_MARKER), 2)
        self.assertIn(
            'cp "$REPO_ROOT/tests/graphics/r1_renderer_runtime_debug.tscn"',
            patched,
        )
        self.assertIn("bahrain-brick-playable-mobile-arm64.apk", patched)
        self.assertIn("com.brickbahrain.playable.mobile", patched)

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

    def test_wrapper_rejects_only_a_diagnostic_main_scene_override(self) -> None:
        text = WRAPPER.read_text(encoding="utf-8")
        self.assertIn("run/main_scene=.*r1_renderer_runtime_debug.tscn", text)
        self.assertNotIn("grep -q 'r1_renderer_runtime_debug.tscn'", text)


if __name__ == "__main__":
    unittest.main()
