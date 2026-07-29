#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

OLD = "environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC"
NEW = "environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def apply(script: Path, report: Path) -> dict[str, object]:
    before = script.read_bytes()
    text = before.decode("utf-8")
    required_signatures = {
        'environment_node.name = "SouqWorldEnvironment"': "world environment",
        "environment.background_mode = Environment.BG_COLOR": "background mode",
        'sun.name = "LateAfternoonSun"': "primary sun",
        'fill.name = "SkyFill"': "fill light",
        "fill.shadow_enabled = false": "unshadowed fill",
    }
    for signature, label in required_signatures.items():
        if text.count(signature) != 1:
            raise ValueError(f"{label} signature must appear exactly once")
    if text.count(OLD) != 1:
        raise ValueError("filmic tonemapper signature must appear exactly once")
    if NEW in text:
        raise ValueError("linear tonemapper is already present")
    after_text = text.replace(OLD, NEW)
    if after_text.count(NEW) != 1 or OLD in after_text:
        raise ValueError("tonemapper was not changed exactly once")
    after = after_text.encode("utf-8")
    script.write_bytes(after)
    result = {
        "schema_version": 1,
        "defect": "RENDER_PIPELINE_STALL",
        "experiment": "MOBILE_ENVIRONMENT_TONEMAPPER_FILMIC_TO_LINEAR",
        "before_value": "Environment.TONE_MAPPER_FILMIC",
        "after_value": "Environment.TONE_MAPPER_LINEAR",
        "changed": before != after,
        "script_before_sha256": digest(before),
        "script_after_sha256": digest(after),
        "world_environment_name": "SouqWorldEnvironment",
        "primary_light_unchanged": True,
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
