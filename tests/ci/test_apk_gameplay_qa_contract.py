#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ApkGameplayQaContractTest(unittest.TestCase):
    def test_probe_creates_required_evidence_and_actions(self) -> None:
        script = (ROOT / "ci/apk-gameplay-probe.sh").read_text(encoding="utf-8")
        for required in (
            "01-install.txt",
            "02-launch.txt",
            "adb-devices.txt",
            "report.md",
            "screenshots/01-after-launch.png",
            "screenshots/02-after-first-tap.png",
            "screenshots/03-after-second-tap.png",
            "screenshots/04-gameplay-probe.png",
            "screenshots/05-after-keyevents.png",
            "video/gameplay-qa.mp4",
            "logs/logcat.txt",
            "logs/crash-logcat.txt",
            "adb install -r -g",
            "cmd package resolve-activity",
            "monkey -p",
            "screenrecord",
            "logcat -b crash",
        ):
            self.assertIn(required, script)

    def test_probe_dismisses_system_overlay_and_enters_world_before_recording(self) -> None:
        script = (ROOT / "ci/apk-gameplay-probe.sh").read_text(encoding="utf-8")
        for required in (
            "settings put secure immersive_mode_confirmations confirmed",
            "dismiss_system_overlays",
            "ui-tree-after-overlay-dismiss.xml",
            "tap_fraction 85 25",
            "tap_fraction 50 93",
            "gameplay-state.txt",
            "world-probe-attempted",
        ):
            self.assertIn(required, script)

        first_world_tap = script.index("tap_fraction 50 93")
        recording_start = script.index("screenrecord --bit-rate")
        self.assertLess(first_world_tap, recording_start)

    def test_workflow_uses_accelerated_api_35_emulator_and_always_uploads(self) -> None:
        workflow = (ROOT / ".github/workflows/apk-gameplay-qa.yml").read_text(encoding="utf-8")
        for required in (
            "workflow_dispatch:",
            "ubuntu-24.04",
            "java-version: '17'",
            "Enable KVM acceleration",
            "ReactiveCircus/android-emulator-runner@v2",
            "api-level: 35",
            "target: google_apis",
            "arch: x86_64",
            "profile: pixel_6",
            "bash ci/apk-gameplay-probe.sh \"$QA_APK\"",
            "name: gameplay-qa-evidence",
            "if: always()",
        ):
            self.assertIn(required, workflow)


if __name__ == "__main__":
    unittest.main()
