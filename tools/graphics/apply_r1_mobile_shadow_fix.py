#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SUN_SHADOW = "sun.shadow_enabled = true"
SUN_UNSHADOWED = "sun.shadow_enabled = false"
FILL_UNSHADOWED = "fill.shadow_enabled = false"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def apply(script: Path, report: Path) -> dict[str, object]:
    before = script.read_bytes()
    text = before.decode("utf-8")
    if text.count(SUN_SHADOW) != 1:
        raise ValueError("LateAfternoonSun shadow assignment was not found exactly once")
    if text.count(FILL_UNSHADOWED) != 1:
        raise ValueError("SkyFill must already be unshadowed before this experiment")
    after_text = text.replace(SUN_SHADOW, SUN_UNSHADOWED, 1)
    after = after_text.encode("utf-8")
    script.write_bytes(after)
    result = {
        "schema_version": 1,
        "root_cause": "RENDER_PIPELINE_STALL",
        "experiment": "DISABLE_ALL_DIRECTIONAL_SHADOWS",
        "second_directional_already_unshadowed": True,
        "changed_shadow_count": 1,
        "script_before_sha256": digest(before),
        "script_after_sha256": digest(after),
        "qa_override_only": True,
        "production_source_modified": False,
        "renderer_defaults_modified": False,
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
