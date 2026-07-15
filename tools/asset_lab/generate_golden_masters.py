#!/usr/bin/env python3
"""Generate the five Bahrain Brick artistic golden masters and their 45 derivatives.

The generation-plan API is ordinary Python and never imports Blender. Geometry
creation imports ``bpy`` only after the ``generate`` command is selected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from golden_master_contract import load_contract, validate_contract
from golden_master_materials import PROFILE_SETTINGS, material_spec

DEFAULT_SEED = 1405
CONTRACT_PATH = ROOT / "docs" / "assets" / "GOLDEN_MASTER_CONTRACT.json"
QUALITY_PROFILES = ("low", "balanced", "high")
LOD_LEVELS = (0, 1, 2)
GOLDEN_MASTER_IDS = (
    "bh_traditional_projecting_window_01",
    "bh_souq_shop_gold_01",
    "bh_waterfront_tower_a_01",
    "bh_supermarket_storefront_a_01",
    "bh_cr_skyscraper_tower_01",
)


def _contract_records() -> list[dict[str, Any]]:
    contract = load_contract(CONTRACT_PATH)
    failures = validate_contract(contract)
    if failures:
        raise RuntimeError(f"invalid golden-master contract: {failures}")
    records = list(contract["golden_masters"])
    by_id = {record["asset_id"]: record for record in records}
    if set(by_id) != set(GOLDEN_MASTER_IDS):
        raise RuntimeError("golden-master contract IDs do not match generator authority")
    return [by_id[asset_id] for asset_id in GOLDEN_MASTER_IDS]


def generation_plan(seed: int) -> dict[str, Any]:
    """Return the deterministic 5 × 3 × 3 generation matrix."""
    if seed != DEFAULT_SEED:
        raise ValueError(f"golden masters require recorded global seed {DEFAULT_SEED}, received {seed}")
    outputs: list[dict[str, Any]] = []
    for record in _contract_records():
        for profile in QUALITY_PROFILES:
            for lod in LOD_LEVELS:
                outputs.append(
                    {
                        "asset_id": record["asset_id"],
                        "family": record["family"],
                        "profile": profile,
                        "lod": lod,
                        "seed": record["seed"],
                        "path": f"{profile}/{record['family']}/{record['asset_id']}_lod{lod}.glb",
                    }
                )
    outputs.sort(key=lambda item: item["path"])
    return {
        "global_seed": seed,
        "source_asset_count": len(GOLDEN_MASTER_IDS),
        "derivative_count": len(outputs),
        "profiles": list(QUALITY_PROFILES),
        "lod_levels": list(LOD_LEVELS),
        "outputs": outputs,
    }


def _blender_args() -> list[str]:
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]


def _reset_scene(bpy: Any) -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def _material(bpy: Any, profile: str, key: str) -> Any:
    spec = material_spec(profile, key)
    material = bpy.data.materials.get(spec["name"]) or bpy.data.materials.new(spec["name"])
    material.use_nodes = True
    material.diffuse_color = (*spec["base_color"], 1.0)
    material.roughness = spec["roughness"]
    material.metallic = spec["metallic"]
    material["material_key"] = key
    material["quality_profile"] = profile
    material["texture_resolution"] = spec["texture_resolution"]
    material["shader_features"] = ",".join(spec["shader_features"])
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if principled is not None:
        principled.inputs["Base Color"].default_value = (*spec["base_color"], 1.0)
        principled.inputs["Roughness"].default_value = spec["roughness"]
        principled.inputs["Metallic"].default_value = spec["metallic"]
    return material


def _apply_material(obj: Any, material: Any) -> None:
    if material is not None and len(obj.data.materials) == 0:
        obj.data.materials.append(material)


def _cube(
    bpy: Any,
    name: str,
    location: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    material: Any,
    *,
    bevel: float = 0.0,
    bevel_segments: int = 1,
    parent: Any = None,
) -> Any:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    _apply_material(obj, material)
    if bevel > 0.0:
        modifier = obj.modifiers.new(name="mobile_bevel", type="BEVEL")
        modifier.width = bevel
        modifier.segments = max(1, int(bevel_segments))
        modifier.limit_method = "ANGLE"
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    if parent is not None:
        obj.parent = parent
    return obj


def _cylinder(
    bpy: Any,
    name: str,
    location: tuple[float, float, float],
    radius: float,
    depth: float,
    vertices: int,
    material: Any,
    *,
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    parent: Any = None,
) -> Any:
    bpy.ops.mesh.primitive_cylinder_add(vertices=max(6, vertices), radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    _apply_material(obj, material)
    if parent is not None:
        obj.parent = parent
    return obj


def _root(bpy: Any, asset_id: str, profile: str, lod: int, seed: int) -> Any:
    root = bpy.data.objects.new(asset_id, None)
    bpy.context.scene.collection.objects.link(root)
    root["asset_id"] = asset_id
    root["quality_profile"] = profile
    root["lod_level"] = lod
    root["generation_seed"] = seed
    root["generator"] = "bahrain-brick-golden-master-v1"
    return root


def _collision(
    bpy: Any,
    root: Any,
    asset_id: str,
    location: tuple[float, float, float],
    dimensions: tuple[float, float, float],
) -> Any:
    obj = _cube(
        bpy,
        f"{asset_id}_mesh_col_box_01",
        location,
        dimensions,
        None,
        parent=root,
    )
    obj.display_type = "WIRE"
    obj.hide_render = True
    obj["collision_proxy"] = True
    obj["collision_type"] = "box"
    return obj


def _detail(profile: str, lod: int) -> int:
    profile_rank = {"low": 0, "balanced": 1, "high": 2}[profile]
    return max(0, profile_rank + (2 - lod))


def _bevel(profile: str, lod: int) -> tuple[float, int]:
    detail = _detail(profile, lod)
    return (0.015 + detail * 0.008, 1 + min(2, detail // 2)) if lod < 2 else (0.0, 1)


def _build_traditional_window(bpy: Any, root: Any, profile: str, lod: int, mats: dict[str, Any]) -> None:
    detail = _detail(profile, lod)
    bevel, segments = _bevel(profile, lod)
    wall = mats["sand_plaster"]
    stone = mats["limestone"]
    timber = mats["dark_timber"]
    _cube(bpy, "wall_left", (-1.15, 0.0, 1.7), (0.70, 0.34, 3.4), wall, bevel=bevel, bevel_segments=segments, parent=root)
    _cube(bpy, "wall_right", (1.15, 0.0, 1.7), (0.70, 0.34, 3.4), wall, bevel=bevel, bevel_segments=segments, parent=root)
    _cube(bpy, "wall_top", (0.0, 0.0, 3.10), (1.60, 0.34, 0.60), wall, bevel=bevel, bevel_segments=segments, parent=root)
    _cube(bpy, "wall_sill", (0.0, 0.0, 0.45), (1.60, 0.34, 0.90), stone, bevel=bevel, bevel_segments=segments, parent=root)
    if lod < 2:
        _cube(bpy, "recess_shadow", (0.0, -0.20, 1.78), (1.48, 0.10, 1.72), timber, parent=root)
        _cube(bpy, "projecting_bay", (0.0, -0.42, 1.78), (1.58, 0.46, 1.82), timber, bevel=bevel, bevel_segments=segments, parent=root)
        _cube(bpy, "shade_hood", (0.0, -0.50, 2.82), (1.92, 0.72, 0.18), timber, bevel=bevel, bevel_segments=segments, parent=root)
        _cube(bpy, "stone_trim_top", (0.0, -0.04, 2.72), (1.82, 0.18, 0.16), stone, parent=root)
        slats = 3 + detail * 2
        for index in range(slats):
            x = -0.62 + index * 1.24 / max(1, slats - 1)
            _cube(bpy, f"timber_slat_{index:02d}", (x, -0.68, 1.80), (0.07, 0.08, 1.44), timber, parent=root)
        if detail >= 2:
            for side in (-1.0, 1.0):
                _cube(bpy, f"hood_bracket_{'l' if side < 0 else 'r'}", (side * 0.73, -0.54, 2.53), (0.12, 0.38, 0.48), timber, bevel=bevel, parent=root)
    else:
        _cube(bpy, "projecting_window_mass", (0.0, -0.28, 1.80), (1.60, 0.34, 1.72), timber, parent=root)
        _cube(bpy, "shade_hood", (0.0, -0.34, 2.76), (1.86, 0.48, 0.16), timber, parent=root)
    _collision(bpy, root, root["asset_id"], (0.0, 0.0, 1.70), (3.0, 0.42, 3.4))


def _build_souq_gold_shop(bpy: Any, root: Any, profile: str, lod: int, mats: dict[str, Any]) -> None:
    detail = _detail(profile, lod)
    bevel, segments = _bevel(profile, lod)
    plaster = mats["sand_plaster"]
    timber = mats["dark_timber"]
    metal = mats["painted_metal"]
    glass = mats["blue_glass"]
    gold = mats["souq_gold"]
    _cube(bpy, "pier_left", (-1.72, 0.0, 1.9), (0.56, 0.44, 3.8), plaster, bevel=bevel, bevel_segments=segments, parent=root)
    _cube(bpy, "pier_right", (1.72, 0.0, 1.9), (0.56, 0.44, 3.8), plaster, bevel=bevel, bevel_segments=segments, parent=root)
    _cube(bpy, "lintel", (0.0, 0.0, 3.50), (2.90, 0.44, 0.60), plaster, bevel=bevel, bevel_segments=segments, parent=root)
    _cube(bpy, "fascia", (0.0, -0.28, 3.32), (3.42, 0.20, 0.62), gold, bevel=bevel, bevel_segments=segments, parent=root)
    _cube(bpy, "awning", (0.0, -0.93, 2.72), (3.35, 1.35, 0.16), gold, bevel=bevel, bevel_segments=segments, parent=root)
    if lod < 2:
        _cube(bpy, "display_glass", (-0.55, -0.25, 1.58), (1.62, 0.10, 2.34), glass, parent=root)
        _cube(bpy, "door", (1.05, -0.25, 1.34), (0.72, 0.12, 2.48), timber, bevel=bevel, parent=root)
        _cube(bpy, "display_plinth", (-0.55, -0.37, 0.40), (1.70, 0.58, 0.44), stone := mats["limestone"], bevel=bevel, parent=root)
        mullions = 2 + detail
        for index in range(mullions):
            x = -1.23 + index * 1.36 / max(1, mullions - 1)
            _cube(bpy, f"display_mullion_{index:02d}", (x, -0.34, 1.62), (0.055, 0.08, 2.28), metal, parent=root)
        if detail >= 2:
            for row in range(2):
                _cube(bpy, f"display_shelf_{row}", (-0.55, -0.48, 0.90 + row * 0.58), (1.50, 0.34, 0.07), gold, parent=root)
            _cube(bpy, "shutter_box", (0.0, -0.12, 2.82), (2.90, 0.20, 0.24), metal, parent=root)
    else:
        _cube(bpy, "shop_infill", (0.0, -0.20, 1.55), (2.86, 0.12, 2.45), glass, parent=root)
    _collision(bpy, root, root["asset_id"], (0.0, 0.0, 1.90), (4.0, 0.50, 3.8))


def _build_waterfront_tower(bpy: Any, root: Any, profile: str, lod: int, mats: dict[str, Any]) -> None:
    detail = _detail(profile, lod)
    bevel, segments = _bevel(profile, lod)
    glass = mats["blue_glass"]
    stone = mats["limestone"]
    metal = mats["painted_metal"]
    _cube(bpy, "podium", (0.0, 0.0, 2.0), (8.4, 7.2, 4.0), stone, bevel=bevel, bevel_segments=segments, parent=root)
    tiers = 2 if lod == 2 else 3 + min(2, detail)
    total_height = 32.0
    base_z = 4.0
    tier_height = (total_height - base_z) / tiers
    for index in range(tiers):
        scale = 1.0 - index * 0.08
        z = base_z + tier_height * (index + 0.5)
        _cube(
            bpy,
            f"tower_tier_{index:02d}",
            (0.18 * index, 0.0, z),
            (6.8 * scale, 6.2 * scale, tier_height * 0.96),
            glass if index % 2 == 0 else stone,
            bevel=bevel,
            bevel_segments=segments,
            parent=root,
        )
    _cube(bpy, "crown", (0.55, 0.0, 32.8), (5.4, 5.0, 1.6), metal, bevel=bevel, bevel_segments=segments, parent=root)
    if lod == 0:
        fin_count = 4 + detail * 2
        for index in range(fin_count):
            x = -2.5 + index * 5.0 / max(1, fin_count - 1)
            _cube(bpy, f"vertical_fin_{index:02d}", (x, -3.16, 18.0), (0.10, 0.18, 26.0), metal, parent=root)
        for level in range(2 + detail):
            _cube(bpy, f"facade_band_{level:02d}", (0.0, -3.18, 8.0 + level * 5.2), (6.4, 0.12, 0.14), stone, parent=root)
    _collision(bpy, root, root["asset_id"], (0.0, 0.0, 16.5), (8.4, 7.2, 33.0))


def _build_supermarket(bpy: Any, root: Any, profile: str, lod: int, mats: dict[str, Any]) -> None:
    detail = _detail(profile, lod)
    bevel, segments = _bevel(profile, lod)
    plaster = mats["sand_plaster"]
    metal = mats["painted_metal"]
    glass = mats["blue_glass"]
    accent = mats["signage_accent"]
    _cube(bpy, "store_body", (0.0, 0.70, 1.80), (8.0, 3.8, 3.6), plaster, bevel=bevel, bevel_segments=segments, parent=root)
    _cube(bpy, "sign_band", (0.0, -1.28, 3.05), (7.45, 0.24, 0.72), accent, bevel=bevel, bevel_segments=segments, parent=root)
    _cube(bpy, "sun_canopy", (0.0, -1.95, 2.66), (7.65, 1.45, 0.18), metal, bevel=bevel, bevel_segments=segments, parent=root)
    if lod < 2:
        _cube(bpy, "front_glazing", (-1.35, -1.24, 1.42), (4.40, 0.10, 2.22), glass, parent=root)
        _cube(bpy, "entrance_door", (2.15, -1.25, 1.40), (1.25, 0.12, 2.48), glass, bevel=bevel, parent=root)
        mullions = 2 + detail
        for index in range(mullions):
            x = -3.25 + index * 3.80 / max(1, mullions - 1)
            _cube(bpy, f"window_mullion_{index:02d}", (x, -1.32, 1.45), (0.07, 0.08, 2.22), metal, parent=root)
        _cube(bpy, "kerb_edge", (0.0, -2.30, 0.16), (8.4, 0.65, 0.32), mats["promenade_paving"], bevel=bevel, parent=root)
        if detail >= 2:
            _cube(bpy, "service_panel", (3.45, 1.62, 1.15), (0.50, 0.18, 1.10), metal, parent=root)
            _cylinder(bpy, "ac_fan", (3.45, 1.48, 1.15), 0.16, 0.08, 12 + detail * 2, metal, rotation=(math.pi / 2, 0.0, 0.0), parent=root)
    else:
        _cube(bpy, "storefront_infill", (0.0, -1.22, 1.42), (6.95, 0.10, 2.20), glass, parent=root)
    _collision(bpy, root, root["asset_id"], (0.0, 0.65, 1.80), (8.0, 3.9, 3.6))


def _build_hero_tower(bpy: Any, root: Any, profile: str, lod: int, mats: dict[str, Any]) -> None:
    detail = _detail(profile, lod)
    bevel, segments = _bevel(profile, lod)
    glass = mats["blue_glass"]
    stone = mats["limestone"]
    metal = mats["painted_metal"]
    _cube(bpy, "hero_podium", (0.0, 0.0, 2.5), (18.0, 10.0, 5.0), stone, bevel=bevel, bevel_segments=segments, parent=root)
    segment_count = 2 if lod == 2 else 3 + min(2, detail)
    for side, base_x, max_height in (("left", -4.5, 52.0), ("right", 4.8, 44.0)):
        segment_height = (max_height - 5.0) / segment_count
        for index in range(segment_count):
            taper = 1.0 - index * 0.09
            x_shift = (index * 0.32) * (-1.0 if side == "left" else 1.0)
            _cube(
                bpy,
                f"{side}_mass_{index:02d}",
                (base_x + x_shift, 0.0, 5.0 + segment_height * (index + 0.5)),
                (6.6 * taper, 7.4 * taper, segment_height * 0.96),
                glass if index % 2 == 0 else stone,
                bevel=bevel,
                bevel_segments=segments,
                parent=root,
            )
    if lod < 2:
        _cube(bpy, "sky_bridge", (0.0, 0.0, 29.0), (5.6, 5.4, 2.2), metal, bevel=bevel, bevel_segments=segments, parent=root)
        _cube(bpy, "left_crown", (-5.6, 0.0, 53.4), (4.2, 4.2, 2.8), metal, bevel=bevel, bevel_segments=segments, parent=root)
        _cube(bpy, "right_crown", (5.6, 0.0, 45.4), (4.0, 4.0, 2.6), metal, bevel=bevel, bevel_segments=segments, parent=root)
    if lod == 0:
        fin_count = 3 + detail
        for index in range(fin_count):
            y = -3.1 + index * 6.2 / max(1, fin_count - 1)
            _cube(bpy, f"left_sail_fin_{index:02d}", (-8.0, y, 31.0), (0.18, 0.12, 38.0), metal, parent=root)
            _cube(bpy, f"right_sail_fin_{index:02d}", (8.2, y, 27.0), (0.18, 0.12, 32.0), metal, parent=root)
    _collision(bpy, root, root["asset_id"], (0.0, 0.0, 27.5), (18.0, 10.0, 55.0))


_BUILDERS: dict[str, Callable[[Any, Any, str, int, dict[str, Any]], None]] = {
    "bh_traditional_projecting_window_01": _build_traditional_window,
    "bh_souq_shop_gold_01": _build_souq_gold_shop,
    "bh_waterfront_tower_a_01": _build_waterfront_tower,
    "bh_supermarket_storefront_a_01": _build_supermarket,
    "bh_cr_skyscraper_tower_01": _build_hero_tower,
}


def _statistics(bpy: Any) -> dict[str, int]:
    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and not obj.get("collision_proxy")]
    collision_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and obj.get("collision_proxy")]
    triangle_count = 0
    material_names: set[str] = set()
    for obj in mesh_objects:
        triangle_count += sum(max(0, len(polygon.vertices) - 2) for polygon in obj.data.polygons)
        material_names.update(material.name for material in obj.data.materials if material is not None)
    return {
        "mesh_object_count": len(mesh_objects),
        "collision_object_count": len(collision_objects),
        "triangle_count": triangle_count,
        "material_count": len(material_names),
    }


def generate_asset(asset_id: str, profile: str, lod: int, output: Path, seed: int) -> dict[str, Any]:
    """Generate one GLB. Must be called from Blender's Python runtime."""
    import bpy  # type: ignore

    if asset_id not in _BUILDERS:
        raise KeyError(f"unknown golden-master asset: {asset_id}")
    if profile not in QUALITY_PROFILES:
        raise KeyError(f"unknown quality profile: {profile}")
    if lod not in LOD_LEVELS:
        raise ValueError(f"invalid LOD: {lod}")

    _reset_scene(bpy)
    root = _root(bpy, asset_id, profile, lod, seed)
    mats = {
        key: _material(bpy, profile, key)
        for key in (
            "sand_plaster",
            "limestone",
            "dark_timber",
            "painted_metal",
            "blue_glass",
            "souq_gold",
            "promenade_paving",
            "signage_accent",
        )
    }
    _BUILDERS[asset_id](bpy, root, profile, lod, mats)
    stats = _statistics(bpy)
    root["triangle_count"] = stats["triangle_count"]
    root["material_count"] = stats["material_count"]
    root["collision_present"] = stats["collision_object_count"] > 0
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(output),
        export_format="GLB",
        export_apply=True,
        export_extras=True,
        export_materials="EXPORT",
        use_selection=False,
    )
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return {
        "asset_id": asset_id,
        "profile": profile,
        "lod": lod,
        "seed": seed,
        "path": output.as_posix(),
        "bytes": output.stat().st_size,
        "sha256": digest,
        **stats,
    }


def generate_all(output_dir: Path, seed: int) -> dict[str, Any]:
    plan = generation_plan(seed)
    reports: list[dict[str, Any]] = []
    for record in plan["outputs"]:
        reports.append(
            generate_asset(
                record["asset_id"],
                record["profile"],
                record["lod"],
                output_dir / record["path"],
                record["seed"],
            )
        )
    return {
        "global_seed": seed,
        "source_asset_count": 5,
        "derivative_count": len(reports),
        "outputs": reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    plan_parser.add_argument("--output", type=Path)
    generate_parser = subparsers.add_parser("generate")
    generate_parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    generate_parser.add_argument("--output-dir", type=Path, required=True)
    generate_parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(_blender_args())

    if args.command == "plan":
        payload = generation_plan(args.seed)
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        else:
            print(text, end="")
        return 0

    payload = generate_all(args.output_dir, args.seed)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if payload["derivative_count"] != 45:
        raise RuntimeError(f"expected 45 golden-master derivatives, generated {payload['derivative_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
