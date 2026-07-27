#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

KEY = "scaling_3d/scale"
VALUE = 0.75
DEFAULT_VALUE = 1.0


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def apply(project: Path, report: Path) -> dict[str, object]:
    before = project.read_bytes()
    text = before.decode("utf-8")
    lines = text.splitlines()
    section: str | None = None
    rendering_index: int | None = None
    matches: list[int] = []

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1]
            if section == "rendering":
                rendering_index = index
        elif section == "rendering" and line.startswith(KEY + "="):
            matches.append(index)

    if len(matches) > 1:
        raise ValueError(f"{KEY} appears more than once")

    before_value = DEFAULT_VALUE
    if matches:
        raw_value = lines[matches[0]].split("=", 1)[1].strip()
        try:
            before_value = float(raw_value)
        except ValueError as exc:
            raise ValueError(f"{KEY} is not numeric: {raw_value}") from exc

    replacement = f"{KEY}={VALUE}"
    if matches:
        lines[matches[0]] = replacement
    elif rendering_index is None:
        lines.extend(["", "[rendering]", "", replacement])
    else:
        insert_at = rendering_index + 1
        while insert_at < len(lines) and not lines[insert_at].startswith("["):
            insert_at += 1
        lines.insert(insert_at, replacement)

    after_text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    if after_text.count(replacement) != 1:
        raise ValueError("Mobile render-scale override was not applied exactly once")

    after = after_text.encode("utf-8")
    project.write_bytes(after)
    result = {
        "schema_version": 1,
        "defect": "RENDER_PIPELINE_STALL",
        "experiment": "MOBILE_QA_RENDER_SCALE_1_0_TO_0_75",
        "setting": f"rendering/{KEY}",
        "before_value": before_value,
        "after_value": VALUE,
        "project_before_sha256": digest(before),
        "project_after_sha256": digest(after),
        "changed": before != after,
        "qa_override_only": True,
        "renderer_default_modified": False,
        "gameplay_modified": False,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(apply(args.project, args.report), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
