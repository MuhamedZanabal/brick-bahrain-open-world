#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

QA_MAIN_SCENE = "res://tests/graphics/android_renderer_evidence.tscn"
VALID_RENDERERS = {"gl_compatibility", "mobile"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def replace_exact_line(text: str, prefix: str, replacement: str) -> str:
    lines = text.splitlines()
    matches = [index for index, line in enumerate(lines) if line.startswith(prefix)]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {prefix!r} line, found {len(matches)}")
    lines[matches[0]] = replacement
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def prepare_variant(
    project_path: Path,
    preset_path: Path,
    *,
    renderer: str,
    package_name: str,
) -> dict[str, Any]:
    if renderer not in VALID_RENDERERS:
        raise ValueError(f"unsupported renderer: {renderer}")
    if not package_name or "." not in package_name:
        raise ValueError("package_name must be a dotted Android package identifier")

    project_before = project_path.read_bytes()
    preset_before = preset_path.read_bytes()
    project = project_before.decode("utf-8")
    preset = preset_before.decode("utf-8")

    project = replace_exact_line(
        project,
        "run/main_scene=",
        f'run/main_scene="{QA_MAIN_SCENE}"',
    )
    project = replace_exact_line(
        project,
        "renderer/rendering_method=",
        f'renderer/rendering_method="{renderer}"',
    )
    project = replace_exact_line(
        project,
        "renderer/rendering_method.mobile=",
        f'renderer/rendering_method.mobile="{renderer}"',
    )

    preset = replace_exact_line(preset, "architectures/armeabi-v7a=", "architectures/armeabi-v7a=false")
    preset = replace_exact_line(preset, "architectures/arm64-v8a=", "architectures/arm64-v8a=false")
    preset = replace_exact_line(preset, "architectures/x86_64=", "architectures/x86_64=true")
    preset = replace_exact_line(preset, "package/unique_name=", f'package/unique_name="{package_name}"')

    project_after = project.encode("utf-8")
    preset_after = preset.encode("utf-8")
    project_path.write_bytes(project_after)
    preset_path.write_bytes(preset_after)

    return {
        "schema_version": 1,
        "renderer": renderer,
        "package_name": package_name,
        "qa_main_scene": QA_MAIN_SCENE,
        "qa_override_only": True,
        "architectures": {
            "armeabi-v7a": False,
            "arm64-v8a": False,
            "x86_64": True,
        },
        "project": {
            "path": project_path.as_posix(),
            "before_sha256": digest(project_before),
            "after_sha256": digest(project_after),
            "changed": project_before != project_after,
        },
        "export_preset": {
            "path": preset_path.as_posix(),
            "before_sha256": digest(preset_before),
            "after_sha256": digest(preset_after),
            "changed": preset_before != preset_after,
        },
        "changed_keys": [
            "application/run/main_scene",
            "rendering/renderer/rendering_method",
            "rendering/renderer/rendering_method.mobile",
            "android/architectures/armeabi-v7a",
            "android/architectures/arm64-v8a",
            "android/architectures/x86_64",
            "android/package/unique_name",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare an isolated Android G0 renderer QA variant.")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--preset", type=Path, required=True)
    parser.add_argument("--renderer", choices=sorted(VALID_RENDERERS), required=True)
    parser.add_argument("--package-name", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = prepare_variant(
        args.project,
        args.preset,
        renderer=args.renderer,
        package_name=args.package_name,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"renderer": result["renderer"], "qa_override_only": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
