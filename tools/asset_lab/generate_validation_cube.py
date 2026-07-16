#!/usr/bin/env python3
"""Generate the canonical deterministic one-meter validation cube in Blender."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

ASSET_ID = "bb_validation_cube_1m"
MATERIAL_NAME = "bb_validation_cube_material"


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    args = _arguments()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    blend_path = output_dir / f"{ASSET_ID}.blend"
    glb_path = output_dir / f"{ASSET_ID}.glb"

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.0))
    cube = bpy.context.active_object
    cube.name = ASSET_ID
    cube.data.name = f"{ASSET_ID}_mesh"
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    material = bpy.data.materials.new(name=MATERIAL_NAME)
    material.diffuse_color = (0.72, 0.68, 0.58, 1.0)
    material.metallic = 0.0
    material.roughness = 0.82
    cube.data.materials.append(material)

    for candidate in bpy.context.selected_objects:
        candidate.select_set(False)
    cube.select_set(True)
    bpy.context.view_layer.objects.active = cube

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True, check_existing=False)
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
        export_animations=False,
    )

    dimensions = [round(float(value), 6) for value in cube.dimensions]
    report = {
        "asset_id": ASSET_ID,
        "generator": "tools/asset_lab/generate_validation_cube.py",
        "blender_version": bpy.app.version_string,
        "blend": {"path": blend_path.as_posix(), "bytes": blend_path.stat().st_size, "sha256": _sha256(blend_path)},
        "glb": {"path": glb_path.as_posix(), "bytes": glb_path.stat().st_size, "sha256": _sha256(glb_path)},
        "mesh_count": 1,
        "material_count": 1,
        "dimensions_m": dimensions,
        "location": [0.0, 0.0, 0.0],
        "rotation_euler": [0.0, 0.0, 0.0],
        "scale": [1.0, 1.0, 1.0],
        "passed": dimensions == [1.0, 1.0, 1.0],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
