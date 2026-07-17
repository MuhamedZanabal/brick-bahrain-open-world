#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "tools" / "vertical_slice" / "run_manama_souq_gate4_export_diagnostic.sh"
INVENTORY_TOOL = ROOT / "tools" / "vertical_slice" / "inventory_godot_android_apk_assets.py"


class ManamaSouqGate4AndroidAssetInventoryContractTests(unittest.TestCase):
    def test_wrapper_replaces_false_pck_assumption_with_direct_android_asset_inventory(self) -> None:
        wrapper = WRAPPER.read_text(encoding="utf-8")
        self.assertIn("inventory_godot_android_apk_assets.py", wrapper)
        self.assertIn("APK_PROJECT_ASSETS.json", wrapper)
        self.assertIn("PCK_CONTENTS.json", wrapper)
        self.assertIn("ProjectSettings.load_resource_pack", wrapper)
        self.assertIn("asset_start_marker", wrapper)
        self.assertIn("asset_end_marker", wrapper)
        self.assertIn("asset_packaging_new", wrapper)
        self.assertIn("default Android APK assets are not a PCK", wrapper)
        self.assertNotIn("asset_packaging_old", wrapper)

    def test_inventory_maps_compiled_and_imported_assets_to_logical_resource_paths(self) -> None:
        self.assertTrue(INVENTORY_TOOL.is_file())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            apk = root / "fixture.apk"
            output = root / "inventory.json"
            compat = root / "compat.json"
            with zipfile.ZipFile(apk, "w") as archive:
                archive.writestr("assets/_cl_", b"command-line metadata")
                archive.writestr("assets/scenes/example.scn", b"scene")
                archive.writestr("assets/scripts/example.gdc", b"script")
                archive.writestr(
                    "assets/models/example.glb.remap",
                    '[remap]\npath="res://.godot/imported/example.glb-deadbeef.scn"\n',
                )
                archive.writestr("assets/.godot/imported/example.glb-deadbeef.scn", b"mesh")
            subprocess.run(
                [
                    "python3",
                    str(INVENTORY_TOOL),
                    "--apk",
                    str(apk),
                    "--output",
                    str(output),
                    "--compat-output",
                    str(compat),
                ],
                check=True,
            )
            value = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(value["packaging"], "godot-4.3-default-android-apk-assets")
            self.assertFalse(value["pck_required"])
            self.assertIn("scenes/example.tscn", value["files"])
            self.assertIn("scripts/example.gd", value["files"])
            self.assertIn("models/example.glb", value["files"])
            self.assertTrue(value["remap_targets_verified"])
            self.assertEqual(json.loads(compat.read_text(encoding="utf-8")), value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
