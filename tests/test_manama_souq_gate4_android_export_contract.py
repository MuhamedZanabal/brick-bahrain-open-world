#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE1 = ROOT / ".github" / "workflows" / "manama-souq-vertical-slice.yml"
GATE2 = ROOT / ".github" / "workflows" / "manama-souq-gate2-source-runtime.yml"
GATE4 = ROOT / ".github" / "workflows" / "manama-souq-gate4-android-export.yml"
EXPORT_RUNNER = ROOT / "tools" / "vertical_slice" / "run_manama_souq_gate4_export.sh"
APK_TOOL = ROOT / "tools" / "vertical_slice" / "manama_souq_apk_evidence.py"
PRESET = ROOT / "export_presets.cfg"

ACCEPTED_GATE1_SHA256 = "ada88cb2d6a19282124f2e836f574dc59d1d61c85348e27f61fb42a59712fdbd"
ACCEPTED_HEAD = "b12e1e012e256036e71066260a4c6392d26c3839"
ACCEPTED_MANIFEST = "ba937afa335170ccaa726297fc23712a44e3295689a86640e1c1dbe6165701ab"
ACCEPTED_TREE = "e0cfa6604569c13e1d75b2439d6936b7e2423ad5ba3715f033200335e864bc4e"
GODOT_EDITOR_SHA512 = "fd52bb4ba8acc30ca5accd1c566d470ad7282f891ccc0995dfafabcf92bcf76280ce182bf9d80ebd885f3ed2165d01e1fc3f2928436b15498dfbd98656c2a45a"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ManamaSouqGate4AndroidExportContractTests(unittest.TestCase):
    def test_prior_gate_workflows_remain_separate_and_gate1_is_immutable(self) -> None:
        self.assertTrue(GATE1.is_file())
        self.assertTrue(GATE2.is_file())
        self.assertEqual(sha256(GATE1), ACCEPTED_GATE1_SHA256)
        gate2 = GATE2.read_text(encoding="utf-8")
        self.assertIn("Bahrain Brick Manama Souq Gate 2 Source Runtime", gate2)
        self.assertIn("run_manama_souq_gate2_source_runtime_v2.sh", gate2)
        self.assertNotEqual(GATE1, GATE2)

    def test_gate4_components_exist_separately(self) -> None:
        for path in (GATE4, EXPORT_RUNNER, APK_TOOL, PRESET):
            self.assertTrue(path.is_file(), f"Gate 4 component missing: {path}")
        self.assertNotEqual(GATE4, GATE1)
        self.assertNotEqual(GATE4, GATE2)

    def test_gate4_consumes_exact_accepted_authority_and_pinned_godot(self) -> None:
        combined = GATE4.read_text(encoding="utf-8") + EXPORT_RUNNER.read_text(encoding="utf-8")
        for value in (
            ACCEPTED_HEAD,
            ACCEPTED_MANIFEST,
            ACCEPTED_TREE,
            "1502",
            "369162800",
            "4.3.stable.official.77dcf97d8",
            GODOT_EDITOR_SHA512,
            "Godot_v4.3-stable_export_templates.tpz",
            "SHA512-SUMS.txt",
        ):
            self.assertIn(value, combined)
        self.assertIn("reconstruct_manama_souq_composite.sh", combined)
        self.assertIn("run_manama_souq_gate2_source_runtime_v2.sh", combined)

    def test_gate4_is_fail_closed_behind_mandatory_contract_and_source_gates(self) -> None:
        workflow = GATE4.read_text(encoding="utf-8")
        self.assertIn("gate4_contracts:", workflow)
        self.assertIn("export_primary:", workflow)
        self.assertIn("export_secondary:", workflow)
        self.assertIn("needs: gate4_contracts", workflow)
        self.assertIn("compare_and_package:", workflow)
        self.assertIn("needs: [export_primary, export_secondary]", workflow)
        self.assertNotIn("continue-on-error: true", workflow)

    def test_gate4_has_no_install_emulator_publish_release_or_historical_apk_path(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8") for path in (GATE4, EXPORT_RUNNER, APK_TOOL)
        ).lower()
        prohibited = (
            "adb install",
            "adb shell",
            "emulator -avd",
            "avdmanager",
            "gh release create",
            "softprops/action-gh-release",
            "upload-release-asset",
            "source_artifact_id",
            "expected_apk_sha256",
            "cp build/source/artifacts",
        )
        for fragment in prohibited:
            self.assertNotIn(fragment, combined)

    def test_existing_android_preset_identity_is_not_rewritten(self) -> None:
        preset = PRESET.read_text(encoding="utf-8")
        for fragment in (
            'name="Android"',
            'platform="Android"',
            "runnable=true",
            "gradle_build/use_gradle_build=false",
            "architectures/armeabi-v7a=true",
            "architectures/arm64-v8a=true",
            "architectures/x86_64=true",
            'keystore/debug="res://debug.keystore"',
            "version/code=1",
            'version/name="1.0.0"',
            'package/unique_name="com.brickbahrain.openworld"',
            'package/name="Zanabal Gaming"',
        ):
            self.assertIn(fragment, preset)
        runner = EXPORT_RUNNER.read_text(encoding="utf-8")
        self.assertNotIn("export_presets.cfg <<", runner)
        self.assertNotIn("re.sub", runner)
        self.assertNotIn("sed -i", runner)

    def test_repository_qa_keystore_is_external_and_does_not_mutate_source_authority(self) -> None:
        runner = EXPORT_RUNNER.read_text(encoding="utf-8")
        for fragment in (
            'SIGNING_KEYSTORE="$REPO_ROOT/debug.keystore"',
            'GODOT_ANDROID_KEYSTORE_DEBUG_PATH="$SIGNING_KEYSTORE"',
            'GODOT_ANDROID_KEYSTORE_DEBUG_USER=androiddebugkey',
            'GODOT_ANDROID_KEYSTORE_DEBUG_PASSWORD=android',
            'sha256sum "$SIGNING_KEYSTORE"',
        ):
            self.assertIn(fragment, runner)
        self.assertNotIn('cp "$SIGNING_KEYSTORE" "$GAME/debug.keystore"', runner)
        self.assertNotIn('"$GAME/debug.keystore"', runner)

    def test_exports_are_independent_bounded_and_inspected(self) -> None:
        workflow = GATE4.read_text(encoding="utf-8")
        runner = EXPORT_RUNNER.read_text(encoding="utf-8")
        inspector = APK_TOOL.read_text(encoding="utf-8")
        surface = workflow + runner + inspector
        for fragment in (
            "--export-debug",
            "timeout --signal=TERM --kill-after=30s",
            '"$APKSIGNER" verify --verbose --print-certs',
            '"$ZIPALIGN" -c -v 4',
            "unzip -tq",
            "APK_PROVENANCE.json",
            "SOURCE_AUTHORITY_PRE_EXPORT.json",
            "SOURCE_AUTHORITY_POST_EXPORT.json",
            "APK_ARCHIVE_REPORT.json",
            "APK_SIZE_BREAKDOWN.json",
        ):
            self.assertIn(fragment, surface)
        self.assertIn("primary", workflow)
        self.assertIn("secondary", workflow)
        self.assertIn("APK_REPRODUCIBILITY.json", surface)

    def test_android_actions_and_components_are_exactly_pinned(self) -> None:
        workflow = GATE4.read_text(encoding="utf-8")
        for fragment in (
            "android-actions/setup-android@4d90f943634881869c98b16d759177c8ee849798",
            "actions/setup-java@c1e323688fd81a25caa38c78aa6df2d33d3e20d9",
            "cmdline-tools-version: '14742923'",
            "java-version: '17.0.12'",
            "build-tools;34.0.0",
            "platforms;android-34",
        ):
            self.assertIn(fragment, workflow)
        self.assertNotIn("@latest", workflow.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
