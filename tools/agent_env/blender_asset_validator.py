#!/usr/bin/env python3
"""Blender background validator for original Bahrain Brick modular assets."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any

try:
    import bpy  # type: ignore
except ImportError as exc:  # pragma: no cover - executed by Blender
    raise SystemExit(f"This validator must run inside Blender: {exc}")

PROTECTED_TERMS = ("lego", "minifig", "minifigure", "bricklink", "ldraw")


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--asset", required=True)
    parser.add_argument("--triangle-budget", required=True, type=int)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def confined(path: Path, root: Path) -> Path:
    resolved = path.resolve(strict=True)
    resolved.relative_to(root)
    return resolved


def load_asset(asset: Path) -> None:
    suffix = asset.suffix.lower()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if suffix == ".blend":
        bpy.ops.wm.open_mainfile(filepath=str(asset))
    elif suffix in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(asset))
    else:
        raise ValueError("unsupported asset type")


def triangles_for(obj: Any) -> int:
    mesh = obj.data
    mesh.calc_loop_triangles()
    return len(mesh.loop_triangles)


def finite_vector(values: Any) -> bool:
    return all(math.isfinite(float(value)) for value in values)


def main() -> int:
    args = arguments()
    root = Path(args.root).resolve(strict=True)
    asset = confined(Path(args.asset), root)
    output = Path(args.output).resolve(strict=False)
    output.relative_to(root)
    output.parent.mkdir(parents=True, exist_ok=True)

    load_asset(asset)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    objects: list[dict[str, Any]] = []
    issues: list[dict[str, str]] = []
    total_triangles = 0
    material_names: set[str] = set()
    texture_paths: set[str] = set()

    for obj in meshes:
        triangles = triangles_for(obj)
        total_triangles += triangles
        scale_applied = all(abs(float(component) - 1.0) <= 1e-4 for component in obj.scale)
        rotation_applied = all(abs(float(component)) <= 1e-4 for component in obj.rotation_euler)
        dimensions_finite = finite_vector(obj.dimensions)
        if not scale_applied:
            issues.append({"code": "UNAPPLIED_SCALE", "object": obj.name})
        if not rotation_applied:
            issues.append({"code": "UNAPPLIED_ROTATION", "object": obj.name})
        if not dimensions_finite or any(float(value) <= 0 for value in obj.dimensions):
            issues.append({"code": "INVALID_DIMENSIONS", "object": obj.name})
        lowered = obj.name.lower()
        for term in PROTECTED_TERMS:
            if term in lowered:
                issues.append({"code": "PROTECTED_NAME", "object": obj.name, "term": term})
        for slot in obj.material_slots:
            if slot.material:
                material_names.add(slot.material.name)
        objects.append(
            {
                "name": obj.name,
                "triangles": triangles,
                "dimensions_metres": [round(float(value), 6) for value in obj.dimensions],
                "scale": [round(float(value), 6) for value in obj.scale],
                "rotation_radians": [round(float(value), 6) for value in obj.rotation_euler],
                "scale_applied": scale_applied,
                "rotation_applied": rotation_applied,
            }
        )

    for image in bpy.data.images:
        raw = str(getattr(image, "filepath", "") or "").strip()
        if not raw or raw.startswith("//"):
            continue
        try:
            resolved = Path(bpy.path.abspath(raw)).resolve(strict=False)
            resolved.relative_to(root)
            texture_paths.add(str(resolved.relative_to(root)))
        except ValueError:
            issues.append({"code": "EXTERNAL_TEXTURE", "image": image.name, "path": raw})

    names_to_scan = [asset.name, *material_names, *(obj["name"] for obj in objects)]
    for name in names_to_scan:
        for term in PROTECTED_TERMS:
            if re.search(rf"(^|[^a-z]){re.escape(term)}([^a-z]|$)", name.lower()):
                issues.append({"code": "PROTECTED_NAME", "name": name, "term": term})

    if not meshes:
        issues.append({"code": "NO_MESHES", "asset": str(asset.relative_to(root))})
    if total_triangles > args.triangle_budget:
        issues.append(
            {
                "code": "TRIANGLE_BUDGET_EXCEEDED",
                "actual": str(total_triangles),
                "budget": str(args.triangle_budget),
            }
        )

    digest = hashlib.sha256()
    with asset.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)

    report = {
        "schema_version": 1,
        "asset": str(asset.relative_to(root)),
        "asset_sha256": digest.hexdigest(),
        "bytes": asset.stat().st_size,
        "blender_version": bpy.app.version_string,
        "scene_unit_system": bpy.context.scene.unit_settings.system,
        "scene_scale_length": bpy.context.scene.unit_settings.scale_length,
        "mesh_count": len(meshes),
        "total_triangles": total_triangles,
        "triangle_budget": args.triangle_budget,
        "material_count": len(material_names),
        "materials": sorted(material_names),
        "textures": sorted(texture_paths),
        "objects": objects,
        "issues": issues,
        "passed": len(issues) == 0,
        "license_verified": False,
        "license_note": "Geometry validation cannot prove licensing; a provenance ledger is still required.",
    }
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
