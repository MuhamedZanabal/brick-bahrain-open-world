#!/usr/bin/env python3
"""Generate the approved textured Bahrain Brick Option A matrix (432 + 4 GLBs)."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_architecture_families as source
import generate_golden_masters as gm
import generate_golden_masters_v3_1 as v31

GENERATOR_VERSION = "bahrain-brick-full-matrix-v1"
DEFAULT_SEED = 1405
PROFILES = ("low", "balanced", "high")
LODS = (0, 1, 2)
FAMILY_COUNTS = {"traditional": 14, "souq": 18, "waterfront": 16}
COMMERCIAL_IDS = (
    "bh_cafe_storefront_karak_a_01",
    "bh_cafe_table_chair_set_a_01",
    "bh_supermarket_shelf_1m_01",
    "bh_supermarket_storefront_a_01",
)
APPROVED_IDS = {
    "bh_traditional_projecting_window_01",
    "bh_souq_shop_gold_01",
    "bh_waterfront_tower_a_01",
    "bh_supermarket_storefront_a_01",
    "bh_cr_skyscraper_tower_01",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_int(text: str, modulus: int) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest()[:12], 16) % modulus


def validate_records(records: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    records = sorted((dict(record) for record in records), key=lambda item: item["asset_id"])
    counts = Counter(record["family"] for record in records)
    if len(records) != 48 or dict(counts) != FAMILY_COUNTS:
        raise RuntimeError(f"architecture record drift: expected 48/{FAMILY_COUNTS}, received {len(records)}/{dict(counts)}")
    if len({record["asset_id"] for record in records}) != 48:
        raise RuntimeError("duplicate architecture asset ID")
    return records


def architecture_records() -> list[dict[str, str]]:
    return validate_records(source.architecture_records())


def build_plan(records: Iterable[dict[str, str]], seed: int = DEFAULT_SEED) -> dict[str, Any]:
    if seed != DEFAULT_SEED:
        raise ValueError(f"full matrix requires seed {DEFAULT_SEED}, received {seed}")
    records = validate_records(records)
    outputs = [
        {
            "asset_id": record["asset_id"],
            "family": record["family"],
            "profile": profile,
            "lod": lod,
            "seed": DEFAULT_SEED + stable_int(record["asset_id"], 100_000),
            "path": f"architecture/{profile}/{record['family']}/{record['asset_id']}_lod{lod}.glb",
        }
        for record in records
        for profile in PROFILES
        for lod in LODS
    ]
    outputs += [
        {
            "asset_id": asset_id,
            "family": "commercial",
            "profile": "shared_mobile",
            "lod": 0,
            "seed": DEFAULT_SEED + stable_int(asset_id, 100_000),
            "path": f"commercial/{asset_id}.glb",
        }
        for asset_id in COMMERCIAL_IDS
    ]
    outputs.sort(key=lambda item: item["path"])
    paths = [item["path"] for item in outputs]
    if len(paths) != 436 or len(set(paths)) != 436:
        raise RuntimeError("436-path closure failed")
    return {
        "generator_version": GENERATOR_VERSION,
        "global_seed": seed,
        "architecture_source_count": 48,
        "architecture_derivative_count": 432,
        "commercial_source_count": 4,
        "commercial_derivative_count": 4,
        "final_glb_count": 436,
        "family_counts": FAMILY_COUNTS,
        "profiles": list(PROFILES),
        "lod_levels": list(LODS),
        "approved_master_ids": sorted(APPROVED_IDS),
        "outputs": outputs,
    }


def runtime_manifest(records: Iterable[dict[str, str]], root: str = "res://assets/generated/full_matrix") -> dict[str, Any]:
    records = validate_records(records)
    assets = []
    for record in records:
        skyline = record["family"] == "waterfront" and ("tower" in record["asset_id"] or "skyline" in record["asset_id"])
        lod0, lod1 = (55.0, 125.0) if skyline else (38.0, 90.0) if record["family"] == "waterfront" else (28.0, 68.0)
        assets.append(
            {
                "asset_id": record["asset_id"],
                "family": record["family"],
                "lod0_max_m": lod0,
                "lod1_max_m": lod1,
                "paths": {
                    profile: [f"{root}/architecture/{profile}/{record['family']}/{record['asset_id']}_lod{lod}.glb" for lod in LODS]
                    for profile in PROFILES
                },
            }
        )
    commercial = [{"asset_id": asset_id, "family": "commercial", "path": f"{root}/commercial/{asset_id}.glb"} for asset_id in COMMERCIAL_IDS]
    return {
        "schema_version": 1,
        "generator_version": GENERATOR_VERSION,
        "default_profile": "balanced",
        "profiles": list(PROFILES),
        "lod_levels": list(LODS),
        "lod_hysteresis_m": 4.0,
        "architecture_asset_count": 48,
        "commercial_asset_count": 4,
        "assets": assets,
        "commercial": commercial,
    }


def _rank(profile: str) -> int:
    return {"low": 0, "balanced": 1, "high": 2}[profile]


def _materials(bpy: Any, profile: str) -> dict[str, Any]:
    return {key: gm._material(bpy, profile, key) for key in (
        "sand_plaster", "limestone", "dark_timber", "painted_metal",
        "blue_glass", "souq_gold", "promenade_paving", "signage_accent",
    )}


def _prefix_and_parent(bpy: Any, root: Any, asset_id: str) -> None:
    for obj in bpy.context.scene.objects:
        if obj == root:
            continue
        if not obj.name.startswith(asset_id):
            obj.name = f"{asset_id}_{obj.name}"
        if obj.parent is None:
            obj.parent = root


def _remove_non_lod0_collision(bpy: Any, lod: int) -> None:
    if lod == 0:
        return
    for obj in list(bpy.context.scene.objects):
        if obj.type == "MESH" and obj.get("collision_proxy"):
            bpy.data.objects.remove(obj, do_unlink=True)


def _signature_detail(bpy: Any, root: Any, family: str, profile: str, lod: int, mats: dict[str, Any]) -> None:
    """Guarantee visible profile and LOD separation without changing primary semantics."""
    if lod == 2:
        return
    count = 2 + _rank(profile) * 2 + (2 if lod == 0 else 0)
    bevel, segments = gm._bevel(profile, lod)
    material = mats["limestone"] if family == "traditional" else mats["signage_accent"] if family == "souq" else mats["painted_metal"]
    width = 3.4 if family != "waterfront" else 5.4
    for index in range(count):
        x = -width / 2 + (index + 0.5) * width / count
        z = 3.0 if family != "waterfront" else 1.0 + index * 0.12
        gm._cube(bpy, f"approved_signature_{index:02d}", (x, -0.35, z), (max(0.08, width / count * 0.28), 0.12, 0.18), material, bevel=bevel * 0.35, bevel_segments=segments, parent=root)


def _generic_architecture(bpy: Any, root: Any, record: dict[str, str], profile: str, lod: int, mats: dict[str, Any]) -> None:
    detail = _rank(profile)
    builders = {"traditional": source._traditional, "souq": source._souq, "waterfront": source._waterfront}
    parts = builders[record["family"]](record["asset_id"], lod, detail, mats)
    for part in parts:
        part.parent = root
    _signature_detail(bpy, root, record["family"], profile, lod, mats)
    if lod == 0 and parts:
        gm._collision(bpy, root, record["asset_id"], tuple(parts[0].location), tuple(max(0.1, float(v)) for v in parts[0].dimensions))


def _build_architecture(bpy: Any, record: dict[str, str], profile: str, lod: int, seed: int) -> dict[str, int]:
    asset_id = record["asset_id"]
    gm._reset_scene(bpy)
    root = gm._root(bpy, asset_id, profile, lod, seed)
    root["generator"] = GENERATOR_VERSION
    root["source_family"] = record["family"]
    root["approved_language"] = "golden-master-v3.1"
    mats = _materials(bpy, profile)
    if asset_id in gm._BUILDERS:
        gm._BUILDERS[asset_id](bpy, root, profile, lod, mats)
    else:
        _generic_architecture(bpy, root, record, profile, lod, mats)
    _remove_non_lod0_collision(bpy, lod)
    _prefix_and_parent(bpy, root, asset_id)
    stats = gm._statistics(bpy)
    for key, value in stats.items():
        root[key] = value
    root["collision_present"] = stats["collision_object_count"] > 0
    return stats


def _commercial(bpy: Any, asset_id: str, seed: int) -> dict[str, int]:
    profile, lod = "balanced", 0
    gm._reset_scene(bpy)
    root = gm._root(bpy, asset_id, profile, lod, seed)
    root["generator"] = GENERATOR_VERSION
    mats = _materials(bpy, profile)
    if asset_id == "bh_supermarket_storefront_a_01":
        gm._BUILDERS[asset_id](bpy, root, profile, lod, mats)
    else:
        bevel, segments = gm._bevel(profile, lod)
        plaster, timber, metal = mats["sand_plaster"], mats["dark_timber"], mats["painted_metal"]
        glass, accent = mats["blue_glass"], mats["signage_accent"]
        if asset_id == "bh_supermarket_shelf_1m_01":
            gm._cube(bpy, "shelf_back", (0, .2, 1.05), (1, .12, 2.1), metal, bevel=bevel, parent=root)
            for row in range(4):
                gm._cube(bpy, f"shelf_{row}", (0, -.1, .25 + row * .55), (1, .62, .08), metal, bevel=bevel, parent=root)
                for slot in range(3):
                    gm._cube(bpy, f"product_{row}_{slot}", (-.3 + slot * .3, -.28, .4 + row * .55), (.18, .18, .24), accent if (row + slot) % 2 == 0 else plaster, bevel=bevel * .2, parent=root)
            gm._collision(bpy, root, asset_id, (0, 0, 1.05), (1, .7, 2.1))
        elif asset_id == "bh_cafe_storefront_karak_a_01":
            gm._cube(bpy, "shell", (0, .65, 1.8), (4.4, 3.3, 3.6), plaster, bevel=bevel, bevel_segments=segments, parent=root)
            gm._cube(bpy, "window", (0, -1.04, 1.78), (2.7, .1, 1.6), glass, parent=root)
            gm._cube(bpy, "counter", (0, -1.42, 1), (3, .68, .18), timber, bevel=bevel, parent=root)
            gm._cube(bpy, "fascia", (0, -1.08, 3.16), (3.6, .18, .6), accent, bevel=bevel, parent=root)
            for index in range(7):
                gm._cube(bpy, f"sign_{index}", (-1.35 + index * .45, -1.2, 3.16), (.14, .05, .22 + index % 3 * .06), mats["limestone"], parent=root)
            gm._collision(bpy, root, asset_id, (0, .65, 1.8), (4.4, 3.3, 3.6))
        elif asset_id == "bh_cafe_table_chair_set_a_01":
            gm._cube(bpy, "table_top", (0, 0, .78), (1.2, 1.2, .1), timber, bevel=bevel, parent=root)
            gm._cylinder(bpy, "table_base", (0, 0, .38), .1, .76, 12, metal, parent=root)
            for index, (x, y) in enumerate(((-.9, 0), (.9, 0), (0, -.9), (0, .9))):
                gm._cube(bpy, f"chair_{index}", (x, y, .48), (.5, .5, .82), timber, bevel=bevel, parent=root)
                gm._cube(bpy, f"chair_back_{index}", (x, y, .82), (.46, .1, .54), accent, bevel=bevel, parent=root)
            gm._collision(bpy, root, asset_id, (0, 0, .55), (2.4, 2.4, 1.1))
        else:
            raise ValueError(asset_id)
    _prefix_and_parent(bpy, root, asset_id)
    stats = gm._statistics(bpy)
    for key, value in stats.items():
        root[key] = value
    root["collision_present"] = True
    return stats


def _export(bpy: Any, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(output), export_format="GLB", export_apply=True, export_extras=True, export_materials="EXPORT", use_selection=False)


def generate_all(output_dir: Path, texture_dir: Path, report_path: Path, manifest_path: Path, seed: int = DEFAULT_SEED) -> dict[str, Any]:
    if seed != DEFAULT_SEED:
        raise ValueError(f"full matrix requires seed {DEFAULT_SEED}")
    try:
        import bpy  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Blender 4.3 Python is required") from exc
    v31.install_v31(texture_dir)
    records = architecture_records()
    plan = build_plan(records, seed)
    by_id = {record["asset_id"]: record for record in records}
    started = time.monotonic()
    outputs = []
    for item in plan["outputs"]:
        output = output_dir / item["path"]
        stats = _commercial(bpy, item["asset_id"], item["seed"]) if item["family"] == "commercial" else _build_architecture(bpy, by_id[item["asset_id"]], item["profile"], item["lod"], item["seed"])
        _export(bpy, output)
        outputs.append({**item, **stats, "bytes": output.stat().st_size, "sha256": sha256(output), "texture_authority": texture_dir.as_posix()})
    report = {**{key: value for key, value in plan.items() if key != "outputs"}, "blender_version": bpy.app.version_string, "generation_duration_seconds": round(time.monotonic() - started, 3), "generator_sha256": sha256(Path(__file__)), "texture_root": texture_dir.as_posix(), "outputs": outputs}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(runtime_manifest(records), indent=2, sort_keys=True) + "\n")
    if len(outputs) != 436:
        raise RuntimeError(f"expected 436 GLBs, generated {len(outputs)}")
    return report


def argv() -> list[str]:
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--seed", type=int, default=DEFAULT_SEED)
    plan.add_argument("--output", type=Path)
    manifest = sub.add_parser("manifest")
    manifest.add_argument("--output", type=Path, required=True)
    generate = sub.add_parser("generate")
    generate.add_argument("--seed", type=int, default=DEFAULT_SEED)
    generate.add_argument("--texture-dir", type=Path, required=True)
    generate.add_argument("--output-dir", type=Path, required=True)
    generate.add_argument("--report", type=Path, required=True)
    generate.add_argument("--runtime-manifest", type=Path, required=True)
    args = parser.parse_args(argv())
    if args.command == "plan":
        text = json.dumps(build_plan(architecture_records(), args.seed), indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text)
        else:
            print(text, end="")
    elif args.command == "manifest":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(runtime_manifest(architecture_records()), indent=2, sort_keys=True) + "\n")
    else:
        generate_all(args.output_dir, args.texture_dir, args.report, args.runtime_manifest, args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
