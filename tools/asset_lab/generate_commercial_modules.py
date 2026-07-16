#!/usr/bin/env python3
"""Generate the four deterministic Bahrain Brick commercial modules."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
ASSET_IDS = [
    "bh_cafe_storefront_karak_a_01",
    "bh_cafe_table_chair_set_a_01",
    "bh_supermarket_shelf_1m_01",
    "bh_supermarket_storefront_a_01",
]


def _box(asset_id, label, location, dimensions, material):
    from _common import cube

    return cube(f"{asset_id}_{label}", location, dimensions, material)


def build(asset_id: str):
    from _common import add_box_collision, mat

    plaster = mat("bh_mat_commercial_plaster", (0.82, 0.75, 0.61), 0.84)
    timber = mat("bh_mat_commercial_timber", (0.25, 0.12, 0.06), 0.72)
    metal = mat("bh_mat_commercial_metal", (0.10, 0.11, 0.12), 0.52, 0.20)
    glass = mat("bh_mat_commercial_glass", (0.06, 0.23, 0.29), 0.24)
    accent = mat("bh_mat_commercial_accent", (0.65, 0.18, 0.08), 0.66)

    if asset_id == "bh_supermarket_storefront_a_01":
        parts = [
            _box(asset_id, "wall_l", (-2.25, 0, 1.8), (1.5, 0.35, 3.6), plaster),
            _box(asset_id, "wall_r", (2.25, 0, 1.8), (1.5, 0.35, 3.6), plaster),
            _box(asset_id, "header", (0, 0, 3.25), (3.0, 0.35, 0.7), accent),
            _box(asset_id, "glazing", (0, -0.2, 1.45), (2.9, 0.06, 2.2), glass),
        ]
    elif asset_id == "bh_supermarket_shelf_1m_01":
        parts = [_box(asset_id, "back", (0, 0.18, 1.05), (1.0, 0.10, 2.1), metal)]
        for index in range(4):
            parts.append(_box(asset_id, f"shelf_{index}", (0, -0.08, 0.25 + index * 0.55), (1.0, 0.55, 0.08), metal))
    elif asset_id == "bh_cafe_storefront_karak_a_01":
        parts = [
            _box(asset_id, "shell", (0, 0, 1.8), (4.2, 0.35, 3.6), plaster),
            _box(asset_id, "service_window", (0, -0.22, 1.8), (2.6, 0.06, 1.55), glass),
            _box(asset_id, "counter", (0, -0.48, 1.0), (2.9, 0.55, 0.18), timber),
            _box(asset_id, "fascia", (0, -0.22, 3.15), (3.4, 0.12, 0.58), accent),
        ]
    elif asset_id == "bh_cafe_table_chair_set_a_01":
        parts = [_box(asset_id, "table_top", (0, 0, 0.78), (1.15, 1.15, 0.10), timber), _box(asset_id, "table_base", (0, 0, 0.38), (0.16, 0.16, 0.76), metal)]
        for index, (x, y) in enumerate(((-0.85, 0), (0.85, 0), (0, -0.85), (0, 0.85))):
            parts.append(_box(asset_id, f"chair_{index}", (x, y, 0.48), (0.48, 0.48, 0.82), timber))
    else:
        raise ValueError(f"unsupported commercial asset: {asset_id}")

    for part in parts:
        part["asset_id"] = asset_id
        part["generator_seed"] = 1405
        part["quality_profile"] = "shared_mobile"
    collision = add_box_collision(parts[0], suffix="col_box_01")
    collision["asset_id"] = asset_id
    collision["collision_type"] = "simplified_box"


def generate(output_dir: Path) -> None:
    from _common import export_glb, reset_scene

    for asset_id in ASSET_IDS:
        reset_scene()
        build(asset_id)
        export_glb(output_dir / f"{asset_id}.glb")


def arguments() -> list[str]:
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list-assets", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(arguments())
    if args.list_assets:
        print(json.dumps(ASSET_IDS))
        return 0
    if args.output_dir is None:
        parser.error("--output-dir is required")
    generate(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
