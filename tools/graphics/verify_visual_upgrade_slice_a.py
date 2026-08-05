#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path

REQUIRED = (
    "scenes/splash_screen.tscn",
    "scenes/loading_screen.tscn",
    "scenes/main_menu.tscn",
    "scenes/character_select.tscn",
    "scripts/ui/bahrain_theme.gd",
    "scripts/ui/safe_area_root.gd",
    "scripts/splash_screen.gd",
    "scripts/loading_screen.gd",
    "scripts/main_menu.gd",
    "scripts/character_select.gd",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_source(root: Path) -> None:
    project_path = root / "project.godot"
    require(project_path.is_file(), f"missing project file: {project_path}")
    project = project_path.read_text(encoding="utf-8")
    require(
        'run/main_scene="res://scenes/splash_screen.tscn"' in project,
        "production splash scene is not selected",
    )
    require(
        'renderer/rendering_method="gl_compatibility"' in project,
        "desktop renderer boundary changed",
    )
    require(
        'renderer/rendering_method.mobile="gl_compatibility"' in project,
        "mobile renderer boundary changed",
    )
    for relative in REQUIRED:
        require((root / relative).is_file(), f"missing required visual resource: {relative}")


def verify_apk(apk: Path) -> str:
    require(apk.is_file(), f"APK does not exist: {apk}")
    require(apk.stat().st_size > 0, f"APK is empty: {apk}")
    require(zipfile.is_zipfile(apk), f"APK is not a valid ZIP archive: {apk}")
    with zipfile.ZipFile(apk) as archive:
        bad_member = archive.testzip()
        require(bad_member is None, f"APK ZIP integrity failure at: {bad_member}")
        names = set(archive.namelist())
        require("AndroidManifest.xml" in names, "APK is missing AndroidManifest.xml")
        require(
            any(name.startswith("lib/arm64-v8a/") for name in names),
            "APK is missing ARM64 native libraries",
        )
    return sha256(apk)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--apk", type=Path)
    args = parser.parse_args()

    try:
        root = args.root.resolve()
        verify_source(root)
        print("visual-upgrade-source: ok")
        if args.apk:
            apk = args.apk.resolve()
            digest = verify_apk(apk)
            print(f"visual-upgrade-apk: ok")
            print(f"sha256:{digest}")
        return 0
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"visual-upgrade-verification: failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
