#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTHORITY = ROOT / "authority/bahrain_brick_g0_2_android_renderer_qualification.json"
WORKFLOW = ROOT / ".github/workflows/bahrain-brick-g0-2-android-paired.yml"
RUNNER = ROOT / "tools/graphics/run_g0_2_android_paired.sh"
FINALIZER = ROOT / "tools/graphics/finalize_g0_2_android_evidence.py"

STATES = [
    "PACKAGE_VERIFIED", "LAUNCHER_RESOLVED", "LOG_CAPTURE_STARTED",
    "ACTIVITY_START_REQUESTED", "PROCESS_CREATED", "WINDOW_VISIBLE",
    "GODOT_STARTED", "RENDERER_IDENTIFIED", "MISSION_STARTED", "SCENE_READY",
    "CAPTURE_FRAME_REACHED", "SCREENSHOT_CAPTURED", "PAUSE_RESUME_PASSED",
    "CRITICAL_LOG_SCAN_PASSED", "EVIDENCE_FINALIZED",
]
CANDIDATE_CLASSIFICATIONS = [
    "ANDROID_RENDERER_FUNCTIONAL_PASS", "ANDROID_PACKAGE_VERIFICATION_FAILURE",
    "ANDROID_INSTALL_FAILURE", "ANDROID_LAUNCHER_RESOLUTION_FAILURE",
    "ANDROID_ACTIVITY_START_FAILURE", "ANDROID_PROCESS_CREATION_FAILURE",
    "ANDROID_VISIBLE_WINDOW_FAILURE", "ANDROID_GODOT_STARTUP_FAILURE",
    "ANDROID_RENDERER_IDENTITY_FAILURE", "ANDROID_SCENE_READINESS_FAILURE",
    "ANDROID_SCREENSHOT_FAILURE", "ANDROID_LIFECYCLE_FAILURE",
    "ANDROID_CRITICAL_RUNTIME_FAILURE", "ANDROID_EVIDENCE_FINALIZATION_FAILURE",
    "ANDROID_INFRASTRUCTURE_FAILURE", "ANDROID_CAUSE_NOT_PROVEN",
]
TERMINAL_OUTCOMES = [
    "G0_2_ANDROID_BOTH_RENDERERS_FUNCTIONAL", "G0_2_ANDROID_GL_ONLY_FUNCTIONAL",
    "G0_2_ANDROID_MOBILE_ONLY_FUNCTIONAL", "G0_2_ANDROID_NEITHER_RENDERER_FUNCTIONAL",
    "G0_2_ANDROID_INFRASTRUCTURE_INSUFFICIENT", "G0_2_EVIDENCE_INSUFFICIENT",
]
REQUIRED_OUTPUTS = [
    "authority.json", "shared_import_equivalence.json", "emulator_environment.json", "apk_inventory.json",
    "gl_compatibility/state_machine.json", "gl_compatibility/package_report.json",
    "gl_compatibility/launch_report.json", "gl_compatibility/runtime.json",
    "gl_compatibility/frame_metrics.csv", "gl_compatibility/logcat_full.txt",
    "gl_compatibility/logcat_critical.txt", "gl_compatibility/screenshot.png",
    "gl_compatibility/classification.json", "mobile_vulkan/state_machine.json",
    "mobile_vulkan/package_report.json", "mobile_vulkan/launch_report.json",
    "mobile_vulkan/runtime.json", "mobile_vulkan/frame_metrics.csv",
    "mobile_vulkan/logcat_full.txt", "mobile_vulkan/logcat_critical.txt",
    "mobile_vulkan/screenshot.png", "mobile_vulkan/classification.json",
    "screenshot_comparison.json", "screenshot_difference.png",
    "G0_2_TERMINAL_REPORT.json", "G0_2_TERMINAL_REPORT.md",
]

class G02ContractTest(unittest.TestCase):
    def test_authority_is_exact(self) -> None:
        data = json.loads(AUTHORITY.read_text())
        self.assertEqual(data["branch"], "work/bahrain-brick-graphics-g0-2-android-renderer-qualification")
        self.assertEqual(data["parent_g0_1_head"], "d89d3e22e25bba8c266219dcca3cfd223e658b7b")
        self.assertEqual(data["renderer_evidence_source_commit"], "6ade72ed02084791128dcf4a91223e695d802c15")
        self.assertEqual(data["source_artifact_id"], 8586122615)
        self.assertEqual(data["state_order"], STATES)
        self.assertFalse(data["renderer_defaults_may_change"])
        self.assertFalse(data["g1_authorized"])
        self.assertEqual([v["package_id"] for v in data["apk_variants"]], ["com.brickbahrain.g0gl", "com.brickbahrain.g0mobile"])
        self.assertEqual([v["sha256"] for v in data["apk_variants"]], [
            "8461e9916b5636a35dd921d674529013b7b4623b3504f2332a9d7b4ac064b7eb",
            "0b33ba62c48ac14f1d5c331c98d1a318de427ad0b6c2dd247af327f5f1bd3a02",
        ])

    def test_workflow_is_terminally_archived(self) -> None:
        text = WORKFLOW.read_text()
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("if: false", text)
        self.assertIn("Do not rerun", text)
        for prohibited in (
            "pull_request:", "android-actions/setup-android", "system-images;android-34",
            "adb shell", "run_g0_2_android_paired.sh", "package_g0_2_terminal.py",
            "reconstruct_manama_souq_composite", "--export-debug", "project.godot",
        ):
            self.assertNotIn(prohibited, text)

    def test_runner_contains_ordered_independent_state_machine(self) -> None:
        text = RUNNER.read_text()
        positions = [text.index(state) for state in STATES]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("run_candidate gl_compatibility", text)
        self.assertIn("run_candidate mobile_vulkan", text)
        self.assertIn("gl_candidate_rc=", text)
        self.assertIn("mobile_candidate_rc=", text)
        self.assertIn("am start -W -S -n", text)
        self.assertIn("dumpsys window windows", text)
        self.assertIn("top-resumed", text)
        self.assertIn("sleep 60", text)
        self.assertIn("1920x1080", text)
        self.assertIn("DIAGNOSTIC_ONLY_NOT_PHYSICAL_DEVICE_ACCEPTANCE", text)
        self.assertNotIn('local out="$OUTPUT_ROOT/$key" state_file="$out/state_machine.json"', text)
        self.assertIn('local state_file="$out/state_machine.json"', text)

    def test_finalizer_declares_all_classifications_and_outputs(self) -> None:
        text = FINALIZER.read_text()
        for value in CANDIDATE_CLASSIFICATIONS + TERMINAL_OUTCOMES:
            self.assertIn(value, text)
        for path in REQUIRED_OUTPUTS:
            self.assertIn(path, text)
        self.assertIn("G0_EVIDENCE_INSUFFICIENT", text)
        self.assertIn("renderer_decision", text)
        self.assertIn("None", text)
        self.assertIn("DIAGNOSTIC_ONLY_NOT_PHYSICAL_DEVICE_ACCEPTANCE", text)

if __name__ == "__main__":
    unittest.main()
