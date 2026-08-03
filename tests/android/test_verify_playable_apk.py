#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/android/verify_playable_apk.py"


def load_module():
    spec = importlib.util.spec_from_file_location("verify_playable_apk", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PlayableApkVerifierTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def test_normalize_scalar_accepts_plain_and_quoted_values(self) -> None:
        self.assertEqual(self.module.normalize_scalar("Bahrain Brick Open World\n"), "Bahrain Brick Open World")
        self.assertEqual(self.module.normalize_scalar("'Bahrain Brick Open World'\n"), "Bahrain Brick Open World")
        self.assertEqual(self.module.normalize_scalar('"Bahrain Brick Open World"\n'), "Bahrain Brick Open World")

    def test_manifest_accepts_android_numeric_serialization(self) -> None:
        manifest = '''
<manifest package="com.brickbahrain.playable.mobile">
  <application android:label="@ref/0x7f0b0003">
    <activity android:name="com.godot.game.GodotApp" android:screenOrientation="11">
    </activity>
  </application>
  <uses-permission name="android.permission.ACCESS_NETWORK_STATE" />
  <uses-permission name="android.permission.INTERNET" />
</manifest>
'''
        self.module.validate_manifest(
            manifest,
            expected_package="com.brickbahrain.playable.mobile",
            required_permissions=(
                "android.permission.INTERNET",
                "android.permission.ACCESS_NETWORK_STATE",
            ),
        )

    def test_manifest_rejects_non_landscape_launcher(self) -> None:
        manifest = '''
<manifest package="com.brickbahrain.playable.mobile">
  <application android:label="@string/godot_project_name_string">
    <activity android:name="com.godot.game.GodotApp" android:screenOrientation="portrait">
    </activity>
  </application>
  <uses-permission name="android.permission.ACCESS_NETWORK_STATE" />
  <uses-permission name="android.permission.INTERNET" />
</manifest>
'''
        with self.assertRaisesRegex(self.module.VerificationError, "landscape"):
            self.module.validate_manifest(
                manifest,
                expected_package="com.brickbahrain.playable.mobile",
                required_permissions=(
                    "android.permission.INTERNET",
                    "android.permission.ACCESS_NETWORK_STATE",
                ),
            )

    def test_inventory_requires_arm64_and_rejects_other_abis(self) -> None:
        self.module.validate_inventory(
            [
                "/AndroidManifest.xml",
                "/lib/arm64-v8a/libgodot_android.so",
                "/assets/_cl_",
            ]
        )
        with self.assertRaisesRegex(self.module.VerificationError, "non-arm64"):
            self.module.validate_inventory(
                [
                    "/lib/arm64-v8a/libgodot_android.so",
                    "/lib/x86_64/libgodot_android.so",
                ]
            )

    def test_known_aapt_warning_is_exact(self) -> None:
        self.assertIn("android:required", self.module.KNOWN_AAPT_WARNING)
        self.assertNotIn("application-label", self.module.KNOWN_AAPT_WARNING)


if __name__ == "__main__":
    unittest.main()
