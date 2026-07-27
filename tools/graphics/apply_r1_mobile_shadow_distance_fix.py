#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

TARGET_NODE = "LateAfternoonSun"
SUN_NAME_LINE = 'sun.name = "LateAfternoonSun"'
SHADOW_LINE = "sun.shadow_enabled = true"
PROPERTY_PREFIX = "sun.directional_shadow_max_distance ="
EXPECTED_BEFORE = 150.0
EXPECTED_AFTER = 75.0


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def apply(script: Path, report: Path) -> dict[str, object]:
    before_bytes = script.read_bytes()
    text = before_bytes.decode("utf-8")
    lines = text.splitlines()

    name_indexes = [index for index, line in enumerate(lines) if line.strip() == SUN_NAME_LINE]
    if len(name_indexes) != 1:
        raise ValueError(f"expected exactly one runtime-created {TARGET_NODE}, found {len(name_indexes)}")

    name_index = name_indexes[0]
    search_end = min(len(lines), name_index + 16)
    block = lines[name_index:search_end]
    if not any(line.strip() == SHADOW_LINE for line in block):
        raise ValueError(f"{TARGET_NODE} is not the active shadow-casting directional light")

    property_indexes = [
        name_index + offset
        for offset, line in enumerate(block)
        if line.strip().startswith(PROPERTY_PREFIX)
    ]
    if len(property_indexes) != 1:
        raise ValueError(f"expected exactly one {PROPERTY_PREFIX!r} near {TARGET_NODE}, found {len(property_indexes)}")

    property_index = property_indexes[0]
    raw_value = lines[property_index].split("=", 1)[1].strip()
    try:
        before_value = float(raw_value)
    except ValueError as exc:
        raise ValueError(f"invalid directional shadow distance: {raw_value!r}") from exc
    if before_value != EXPECTED_BEFORE:
        raise ValueError(f"unexpected {TARGET_NODE} shadow distance: {before_value}")

    lines[property_index] = "\tsun.directional_shadow_max_distance = 75.0"
    after_text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    if after_text.count("sun.directional_shadow_max_distance = 75.0") != 1:
        raise ValueError("directional shadow distance override was not applied exactly once")
    if after_text.count('fill.name = "SkyFill"') != text.count('fill.name = "SkyFill"'):
        raise ValueError("secondary directional light was unexpectedly modified")

    after_bytes = after_text.encode("utf-8")
    script.write_bytes(after_bytes)
    result = {
        "schema_version": 1,
        "defect": "RENDER_PIPELINE_STALL",
        "experiment": "DIRECTIONAL_SHADOW_MAX_DISTANCE_150_TO_75",
        "target_node": TARGET_NODE,
        "property": "directional_shadow_max_distance",
        "before_value": before_value,
        "after_value": EXPECTED_AFTER,
        "qa_override_only": True,
        "renderer_default_modified": False,
        "production_source_modified": False,
        "gameplay_modified": False,
        "script_before_sha256": digest(before_bytes),
        "script_after_sha256": digest(after_bytes),
        "changed": before_bytes != after_bytes,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(apply(args.script, args.report), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
