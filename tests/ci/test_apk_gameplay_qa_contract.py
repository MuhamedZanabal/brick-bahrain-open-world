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

    def test_probe_dismisses_overlay_and_drives_splash_menu_character_world(self) -> None:
        script = (ROOT / "ci/apk-gameplay-probe.sh").read_text(encoding="utf-8")
        for required in (
            "settings put secure immersive_mode_confirmations confirmed",
            "am force-stop com.google.android.apps.nexuslauncher",
            "dismiss_system_overlays",
            "ui-tree-after-overlay-dismiss.xml",
            "pixel_launcher_anr",
            "android:id/aerr_close",
            "tap_fraction 50 82",
            "tap_fraction 88 34",
            "tap_fraction 50 93",
            "verify_perceptual_transition",
            "ImageChops.difference",
            "MIN_SCENE_MEAN_DIFFERENCE=5.0",
            "world-entry.png",
            "gameplay-state.txt",
            "world-probe-attempted",
            "world-transition-observed",
        ):
            self.assertIn(required, script)

        splash_tap = script.index("tap_fraction 50 82")
        character_tap = script.index("tap_fraction 88 34")
        world_tap = script.index("tap_fraction 50 93")
        recording_start = script.index("screenrecord --bit-rate")
        self.assertLess(splash_tap, character_tap)
        self.assertLess(character_tap, world_tap)
        self.assertLess(world_tap, recording_start)

    def test_workflow_uses_accelerated_api_35_emulator_and_always_uploads(self) -> None:
        workflow = (ROOT / ".github/workflows/apk-gameplay-qa.yml").read_text(encoding="utf-8")
        for required in (
            "workflow_dispatch:",
            "ubuntu-24.04",
            "java-version: '17'",
            "Enable KVM acceleration",
            "python3-pil",
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
