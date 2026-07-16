#!/usr/bin/env python3
"""Production V2 layer for textured, higher-detail Bahrain Brick golden masters."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_golden_masters as base

GENERATOR_VERSION = "bahrain-brick-golden-master-v2"
_TEXTURE_ROOT: Path | None = None
_ORIGINAL_BUILDERS = dict(base._BUILDERS)


def generation_plan(seed: int) -> dict[str, Any]:
    plan = base.generation_plan(seed)
    plan["generator_version"] = GENERATOR_VERSION
    plan["texture_count"] = 24
    return plan


def _textured_material(bpy: Any, profile: str, key: str) -> Any:
    material = _BASE_MATERIAL(bpy, profile, key)
    if _TEXTURE_ROOT is None:
        raise RuntimeError("golden-master V2 texture root is not configured")
    texture_path = (_TEXTURE_ROOT / profile / f"{key}_albedo.png").resolve()
    if not texture_path.is_file():
        raise FileNotFoundError(f"required golden-master texture missing: {texture_path}")
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    principled = nodes.get("Principled BSDF")
    texture = nodes.get(f"gm_{key}_albedo") or nodes.new("ShaderNodeTexImage")
    texture.name = f"gm_{key}_albedo"
    texture.label = f"{profile}/{key}"
    texture.image = bpy.data.images.load(str(texture_path), check_existing=True)
    texture.interpolation = "Linear"
    if principled is not None:
        for link in list(principled.inputs["Base Color"].links):
            links.remove(link)
        links.new(texture.outputs["Color"], principled.inputs["Base Color"])
    material["albedo_texture"] = texture_path.as_posix()
    material["generator_version"] = GENERATOR_VERSION
    return material


def _detail_count(profile: str, lod: int, low: int, balanced: int, high: int) -> int:
    value = {"low": low, "balanced": balanced, "high": high}[profile]
    if lod == 1:
        return max(1, value // 2)
    if lod == 2:
        return 0
    return value


def _enhance_traditional(bpy: Any, root: Any, profile: str, lod: int, mats: dict[str, Any]) -> None:
    if lod == 2:
        return
    bevel, segments = base._bevel(profile, lod)
    timber = mats["dark_timber"]
    stone = mats["limestone"]
    count = _detail_count(profile, lod, 4, 6, 8)
    for index in range(count):
        z = 1.18 + index * 1.18 / max(1, count - 1)
        base._cube(bpy, f"mashrabiya_crossbar_{index:02d}", (0.0, -0.725, z), (1.34, 0.065, 0.045), timber, bevel=bevel * 0.4, bevel_segments=segments, parent=root)
    side_count = _detail_count(profile, lod, 2, 3, 4)
    for side in (-1.0, 1.0):
        for index in range(side_count):
            z = 1.25 + index * 1.05 / max(1, side_count - 1)
            base._cube(bpy, f"side_lattice_{'l' if side < 0 else 'r'}_{index:02d}", (side * 0.785, -0.52, z), (0.055, 0.32, 0.52), timber, bevel=bevel * 0.5, parent=root)
        base._cube(bpy, f"stone_jamb_{'l' if side < 0 else 'r'}", (side * 0.89, -0.06, 1.82), (0.16, 0.20, 1.96), stone, bevel=bevel, bevel_segments=segments, parent=root)
    if lod == 0:
        for index in range(_detail_count(profile, lod, 2, 3, 4)):
            x = -0.60 + index * 1.20 / max(1, _detail_count(profile, lod, 2, 3, 4) - 1)
            base._cube(bpy, f"hood_rib_{index:02d}", (x, -0.67, 2.82), (0.055, 0.36, 0.24), timber, bevel=bevel * 0.4, parent=root)


def _enhance_souq(bpy: Any, root: Any, profile: str, lod: int, mats: dict[str, Any]) -> None:
    if lod == 2:
        return
    bevel, segments = base._bevel(profile, lod)
    gold = mats["souq_gold"]
    metal = mats["painted_metal"]
    timber = mats["dark_timber"]
    trim_count = _detail_count(profile, lod, 4, 6, 8)
    for index in range(trim_count):
        x = -1.45 + index * 2.90 / max(1, trim_count - 1)
        base._cube(bpy, f"fascia_trim_{index:02d}", (x, -0.405, 3.32), (0.06, 0.08, 0.52), gold, bevel=bevel * 0.35, parent=root)
    if lod == 0:
        jewelry_count = _detail_count(profile, lod, 5, 8, 12)
        for index in range(jewelry_count):
            column = index % 4
            row = index // 4
            x = -1.08 + column * 0.36
            z = 0.84 + row * 0.50
            base._cylinder(bpy, f"gold_display_{index:02d}", (x, -0.69, z), 0.07, 0.12, 8 + base._detail(profile, lod) * 2, gold, rotation=(math.pi / 2, 0.0, 0.0), parent=root)
        for side in (-1.0, 1.0):
            base._cube(bpy, f"awning_brace_{'l' if side < 0 else 'r'}", (side * 1.45, -0.78, 2.48), (0.10, 0.75, 0.12), metal, bevel=bevel, parent=root)
            base._cube(bpy, f"door_trim_{'l' if side < 0 else 'r'}", (1.05 + side * 0.40, -0.34, 1.34), (0.08, 0.10, 2.58), timber, bevel=bevel, parent=root)


def _enhance_waterfront(bpy: Any, root: Any, profile: str, lod: int, mats: dict[str, Any]) -> None:
    if lod == 2:
        return
    bevel, segments = base._bevel(profile, lod)
    metal = mats["painted_metal"]
    stone = mats["limestone"]
    band_count = _detail_count(profile, lod, 5, 8, 11)
    for index in range(band_count):
        z = 6.5 + index * 23.0 / max(1, band_count - 1)
        width = 6.6 - index * 0.10
        base._cube(bpy, f"horizontal_shade_{index:02d}", (0.18, -3.15, z), (width, 0.22, 0.16), metal, bevel=bevel * 0.35, parent=root)
    podium_columns = _detail_count(profile, lod, 4, 6, 8)
    for index in range(podium_columns):
        x = -3.45 + index * 6.9 / max(1, podium_columns - 1)
        base._cube(bpy, f"podium_column_{index:02d}", (x, -3.66, 2.0), (0.18, 0.22, 3.5), stone, bevel=bevel, bevel_segments=segments, parent=root)
    if lod == 0:
        terrace_count = _detail_count(profile, lod, 2, 3, 4)
        for index in range(terrace_count):
            z = 8.0 + index * 6.2
            base._cube(bpy, f"terrace_slab_{index:02d}", (0.0, -3.35, z), (5.7 - index * 0.25, 0.85, 0.18), stone, bevel=bevel, parent=root)
            base._cube(bpy, f"terrace_rail_{index:02d}", (0.0, -3.72, z + 0.48), (5.5 - index * 0.25, 0.06, 0.78), metal, parent=root)


def _enhance_supermarket(bpy: Any, root: Any, profile: str, lod: int, mats: dict[str, Any]) -> None:
    if lod == 2:
        return
    bevel, segments = base._bevel(profile, lod)
    metal = mats["painted_metal"]
    accent = mats["signage_accent"]
    plaster = mats["sand_plaster"]
    for side in (-1.0, 1.0):
        base._cube(bpy, f"front_column_{'l' if side < 0 else 'r'}", (side * 3.72, -1.30, 1.72), (0.30, 0.42, 3.24), plaster, bevel=bevel, bevel_segments=segments, parent=root)
        base._cube(bpy, f"canopy_post_{'l' if side < 0 else 'r'}", (side * 3.35, -2.25, 1.25), (0.14, 0.14, 2.50), metal, bevel=bevel, parent=root)
        base._cube(bpy, f"canopy_brace_{'l' if side < 0 else 'r'}", (side * 3.35, -1.92, 2.45), (0.12, 0.70, 0.12), metal, bevel=bevel, parent=root)
    sign_blocks = _detail_count(profile, lod, 5, 8, 12)
    for index in range(sign_blocks):
        x = -2.65 + index * 5.30 / max(1, sign_blocks - 1)
        height = 0.20 if index % 3 else 0.32
        base._cube(bpy, f"sign_glyph_{index:02d}", (x, -1.43, 3.05), (0.22, 0.06, height), accent, bevel=bevel * 0.4, parent=root)
    if lod == 0:
        bollards = _detail_count(profile, lod, 3, 5, 7)
        for index in range(bollards):
            x = -2.9 + index * 5.8 / max(1, bollards - 1)
            base._cylinder(bpy, f"entry_bollard_{index:02d}", (x, -2.58, 0.45), 0.09, 0.90, 8 + base._detail(profile, lod) * 2, metal, parent=root)
        ac_count = _detail_count(profile, lod, 1, 2, 3)
        for index in range(ac_count):
            x = 2.7 - index * 0.9
            base._cube(bpy, f"roof_ac_{index:02d}", (x, 1.10, 3.95), (0.70, 0.55, 0.55), metal, bevel=bevel, parent=root)
            base._cylinder(bpy, f"roof_ac_fan_{index:02d}", (x, 0.81, 3.95), 0.18, 0.06, 12 + base._detail(profile, lod) * 2, metal, rotation=(math.pi / 2, 0.0, 0.0), parent=root)
        for side in (-1.0, 1.0):
            base._cube(bpy, f"roof_parapet_{'l' if side < 0 else 'r'}", (side * 3.85, 0.55, 3.90), (0.22, 3.45, 0.58), plaster, bevel=bevel, parent=root)


def _enhance_hero(bpy: Any, root: Any, profile: str, lod: int, mats: dict[str, Any]) -> None:
    if lod == 2:
        return
    bevel, segments = base._bevel(profile, lod)
    metal = mats["painted_metal"]
    stone = mats["limestone"]
    band_count = _detail_count(profile, lod, 7, 11, 15)
    for side, x, height in (("left", -4.5, 49.0), ("right", 4.8, 41.0)):
        for index in range(band_count):
            z = 7.0 + index * (height - 8.0) / max(1, band_count - 1)
            base._cube(bpy, f"{side}_facade_band_{index:02d}", (x, -3.82, z), (5.4, 0.18, 0.16), metal, bevel=bevel * 0.3, parent=root)
    podium_fins = _detail_count(profile, lod, 5, 8, 11)
    for index in range(podium_fins):
        x = -7.5 + index * 15.0 / max(1, podium_fins - 1)
        base._cube(bpy, f"podium_fin_{index:02d}", (x, -5.08, 2.6), (0.18, 0.18, 4.2), stone, bevel=bevel, parent=root)
    if lod == 0:
        crown_count = _detail_count(profile, lod, 3, 5, 7)
        for side, x, z in (("left", -5.6, 55.0), ("right", 5.6, 47.0)):
            for index in range(crown_count):
                offset = (index - (crown_count - 1) / 2) * 0.48
                base._cube(bpy, f"{side}_crown_fin_{index:02d}", (x + offset, 0.0, z + abs(offset) * 0.55), (0.16, 3.4, 3.8 - abs(offset) * 0.4), metal, bevel=bevel, bevel_segments=segments, parent=root)
        for level in range(_detail_count(profile, lod, 2, 3, 4)):
            base._cube(bpy, f"bridge_shade_{level:02d}", (0.0, -2.85, 28.4 + level * 0.55), (5.2, 0.22, 0.12), stone, parent=root)


_ENHANCERS = {
    "bh_traditional_projecting_window_01": _enhance_traditional,
    "bh_souq_shop_gold_01": _enhance_souq,
    "bh_waterfront_tower_a_01": _enhance_waterfront,
    "bh_supermarket_storefront_a_01": _enhance_supermarket,
    "bh_cr_skyscraper_tower_01": _enhance_hero,
}


def _builder(asset_id: str):
    original = _ORIGINAL_BUILDERS[asset_id]
    enhancer = _ENHANCERS[asset_id]

    def build(bpy: Any, root: Any, profile: str, lod: int, mats: dict[str, Any]) -> None:
        original(bpy, root, profile, lod, mats)
        enhancer(bpy, root, profile, lod, mats)
        root["generator"] = GENERATOR_VERSION
        root["textured"] = True

    return build


def install_v2(texture_root: Path) -> None:
    global _TEXTURE_ROOT
    _TEXTURE_ROOT = texture_root.resolve()
    if not _TEXTURE_ROOT.is_dir():
        raise FileNotFoundError(f"golden-master texture directory missing: {_TEXTURE_ROOT}")
    base._material = _textured_material
    for asset_id in base.GOLDEN_MASTER_IDS:
        base._BUILDERS[asset_id] = _builder(asset_id)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=base.DEFAULT_SEED)
    parser.add_argument("--texture-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    args = parser.parse_args(argv)
    install_v2(args.texture_dir)
    report = base.generate_all(args.output_dir, args.seed)
    report["generator_version"] = GENERATOR_VERSION
    report["texture_root"] = args.texture_dir.as_posix()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if report["derivative_count"] != 45:
        raise RuntimeError(f"expected 45 derivatives, generated {report['derivative_count']}")
    return 0


_BASE_MATERIAL = base._material

if __name__ == "__main__":
    raise SystemExit(main())
