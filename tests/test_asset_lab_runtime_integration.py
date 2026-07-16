from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AssetLabRuntimeIntegrationTests(unittest.TestCase):
    def test_runtime_declares_all_verified_architecture_destinations(self):
        runtime = (ROOT / "scripts" / "asset_lab_runtime.gd").read_text(encoding="utf-8")
        self.assertEqual(runtime.count("res://assets/environment/architecture/villas/bh_villa_"), 18)
        self.assertEqual(runtime.count("res://assets/environment/architecture/traditional/bh_traditional_"), 14)
        self.assertEqual(runtime.count("res://assets/environment/architecture/souq/bh_souq_"), 18)
        self.assertEqual(runtime.count("res://assets/environment/architecture/waterfront/bh_waterfront_"), 16)
        for district in ("VillaDistrict", "TraditionalDistrict", "SouqDistrict", "WaterfrontDistrict", "CommercialDistrict", "RoadNetwork"):
            self.assertIn(f'"{district}"', runtime)

    def test_runtime_keeps_all_eight_clean_room_mappings(self):
        runtime = (ROOT / "scripts" / "asset_lab_runtime.gd").read_text(encoding="utf-8")
        for replacement in (
            "bh_cr_building_block_01_lod0.glb",
            "bh_cr_skyscraper_tower_01_lod0.glb",
            "bh_cr_vehicle_sedan_01_lod0.glb",
            "bh_cr_date_palm_01_lod0.glb",
            "bh_cr_shade_tree_01_lod0.glb",
            "bh_cr_desert_planter_01_lod0.glb",
            "bh_cr_road_straight_01_lod0.glb",
            "bh_cr_mobile_toon_shader_01.gdshader",
        ):
            self.assertIn(replacement, runtime)

    def test_runtime_declares_all_24_remaining_generator_records(self):
        runtime = (ROOT / "scripts" / "asset_lab_runtime.gd").read_text(encoding="utf-8")
        self.assertEqual(runtime.count("res://assets/environment/roads/bh_"), 14)
        self.assertEqual(runtime.count("res://assets/props/street/bh_prop_"), 6)
        commercial = (
            "bh_supermarket_storefront_a_01.glb",
            "bh_supermarket_shelf_1m_01.glb",
            "bh_cafe_storefront_karak_a_01.glb",
            "bh_cafe_table_chair_set_a_01.glb",
            "bh_prop_supermarket_checkout_a_01.glb",
        )
        for asset in commercial:
            self.assertIn(asset, runtime)

    def test_runtime_does_not_reference_protected_controls(self):
        runtime = (ROOT / "scripts" / "asset_lab_runtime.gd").read_text(encoding="utf-8").lower()
        for protected in ("touchinput", "touch_input", "player_controller", "joystick", "camera_touch", "hud"):
            self.assertNotIn(protected, runtime)


if __name__ == "__main__":
    unittest.main()
