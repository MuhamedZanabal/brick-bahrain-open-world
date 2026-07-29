#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct
import zipfile
from pathlib import Path

MAGIC = b"BBPATCH2"
COPY_CHUNK = 4 * 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(COPY_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def apply_patch(source: Path, patch_path: Path, output: Path) -> dict:
    raw = gzip.decompress(patch_path.read_bytes())
    if raw[:8] != MAGIC:
        raise SystemExit("invalid patch magic")
    if len(raw) < 12:
        raise SystemExit("truncated patch header")
    manifest_length = struct.unpack("<I", raw[8:12])[0]
    manifest_start = 12
    manifest_end = manifest_start + manifest_length
    if manifest_end > len(raw):
        raise SystemExit("truncated patch manifest")
    manifest = json.loads(raw[manifest_start:manifest_end].decode("utf-8"))
    literals = memoryview(raw)[manifest_end:]

    source_size = source.stat().st_size
    source_sha = sha256(source)
    if source_size != int(manifest["old_size"]):
        raise SystemExit(f"source size mismatch: {source_size}")
    if source_sha != manifest["old_sha256"]:
        raise SystemExit(f"source SHA-256 mismatch: {source_sha}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as source_stream, output.open("wb") as output_stream:
        for index, operation in enumerate(manifest["ops"]):
            if not isinstance(operation, list) or len(operation) != 3:
                raise SystemExit(f"invalid patch operation at index {index}")
            mode, offset, length = operation
            offset = int(offset)
            length = int(length)
            if mode == "c":
                source_stream.seek(offset)
                remaining = length
                while remaining:
                    chunk = source_stream.read(min(COPY_CHUNK, remaining))
                    if not chunk:
                        raise SystemExit(f"source ended during copy operation {index}")
                    output_stream.write(chunk)
                    remaining -= len(chunk)
            elif mode == "l":
                end = offset + length
                if end > len(literals):
                    raise SystemExit(f"literal range exceeds patch at operation {index}")
                output_stream.write(literals[offset:end])
            else:
                raise SystemExit(f"unknown patch operation mode {mode!r} at index {index}")

    output_size = output.stat().st_size
    output_sha = sha256(output)
    if output_size != int(manifest["new_size"]):
        raise SystemExit(f"output size mismatch: {output_size}")
    if output_sha != manifest["new_sha256"]:
        raise SystemExit(f"output SHA-256 mismatch: {output_sha}")

    with zipfile.ZipFile(output) as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise SystemExit(f"APK ZIP integrity failed at {bad_member}")
        project_binary = archive.read("assets/project.binary")
    if b"res://scenes/splash_screen.tscn" not in project_binary:
        raise SystemExit("production splash scene not selected")
    if b"res://tests/graphics/r1_renderer_runtime_debug.tscn" in project_binary:
        raise SystemExit("diagnostic main scene remains selected")

    return {
        "schema_version": 1,
        "purpose": "Corrected playable Android QA package using the production splash and game scenes",
        "source_apk": source.name,
        "source_size_bytes": source_size,
        "source_sha256": source_sha,
        "patch": patch_path.name,
        "patch_size_bytes": patch_path.stat().st_size,
        "patch_sha256": sha256(patch_path),
        "filename": output.name,
        "size_bytes": output_size,
        "sha256": output_sha,
        "package": "com.brickbahrain.r1physical.mobile",
        "engine": "4.3-stable",
        "renderer": "mobile",
        "architecture": "arm64-v8a",
        "production_main_scene": "res://scenes/splash_screen.tscn",
        "production_main_scene_selected": True,
        "diagnostic_main_scene_selected": False,
        "diagnostic_evidence_camera_selected": False,
        "production_renderer_defaults_modified": False,
        "production_fix_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--handoff", type=Path, required=True)
    args = parser.parse_args()

    handoff = apply_patch(args.source, args.patch, args.output)
    args.handoff.parent.mkdir(parents=True, exist_ok=True)
    args.handoff.write_text(json.dumps(handoff, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(handoff, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
