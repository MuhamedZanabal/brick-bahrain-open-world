#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

TARGET_NODE = "LateAfternoonSun"
DEFAULT_DISTANCE = 100.0
PROPERTY = "directional_shadow_max_distance"
NODE_RE = re.compile(r'^\[node name="([^"]+)" type="([^"]+)"[^\]]*\]$')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def format_float(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".") + ".0" if value.is_integer() else f"{value:.6f}".rstrip("0").rstrip(".")


def apply(scene: Path, report: Path) -> dict[str, object]:
    before_bytes = scene.read_bytes()
    text = before_bytes.decode("utf-8")
    lines = text.splitlines()

    starts: list[int] = []
    for index, line in enumerate(lines):
        match = NODE_RE.match(line.strip())
        if match and match.group(1) == TARGET_NODE and match.group(2) == "DirectionalLight3D":
            starts.append(index)
    if len(starts) != 1:
        raise ValueError(f"expected exactly one {TARGET_NODE} DirectionalLight3D node, found {len(starts)}")

    start = starts[0]
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("[node "):
            end = index
            break

    block = lines[start:end]
    if not any(line.strip() == "shadow_enabled = true" for line in block):
        raise ValueError(f"{TARGET_NODE} is not the active shadow-casting directional light")

    property_indexes = [
        start + offset
        for offset, line in enumerate(block)
        if line.strip().startswith(PROPERTY + " =")
    ]
    if len(property_indexes) > 1:
        raise ValueError(f"{PROPERTY} appears more than once in {TARGET_NODE}")

    before_value = DEFAULT_DISTANCE
    if property_indexes:
        index = property_indexes[0]
        raw = lines[index].split("=", 1)[1].strip()
        try:
            before_value = float(raw)
        except ValueError as exc:
            raise ValueError(f"invalid {PROPERTY} value: {raw!r}") from exc
        after_value = before_value / 2.0
        lines[index] = f"{PROPERTY} = {format_float(after_value)}"
    else:
        after_value = DEFAULT_DISTANCE / 2.0
        insert_at = start + 1
        for index in range(start + 1, end):
            if lines[index].strip() == "shadow_enabled = true":
                insert_at = index + 1
                break
        lines.insert(insert_at, f"{PROPERTY} = {format_float(after_value)}")

    after_text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    expected = f"{PROPERTY} = {format_float(after_value)}"
    target_block = after_text.split(f'[node name="{TARGET_NODE}"', 1)[1].split("[node ", 1)[0]
    if target_block.count(expected) != 1:
        raise ValueError("directional shadow distance override was not applied exactly once")

    after_bytes = after_text.encode("utf-8")
    scene.write_bytes(after_bytes)
    result = {
        "schema_version": 1,
        "defect": "RENDER_PIPELINE_STALL",
        "experiment": "DIRECTIONAL_SHADOW_MAX_DISTANCE_HALVED",
        "target_node": TARGET_NODE,
        "property": PROPERTY,
        "before_value": before_value,
        "after_value": after_value,
        "qa_override_only": True,
        "renderer_default_modified": False,
        "production_source_modified": False,
        "gameplay_modified": False,
        "scene_before_sha256": digest(before_bytes),
        "scene_after_sha256": digest(after_bytes),
        "changed": before_bytes != after_bytes,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(apply(args.scene, args.report), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
