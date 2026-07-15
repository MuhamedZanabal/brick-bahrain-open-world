import json
import tempfile
import unittest
from pathlib import Path

from tools.asset_lab.golden_master_contract import evaluate_gate, load_contract, validate_contract


EXPECTED_IDS = {
    "bh_traditional_projecting_window_01",
    "bh_souq_shop_gold_01",
    "bh_waterfront_tower_a_01",
    "bh_supermarket_storefront_a_01",
    "bh_cr_skyscraper_tower_01",
}
EXPECTED_PROFILES = ["low", "balanced", "high"]
EXPECTED_LODS = [0, 1, 2]
REQUIRED_VISUAL_CRITERIA = {
    "bahrain_identity",
    "primary_silhouette",
    "facade_depth",
    "material_control",
    "adjacent_variation",
    "scale_consistency",
    "uv_integrity",
    "lod_integrity",
}


class GoldenMasterContractTests(unittest.TestCase):
    def setUp(self):
        self.path = Path("docs/assets/GOLDEN_MASTER_CONTRACT.json")

    def test_authoritative_contract_is_valid(self):
        contract = load_contract(self.path)
        self.assertEqual(validate_contract(contract), [])

    def test_contract_defines_exact_five_unique_assets(self):
        contract = load_contract(self.path)
        records = contract["golden_masters"]
        ids = [record["asset_id"] for record in records]
        self.assertEqual(len(records), 5)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), EXPECTED_IDS)

    def test_contract_defines_complete_profile_and_lod_matrix(self):
        contract = load_contract(self.path)
        self.assertEqual(contract["quality_profiles"], EXPECTED_PROFILES)
        self.assertEqual(contract["lod_levels"], EXPECTED_LODS)
        self.assertEqual(contract["expected_derivative_count"], 45)
        for record in contract["golden_masters"]:
            self.assertEqual(record["profiles"], EXPECTED_PROFILES)
            self.assertEqual(record["lod_levels"], EXPECTED_LODS)
            self.assertIsInstance(record["seed"], int)
            self.assertGreater(record["seed"], 0)

    def test_every_asset_has_complete_visual_acceptance_criteria(self):
        contract = load_contract(self.path)
        for record in contract["golden_masters"]:
            self.assertEqual(set(record["visual_acceptance"]), REQUIRED_VISUAL_CRITERIA)
            self.assertTrue(all(str(value).strip() for value in record["visual_acceptance"].values()))

    def test_gate_is_closed_without_complete_evidence(self):
        contract = load_contract(self.path)
        result = evaluate_gate(contract, {})
        self.assertFalse(result["mass_regeneration_allowed"])
        self.assertGreater(len(result["failures"]), 0)

    def test_gate_opens_only_for_complete_passing_evidence(self):
        contract = load_contract(self.path)
        asset_ids = [record["asset_id"] for record in contract["golden_masters"]]
        evidence = {
            "technical_pass": True,
            "protected_authority_pass": True,
            "godot_import_pass": True,
            "android_runtime_pass": True,
            "balanced_lod0_contact_sheets": asset_ids,
            "android_screenshots": asset_ids,
            "approved_assets": asset_ids,
        }
        result = evaluate_gate(contract, evidence)
        self.assertTrue(result["mass_regeneration_allowed"], result["failures"])
        self.assertEqual(result["failures"], [])

    def test_loader_rejects_non_object_json(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "contract.json"
            path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_contract(path)


if __name__ == "__main__":
    unittest.main()
