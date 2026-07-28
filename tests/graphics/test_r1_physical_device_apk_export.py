#!/usr/bin/env python3
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
EXPORTER = ROOT / "tools/graphics/export_r1_physical_device_apks.sh"


class R1PhysicalDeviceApkExportTest(unittest.TestCase):
    def test_exporter_is_arm64_export_only_and_preserves_r1_boundary(self) -> None:
        text = EXPORTER.read_text(encoding="utf-8")
        self.assertIn('GODOT_RELEASE="4.3-stable"', text)
        self.assertIn('architectures/arm64-v8a=true', text)
        self.assertIn('architectures/armeabi-v7a=false', text)
        self.assertIn('architectures/x86_64=false', text)
        self.assertIn('gl_production', text)
        self.assertIn('mobile_baseline', text)
        self.assertIn('--export-debug Android "$GL_APK"', text)
        self.assertIn('--export-debug Android "$MOBILE_APK"', text)
        self.assertIn('apksigner" verify --verbose --print-certs', text)
        self.assertIn('R1_PHYSICAL_DEVICE_APK_MANIFEST.json', text)
        self.assertIn('"renderer_defaults_modified": False', text)
        self.assertIn('"production_fix_authorized": False', text)
        self.assertNotIn('avdmanager', text.lower())
        self.assertNotIn('emulator ', text.lower())
        self.assertNotIn('adb ', text.lower())
        self.assertNotIn('run_target', text)


if __name__ == "__main__":
    unittest.main()
