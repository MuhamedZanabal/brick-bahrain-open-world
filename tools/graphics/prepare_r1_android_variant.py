#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

QA_MAIN_SCENE = "res://tests/graphics/r1_renderer_runtime_debug.tscn"
VALID_RENDERERS = {"gl_compatibility", "mobile"}


def replace_exact_line(text: str, prefix: str, replacement: str) -> str:
    lines = text.splitlines()
    matches = [index for index, line in enumerate(lines) if line.startswith(prefix)]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {prefix!r} line, found {len(matches)}")
    lines[matches[0]] = replacement
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare(project: Path, preset: Path, renderer: str, package_name: str) -> dict[str, object]:
    if renderer not in VALID_RENDERERS:
        raise ValueError(renderer)
    project_before = project.read_bytes()
    preset_before = preset.read_bytes()
    project_text = project_before.decode()
    preset_text = preset_before.decode()
    project_text = replace_exact_line(project_text, "run/main_scene=", f'run/main_scene="{QA_MAIN_SCENE}"')
    project_text = replace_exact_line(project_text, "renderer/rendering_method=", f'renderer/rendering_method="{renderer}"')
    project_text = replace_exact_line(project_text, "renderer/rendering_method.mobile=", f'renderer/rendering_method.mobile="{renderer}"')
    preset_text = replace_exact_line(preset_text, "architectures/armeabi-v7a=", "architectures/armeabi-v7a=false")
    preset_text = replace_exact_line(preset_text, "architectures/arm64-v8a=", "architectures/arm64-v8a=false")
    preset_text = replace_exact_line(preset_text, "architectures/x86_64=", "architectures/x86_64=true")
    preset_text = replace_exact_line(preset_text, "package/unique_name=", f'package/unique_name="{package_name}"')
    project_after = project_text.encode()
    preset_after = preset_text.encode()
    project.write_bytes(project_after)
    preset.write_bytes(preset_after)
    return {
        "schema_version": 1,
        "renderer": renderer,
        "package_name": package_name,
        "qa_main_scene": QA_MAIN_SCENE,
        "qa_override_only": True,
        "project_before_sha256": digest(project_before),
        "project_after_sha256": digest(project_after),
        "preset_before_sha256": digest(preset_before),
        "preset_after_sha256": digest(preset_after),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--preset", type=Path, required=True)
    parser.add_argument("--renderer", choices=sorted(VALID_RENDERERS), required=True)
    parser.add_argument("--package-name", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.project, args.preset, args.renderer, args.package_name)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
