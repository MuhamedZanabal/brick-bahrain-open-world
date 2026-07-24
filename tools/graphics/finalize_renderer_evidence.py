#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

PATTERNS = {
    "fatal_error_count": re.compile(r"\bFATAL\b|Fatal signal|Segmentation fault|core dumped", re.I),
    "shader_error_count": re.compile(r"shader.*(?:error|failed)|failed.*shader|SPIR-V|GLSL.*error", re.I),
    "missing_resource_error_count": re.compile(r"Failed loading resource|Failed to load resource|Could not load resource|missing resource", re.I),
    "script_error_count": re.compile(r"SCRIPT ERROR|Parse Error|Parser Error|Failed to load script", re.I),
    "renderer_blocking_error_count": re.compile(r"rendering device.*failed|failed to initialize.*render|Vulkan.*(?:unavailable|failed)|OpenGL.*(?:unavailable|failed)", re.I),
}
READY_MARKER = "BAHRAIN_BRICK_SOUQ_SLICE_READY assets=35 pedestrians=12 traffic=6"
MISSION_MARKER = "BAHRAIN_BRICK_KARAK_MISSION_STARTED"


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_metrics(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"row_count": 0, "columns": []}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return {"row_count": len(rows), "columns": reader.fieldnames or []}


def parse_renderer_startup(log_text: str) -> dict[str, str | None]:
    gl = re.search(r"OpenGL API\s+([^\n]+?)\s+-\s+Compatibility\s+-\s+Using Device:\s*([^\n]+)", log_text)
    if gl:
        return {
            "renderer": "gl_compatibility",
            "rendering_driver": "opengl3",
            "rendering_api": gl.group(1).strip(),
            "rendering_device": gl.group(2).strip(),
        }
    mobile = re.search(r"Vulkan\s+([^\n]+?)\s+-\s+Forward Mobile\s+-\s+Using Device[^:]*:\s*([^\n]+)", log_text)
    if mobile:
        return {
            "renderer": "mobile",
            "rendering_driver": "vulkan",
            "rendering_api": mobile.group(1).strip(),
            "rendering_device": mobile.group(2).strip(),
        }
    forward_plus = re.search(r"Vulkan\s+([^\n]+?)\s+-\s+Forward\+\s+-\s+Using Device[^:]*:\s*([^\n]+)", log_text)
    if forward_plus:
        return {
            "renderer": "gl_compatibility" if False else "forward_plus",
            "rendering_driver": "vulkan",
            "rendering_api": forward_plus.group(1).strip(),
            "rendering_device": forward_plus.group(2).strip(),
        }
    return {"renderer": None, "rendering_driver": None, "rendering_api": None, "rendering_device": None}


def finalize_evidence(
    evidence_dir: Path,
    *,
    expected_renderer: str,
    exit_code: int | None = None,
    command: str | None = None,
    host_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence_dir = evidence_dir.resolve()
    runtime_path = evidence_dir / "runtime.json"
    runtime: dict[str, Any] = {}
    if runtime_path.is_file():
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    log_path = evidence_dir / "runtime.log"
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
    counts = {name: len(pattern.findall(log_text)) for name, pattern in PATTERNS.items()}
    critical_lines = [
        line
        for line in log_text.splitlines()
        if any(pattern.search(line) for pattern in PATTERNS.values())
    ]
    (evidence_dir / "critical_errors.txt").write_text(
        "\n".join(critical_lines) + ("\n" if critical_lines else ""),
        encoding="utf-8",
    )

    actual_exit_code = int(runtime.get("exit_code", 1) if exit_code is None else exit_code)
    startup = parse_renderer_startup(log_text)
    renderer = startup["renderer"]
    screenshot = evidence_dir / "screenshot.png"
    metrics = read_metrics(evidence_dir / "frame_metrics.csv")
    marker_ready = READY_MARKER in log_text
    marker_mission = MISSION_MARKER in log_text
    screenshot_valid = bool(runtime.get("screenshot", {}).get("valid_non_black", False)) and screenshot.is_file()
    renderer_matches = renderer == expected_renderer
    critical_count = sum(counts.values())
    evidence_complete = all(
        (
            actual_exit_code == 0,
            renderer_matches,
            marker_ready,
            marker_mission,
            metrics["row_count"] > 0,
            screenshot_valid,
            critical_count == 0,
        )
    )

    finalized = {
        **runtime,
        **startup,
        "schema_version": 1,
        "expected_renderer": expected_renderer,
        "renderer_matches_expected": renderer_matches,
        "exit_code": actual_exit_code,
        "command": command or runtime.get("command"),
        "scene_ready_marker": marker_ready,
        "mission_start_marker": marker_mission,
        "frame_metrics": metrics,
        "runtime_log_sha256": sha256(log_path),
        "frame_metrics_sha256": sha256(evidence_dir / "frame_metrics.csv"),
        "screenshot_sha256": sha256(screenshot),
        "critical_errors_sha256": sha256(evidence_dir / "critical_errors.txt"),
        **counts,
        "critical_error_count": critical_count,
        "host_metadata": host_metadata or runtime.get("host_metadata", {}),
        "evidence_complete": evidence_complete,
    }
    runtime_path.write_text(json.dumps(finalized, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return finalized


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize one G0 renderer evidence directory.")
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--expected-renderer", required=True)
    parser.add_argument("--exit-code", type=int)
    parser.add_argument("--command")
    parser.add_argument("--host-metadata", type=Path)
    args = parser.parse_args()
    host = None
    if args.host_metadata and args.host_metadata.is_file():
        host = json.loads(args.host_metadata.read_text(encoding="utf-8"))
    result = finalize_evidence(
        args.evidence_dir,
        expected_renderer=args.expected_renderer,
        exit_code=args.exit_code,
        command=args.command,
        host_metadata=host,
    )
    print(json.dumps({"renderer": result.get("renderer"), "evidence_complete": result["evidence_complete"]}, sort_keys=True))
    return 0 if result["evidence_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
