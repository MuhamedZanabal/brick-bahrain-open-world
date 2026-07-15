#!/usr/bin/env python3
"""Render and compose deterministic visual evidence for five golden masters."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

ASSET_FAMILIES = {
    "bh_traditional_projecting_window_01": "traditional",
    "bh_souq_shop_gold_01": "souq",
    "bh_waterfront_tower_a_01": "waterfront",
    "bh_supermarket_storefront_a_01": "commercial",
    "bh_cr_skyscraper_tower_01": "hero_skyline",
}
VIEWS = ("front", "three_quarter", "rear")
VIEW_VECTORS = {
    "front": (0.0, -1.0, 0.18),
    "three_quarter": (0.82, -0.82, 0.24),
    "rear": (0.0, 1.0, 0.18),
}
VIEW_LABELS = {
    "front": "Front",
    "three_quarter": "Three-quarter",
    "rear": "Rear",
}
ASSET_LABELS = {
    "bh_traditional_projecting_window_01": "Traditional projecting window",
    "bh_souq_shop_gold_01": "Manama Souq gold shop",
    "bh_waterfront_tower_a_01": "Waterfront tower",
    "bh_supermarket_storefront_a_01": "Neighbourhood supermarket",
    "bh_cr_skyscraper_tower_01": "Original hero skyline tower",
}


def render_plan(input_root: Path, output_root: Path) -> dict[str, Any]:
    renders: list[dict[str, Any]] = []
    contact_sheets: list[dict[str, Any]] = []
    for asset_id, family in ASSET_FAMILIES.items():
        source = input_root / "balanced" / family / f"{asset_id}_lod0.glb"
        for view in VIEWS:
            renders.append(
                {
                    "asset_id": asset_id,
                    "family": family,
                    "profile": "balanced",
                    "lod": 0,
                    "view": view,
                    "input": source.as_posix(),
                    "output": (output_root / "views" / f"{asset_id}__{view}.png").as_posix(),
                }
            )
        contact_sheets.append(
            {
                "asset_id": asset_id,
                "family": family,
                "profile": "balanced",
                "lod": 0,
                "path": (output_root / "contact-sheets" / f"{asset_id}.png").as_posix(),
            }
        )
    return {
        "asset_count": len(ASSET_FAMILIES),
        "view_count": len(renders),
        "renders": renders,
        "contact_sheets": contact_sheets,
    }


def _blender_argv() -> list[str]:
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]


def _reset_blender(bpy: Any) -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def _visible_meshes(bpy: Any) -> list[Any]:
    meshes: list[Any] = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        lowered = obj.name.lower()
        is_collision = obj.get("collision_proxy") or "_col_" in lowered or lowered.endswith("collision")
        obj.hide_render = bool(is_collision)
        if not is_collision:
            meshes.append(obj)
    return meshes


def _world_bounds(objects: list[Any]) -> tuple[Any, Any]:
    from mathutils import Vector

    if not objects:
        raise RuntimeError("imported golden master contains no visible mesh objects")
    minimum = Vector((float("inf"), float("inf"), float("inf")))
    maximum = Vector((float("-inf"), float("-inf"), float("-inf")))
    for obj in objects:
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            minimum.x = min(minimum.x, world.x)
            minimum.y = min(minimum.y, world.y)
            minimum.z = min(minimum.z, world.z)
            maximum.x = max(maximum.x, world.x)
            maximum.y = max(maximum.y, world.y)
            maximum.z = max(maximum.z, world.z)
    return minimum, maximum


def _look_at(obj: Any, target: Any) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _setup_scene(bpy: Any, minimum: Any, maximum: Any, output: Path) -> tuple[Any, Any, float]:
    from mathutils import Vector

    center = (minimum + maximum) * 0.5
    extents = maximum - minimum
    radius = max(float(extents.x), float(extents.y), float(extents.z)) * 0.5
    radius = max(radius, 1.0)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.filepath = str(output)
    scene.render.use_file_extension = True
    scene.render.use_compositing = True
    scene.render.use_sequencer = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.world.color = (0.035, 0.045, 0.065)

    bpy.ops.mesh.primitive_plane_add(size=radius * 5.0, location=(center.x, center.y, minimum.z - radius * 0.015))
    ground = bpy.context.object
    ground.name = "QA_Ground"
    ground_material = bpy.data.materials.new("qa_ground_material")
    ground_material.diffuse_color = (0.12, 0.14, 0.17, 1.0)
    ground_material.roughness = 0.94
    ground.data.materials.append(ground_material)

    bpy.ops.object.light_add(type="AREA", location=(center.x - radius * 1.2, center.y - radius * 1.4, maximum.z + radius * 1.5))
    key = bpy.context.object
    key.name = "QA_Key"
    key.data.energy = 900.0 + radius * 60.0
    key.data.shape = "DISK"
    key.data.size = radius * 1.6
    _look_at(key, center)

    bpy.ops.object.light_add(type="AREA", location=(center.x + radius * 1.4, center.y + radius * 0.8, center.z + radius * 0.6))
    fill = bpy.context.object
    fill.name = "QA_Fill"
    fill.data.energy = 500.0 + radius * 35.0
    fill.data.size = radius * 1.8
    _look_at(fill, center)

    bpy.ops.object.light_add(type="SUN", location=(center.x, center.y, maximum.z + radius))
    sun = bpy.context.object
    sun.name = "QA_Sun"
    sun.data.energy = 1.6
    sun.rotation_euler = (math.radians(28.0), math.radians(-24.0), math.radians(32.0))

    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "QA_Camera"
    camera.data.lens = 52.0
    camera.data.sensor_width = 36.0
    camera.data.dof.use_dof = False
    scene.camera = camera
    return camera, center, radius


def _render_one(source: Path, output: Path, view: str) -> dict[str, Any]:
    import bpy  # type: ignore
    from mathutils import Vector

    if not source.is_file():
        raise FileNotFoundError(f"golden-master GLB missing: {source}")
    _reset_blender(bpy)
    bpy.ops.import_scene.gltf(filepath=str(source))
    meshes = _visible_meshes(bpy)
    minimum, maximum = _world_bounds(meshes)
    output.parent.mkdir(parents=True, exist_ok=True)
    camera, center, radius = _setup_scene(bpy, minimum, maximum, output)
    vector = Vector(VIEW_VECTORS[view]).normalized()
    distance = radius * 3.05
    camera.location = center + vector * distance
    camera.location.z = max(camera.location.z, minimum.z + radius * 0.70)
    _look_at(camera, center)
    bpy.context.scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    if not output.is_file() or output.stat().st_size < 4096:
        raise RuntimeError(f"render did not produce a valid PNG: {output}")
    return {
        "path": output.as_posix(),
        "bytes": output.stat().st_size,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "mesh_object_count": len(meshes),
        "bounds_min": [round(float(value), 6) for value in minimum],
        "bounds_max": [round(float(value), 6) for value in maximum],
    }


def render_views(input_root: Path, output_root: Path) -> dict[str, Any]:
    plan = render_plan(input_root, output_root)
    results: list[dict[str, Any]] = []
    for record in plan["renders"]:
        result = _render_one(Path(record["input"]), Path(record["output"]), record["view"])
        results.append({**record, **result})
    return {"asset_count": 5, "view_count": 15, "renders": results}


def compose_contact_sheets(view_report: dict[str, Any], output_root: Path) -> dict[str, Any]:
    from PIL import Image, ImageDraw, ImageFont

    records = view_report.get("renders")
    if not isinstance(records, list):
        raise ValueError("view report must contain a renders list")
    by_asset: dict[str, dict[str, dict[str, Any]]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        by_asset.setdefault(record["asset_id"], {})[record["view"]] = record

    sheets: list[dict[str, Any]] = []
    output_dir = output_root / "contact-sheets"
    output_dir.mkdir(parents=True, exist_ok=True)
    for asset_id, family in ASSET_FAMILIES.items():
        view_records = by_asset.get(asset_id, {})
        if set(view_records) != set(VIEWS):
            raise RuntimeError(f"missing rendered views for {asset_id}: {sorted(view_records)}")
        panels = [Image.open(view_records[view]["path"]).convert("RGB") for view in VIEWS]
        panel_width = max(image.width for image in panels)
        panel_height = max(image.height for image in panels)
        header = 88
        footer = 42
        sheet = Image.new("RGB", (panel_width * 3, panel_height + header + footer), (18, 22, 30))
        draw = ImageDraw.Draw(sheet)
        font = ImageFont.load_default()
        title = f"Bahrain Brick — {ASSET_LABELS[asset_id]} — Balanced / LOD0"
        draw.text((24, 22), title, fill=(244, 246, 250), font=font)
        draw.text((24, 48), f"Asset ID: {asset_id} | Family: {family}", fill=(174, 184, 202), font=font)
        for index, view in enumerate(VIEWS):
            image = panels[index]
            x = index * panel_width
            sheet.paste(image, (x, header))
            draw.text((x + 18, header + panel_height + 14), VIEW_LABELS[view], fill=(230, 234, 242), font=font)
        path = output_dir / f"{asset_id}.png"
        sheet.save(path, format="PNG", optimize=True)
        sheets.append(
            {
                "asset_id": asset_id,
                "family": family,
                "profile": "balanced",
                "lod": 0,
                "path": path.as_posix(),
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "views": list(VIEWS),
            }
        )
        for image in panels:
            image.close()
    return {"asset_count": 5, "contact_sheet_count": 5, "contact_sheets": sheets}


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("--input-root", type=Path, required=True)
    render_parser.add_argument("--output-root", type=Path, required=True)
    render_parser.add_argument("--report", type=Path, required=True)
    compose_parser = subparsers.add_parser("compose")
    compose_parser.add_argument("--view-report", type=Path, required=True)
    compose_parser.add_argument("--output-root", type=Path, required=True)
    compose_parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(_blender_argv())

    if args.command == "render":
        report = render_views(args.input_root, args.output_root)
    else:
        view_report = json.loads(args.view_report.read_text(encoding="utf-8"))
        report = compose_contact_sheets(view_report, args.output_root)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
