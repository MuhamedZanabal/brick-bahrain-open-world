import unittest

from tools.asset_lab.generate_golden_masters import DEFAULT_SEED, GOLDEN_MASTER_IDS, generation_plan


EXPECTED_IDS = {
    "bh_traditional_projecting_window_01",
    "bh_souq_shop_gold_01",
    "bh_waterfront_tower_a_01",
    "bh_supermarket_storefront_a_01",
    "bh_cr_skyscraper_tower_01",
}


class GoldenMasterGenerationPlanTests(unittest.TestCase):
    def test_generation_plan_contains_exactly_45_unique_outputs(self):
        plan = generation_plan(DEFAULT_SEED)
        outputs = plan["outputs"]
        paths = [record["path"] for record in outputs]
        self.assertEqual(plan["source_asset_count"], 5)
        self.assertEqual(plan["derivative_count"], 45)
        self.assertEqual(len(outputs), 45)
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual(set(GOLDEN_MASTER_IDS), EXPECTED_IDS)

    def test_every_asset_has_three_profiles_and_three_lods(self):
        plan = generation_plan(DEFAULT_SEED)
        by_asset = {}
        for record in plan["outputs"]:
            by_asset.setdefault(record["asset_id"], set()).add((record["profile"], record["lod"]))
        expected_matrix = {
            (profile, lod)
            for profile in ("low", "balanced", "high")
            for lod in (0, 1, 2)
        }
        self.assertEqual(set(by_asset), EXPECTED_IDS)
        for asset_id in EXPECTED_IDS:
            self.assertEqual(by_asset[asset_id], expected_matrix)

    def test_paths_are_stable_and_encode_profile_family_asset_and_lod(self):
        first = generation_plan(DEFAULT_SEED)
        second = generation_plan(DEFAULT_SEED)
        self.assertEqual(first, second)
        for record in first["outputs"]:
            self.assertEqual(
                record["path"],
                f"{record['profile']}/{record['family']}/{record['asset_id']}_lod{record['lod']}.glb",
            )
            self.assertGreater(record["seed"], 0)

    def test_unrecorded_global_seed_is_rejected(self):
        with self.assertRaises(ValueError):
            generation_plan(DEFAULT_SEED + 1)


if __name__ == "__main__":
    unittest.main()
