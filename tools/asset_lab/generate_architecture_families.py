#!/usr/bin/env python3
"""Generate the 48 non-villa architecture records as deterministic runtime GLBs.

Metadata-only commands run under ordinary Python. Geometry export requires Blender
4.3 and deliberately imports ``bpy`` only after the production command is chosen.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "assets" / "ASSET_MASTER_MANIFEST.csv"
FAMILIES = ("traditional", "souq", "waterfront")
QUALITY_PROFILES = ("low", "balanced", "high")
LOD_LEVELS = (0, 1, 2)
DEFAULT_SEED = 1405


def architecture_records() -> list[dict[str, str]]:
    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        records = [
            {
                "asset_id": row["asset_id"],
                "name": row["name"],
                "family": row["subcategory"],
                "source_type": row["source_type"],
            }
            for row in csv.DictReader(handle)
            if row["category"] == "architecture"
            and row["subcategory"] in FAMILIES
            and row["source_type"] == "original_spec"
        ]
    records.sort(key=lambda record: record["asset_id"])
    expected = {"traditional": 14, "souq": 18, "waterfront": 16}
    actual = {family: sum(r["family"] == family for r in records) for family in FAMILIES}
    if actual != expected or len(records) != 48:
        raise RuntimeError(f"architecture manifest drift: expected {expected}, received {actual}")
    return records


def generation_plan(seed: int) -> dict[str, object]:
    if seed != DEFAULT_SEED:
        raise ValueError(f"architecture families require recorded seed {DEFAULT_SEED}, received {seed}")
    records = architecture_records()
    outputs = [
        {
            "asset_id": record["asset_id"],
            "family": record["family"],
            "profile": profile,
            "lod": lod,
            "path": f"{profile}/{record['family']}/{record['asset_id']}_lod{lod}.glb",
        }
        for profile in QUALITY_PROFILES
        for record in records
        for lod in LOD_LEVELS
    ]
    outputs.sort(key=lambda output: output["path"])
    return {
        "seed": seed,
        "asset_records": len(records),
        "runtime_derivatives": len(outputs),
        "profiles": list(QUALITY_PROFILES),
        "lod_levels": list(LOD_LEVELS),
        "outputs": outputs,
    }


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _materials(asset_id: str):
    from _common import mat

    hue = int(hashlib.sha256(asset_id.encode("utf-8")).hexdigest()[:2], 16) / 255.0
    accent = (0.25 + hue * 0.45, 0.18 + (1.0 - hue) * 0.34, 0.12 + hue * 0.20)
    return {
        "sand": mat("bh_mat_sand_plaster", (0.82, 0.70, 0.53), 0.86),
        "stone": mat("bh_mat_limestone", (0.66, 0.56, 0.43), 0.90),
        "wood": mat("bh_mat_dark_timber", (0.22, 0.10, 0.05), 0.72),
        "metal": mat("bh_mat_mobile_metal", (0.10, 0.11, 0.12), 0.50, 0.25),
        "glass": mat("bh_mat_blue_glass", (0.08, 0.24, 0.31), 0.24),
        "paving": mat("bh_mat_promenade_paving", (0.50, 0.49, 0.46), 0.92),
        "accent": mat(f"bh_mat_accent_{asset_id}", accent, 0.68),
        "green": mat("bh_mat_planter_green", (0.10, 0.31, 0.13), 0.88),
    }


def _box(asset_id, label, location, dimensions, material):
    from _common import cube

    return cube(f"{asset_id}_{label}", location, dimensions, material)


def _opening(asset_id, width, height, opening_width, opening_height, sill, depth, wall, infill):
    side = (width - opening_width) / 2.0
    parts = [
        _box(asset_id, "left", (-(opening_width + side) / 2, 0, height / 2), (side, depth, height), wall),
        _box(asset_id, "right", ((opening_width + side) / 2, 0, height / 2), (side, depth, height), wall),
        _box(asset_id, "top", (0, 0, sill + opening_height + (height - sill - opening_height) / 2), (opening_width, depth, height - sill - opening_height), wall),
    ]
    if sill > 0:
        parts.append(_box(asset_id, "sill", (0, 0, sill / 2), (opening_width, depth, sill), wall))
    if infill is not None:
        parts.append(_box(asset_id, "infill", (0, -depth * 0.52, sill + opening_height / 2), (opening_width * 0.94, 0.05, opening_height * 0.94), infill))
    return parts


def _traditional(asset_id: str, lod: int, detail: int, m) -> list:
    if "door" in asset_id:
        return _opening(asset_id, 3.0, 3.4, 1.15, 2.45, 0, 0.30, m["sand"], m["wood"] if lod < 2 else None)
    if "window" in asset_id:
        parts = _opening(asset_id, 3.0, 3.4, 1.45, 1.45, 0.85, 0.30, m["sand"], m["wood"] if lod < 2 else None)
        if lod == 0:
            parts.append(_box(asset_id, "hood", (0, -0.28, 2.55), (1.85, 0.30, 0.18), m["wood"]))
        return parts
    if "arch" in asset_id:
        return _opening(asset_id, 4.0, 3.8, 2.35, 2.9, 0, 0.42, m["stone"], None)
    if "shop_bay" in asset_id:
        return _opening(asset_id, 4.2, 3.6, 3.0, 2.5, 0, 0.38, m["sand"], m["wood"] if lod < 2 else None)
    if "canopy" in asset_id:
        return [
            _box(asset_id, "roof", (0, 0, 2.65), (3.6, 2.2, 0.18), m["wood"]),
            _box(asset_id, "post_l", (-1.55, -0.85, 1.30), (0.16, 0.16, 2.6), m["wood"]),
            _box(asset_id, "post_r", (1.55, -0.85, 1.30), (0.16, 0.16, 2.6), m["wood"]),
        ]
    if "tank" in asset_id:
        return [_box(asset_id, "tank", (0, 0, 0.85), (1.25, 1.25, 1.7), m["sand"])]
    if "ac_screen" in asset_id or "vent_panel" in asset_id:
        slats = max(2, (6 + detail * 2) // (lod + 1))
        return [_box(asset_id, f"slat_{i:02d}", (-1.2 + i * 2.4 / max(1, slats - 1), 0, 1.1), (0.10, 0.18, 2.2), m["wood"]) for i in range(slats)]
    if "lamp" in asset_id:
        return [_box(asset_id, "bracket", (0, 0, 1.35), (0.12, 0.45, 2.7), m["metal"]), _box(asset_id, "lantern", (0, -0.32, 2.35), (0.55, 0.55, 0.75), m["accent"])]
    if "bench" in asset_id:
        return [_box(asset_id, "seat", (0, 0, 0.55), (2.2, 0.55, 0.16), m["wood"]), _box(asset_id, "back", (0, 0.23, 1.0), (2.2, 0.14, 0.85), m["wood"])]
    if "cable" in asset_id:
        return [_box(asset_id, "cable", (0, 0, 2.9), (5.0, 0.05, 0.05), m["metal"])]
    height = 0.75 if "parapet" in asset_id else 3.4
    depth = 0.22 if "parapet" in asset_id else 0.32
    return [_box(asset_id, f"wall_lod{lod}", (0, 0, height / 2), (4.0, depth, height), m["sand"])]


def _souq(asset_id: str, lod: int, detail: int, m) -> list:
    if "shop_" in asset_id:
        parts = _opening(asset_id, 4.0, 3.8, 2.9, 2.55, 0, 0.40, m["sand"], m["accent"] if lod < 2 else None)
        parts.append(_box(asset_id, "fascia", (0, -0.26, 3.25), (3.35, 0.16, 0.55), m["accent"]))
        if lod == 0:
            parts.append(_box(asset_id, "awning", (0, -0.85, 2.65), (3.25, 1.25, 0.14), m["accent"]))
        return parts
    if "awning" in asset_id:
        return [_box(asset_id, "fabric", (0, 0, 2.65), (3.5, 1.6, 0.14), m["accent"])]
    if "display_table" in asset_id:
        return [_box(asset_id, "top", (0, 0, 0.9), (2.0, 0.9, 0.14), m["wood"]), _box(asset_id, "base", (0, 0, 0.43), (1.55, 0.62, 0.8), m["wood"])]
    if "crate_set" in asset_id:
        count = max(2, 5 - lod)
        return [_box(asset_id, f"crate_{i:02d}", ((i % 3 - 1) * 0.62, (i // 3) * 0.62, 0.3 + (i // 3) * 0.6), (0.55, 0.55, 0.55), m["wood"]) for i in range(count)]
    if "covered_passage" in asset_id:
        return [_box(asset_id, "roof", (0, 0, 3.2), (4.0, 6.0, 0.20), m["wood"]), _box(asset_id, "wall_l", (-1.9, 0, 1.6), (0.2, 6.0, 3.2), m["sand"]), _box(asset_id, "wall_r", (1.9, 0, 1.6), (0.2, 6.0, 3.2), m["sand"])]
    if "sign_panel" in asset_id:
        return [_box(asset_id, "panel", (0, 0, 1.1), (2.8, 0.12, 1.0), m["accent"])]
    infill = m["metal"] if "shutter" in asset_id else m["wood"]
    return _opening(asset_id, 3.2, 3.4, 2.25, 2.65, 0, 0.34, m["sand"], infill if lod < 2 else None)


def _waterfront(asset_id: str, lod: int, detail: int, m) -> list:
    if "tower_" in asset_id:
        variant = {"a": (7.0, 7.0, 32.0), "b": (6.0, 8.0, 38.0), "c": (8.0, 6.0, 29.0)}
        key = "a" if "tower_a" in asset_id else "b" if "tower_b" in asset_id else "c"
        width, depth, height = variant[key]
        tiers = max(2, 5 - lod + detail)
        parts = []
        for i in range(tiers):
            scale = 1.0 - i * 0.06
            parts.append(_box(asset_id, f"tier_{i:02d}", (0, 0, height * (i + 0.5) / tiers), (width * scale, depth * scale, height / tiers), m["glass"] if i % 2 == 0 else m["stone"]))
        return parts
    if "skyline" in asset_id:
        return [_box(asset_id, f"mass_{i:02d}", ((i - 2) * 4.2, 0, (7 + i * 2) / 2), (3.6, 2.0, 7 + i * 2), m["glass"]) for i in range(max(3, 5 - lod))]
    if "promenade" in asset_id or "curve_" in asset_id or "marina_edge" in asset_id:
        length = 20.0 if "20m" in asset_id else 10.0
        width = 5.0 if "marina" not in asset_id else 3.5
        return [_box(asset_id, f"deck_lod{lod}", (0, 0, 0.12), (width, length, 0.24), m["paving"])]
    if "railing" in asset_id:
        parts = [_box(asset_id, "rail", (0, 0, 1.05), (4.0, 0.10, 0.10), m["metal"])]
        if lod < 2:
            for i in range(5 + detail):
                parts.append(_box(asset_id, f"post_{i:02d}", (-2.0 + i * 4.0 / (4 + detail), 0, 0.55), (0.10, 0.10, 1.1), m["metal"]))
        return parts
    if "bench" in asset_id:
        return [_box(asset_id, "seat", (0, 0, 0.55), (2.4, 0.65, 0.16), m["wood"]), _box(asset_id, "base_l", (-0.85, 0, 0.27), (0.18, 0.55, 0.55), m["metal"]), _box(asset_id, "base_r", (0.85, 0, 0.27), (0.18, 0.55, 0.55), m["metal"])]
    if "palm_planter" in asset_id:
        return [_box(asset_id, "planter", (0, 0, 0.45), (2.2, 2.2, 0.9), m["stone"]), _box(asset_id, "palm_proxy", (0, 0, 2.8), (0.28, 0.28, 4.7), m["green"])]
    if "cafe_terrace" in asset_id:
        return [_box(asset_id, "deck", (0, 0, 0.10), (6.0, 5.0, 0.20), m["paving"]), _box(asset_id, "shade", (0, 0, 2.8), (4.5, 3.8, 0.16), m["accent"])]
    if "water_stair" in asset_id:
        count = max(3, 8 - lod * 2)
        return [_box(asset_id, f"step_{i:02d}", (0, i * 0.55, 0.18 * (i + 1)), (4.0, 0.58, 0.36 * (i + 1)), m["stone"]) for i in range(count)]
    if "hotel_dropoff" in asset_id:
        return [_box(asset_id, "drive", (0, 0, 0.08), (12.0, 9.0, 0.16), m["paving"]), _box(asset_id, "canopy", (0, 0, 3.1), (8.0, 5.0, 0.25), m["metal"])]
    return [_box(asset_id, f"module_lod{lod}", (0, 0, 0.15), (4.0, 8.0, 0.30), m["paving"])]


def build_geometry(record: dict[str, str], lod: int, profile: str):
    from _common import add_box_collision

    detail = {"low": 0, "balanced": 1, "high": 2}[profile]
    m = _materials(record["asset_id"])
    builders = {"traditional": _traditional, "souq": _souq, "waterfront": _waterfront}
    parts = builders[record["family"]](record["asset_id"], lod, detail, m)
    for part in parts:
        part["asset_id"] = record["asset_id"]
        part["asset_family"] = record["family"]
        part["lod_level"] = lod
        part["quality_profile"] = profile
        part["generator_seed"] = DEFAULT_SEED
    if lod == 0 and parts:
        collision = add_box_collision(parts[0], suffix="col_box_01")
        collision["asset_id"] = record["asset_id"]
        collision["collision_type"] = "simplified_box"
    return parts


def generate(output_dir: Path, seed: int, report_path: Path) -> None:
    if seed != DEFAULT_SEED:
        raise ValueError(f"architecture families require recorded seed {DEFAULT_SEED}, received {seed}")
    try:
        import bpy
        from _common import export_glb, reset_scene
    except ImportError as exc:
        raise RuntimeError("GLB generation requires Blender 4.3 Python") from exc

    started = time.monotonic()
    outputs = []
    records_by_id = {record["asset_id"]: record for record in architecture_records()}
    for planned in generation_plan(seed)["outputs"]:
        record = records_by_id[planned["asset_id"]]
        reset_scene()
        build_geometry(record, planned["lod"], planned["profile"])
        output = output_dir / planned["path"]
        export_glb(output)
        outputs.append({**planned, "bytes": output.stat().st_size, "sha256": hash_file(output)})
    report = {
        "family": "architecture_non_villa",
        "asset_records": len(records_by_id),
        "runtime_derivatives": len(outputs),
        "seed": seed,
        "blender_version": bpy.app.version_string,
        "generator": Path(__file__).as_posix(),
        "generator_sha256": hash_file(Path(__file__)),
        "generation_duration_seconds": round(time.monotonic() - started, 3),
        "validation_result": "generated_pending_external_validation",
        "outputs": outputs,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def blender_arguments() -> list[str]:
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list-assets", action="store_true")
    parser.add_argument("--plan-json", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(blender_arguments())
    try:
        if args.list_assets:
            print(json.dumps(architecture_records(), indent=2, sort_keys=True))
        elif args.plan_json:
            print(json.dumps(generation_plan(args.seed), indent=2, sort_keys=True))
        else:
            if args.output_dir is None or args.report is None:
                parser.error("--output-dir and --report are required for GLB generation")
            generate(args.output_dir, args.seed, args.report)
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
