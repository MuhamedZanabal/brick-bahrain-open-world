from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "asset_lab"
sys.path.insert(0, str(TOOLS_DIR))

from generate_asset_index import generate_index
from validate_manifest_schema import semantic_failures, validate_examples, validate_manifest_file, validate_manifest_tree


class Phase3ManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[2]

    def test_valid_example_passes(self) -> None:
        path = self.root / "asset_lab/manifests/examples/valid/bb_props_validation_cube_001.json"
        result = validate_manifest_file(self.root, path)
        self.assertTrue(result["passed"], result)

    def test_all_invalid_examples_fail_and_valid_examples_pass(self) -> None:
        result = validate_examples(self.root)
        self.assertTrue(result["passed"], result)
        self.assertEqual(len(result["valid_examples"]), 1)
        self.assertEqual(len(result["invalid_examples"]), 4)
        self.assertTrue(all(not item["passed"] for item in result["invalid_examples"]))
        failures_by_name = {Path(item["path"]).name: item["failures"] for item in result["invalid_examples"]}
        self.assertIn("missing_license.json", failures_by_name)
        self.assertIn("invalid_asset_id.json", failures_by_name)
        self.assertIn("missing_lod.json", failures_by_name)
        self.assertIn("oversized_texture.json", failures_by_name)
        self.assertTrue(any("license" in str(failure).lower() for failure in failures_by_name["missing_license.json"]))
        self.assertTrue(any("asset_id" in str(failure) for failure in failures_by_name["invalid_asset_id.json"]))
        self.assertTrue(any("lods" in str(failure) for failure in failures_by_name["missing_lod.json"]))
        self.assertTrue(any("width" in str(failure) and "4096" in str(failure) for failure in failures_by_name["oversized_texture.json"]))

    def test_legacy_bh_id_is_alias_only(self) -> None:
        manifest = json.loads((self.root / "asset_lab/manifests/examples/valid/bb_props_validation_cube_001.json").read_text())
        self.assertEqual(manifest["legacy_ids"], ["bh_validation_cube_01"])
        manifest["asset_id"] = "bh_validation_cube_01"
        failures = semantic_failures(manifest)
        self.assertTrue(any("derived ID" in str(item) for item in failures))

    def test_filename_must_match_asset_id(self) -> None:
        manifest = json.loads((self.root / "asset_lab/manifests/examples/valid/bb_props_validation_cube_001.json").read_text())
        manifest["export_path"] = "asset_lab/exports/glb/wrong_name.glb"
        failures = semantic_failures(manifest)
        self.assertTrue(any(item["json_path"] == ["export_path"] for item in failures))

    def test_lod_levels_are_exact(self) -> None:
        manifest = json.loads((self.root / "asset_lab/manifests/examples/valid/bb_props_validation_cube_001.json").read_text())
        manifest["lods"][2]["level"] = 1
        failures = semantic_failures(manifest)
        self.assertTrue(any(item["json_path"] == ["lods"] for item in failures))

    def test_texture_filename_role_suffix_is_enforced(self) -> None:
        manifest = json.loads((self.root / "asset_lab/manifests/examples/valid/bb_props_validation_cube_001.json").read_text())
        manifest["textures"][0]["path"] = "asset_lab/materials/bb_tex_validation_orange_001_normal.png"
        failures = semantic_failures(manifest)
        self.assertTrue(any(item["json_path"] == ["textures", 0, "path"] for item in failures))

    def test_empty_production_manifest_set_validates_with_schema_present(self) -> None:
        result = validate_manifest_tree(self.root, allow_empty=False)
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["manifest_count"], 0)

    def test_index_generation_is_deterministic_and_nonempty_when_manifest_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(self.root / "asset_lab", root / "asset_lab")
            assets = root / "asset_lab/manifests/assets"
            assets.mkdir(parents=True, exist_ok=True)
            src = root / "asset_lab/manifests/examples/valid/bb_props_validation_cube_001.json"
            shutil.copy2(src, assets / "bb_props_validation_cube_001.json")
            first = generate_index(root)
            second = generate_index(root)
            self.assertEqual(first, second)
            self.assertEqual(first["manifest_count"], 1)
            self.assertEqual(first["assets"][0]["asset_id"], "bb_props_validation_cube_001")


if __name__ == "__main__":
    unittest.main()
