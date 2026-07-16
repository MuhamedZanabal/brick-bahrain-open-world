#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "asset_lab" / "runtime" / "manama_souq_layout_v1.json"

ALLOWED = {
    "traditional": {
        "bh_traditional_party_wall_01",
        "bh_traditional_timber_door_01",
        "bh_traditional_projecting_window_01",
        "bh_traditional_alley_arch_01",
        "bh_traditional_parapet_01",
        "bh_traditional_courtyard_hint_01",
        "bh_traditional_shop_bay_01",
        "bh_traditional_shade_canopy_01",
        "bh_traditional_traditional_lamp_01",
        "bh_traditional_bench_01",
    },
    "souq": {
        "bh_souq_shop_gold_01",
        "bh_souq_shop_spice_01",
        "bh_souq_shop_tailor_01",
        "bh_souq_shop_perfume_01",
        "bh_souq_shop_electronics_01",
        "bh_souq_shop_fabric_01",
        "bh_souq_shop_toy_01",
        "bh_souq_shop_grocery_01",
        "bh_souq_shop_cafe_01",
        "bh_souq_shop_bakery_01",
        "bh_souq_shop_souvenir_01",
        "bh_souq_awning_01",
        "bh_souq_covered_passage_01",
        "bh_souq_sign_panel_01",
    },
    "waterfront": {
        "bh_waterfront_promenade_10m_01",
        "bh_waterfront_promenade_20m_01",
        "bh_waterfront_marina_edge_01",
        "bh_waterfront_railing_01",
        "bh_waterfront_bench_01",
        "bh_waterfront_cafe_terrace_01",
        "bh_waterfront_tower_a_01",
    },
    "commercial": {
        "bh_cafe_storefront_karak_a_01",
        "bh_cafe_table_chair_set_a_01",
        "bh_supermarket_shelf_1m_01",
        "bh_supermarket_storefront_a_01",
    },
}

MINIMUMS = {"traditional": 8, "souq": 12, "waterfront": 5, "commercial": 4}
REQUIRED_ZONES = {"cafe_start", "souq_lane", "vehicle_route", "waterfront_delivery"}
REQUIRED_MISSION_POINTS = {
    "player_spawn",
    "cafe_collection",
    "vehicle_spawn",
    "waterfront_dropoff",
    "replay_anchor",
}


class ManamaSouqLayoutContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not LAYOUT.is_file():
            raise AssertionError(f"layout authority missing: {LAYOUT}")
        cls.layout = json.loads(LAYOUT.read_text(encoding="utf-8"))

    def test_schema_authority_and_profile_are_locked(self) -> None:
        self.assertEqual(self.layout["schema"], "bahrain-brick-manama-souq-layout-v1")
        self.assertEqual(self.layout["schema_version"], 1)
        self.assertEqual(self.layout["parent_authority"], "fc8f00182f97c39015610d6603fa7c9c44364c5d")
        self.assertEqual(self.layout["asset_profile"], "balanced")
        self.assertEqual(self.layout["seed"], 1409)

    def test_playable_bounds_are_exactly_220_by_220_metres(self) -> None:
        bounds = self.layout["bounds"]
        self.assertEqual(bounds, {"min_x": -110.0, "max_x": 110.0, "min_z": -110.0, "max_z": 110.0})

    def test_required_zones_and_mission_points_exist(self) -> None:
        self.assertEqual(set(self.layout["zones"]), REQUIRED_ZONES)
        self.assertEqual(set(self.layout["mission_points"]), REQUIRED_MISSION_POINTS)
        for name, value in self.layout["mission_points"].items():
            self.assertEqual(len(value), 3, name)
            self.assertTrue(all(math.isfinite(float(component)) for component in value), name)

    def test_placements_are_unique_bounded_and_from_approved_sources(self) -> None:
        placements = self.layout["placements"]
        ids = [record["placement_id"] for record in placements]
        self.assertEqual(len(ids), len(set(ids)), "duplicate placement_id")
        bounds = self.layout["bounds"]
        for record in placements:
            family = record["family"]
            self.assertIn(family, ALLOWED)
            self.assertIn(record["asset_id"], ALLOWED[family])
            self.assertIn(record["zone"], REQUIRED_ZONES)
            self.assertEqual(record["profile"], "balanced")
            self.assertEqual(len(record["position"]), 3)
            self.assertEqual(len(record["rotation_degrees"]), 3)
            self.assertEqual(len(record["scale"]), 3)
            x, _, z = map(float, record["position"])
            self.assertGreaterEqual(x, bounds["min_x"])
            self.assertLessEqual(x, bounds["max_x"])
            self.assertGreaterEqual(z, bounds["min_z"])
            self.assertLessEqual(z, bounds["max_z"])
            self.assertTrue(all(float(v) > 0.0 for v in record["scale"]))

    def test_family_minimums_and_complete_commercial_set_are_met(self) -> None:
        counts = Counter(record["family"] for record in self.layout["placements"])
        for family, minimum in MINIMUMS.items():
            self.assertGreaterEqual(counts[family], minimum, family)
        commercial_ids = {
            record["asset_id"]
            for record in self.layout["placements"]
            if record["family"] == "commercial"
        }
        self.assertEqual(commercial_ids, ALLOWED["commercial"])

    def test_route_and_population_contracts_are_release_bounded(self) -> None:
        route = self.layout["traffic_route"]
        self.assertGreaterEqual(len(route), 8)
        self.assertEqual(route[0], route[-1], "traffic route must be closed")
        self.assertEqual(self.layout["population"], {"pedestrians": 12, "traffic": 6})
        self.assertEqual(self.layout["mission"]["id"], "karak_delivery_v1")
        self.assertEqual(self.layout["mission"]["reward_coins"], 250)
        self.assertEqual(self.layout["mission"]["time_limit_seconds"], 300)


if __name__ == "__main__":
    unittest.main(verbosity=2)
