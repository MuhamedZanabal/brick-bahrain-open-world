#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

OLD = "sun.directional_shadow_max_distance = 150.0"
NEW = "sun.directional_shadow_max_distance = 100.0"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def apply(script: Path, report: Path) -> dict[str, object]:
    before = script.read_bytes()
    text = before.decode("utf-8")
    if text.count('sun.name = "LateAfternoonSun"') != 1:
        raise ValueError("LateAfternoonSun signature must appear exactly once")
    if text.count('fill.name = "SkyFill"') != 1 or text.count("fill.shadow_enabled = false") != 1:
        raise ValueError("SkyFill unshadowed signature must remain exact")
    if text.count(OLD) != 1:
        raise ValueError("LateAfternoonSun shadow-distance signature must appear exactly once")
    after_text = text.replace(OLD, NEW)
    if after_text.count(NEW) != 1:
        raise ValueError("LateAfternoonSun shadow distance was not changed exactly once")
    after = after_text.encode("utf-8")
    script.write_bytes(after)
    result = {
        "schema_version": 1,
        "defect": "RENDER_PIPELINE_STALL",
        "experiment": "LATE_AFTERNOON_SUN_SHADOW_DISTANCE_150_TO_100",
        "light_name": "LateAfternoonSun",
        "before_value": 150.0,
        "after_value": 100.0,
        "changed": before != after,
        "script_before_sha256": digest(before),
        "script_after_sha256": digest(after),
        "secondary_light_remains_unshadowed": True,
        "qa_override_only": True,
        "renderer_default_modified": False,
        "gameplay_modified": False,
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
