#!/usr/bin/env python3
"""V3.1 production wrapper adding a functional hero-tower podium colonnade."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_golden_masters as base
import generate_golden_masters_v3 as v3

REVISION_ID = "bahrain-brick-golden-master-v3.1-hero-colonnade"
_PROFILE_RANK = {"low": 0, "balanced": 1, "high": 2}
_ORIGINAL_HERO_BUILDER = v3._build_hero_v3


def hero_colonnade_plan(profile: str, lod: int) -> dict[str, Any]:
    if profile not in _PROFILE_RANK:
        raise KeyError(f"unknown quality profile: {profile}")
    if lod not in (0, 1, 2):
        raise ValueError(f"invalid LOD: {lod}")
    rank = _PROFILE_RANK[profile]
    if lod == 2:
        return {
            "profile": profile,
            "lod": lod,
            "detail_score": 100 + rank * 10,
            "front_column_count": 0,
            "rear_column_count": 0,
            "column_vertices": 8 + rank * 2,
            "column_height": 0.0,
            "entrance_lintel": False,
            "rear_column_echo": False,
        }
    front = (5, 8, 11)[rank] if lod == 0 else (2, 4, 6)[rank]
    rear = max(1, front - (2 if lod == 0 else 1))
    vertices = (10, 14, 18)[rank] - lod * 2
    return {
        "profile": profile,
        "lod": lod,
        "detail_score": (3 - lod) * 100 + rank * 10,
        "front_column_count": front,
        "rear_column_count": rear,
        "column_vertices": vertices,
        "column_height": 4.6 if lod == 0 else 4.2,
        "entrance_lintel": True,
        "rear_column_echo": True,
    }


def _build_hero_v31(bpy: Any, root: Any, profile: str, lod: int, mats: dict[str, Any]) -> None:
    _ORIGINAL_HERO_BUILDER(bpy, root, profile, lod, mats)
    plan = hero_colonnade_plan(profile, lod)
    if plan["front_column_count"] == 0:
        root["generator"] = REVISION_ID
        root["art_revision"] = "asymmetric_twin_sail_with_podium_colonnade"
        return

    bevel, segments = base._bevel(profile, lod)
    stone = mats["limestone"]
    metal = mats["painted_metal"]
    accent = mats["signage_accent"]

    front_count = plan["front_column_count"]
    front_span = 17.4
    for index in range(front_count):
        x = -front_span / 2.0 + index * front_span / max(1, front_count - 1)
        base._cylinder(
            bpy,
            f"v31_front_colonnade_{index:02d}",
            (x, -6.10, plan["column_height"] / 2.0 + 0.18),
            0.18,
            plan["column_height"],
            plan["column_vertices"],
            stone,
            parent=root,
        )
        if lod == 0:
            base._cube(
                bpy,
                f"v31_front_column_cap_{index:02d}",
                (x, -6.10, plan["column_height"] + 0.34),
                (0.48, 0.48, 0.18),
                accent if index % 3 == 0 else metal,
                bevel=bevel * 0.45,
                bevel_segments=segments,
                parent=root,
            )

    rear_count = plan["rear_column_count"]
    rear_span = 15.6
    for index in range(rear_count):
        x = -rear_span / 2.0 + index * rear_span / max(1, rear_count - 1)
        base._cylinder(
            bpy,
            f"v31_rear_colonnade_{index:02d}",
            (x, 6.05, plan["column_height"] / 2.0 + 0.18),
            0.15,
            plan["column_height"],
            max(8, plan["column_vertices"] - 2),
            stone,
            parent=root,
        )

    base._cube(
        bpy,
        "v31_front_entrance_lintel",
        (0.0, -6.08, plan["column_height"] + 0.52),
        (19.0, 0.62, 0.42),
        metal,
        bevel=bevel,
        bevel_segments=segments,
        parent=root,
    )
    base._cube(
        bpy,
        "v31_rear_entrance_lintel",
        (0.0, 6.03, plan["column_height"] + 0.46),
        (17.2, 0.50, 0.34),
        stone,
        bevel=bevel,
        bevel_segments=segments,
        parent=root,
    )
    if lod == 0:
        base._cube(
            bpy,
            "v31_central_entry_canopy",
            (0.0, -6.85, 4.15),
            (5.6, 1.75, 0.24),
            accent,
            bevel=bevel,
            bevel_segments=segments,
            parent=root,
        )

    root["generator"] = REVISION_ID
    root["art_revision"] = "asymmetric_twin_sail_with_podium_colonnade"
    root["front_colonnade_count"] = front_count
    root["rear_colonnade_count"] = rear_count


def install_v31(texture_root: Path) -> None:
    v3.install_v3(texture_root)
    base._BUILDERS["bh_cr_skyscraper_tower_01"] = _build_hero_v31


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=base.DEFAULT_SEED)
    parser.add_argument("--texture-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    args = parser.parse_args(argv)
    install_v31(args.texture_dir)
    report = base.generate_all(args.output_dir, args.seed)
    report["generator_version"] = REVISION_ID
    report["revised_assets"] = list(v3.REVISED_TOWER_IDS)
    report["texture_root"] = args.texture_dir.as_posix()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if report["derivative_count"] != 45:
        raise RuntimeError(f"expected 45 derivatives, generated {report['derivative_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
