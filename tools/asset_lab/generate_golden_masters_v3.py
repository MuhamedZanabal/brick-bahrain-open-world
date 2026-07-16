#!/usr/bin/env python3
"""V3 corrective production layer for the two rejected skyline golden masters."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_golden_masters as base
import generate_golden_masters_v2 as v2

REVISION_ID = "bahrain-brick-golden-master-v3-tower-rework"
REVISED_TOWER_IDS = (
    "bh_waterfront_tower_a_01",
    "bh_cr_skyscraper_tower_01",
)
_PROFILE_RANK = {"low": 0, "balanced": 1, "high": 2}


def tower_massing_plan(asset_id: str, profile: str, lod: int) -> dict[str, Any]:
    if asset_id not in REVISED_TOWER_IDS:
        raise KeyError(f"unknown V3 tower authority: {asset_id}")
    if profile not in _PROFILE_RANK:
        raise KeyError(f"unknown quality profile: {profile}")
    if lod not in (0, 1, 2):
        raise ValueError(f"invalid LOD: {lod}")
    rank = _PROFILE_RANK[profile]
    detail_score = (3 - lod) * 100 + rank * 10
    if asset_id == "bh_waterfront_tower_a_01":
        return {
            "asset_id": asset_id,
            "profile": profile,
            "lod": lod,
            "detail_score": detail_score,
            "podium_width": 13.0,
            "podium_depth": 9.0,
            "mass_count": max(2, 5 + rank - lod * 2),
            "terrace_count": max(1, 5 + rank - lod * 2),
            "front_fin_count": max(2, 9 + rank * 2 - lod * 3),
            "rear_fin_count": max(2, 7 + rank * 2 - lod * 2),
            "side_fin_count": max(1, 5 + rank - lod * 2),
            "band_count": max(2, 10 + rank * 2 - lod * 3),
            "integrated_crown": True,
        }
    return {
        "asset_id": asset_id,
        "profile": profile,
        "lod": lod,
        "detail_score": detail_score,
        "podium_width": 22.0,
        "podium_depth": 12.0,
        "left_segment_count": max(2, 6 + rank - lod * 2),
        "right_segment_count": max(2, 5 + rank - lod * 2),
        "left_height": 58.0,
        "right_height": 49.0,
        "central_void_width": 4.5,
        "bridge_count": max(1, 2 + rank // 2 - lod // 2),
        "front_band_count": max(3, 12 + rank * 2 - lod * 4),
        "rear_band_count": max(2, 10 + rank * 2 - lod * 3),
        "side_fin_count": max(1, 6 + rank - lod * 2),
        "asymmetric_crown": True,
    }


def _rotated_cube(
    bpy: Any,
    name: str,
    location: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    material: Any,
    rotation_z_degrees: float,
    *,
    bevel: float,
    bevel_segments: int,
    parent: Any,
) -> Any:
    obj = base._cube(
        bpy,
        name,
        location,
        dimensions,
        material,
        bevel=bevel,
        bevel_segments=bevel_segments,
        parent=parent,
    )
    obj.rotation_euler.z = math.radians(rotation_z_degrees)
    return obj


def _build_waterfront_v3(bpy: Any, root: Any, profile: str, lod: int, mats: dict[str, Any]) -> None:
    plan = tower_massing_plan(root["asset_id"], profile, lod)
    bevel, segments = base._bevel(profile, lod)
    glass = mats["blue_glass"]
    stone = mats["limestone"]
    metal = mats["painted_metal"]
    paving = mats["promenade_paving"]

    base._cube(bpy, "v3_podium", (0.0, 0.0, 2.5), (13.0, 9.0, 5.0), stone, bevel=bevel, bevel_segments=segments, parent=root)
    base._cube(bpy, "v3_podium_step", (0.0, -0.25, 5.35), (11.6, 8.1, 0.70), paving, bevel=bevel, bevel_segments=segments, parent=root)
    if lod < 2:
        for side in (-1.0, 1.0):
            base._cube(
                bpy,
                f"v3_podium_wing_{'l' if side < 0 else 'r'}",
                (side * 5.4, 0.45, 4.5),
                (2.6, 7.4, 2.0),
                stone,
                bevel=bevel,
                bevel_segments=segments,
                parent=root,
            )

    mass_count = plan["mass_count"]
    tower_bottom = 5.7
    tower_top = 34.0
    tier_height = (tower_top - tower_bottom) / mass_count
    mass_records = []
    for index in range(mass_count):
        progress = index / max(1, mass_count - 1)
        width = 10.6 - progress * 3.0
        depth = 7.6 - progress * 1.5
        x = -0.45 + progress * 1.35
        y = 0.15 - progress * 0.25
        z = tower_bottom + tier_height * (index + 0.5)
        material = glass if index % 3 != 1 else stone
        obj = _rotated_cube(
            bpy,
            f"v3_stepped_mass_{index:02d}",
            (x, y, z),
            (width, depth, tier_height * 0.94),
            material,
            -2.5 + progress * 5.0,
            bevel=bevel,
            bevel_segments=segments,
            parent=root,
        )
        mass_records.append((obj, width, depth, z))

    terrace_count = min(plan["terrace_count"], mass_count)
    for index in range(terrace_count):
        mass_index = min(mass_count - 1, index)
        _, width, depth, z = mass_records[mass_index]
        terrace_z = z + tier_height * 0.47
        base._cube(
            bpy,
            f"v3_terrace_slab_{index:02d}",
            (0.15 + index * 0.12, -depth * 0.48, terrace_z),
            (width + 0.65, 1.15, 0.20),
            stone,
            bevel=bevel,
            bevel_segments=segments,
            parent=root,
        )
        if lod == 0:
            base._cube(
                bpy,
                f"v3_terrace_rail_{index:02d}",
                (0.15 + index * 0.12, -depth * 0.92, terrace_z + 0.46),
                (width + 0.35, 0.08, 0.78),
                metal,
                parent=root,
            )

    front_fin_count = plan["front_fin_count"]
    for index in range(front_fin_count):
        x = -4.4 + index * 8.8 / max(1, front_fin_count - 1)
        base._cube(bpy, f"v3_front_fin_{index:02d}", (x, -3.92, 19.4), (0.12, 0.22, 25.2), metal, bevel=bevel * 0.4, parent=root)
    rear_fin_count = plan["rear_fin_count"]
    for index in range(rear_fin_count):
        x = -4.1 + index * 8.2 / max(1, rear_fin_count - 1)
        base._cube(bpy, f"v3_rear_fin_{index:02d}", (x, 3.72, 18.8), (0.11, 0.20, 23.8), metal, bevel=bevel * 0.35, parent=root)
    side_fin_count = plan["side_fin_count"]
    for side in (-1.0, 1.0):
        for index in range(side_fin_count):
            z = 9.0 + index * 20.0 / max(1, side_fin_count - 1)
            base._cube(bpy, f"v3_side_fin_{'l' if side < 0 else 'r'}_{index:02d}", (side * 5.25, 0.0, z), (0.16, 6.6, 0.22), stone, bevel=bevel * 0.4, parent=root)

    for index in range(plan["band_count"]):
        z = 7.2 + index * 25.5 / max(1, plan["band_count"] - 1)
        width = 9.8 - (z - 7.2) / 25.5 * 2.1
        base._cube(bpy, f"v3_front_band_{index:02d}", (0.30, -3.88, z), (width, 0.15, 0.16), stone, parent=root)
        if lod == 0 or index % 2 == 0:
            base._cube(bpy, f"v3_rear_band_{index:02d}", (0.30, 3.69, z), (width, 0.14, 0.14), stone, parent=root)

    base._cube(bpy, "v3_crown_base", (1.00, -0.05, 34.7), (7.4, 6.0, 1.5), metal, bevel=bevel, bevel_segments=segments, parent=root)
    crown_fins = 4 + _PROFILE_RANK[profile] - lod
    for index in range(max(2, crown_fins)):
        x = -1.7 + index * 5.5 / max(1, crown_fins - 1)
        height = 2.8 + abs(index - (crown_fins - 1) / 2) * 0.35
        base._cube(bpy, f"v3_crown_fin_{index:02d}", (x, 0.0, 36.2 + height * 0.25), (0.20, 4.8, height), metal, bevel=bevel, parent=root)

    root["generator"] = REVISION_ID
    root["art_revision"] = "broader_stepped_waterfront_massing"
    base._collision(bpy, root, root["asset_id"], (0.0, 0.0, 18.5), (13.0, 9.0, 37.0))


def _build_hero_v3(bpy: Any, root: Any, profile: str, lod: int, mats: dict[str, Any]) -> None:
    plan = tower_massing_plan(root["asset_id"], profile, lod)
    bevel, segments = base._bevel(profile, lod)
    glass = mats["blue_glass"]
    stone = mats["limestone"]
    metal = mats["painted_metal"]
    accent = mats["signage_accent"]

    base._cube(bpy, "v3_hero_podium", (0.0, 0.0, 2.75), (22.0, 12.0, 5.5), stone, bevel=bevel, bevel_segments=segments, parent=root)
    base._cube(bpy, "v3_hero_podium_cap", (0.0, -0.20, 5.80), (20.2, 10.8, 0.65), metal, bevel=bevel, bevel_segments=segments, parent=root)
    if lod < 2:
        for side in (-1.0, 1.0):
            base._cube(bpy, f"v3_hero_lower_wing_{'l' if side < 0 else 'r'}", (side * 8.4, 0.7, 7.5), (5.0, 9.0, 3.8), stone, bevel=bevel, bevel_segments=segments, parent=root)

    def build_sail(side: str, center_x: float, height: float, count: int, outward: float, rotation_sign: float) -> list[dict[str, float]]:
        bottom = 6.1
        segment_height = (height - bottom) / count
        records = []
        for index in range(count):
            progress = index / max(1, count - 1)
            width = 8.4 - progress * 2.4
            depth = 8.6 - progress * 1.8
            x = center_x + outward * progress
            y = 0.20 - progress * 0.35
            z = bottom + segment_height * (index + 0.5)
            material = glass if index % 3 != 1 else stone
            _rotated_cube(
                bpy,
                f"v3_{side}_sail_mass_{index:02d}",
                (x, y, z),
                (width, depth, segment_height * 0.95),
                material,
                rotation_sign * (2.0 + progress * 4.0),
                bevel=bevel,
                bevel_segments=segments,
                parent=root,
            )
            records.append({"x": x, "z": z, "width": width, "depth": depth})
        return records

    left = build_sail("left", -6.3, plan["left_height"], plan["left_segment_count"], -1.8, -1.0)
    right = build_sail("right", 6.4, plan["right_height"], plan["right_segment_count"], 1.5, 1.0)

    bridge_levels = [23.0, 34.0, 42.0][: plan["bridge_count"]]
    for index, z in enumerate(bridge_levels):
        width = 7.0 - index * 0.6
        base._cube(bpy, f"v3_atrium_bridge_{index:02d}", (0.0, -0.25, z), (width, 5.0, 1.6), glass, bevel=bevel, bevel_segments=segments, parent=root)
        if lod == 0:
            base._cube(bpy, f"v3_bridge_shade_{index:02d}", (0.0, -2.78, z + 0.72), (width + 0.5, 0.18, 0.20), metal, parent=root)

    for side, records, front_x_sign in (("left", left, -1.0), ("right", right, 1.0)):
        max_height = plan["left_height"] if side == "left" else plan["right_height"]
        band_count = plan["front_band_count"]
        for index in range(band_count):
            z = 8.0 + index * (max_height - 10.0) / max(1, band_count - 1)
            progress = (z - 8.0) / max(1.0, max_height - 10.0)
            center_x = (-6.3 - 1.8 * progress) if side == "left" else (6.4 + 1.5 * progress)
            width = 7.8 - progress * 2.2
            base._cube(bpy, f"v3_{side}_front_band_{index:02d}", (center_x, -4.30 + progress * 0.5, z), (width, 0.16, 0.15), accent if index % 4 == 0 else metal, parent=root)
        rear_count = plan["rear_band_count"]
        for index in range(rear_count):
            z = 8.5 + index * (max_height - 11.0) / max(1, rear_count - 1)
            progress = (z - 8.5) / max(1.0, max_height - 11.0)
            center_x = (-6.3 - 1.8 * progress) if side == "left" else (6.4 + 1.5 * progress)
            width = 7.6 - progress * 2.0
            base._cube(bpy, f"v3_{side}_rear_band_{index:02d}", (center_x, 4.12 - progress * 0.4, z), (width, 0.15, 0.14), metal, parent=root)

    side_fin_count = plan["side_fin_count"]
    for side_name, x_sign, height in (("left", -1.0, plan["left_height"]), ("right", 1.0, plan["right_height"])):
        for index in range(side_fin_count):
            z = 10.0 + index * (height - 14.0) / max(1, side_fin_count - 1)
            x = x_sign * (10.0 + index * 0.12)
            base._cube(bpy, f"v3_{side_name}_edge_fin_{index:02d}", (x, 0.0, z), (0.18, 7.2, 0.28), stone, bevel=bevel * 0.4, parent=root)

    for side_name, x, z, count in (
        ("left", -8.3, plan["left_height"] + 1.8, 7 + _PROFILE_RANK[profile] - lod),
        ("right", 7.9, plan["right_height"] + 1.6, 5 + _PROFILE_RANK[profile] - lod),
    ):
        count = max(2, count)
        for index in range(count):
            offset = (index - (count - 1) / 2) * 0.55
            height = 4.8 - abs(offset) * 0.45
            base._cube(bpy, f"v3_{side_name}_crown_fin_{index:02d}", (x + offset, 0.0, z + abs(offset) * 0.35), (0.20, 5.2, height), metal, bevel=bevel, bevel_segments=segments, parent=root)

    root["generator"] = REVISION_ID
    root["art_revision"] = "asymmetric_twin_sail_central_void"
    base._collision(bpy, root, root["asset_id"], (0.0, 0.0, 30.0), (22.0, 12.0, 60.0))


def install_v3(texture_root: Path) -> None:
    v2.install_v2(texture_root)
    base._BUILDERS["bh_waterfront_tower_a_01"] = _build_waterfront_v3
    base._BUILDERS["bh_cr_skyscraper_tower_01"] = _build_hero_v3


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=base.DEFAULT_SEED)
    parser.add_argument("--texture-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    args = parser.parse_args(argv)
    install_v3(args.texture_dir)
    report = base.generate_all(args.output_dir, args.seed)
    report["generator_version"] = REVISION_ID
    report["revised_assets"] = list(REVISED_TOWER_IDS)
    report["texture_root"] = args.texture_dir.as_posix()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if report["derivative_count"] != 45:
        raise RuntimeError(f"expected 45 derivatives, generated {report['derivative_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
