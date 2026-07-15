import unittest

from tools.asset_lab.golden_master_materials import (
    MATERIAL_KEYS,
    PROFILE_SETTINGS,
    material_spec,
    validate_profile_ordering,
)


EXPECTED_MATERIAL_KEYS = {
    "sand_plaster",
    "limestone",
    "dark_timber",
    "painted_metal",
    "blue_glass",
    "souq_gold",
    "promenade_paving",
    "signage_accent",
}


class GoldenMasterMaterialTests(unittest.TestCase):
    def test_required_material_keys_are_exact(self):
        self.assertEqual(set(MATERIAL_KEYS), EXPECTED_MATERIAL_KEYS)
        self.assertEqual(len(MATERIAL_KEYS), len(set(MATERIAL_KEYS)))

    def test_profiles_have_strictly_ordered_mobile_budgets(self):
        self.assertEqual(list(PROFILE_SETTINGS), ["low", "balanced", "high"])
        self.assertEqual(validate_profile_ordering(), [])
        self.assertLess(PROFILE_SETTINGS["low"]["texture_resolution"], PROFILE_SETTINGS["balanced"]["texture_resolution"])
        self.assertLess(PROFILE_SETTINGS["balanced"]["texture_resolution"], PROFILE_SETTINGS["high"]["texture_resolution"])
        self.assertLess(PROFILE_SETTINGS["low"]["detail_scale"], PROFILE_SETTINGS["balanced"]["detail_scale"])
        self.assertLess(PROFILE_SETTINGS["balanced"]["detail_scale"], PROFILE_SETTINGS["high"]["detail_scale"])
        self.assertLessEqual(PROFILE_SETTINGS["low"]["shader_feature_count"], PROFILE_SETTINGS["balanced"]["shader_feature_count"])
        self.assertLessEqual(PROFILE_SETTINGS["balanced"]["shader_feature_count"], PROFILE_SETTINGS["high"]["shader_feature_count"])

    def test_every_material_has_a_valid_profile_specific_specification(self):
        names = set()
        for profile in PROFILE_SETTINGS:
            for material_key in MATERIAL_KEYS:
                spec = material_spec(profile, material_key)
                self.assertEqual(spec["profile"], profile)
                self.assertEqual(spec["material_key"], material_key)
                self.assertEqual(spec["texture_resolution"], PROFILE_SETTINGS[profile]["texture_resolution"])
                self.assertEqual(len(spec["base_color"]), 3)
                self.assertTrue(all(0.0 <= value <= 1.0 for value in spec["base_color"]))
                self.assertGreaterEqual(spec["roughness"], 0.0)
                self.assertLessEqual(spec["roughness"], 1.0)
                self.assertGreaterEqual(spec["metallic"], 0.0)
                self.assertLessEqual(spec["metallic"], 1.0)
                self.assertLessEqual(len(spec["shader_features"]), PROFILE_SETTINGS[profile]["shader_feature_count"])
                names.add(spec["name"])
        self.assertEqual(len(names), len(PROFILE_SETTINGS) * len(MATERIAL_KEYS))

    def test_unknown_profile_or_material_is_rejected(self):
        with self.assertRaises(KeyError):
            material_spec("ultra", "sand_plaster")
        with self.assertRaises(KeyError):
            material_spec("balanced", "unknown")


if __name__ == "__main__":
    unittest.main()
