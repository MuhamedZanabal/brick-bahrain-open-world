#!/usr/bin/env python3
"""Fail-closed validation for the textured Bahrain Brick 436-GLB matrix."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from validate_generated_asset_batch import validate_batch


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_full_matrix(architecture_root: Path, commercial_root: Path, manifest_path: Path) -> dict:
    result = validate_batch(architecture_root, commercial_root, manifest_path)
    failures = list(result["failures"])
    assets = result["assets"]
    by_key = {
        (item["asset_id"], item["profile"], item["lod"]): item
        for item in assets
        if item["group"] == "architecture"
    }

    if result["total_derivatives"] != 436:
        failures.append(f"full_matrix_count:{result['total_derivatives']}")
    if result["architecture_derivatives"] != 432 or result["commercial_derivatives"] != 4:
        failures.append("matrix_partition")

    for item in assets:
        path = Path(item["path"])
        item["sha256"] = sha256(path)
        if item["texture_count"] <= 0 or item["image_count"] <= 0:
            failures.append(f"asset:{item['relative_path']}:textured_material_required")
        if item["group"] == "architecture" and item["lod"] != 0 and item["collision_present"]:
            failures.append(f"asset:{item['relative_path']}:collision_only_allowed_on_lod0")

    collision_required = sum(1 for item in assets if item["collision_required"])
    collision_present = sum(1 for item in assets if item["collision_present"])
    if collision_required != 148:
        failures.append(f"collision_required_count:{collision_required}")
    if collision_present != 148:
        failures.append(f"collision_present_count:{collision_present}")

    architecture_ids = sorted(
        {item["asset_id"] for item in assets if item["group"] == "architecture"}
    )
    for asset_id in architecture_ids:
        for profile in ("low", "balanced", "high"):
            triangles = [
                by_key[(asset_id, profile, lod)]["triangle_count"]
                for lod in (0, 1, 2)
            ]
            if not triangles[0] > triangles[1] > triangles[2]:
                failures.append(f"lod_triangle_order:{asset_id}:{profile}:{triangles}")
        for lod in (0, 1, 2):
            profile_items = [
                by_key[(asset_id, profile, lod)]
                for profile in ("low", "balanced", "high")
            ]
            triangles = [item["triangle_count"] for item in profile_items]
            byte_sizes = [item["bytes"] for item in profile_items]
            if not triangles[0] <= triangles[1] <= triangles[2]:
                failures.append(f"profile_triangle_order:{asset_id}:lod{lod}:{triangles}")
            if not byte_sizes[0] < byte_sizes[1] < byte_sizes[2]:
                failures.append(f"profile_byte_order:{asset_id}:lod{lod}:{byte_sizes}")

    hashes = [item["sha256"] for item in assets]
    if len(hashes) != 436 or len(set(hashes)) != 436:
        failures.append(f"unique_hash_closure:{len(hashes)}:{len(set(hashes))}")

    result.update(
        {
            "generator_contract": "bahrain-brick-full-matrix-v1",
            "textured_asset_count": sum(item["texture_count"] > 0 for item in assets),
            "unique_sha256_count": len(set(hashes)),
            "collision_required_count": collision_required,
            "collision_present_total": collision_present,
            "failures": sorted(set(failures)),
            "passed": not failures,
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--architecture-root", type=Path, required=True)
    parser.add_argument("--commercial-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = validate_full_matrix(args.architecture_root, args.commercial_root, args.manifest)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "assets"}, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
