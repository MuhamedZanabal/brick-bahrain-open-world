from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AssetLabRuntimeIntegrationTests(unittest.TestCase):
    def test_world_scene_has_asset_lab_runtime_node(self):
        world = (ROOT / "scenes" / "world.tscn").read_text(encoding="utf-8")
        self.assertIn('path="res://scripts/asset_lab_runtime.gd"', world)
        self.assertIn('[node name="AssetLab" type="Node3D" parent="."]', world)

    def test_runtime_declares_real_district_nodes_and_verified_destinations(self):
        runtime = (ROOT / "scripts" / "asset_lab_runtime.gd").read_text(encoding="utf-8")
        for district in ("VillaDistrict", "TraditionalDistrict", "SouqDistrict", "WaterfrontDistrict", "CommercialDistrict"):
            self.assertIn(f'"{district}"', runtime)
        self.assertEqual(runtime.count("res://assets/environment/architecture/villas/bh_villa_"), 18)
        for path in (
            "res://assets/environment/architecture/commercial/bh_cr_building_block_01_lod0.glb",
            "res://assets/environment/architecture/waterfront/bh_cr_skyscraper_tower_01_lod0.glb",
            "res://assets/vehicles/clean_room/bh_cr_vehicle_sedan_01_lod0.glb",
            "res://assets/environment/vegetation/bh_cr_date_palm_01_lod0.glb",
            "res://assets/environment/vegetation/bh_cr_shade_tree_01_lod0.glb",
            "res://assets/props/street/bh_cr_desert_planter_01_lod0.glb",
            "res://assets/environment/roads/bh_cr_road_straight_01_lod0.glb",
            "res://assets/shaders/bh_cr_mobile_toon_shader_01.gdshader",
        ):
            self.assertIn(path, runtime)

    def test_runtime_does_not_reference_protected_controls(self):
        runtime = (ROOT / "scripts" / "asset_lab_runtime.gd").read_text(encoding="utf-8").lower()
        for protected in ("touchinput", "touch_input", "player_controller", "joystick", "camera_touch", "hud"):
            self.assertNotIn(protected, runtime)


if __name__ == "__main__":
    unittest.main()
