import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "asset_lab" / "generate_full_asset_matrix_v1.py"


def load_module():
    spec = importlib.util.spec_from_file_location("generate_full_asset_matrix_v1", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def records():
    output = []
    for family, count in (("traditional", 14), ("souq", 18), ("waterfront", 16)):
        for index in range(count):
            output.append(
                {
                    "asset_id": f"bh_{family}_test_{index:02d}",
                    "family": family,
                    "name": f"{family} {index}",
                    "source_type": "original_spec",
                }
            )
    return output


class FullAssetMatrixPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_plan_has_exact_48_432_4_436_closure(self):
        plan = self.module.build_plan(records())
        self.assertEqual(plan["architecture_source_count"], 48)
        self.assertEqual(plan["architecture_derivative_count"], 432)
        self.assertEqual(plan["commercial_source_count"], 4)
        self.assertEqual(plan["final_glb_count"], 436)
        paths = [item["path"] for item in plan["outputs"]]
        self.assertEqual(len(paths), 436)
        self.assertEqual(len(set(paths)), 436)

    def test_every_architecture_record_has_complete_profile_lod_matrix(self):
        plan = self.module.build_plan(records())
        architecture = [item for item in plan["outputs"] if item["family"] != "commercial"]
        observed = {}
        for item in architecture:
            observed.setdefault(item["asset_id"], set()).add((item["profile"], item["lod"]))
        expected = {
            (profile, lod)
            for profile in self.module.PROFILES
            for lod in self.module.LODS
        }
        self.assertEqual(len(observed), 48)
        self.assertTrue(all(matrix == expected for matrix in observed.values()))

    def test_runtime_manifest_is_complete_and_manifest_driven(self):
        manifest = self.module.runtime_manifest(records())
        self.assertEqual(manifest["architecture_asset_count"], 48)
        self.assertEqual(manifest["commercial_asset_count"], 4)
        self.assertEqual(manifest["default_profile"], "balanced")
        for item in manifest["assets"]:
            self.assertEqual(set(item["paths"]), {"low", "balanced", "high"})
            self.assertTrue(all(len(paths) == 3 for paths in item["paths"].values()))
            self.assertLess(item["lod0_max_m"], item["lod1_max_m"])

    def test_generator_inherits_approved_v31_material_and_collision_authority(self):
        text = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn("v31.install_v31(texture_dir)", text)
        self.assertIn("_remove_non_lod0_collision", text)
        self.assertIn('GENERATOR_VERSION = "bahrain-brick-full-matrix-v1"', text)
        for master in (
            "bh_traditional_projecting_window_01",
            "bh_souq_shop_gold_01",
            "bh_waterfront_tower_a_01",
            "bh_supermarket_storefront_a_01",
            "bh_cr_skyscraper_tower_01",
        ):
            self.assertIn(master, text)

    def test_record_drift_and_non_authorized_seed_fail_closed(self):
        with self.assertRaises(RuntimeError):
            self.module.build_plan(records()[:-1])
        with self.assertRaises(ValueError):
            self.module.build_plan(records(), 1406)


if __name__ == "__main__":
    unittest.main()
