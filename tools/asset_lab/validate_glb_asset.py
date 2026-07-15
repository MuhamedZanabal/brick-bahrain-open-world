#!/usr/bin/env python3
"""Independently validate a constrained static GLB asset contract."""
from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path
from typing import Any

GLB_MAGIC = b"glTF"
JSON_CHUNK = 0x4E4F534A


def _identity_transform(node: dict[str, Any]) -> bool:
    return (
        node.get("translation", [0.0, 0.0, 0.0]) == [0.0, 0.0, 0.0]
        and node.get("rotation", [0.0, 0.0, 0.0, 1.0]) == [0.0, 0.0, 0.0, 1.0]
        and node.get("scale", [1.0, 1.0, 1.0]) == [1.0, 1.0, 1.0]
        and "matrix" not in node
    )


def _read_document(path: Path) -> tuple[dict[str, Any], int]:
    data = path.read_bytes()
    if len(data) < 20:
        raise ValueError("file_too_small")
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != GLB_MAGIC:
        raise ValueError("magic")
    if version != 2:
        raise ValueError("version")
    if declared_length != len(data):
        raise ValueError("declared_length")

    offset = 12
    document: dict[str, Any] | None = None
    chunk_count = 0
    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError("truncated_chunk_header")
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        end = offset + chunk_length
        if end > len(data):
            raise ValueError("truncated_chunk")
        payload = data[offset:end]
        offset = end
        chunk_count += 1
        if chunk_type == JSON_CHUNK:
            if document is not None:
                raise ValueError("duplicate_json_chunk")
            document = json.loads(payload.rstrip(b" \t\r\n\x00").decode("utf-8"))
    if document is None:
        raise ValueError("missing_json_chunk")
    return document, chunk_count


def validate_glb(path: Path, *, expected_name: str, expected_size: float, tolerance: float = 1e-5) -> dict[str, Any]:
    failures: list[str] = []
    result: dict[str, Any] = {
        "path": path.as_posix(),
        "expected_name": expected_name,
        "expected_size_m": expected_size,
        "failures": failures,
    }
    try:
        document, chunk_count = _read_document(path)
    except Exception as error:
        failures.append(f"container:{error}")
        result.update({"passed": False, "chunk_count": 0})
        return result

    asset = document.get("asset", {})
    meshes = document.get("meshes", [])
    materials = document.get("materials", [])
    nodes = document.get("nodes", [])
    result.update(
        {
            "asset_version": asset.get("version"),
            "generator": asset.get("generator"),
            "chunk_count": chunk_count,
            "mesh_count": len(meshes),
            "material_count": len(materials),
            "node_count": len(nodes),
        }
    )

    if asset.get("version") != "2.0":
        failures.append("asset_version")
    if len(meshes) != 1:
        failures.append("mesh_count")
    if len(materials) != 1:
        failures.append("material_count")
    if len(nodes) != 1:
        failures.append("node_count")
    if nodes and (nodes[0].get("name") != expected_name or not _identity_transform(nodes[0])):
        failures.append("node_transform_or_name")
    if document.get("animations"):
        failures.append("animations")
    if document.get("skins"):
        failures.append("skins")

    triangle_count = 0
    bounds: dict[str, Any] | None = None
    try:
        primitive = meshes[0]["primitives"][0]
        accessors = document["accessors"]
        position = accessors[primitive["attributes"]["POSITION"]]
        indices = accessors[primitive["indices"]]
        minimum = [float(value) for value in position["min"]]
        maximum = [float(value) for value in position["max"]]
        dimensions = [hi - lo for lo, hi in zip(minimum, maximum)]
        bounds = {"min": minimum, "max": maximum, "dimensions": dimensions}
        if len(minimum) != 3 or len(maximum) != 3 or any(
            not math.isclose(dimension, expected_size, rel_tol=0.0, abs_tol=tolerance)
            for dimension in dimensions
        ):
            failures.append("bounds")
        if indices.get("type") != "SCALAR" or int(indices.get("count", 0)) % 3:
            failures.append("indices")
        else:
            triangle_count = int(indices["count"]) // 3
        if triangle_count != 12:
            failures.append("triangle_count")
        if primitive.get("material") != 0:
            failures.append("material_binding")
    except (IndexError, KeyError, TypeError, ValueError) as error:
        failures.append(f"mesh_contract:{error}")

    result.update({"bounds": bounds, "triangle_count": triangle_count, "passed": not failures})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("glb", type=Path)
    parser.add_argument("--expected-name", default="bb_validation_cube_1m")
    parser.add_argument("--expected-size", type=float, default=1.0)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = validate_glb(args.glb, expected_name=args.expected_name, expected_size=args.expected_size)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
