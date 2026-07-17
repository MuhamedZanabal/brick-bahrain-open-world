#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

ASSET_PREFIX = "assets/"
REMAP_PATH_RE = re.compile(r'(?m)^path="res://([^"\r\n]+)"\s*$')
COMPILED_ALIASES = {
    ".scn": ".tscn",
    ".res": ".tres",
    ".gdc": ".gd",
}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def source_exists(source_root: Path | None, relative: str) -> bool:
    return source_root is None or (source_root / relative).is_file()


def normalize_target(value: str) -> str:
    return value.replace("\\", "/").lstrip("/")


def inventory_apk(apk: Path, source_root: Path | None) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    raw_paths: set[str] = set()
    remap_payloads: dict[str, str] = {}

    with zipfile.ZipFile(apk) as archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.startswith(ASSET_PREFIX):
                continue
            relative = normalize_target(info.filename[len(ASSET_PREFIX) :])
            if not relative:
                continue
            raw_paths.add(relative)
            entries.append(
                {
                    "apk_path": info.filename,
                    "path": relative,
                    "compressed_bytes": info.compress_size,
                    "uncompressed_bytes": info.file_size,
                    "crc32": f"{info.CRC:08x}",
                    "compression": info.compress_type,
                }
            )
            if relative.endswith(".remap") and info.file_size <= 1024 * 1024:
                remap_payloads[relative] = archive.read(info).decode("utf-8", errors="replace")

    logical_paths = set(raw_paths)
    aliases: list[dict[str, Any]] = []
    remap_failures: list[dict[str, Any]] = []

    for actual in sorted(raw_paths):
        suffix = PurePosixPath(actual).suffix.lower()
        logical_suffix = COMPILED_ALIASES.get(suffix)
        if logical_suffix:
            logical = str(PurePosixPath(actual).with_suffix(logical_suffix))
            if source_exists(source_root, logical):
                logical_paths.add(logical)
                aliases.append(
                    {
                        "logical_path": logical,
                        "packaged_path": actual,
                        "reason": f"Godot compiled {logical_suffix} resource",
                        "target_verified": True,
                    }
                )

    for remap_path, text in sorted(remap_payloads.items()):
        logical = remap_path[: -len(".remap")]
        match = REMAP_PATH_RE.search(text)
        target = normalize_target(match.group(1)) if match else None
        target_verified = bool(target and target in raw_paths)
        source_verified = source_exists(source_root, logical)
        if target_verified and source_verified:
            logical_paths.add(logical)
            aliases.append(
                {
                    "logical_path": logical,
                    "packaged_path": remap_path,
                    "remap_target": target,
                    "reason": "Godot imported-resource remap",
                    "source_verified": source_verified,
                    "target_verified": target_verified,
                }
            )
        else:
            remap_failures.append(
                {
                    "remap_path": remap_path,
                    "logical_path": logical,
                    "remap_target": target,
                    "source_verified": source_verified,
                    "target_verified": target_verified,
                }
            )

    value = {
        "passed": bool(entries) and not remap_failures,
        "packaging": "godot-4.3-default-android-apk-assets",
        "pck_required": False,
        "apk": str(apk.resolve()),
        "apk_asset_prefix": ASSET_PREFIX,
        "raw_asset_count": len(raw_paths),
        "logical_file_count": len(logical_paths),
        "files": sorted(logical_paths),
        "raw_files": sorted(raw_paths),
        "entries": sorted(entries, key=lambda item: item["path"]),
        "logical_aliases": sorted(aliases, key=lambda item: (item["logical_path"], item["packaged_path"])),
        "remap_count": len(remap_payloads),
        "remap_targets_verified": not remap_failures,
        "remap_failures": remap_failures,
        "source_root": str(source_root.resolve()) if source_root else None,
        "source_authority": "Godot 4.3 Android save_apk_file stores exported res:// paths beneath APK assets/",
        "compatibility_note": "The optional compatibility output preserves the existing inspector input schema; it is not evidence of a PCK payload.",
    }
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--compat-output")
    parser.add_argument("--source-root")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    apk = Path(args.apk)
    if not apk.is_file() or apk.stat().st_size == 0:
        raise SystemExit(f"APK missing or empty: {apk}")
    source_root = Path(args.source_root) if args.source_root else None
    if source_root is not None and not source_root.is_dir():
        raise SystemExit(f"source root missing: {source_root}")
    value = inventory_apk(apk, source_root)
    write_json(Path(args.output), value)
    if args.compat_output:
        write_json(Path(args.compat_output), value)
    return 0 if value["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
