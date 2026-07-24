#!/usr/bin/env python3
from __future__ import annotations

import base64
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests" / "graphics" / "android_renderer_evidence.gd"
SCENE = ROOT / "tests" / "graphics" / "android_renderer_evidence.tscn"
PREPARER = ROOT / "tools" / "graphics" / "prepare_android_renderer_variant.py"
FINALIZER = ROOT / "tools" / "graphics" / "finalize_android_emulator_evidence.py"
RUNNER = ROOT / "tools" / "graphics" / "run_android_tier_b.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "bahrain-brick-graphics-g0.yml"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AndroidTierBContractTests(unittest.TestCase):
    def test_required_components_and_fixed_android_protocol_exist(self) -> None:
        for path in (HARNESS, SCENE, PREPARER, FINALIZER, RUNNER, WORKFLOW):
            self.assertTrue(path.is_file(), f"Tier B component missing: {path}")
        harness = HARNESS.read_text(encoding="utf-8")
        for fragment in (
            "const VIEWPORT_SIZE := Vector2i(2400, 1080)",
            "const WARMUP_FRAMES := 180",
            "const CAPTURE_FRAME := 300",
            "BAHRAIN_BRICK_SOUQ_SLICE_READY",
            "BAHRAIN_BRICK_KARAK_MISSION_STARTED",
            "G0_ANDROID_RENDERER_READY",
            "G0_ANDROID_CAPTURE_FRAME",
            "G0_ANDROID_LIFECYCLE_PAUSED",
            "G0_ANDROID_LIFECYCLE_RESUMED",
        ):
            self.assertIn(fragment, harness)
        self.assertNotIn("ProjectSettings.save", harness)

    def test_preparer_changes_only_isolated_qa_configuration(self) -> None:
        module = load_module(PREPARER, "prepare_android_renderer_variant")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project.godot"
            preset = root / "export_presets.cfg"
            project.write_text(
                'config_version=5\n[application]\nrun/main_scene="res://scenes/splash_screen.tscn"\n'
                '[rendering]\nrenderer/rendering_method="gl_compatibility"\n'
                'renderer/rendering_method.mobile="gl_compatibility"\n',
                encoding="utf-8",
            )
            preset.write_text(
                '[preset.0]\nname="Android"\n[preset.0.options]\n'
                'architectures/armeabi-v7a=true\narchitectures/arm64-v8a=true\n'
                'architectures/x86_64=true\npackage/unique_name="com.brickbahrain.openworld"\n',
                encoding="utf-8",
            )
            original_project = project.read_bytes()
            original_preset = preset.read_bytes()
            report = module.prepare_variant(
                project,
                preset,
                renderer="mobile",
                package_name="com.brickbahrain.g0mobile",
            )
            updated_project = project.read_text(encoding="utf-8")
            updated_preset = preset.read_text(encoding="utf-8")
            self.assertIn('run/main_scene="res://tests/graphics/android_renderer_evidence.tscn"', updated_project)
            self.assertIn('renderer/rendering_method="mobile"', updated_project)
            self.assertIn('renderer/rendering_method.mobile="mobile"', updated_project)
            self.assertIn('architectures/armeabi-v7a=false', updated_preset)
            self.assertIn('architectures/arm64-v8a=false', updated_preset)
            self.assertIn('architectures/x86_64=true', updated_preset)
            self.assertIn('package/unique_name="com.brickbahrain.g0mobile"', updated_preset)
            self.assertNotEqual(original_project, project.read_bytes())
            self.assertNotEqual(original_preset, preset.read_bytes())
            self.assertEqual(report["renderer"], "mobile")
            self.assertTrue(report["qa_override_only"])

    def test_finalizer_parses_android_markers_png_and_diagnostics(self) -> None:
        module = load_module(FINALIZER, "finalize_android_emulator_evidence")
        # 1x1 non-black RGBA PNG.
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAF"
            "AAH/iZk9HQAAAABJRU5ErkJggg=="
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "runtime.log").write_text(
                "Vulkan 1.3.0 - Forward Mobile - Using Device #0: SwiftShader Device\n"
                "BAHRAIN_BRICK_SOUQ_SLICE_READY assets=35 pedestrians=12 traffic=6\n"
                "BAHRAIN_BRICK_KARAK_MISSION_STARTED\n"
                "G0_ANDROID_RENDERER_READY renderer=mobile driver=vulkan\n"
                "G0_ANDROID_WARMUP_COMPLETE frame=180\n"
                "G0_ANDROID_CAPTURE_FRAME frame=300\n"
                "G0_ANDROID_LIFECYCLE_PAUSED\n"
                "G0_ANDROID_LIFECYCLE_RESUMED\n",
                encoding="utf-8",
            )
            (root / "screenshot.png").write_bytes(png)
            (root / "gfxinfo.txt").write_text(
                "---PROFILEDATA---\n"
                "Flags,IntendedVsync,FrameCompleted\n"
                "0,1000000000,1016000000\n"
                "0,1016666666,1034666666\n"
                "---PROFILEDATA---\n",
                encoding="utf-8",
            )
            (root / "meminfo.txt").write_text(" TOTAL PSS: 12345 TOTAL RSS: 23456\n", encoding="utf-8")
            (root / "device.json").write_text(
                json.dumps({
                    "manufacturer": "Google",
                    "model": "AOSP on x86_64",
                    "android_version": "14",
                    "api_level": 34,
                    "abi": "x86_64",
                    "resolution": "2400x1080",
                    "gpu": "SwiftShader",
                }),
                encoding="utf-8",
            )
            (root / "lifecycle.json").write_text(
                json.dumps({"pause_observed": True, "resume_observed": True, "process_alive": True}),
                encoding="utf-8",
            )
            apk = root / "qa.apk"
            apk.write_bytes(b"apk")
            result = module.finalize_android_evidence(
                root,
                expected_renderer="mobile",
                apk_path=apk,
                package_name="com.brickbahrain.g0mobile",
            )
            self.assertEqual(result["renderer"], "mobile")
            self.assertEqual(result["evidence_tier"], "B")
            self.assertFalse(result["performance_acceptance"])
            self.assertTrue(result["screenshot"]["valid_non_black"])
            self.assertEqual(result["frame_metrics"]["row_count"], 2)
            self.assertEqual(result["process_memory"]["total_pss_kb"], 12345)
            self.assertTrue(result["evidence_complete"])
            self.assertTrue((root / "frame_metrics.csv").is_file())
            self.assertTrue((root / "critical_errors.txt").is_file())
            self.assertTrue((root / "runtime.json").is_file())

    def test_workflow_and_runner_preserve_evidence_tiers_and_shared_import(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        runner = RUNNER.read_text(encoding="utf-8")
        for fragment in (
            "renderer_tier_b:",
            "system-images;android-34;default;x86_64",
            "run_android_tier_b.sh",
            "bahrain-brick-graphics-g0-tier-b-${{ github.run_id }}",
        ):
            self.assertIn(fragment, workflow)
        for fragment in (
            "shared-import",
            "android_gl_compatibility",
            "android_mobile_vulkan",
            "-gpu swiftshader",
            "-accel-check",
            "dumpsys gfxinfo",
            "dumpsys meminfo",
            "gl_compatibility/runtime.json",
            "mobile_vulkan/runtime.json",
            "TIER_B_COMPARISON.json",
            "performance_acceptance",
        ):
            self.assertIn(fragment, runner)
        self.assertNotIn("emulator frame-rate acceptance", runner.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
