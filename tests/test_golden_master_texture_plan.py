import unittest
from pathlib import Path

from tools.asset_lab.generate_golden_master_textures import DEFAULT_TEXTURE_SEED, pixel_rgb, texture_plan


class GoldenMasterTexturePlanTests(unittest.TestCase):
    def test_plan_contains_exactly_24_profile_material_textures(self):
        plan = texture_plan(Path("build/textures"), DEFAULT_TEXTURE_SEED)
        outputs = plan["outputs"]
        self.assertEqual(plan["texture_count"], 24)
        self.assertEqual(len(outputs), 24)
        paths = [record["path"] for record in outputs]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual({record["profile"] for record in outputs}, {"low", "balanced", "high"})
        self.assertEqual(len({record["material_key"] for record in outputs}), 8)

    def test_profile_texture_resolutions_are_exact(self):
        plan = texture_plan(Path("build/textures"), DEFAULT_TEXTURE_SEED)
        expected = {"low": 256, "balanced": 512, "high": 1024}
        for record in plan["outputs"]:
            self.assertEqual(record["resolution"], expected[record["profile"]])
            self.assertEqual(record["path"], f"build/textures/{record['profile']}/{record['material_key']}_albedo.png")

    def test_pixel_generation_is_deterministic_bounded_and_material_specific(self):
        first = pixel_rgb("sand_plaster", 11, 17, 64, DEFAULT_TEXTURE_SEED)
        second = pixel_rgb("sand_plaster", 11, 17, 64, DEFAULT_TEXTURE_SEED)
        timber = pixel_rgb("dark_timber", 11, 17, 64, DEFAULT_TEXTURE_SEED)
        self.assertEqual(first, second)
        self.assertNotEqual(first, timber)
        self.assertTrue(all(0 <= channel <= 255 for channel in first))

    def test_unrecorded_seed_is_rejected(self):
        with self.assertRaises(ValueError):
            texture_plan(Path("build/textures"), DEFAULT_TEXTURE_SEED + 1)


if __name__ == "__main__":
    unittest.main()
