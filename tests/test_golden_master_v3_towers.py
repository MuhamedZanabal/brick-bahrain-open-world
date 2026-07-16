import unittest

from tools.asset_lab.generate_golden_masters_v3 import (
    REVISION_ID,
    REVISED_TOWER_IDS,
    tower_massing_plan,
)


class GoldenMasterV3TowerTests(unittest.TestCase):
    def test_revision_targets_only_two_rejected_skyline_assets(self):
        self.assertEqual(REVISION_ID, "bahrain-brick-golden-master-v3-tower-rework")
        self.assertEqual(
            set(REVISED_TOWER_IDS),
            {"bh_waterfront_tower_a_01", "bh_cr_skyscraper_tower_01"},
        )

    def test_waterfront_tower_has_broad_stepped_massing_and_four_sided_detail(self):
        plan = tower_massing_plan("bh_waterfront_tower_a_01", "balanced", 0)
        self.assertGreaterEqual(plan["podium_width"], 12.0)
        self.assertGreaterEqual(plan["podium_depth"], 8.0)
        self.assertGreaterEqual(plan["mass_count"], 4)
        self.assertGreaterEqual(plan["terrace_count"], 4)
        self.assertGreaterEqual(plan["front_fin_count"], 8)
        self.assertGreaterEqual(plan["rear_fin_count"], 6)
        self.assertGreaterEqual(plan["side_fin_count"], 4)
        self.assertTrue(plan["integrated_crown"])

    def test_hero_tower_has_asymmetric_twin_sails_and_central_void(self):
        plan = tower_massing_plan("bh_cr_skyscraper_tower_01", "balanced", 0)
        self.assertGreaterEqual(plan["podium_width"], 20.0)
        self.assertGreaterEqual(plan["left_segment_count"], 5)
        self.assertGreaterEqual(plan["right_segment_count"], 4)
        self.assertGreater(plan["left_height"], plan["right_height"])
        self.assertGreaterEqual(plan["central_void_width"], 4.0)
        self.assertGreaterEqual(plan["bridge_count"], 2)
        self.assertGreaterEqual(plan["rear_band_count"], 8)
        self.assertTrue(plan["asymmetric_crown"])

    def test_lod_and_profile_cost_plans_are_monotonic(self):
        for asset_id in REVISED_TOWER_IDS:
            with self.subTest(asset_id=asset_id):
                for profile in ("low", "balanced", "high"):
                    lods = [tower_massing_plan(asset_id, profile, lod)["detail_score"] for lod in (0, 1, 2)]
                    self.assertGreater(lods[0], lods[1])
                    self.assertGreater(lods[1], lods[2])
                for lod in (0, 1, 2):
                    profiles = [tower_massing_plan(asset_id, profile, lod)["detail_score"] for profile in ("low", "balanced", "high")]
                    self.assertLess(profiles[0], profiles[1])
                    self.assertLess(profiles[1], profiles[2])

    def test_unknown_asset_profile_or_lod_is_rejected(self):
        with self.assertRaises(KeyError):
            tower_massing_plan("unknown", "balanced", 0)
        with self.assertRaises(KeyError):
            tower_massing_plan("bh_waterfront_tower_a_01", "ultra", 0)
        with self.assertRaises(ValueError):
            tower_massing_plan("bh_waterfront_tower_a_01", "balanced", 3)


if __name__ == "__main__":
    unittest.main()
