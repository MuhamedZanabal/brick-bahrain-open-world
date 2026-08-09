#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable

MIB = 1024 * 1024
DEFAULT_LIMITS = {
    ".blend": 100 * MIB,
    ".glb": 50 * MIB,
    ".gltf": 10 * MIB,
    ".png": 16 * MIB,
    ".jpg": 16 * MIB,
    ".jpeg": 16 * MIB,
    ".webp": 16 * MIB,
    ".tif": 32 * MIB,
    ".tiff": 32 * MIB,
    ".exr": 64 * MIB,
    ".psd": 100 * MIB,
    ".kra": 100 * MIB,
    ".mp4": 100 * MIB,
    ".mov": 100 * MIB,
    ".webm": 100 * MIB,
    ".mkv": 100 * MIB,
    ".avi": 100 * MIB,
    ".apk": 100 * MIB,
    ".aab": 100 * MIB,
    ".zip": 100 * MIB,
    ".7z": 100 * MIB,
    ".pdf": 32 * MIB,
}
BINARY_EXTENSIONS = frozenset(DEFAULT_LIMITS)
SKIP_DIR_NAMES = frozenset({".git", ".godot", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"})
SKIP_RELATIVE_PREFIXES = (
    Path("build"),
    Path("android/build"),
)
CONTROLLED_BINARY_ROOTS = (
    Path("asset_lab/source"),
    Path("asset_lab/references"),
    Path("asset_lab/materials"),
    Path("asset_lab/exports"),
    Path("asset_lab/evidence"),
    Path("asset_lab/quarantine"),
    Path("game/assets/bahrain"),
)


def _is_skipped(relative: Path) -> bool:
    if any(part in SKIP_DIR_NAMES for part in relative.parts):
        return True
    return any(relative == prefix or prefix in relative.parents for prefix in SKIP_RELATIVE_PREFIXES)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_files(root: Path, scan_roots: tuple[Path, ...]) -> Iterable[tuple[Path, Path]]:
    seen: set[Path] = set()
    for relative_root in scan_roots:
        absolute_root = root / relative_root
        if not absolute_root.exists():
            continue
        for path in sorted(absolute_root.rglob("*")):
            if not path.is_file() or path in seen:
                continue
            seen.add(path)
            relative = path.relative_to(root)
            if _is_skipped(relative):
                continue
            yield path, relative


def scan_repository(
    root: Path,
    *,
    limits: dict[str, int] | None = None,
    duplicate_min_bytes: int = 256 * 1024,
    scan_roots: tuple[Path, ...] = CONTROLLED_BINARY_ROOTS,
) -> dict[str, object]:
    root = root.resolve()
    active_limits = dict(DEFAULT_LIMITS if limits is None else limits)
    oversized: list[dict[str, object]] = []
    hashes: dict[str, list[str]] = defaultdict(list)
    scanned_binary_files = 0

    for path, relative in _iter_files(root, scan_roots):
        suffix = path.suffix.lower()
        if suffix not in BINARY_EXTENSIONS and suffix not in active_limits:
            continue
        scanned_binary_files += 1
        size = path.stat().st_size
        limit = active_limits.get(suffix)
        if limit is not None and size > limit:
            oversized.append({
                "path": relative.as_posix(),
                "size_bytes": size,
                "limit_bytes": limit,
                "extension": suffix,
            })
        if size >= duplicate_min_bytes:
            hashes[_sha256(path)].append(relative.as_posix())

    duplicates = [
        {"sha256": sha, "paths": sorted(paths)}
        for sha, paths in sorted(hashes.items())
        if len(paths) > 1
    ]
    return {
        "passed": not oversized and not duplicates,
        "root": root.as_posix(),
        "scanned_binary_files": scanned_binary_files,
        "duplicate_min_bytes": duplicate_min_bytes,
        "scan_roots": [path.as_posix() for path in scan_roots],
        "oversized": oversized,
        "duplicates": duplicates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Reject oversized or duplicate binary assets/evidence.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--duplicate-min-bytes", type=int, default=256 * 1024)
    parser.add_argument("--json-report", type=Path)
    args = parser.parse_args()
    report = scan_repository(args.root, duplicate_min_bytes=args.duplicate_min_bytes)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.json_report:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
