#!/usr/bin/env python3
"""Fail-closed validation for generated Bahrain Brick architecture/commercial GLBs."""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import struct
from collections import Counter, defaultdict
from pathlib import Path

ARCHITECTURE_RECORDS = {"traditional": 14, "souq": 18, "waterfront": 16}
PROFILES = {"low", "balanced", "high"}
LODS = {0, 1, 2}
COMMERCIAL_IDS = {
    "bh_cafe_storefront_karak_a_01",
    "bh_cafe_table_chair_set_a_01",
    "bh_supermarket_shelf_1m_01",
    "bh_supermarket_storefront_a_01",
}
ARCH_PATTERN = re.compile(
    r"^(low|balanced|high)/(traditional|souq|waterfront)/(.+)_lod([012])\.glb$"
)


def _load_glb(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < 20:
        raise ValueError("GLB shorter than header plus JSON chunk")
    magic, version, total = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or total != len(data):
        raise ValueError(f"invalid GLB header: magic={magic!r} version={version} total={total} bytes={len(data)}")
    offset = 12
    document = None
    while offset < total:
        if offset + 8 > total:
            raise ValueError("truncated GLB chunk header")
        length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        end = offset + length
        if end > total:
            raise ValueError("truncated GLB chunk payload")
        payload = data[offset:end]
        offset = end
        if chunk_type == 0x4E4F534A and document is None:
            document = json.loads(payload.decode("utf-8").rstrip("\x00 "))
    if document is None:
        raise ValueError("GLB JSON chunk missing")
    return document


def _triangles(document: dict) -> int:
    accessors = document.get("accessors", [])
    total = 0
    for mesh in document.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            mode = primitive.get("mode", 4)
            if mode != 4:
                raise ValueError(f"unsupported primitive mode {mode}; TRIANGLES required")
            if "indices" in primitive:
                count = int(accessors[primitive["indices"]]["count"])
            else:
                position = primitive.get("attributes", {}).get("POSITION")
                if position is None:
                    raise ValueError("primitive POSITION accessor missing")
                count = int(accessors[position]["count"])
            if count % 3:
                raise ValueError(f"triangle index/vertex count not divisible by 3: {count}")
            total += count // 3
    return total


def _node_scale_failures(document: dict) -> list[str]:
    failures = []
    for node in document.get("nodes", []):
        scale = node.get("scale")
        if scale is not None and any(not math.isclose(float(value), 1.0, abs_tol=1e-6) for value in scale):
            failures.append(f"node {node.get('name', '<unnamed>')} has non-unit scale {scale}")
    return failures


def _inspect(path: Path, *, asset_id: str, collision_required: bool) -> dict:
    document = _load_glb(path)
    nodes = document.get("nodes", [])
    names = [str(node.get("name", "")) for node in nodes]
    failures = []
    if not document.get("meshes"):
        failures.append("mesh_count")
    if not document.get("materials"):
        failures.append("material_count")
    if any(name and not name.startswith(asset_id) for name in names):
        failures.append("node_name_contract")
    has_collision = any("col_box_01" in name or name.endswith("_col") for name in names)
    if collision_required and not has_collision:
        failures.append("required_collision")
    failures.extend(_node_scale_failures(document))
    try:
        triangles = _triangles(document)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        triangles = 0
        failures.append(f"triangles:{exc}")
    if triangles <= 0:
        failures.append("triangle_count")
    result = {
        "path": path.as_posix(),
        "asset_id": asset_id,
        "bytes": path.stat().st_size,
        "mesh_count": len(document.get("meshes", [])),
        "node_count": len(nodes),
        "material_count": len(document.get("materials", [])),
        "texture_count": len(document.get("textures", [])),
        "image_count": len(document.get("images", [])),
        "triangle_count": triangles,
        "collision_required": collision_required,
        "collision_present": has_collision,
        "failures": failures,
        "passed": not failures,
    }
    return result


def _manifest_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    by_id = {row["asset_id"]: row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError("manifest contains duplicate asset IDs")
    return by_id


def validate_batch(architecture_root: Path, commercial_root: Path, manifest_path: Path) -> dict:
    manifest = _manifest_rows(manifest_path)
    failures: list[str] = []
    assets: list[dict] = []
    architecture_glbs = sorted(architecture_root.rglob("*.glb"))
    commercial_glbs = sorted(commercial_root.glob("*.glb"))
    if len(architecture_glbs) != 432:
        failures.append(f"architecture_derivative_count:{len(architecture_glbs)}")
    if len(commercial_glbs) != 4:
        failures.append(f"commercial_derivative_count:{len(commercial_glbs)}")

    observed: dict[tuple[str, str], set[int]] = defaultdict(set)
    family_asset_ids: dict[str, set[str]] = defaultdict(set)
    family_derivatives = Counter()
    for path in architecture_glbs:
        relative = path.relative_to(architecture_root).as_posix()
        match = ARCH_PATTERN.fullmatch(relative)
        if not match:
            failures.append(f"architecture_path_contract:{relative}")
            continue
        profile, family, asset_id, lod_text = match.groups()
        lod = int(lod_text)
        row = manifest.get(asset_id)
        if row is None:
            failures.append(f"manifest_missing:{asset_id}")
        elif row.get("category") != "architecture" or row.get("subcategory") != family:
            failures.append(f"manifest_family_mismatch:{asset_id}:{row.get('category')}:{row.get('subcategory')}:{family}")
        observed[(asset_id, profile)].add(lod)
        family_asset_ids[family].add(asset_id)
        family_derivatives[family] += 1
        result = _inspect(path, asset_id=asset_id, collision_required=lod == 0)
        result.update({"group": "architecture", "profile": profile, "family": family, "lod": lod, "relative_path": relative})
        assets.append(result)

    for family, expected_records in ARCHITECTURE_RECORDS.items():
        actual_records = len(family_asset_ids[family])
        if actual_records != expected_records:
            failures.append(f"family_record_count:{family}:{actual_records}")
        expected_derivatives = expected_records * len(PROFILES) * len(LODS)
        if family_derivatives[family] != expected_derivatives:
            failures.append(f"family_derivative_count:{family}:{family_derivatives[family]}")
    for family in family_asset_ids:
        if family not in ARCHITECTURE_RECORDS:
            failures.append(f"unexpected_family:{family}")
    for asset_id in sorted({asset for asset, _profile in observed}):
        profiles = {profile for asset, profile in observed if asset == asset_id}
        if profiles != PROFILES:
            failures.append(f"profile_set:{asset_id}:{sorted(profiles)}")
        for profile in PROFILES:
            if observed[(asset_id, profile)] != LODS:
                failures.append(f"lod_set:{asset_id}:{profile}:{sorted(observed[(asset_id, profile)])}")

    commercial_ids = {path.stem for path in commercial_glbs}
    if commercial_ids != COMMERCIAL_IDS:
        failures.append(f"commercial_id_set:{sorted(commercial_ids)}")
    for path in commercial_glbs:
        asset_id = path.stem
        row = manifest.get(asset_id)
        if row is None:
            failures.append(f"manifest_missing:{asset_id}")
        result = _inspect(path, asset_id=asset_id, collision_required=True)
        result.update({"group": "commercial", "profile": "shared_mobile", "family": row.get("subcategory") if row else None, "lod": 0, "relative_path": path.name})
        assets.append(result)

    for item in assets:
        for failure in item["failures"]:
            failures.append(f"asset:{item['relative_path']}:{failure}")

    total_triangles = sum(item["triangle_count"] for item in assets)
    summary = {
        "architecture_asset_records": sum(len(ids) for ids in family_asset_ids.values()),
        "architecture_derivatives": len(architecture_glbs),
        "commercial_asset_records": len(commercial_ids),
        "commercial_derivatives": len(commercial_glbs),
        "total_derivatives": len(architecture_glbs) + len(commercial_glbs),
        "validated_assets": len(assets),
        "family_asset_records": {family: len(family_asset_ids[family]) for family in sorted(ARCHITECTURE_RECORDS)},
        "family_derivatives": {family: family_derivatives[family] for family in sorted(ARCHITECTURE_RECORDS)},
        "profiles": sorted(PROFILES),
        "lods": sorted(LODS),
        "total_triangles": total_triangles,
        "max_material_count": max((item["material_count"] for item in assets), default=0),
        "max_texture_count": max((item["texture_count"] for item in assets), default=0),
        "collision_required_count": sum(item["collision_required"] for item in assets),
        "collision_present_count": sum(item["collision_present"] for item in assets if item["collision_required"]),
        "failures": failures,
        "passed": not failures,
        "assets": assets,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--architecture-root", type=Path, required=True)
    parser.add_argument("--commercial-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = validate_batch(args.architecture_root, args.commercial_root, args.manifest)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "assets"}, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
