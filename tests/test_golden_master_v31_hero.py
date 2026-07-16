import unittest

from tools.asset_lab.generate_golden_masters_v3_1 import REVISION_ID, hero_colonnade_plan


class GoldenMasterV31HeroTests(unittest.TestCase):
    def test_revision_identity_is_explicit(self):
        self.assertEqual(REVISION_ID, "bahrain-brick-golden-master-v3.1-hero-colonnade")

    def test_balanced_lod0_has_substantial_visible_colonnade(self):
        plan = hero_colonnade_plan("balanced", 0)
        self.assertGreaterEqual(plan["front_column_count"], 8)
        self.assertGreaterEqual(plan["column_vertices"], 14)
        self.assertGreaterEqual(plan["column_height"], 4.2)
        self.assertTrue(plan["entrance_lintel"])
        self.assertTrue(plan["rear_column_echo"])

    def test_profile_and_lod_costs_are_monotonic(self):
        for profile in ("low", "balanced", "high"):
            scores = [hero_colonnade_plan(profile, lod)["detail_score"] for lod in (0, 1, 2)]
            self.assertGreater(scores[0], scores[1])
            self.assertGreater(scores[1], scores[2])
        for lod in (0, 1, 2):
            scores = [hero_colonnade_plan(profile, lod)["detail_score"] for profile in ("low", "balanced", "high")]
            self.assertLess(scores[0], scores[1])
            self.assertLess(scores[1], scores[2])

    def test_lod2_removes_secondary_colonnade_geometry(self):
        for profile in ("low", "balanced", "high"):
            plan = hero_colonnade_plan(profile, 2)
            self.assertEqual(plan["front_column_count"], 0)
            self.assertEqual(plan["rear_column_count"], 0)
            self.assertFalse(plan["entrance_lintel"])

    def test_unknown_profile_or_lod_is_rejected(self):
        with self.assertRaises(KeyError):
            hero_colonnade_plan("ultra", 0)
        with self.assertRaises(ValueError):
            hero_colonnade_plan("balanced", 3)


if __name__ == "__main__":
    unittest.main()
