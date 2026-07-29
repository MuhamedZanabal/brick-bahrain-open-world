#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

DIAGNOSTIC_MAIN_SCENE_OVERRIDE = (
    'project_text = replace_line(project_text, "run/main_scene=", '
    "'run/main_scene=\"res://tests/graphics/r1_renderer_runtime_debug.tscn\"')"
)
PRODUCTION_MAIN_SCENE_MARKER = '# Production main scene intentionally preserved for playable export.'
OLD_MOBILE_APK = 'MOBILE_APK="$OUTPUT_ROOT/bahrain-brick-r1-physical-mobile-arm64.apk"'
NEW_MOBILE_APK = 'MOBILE_APK="$OUTPUT_ROOT/bahrain-brick-playable-mobile-arm64.apk"'
OLD_PACKAGE = 'com.brickbahrain.r1physical.mobile'
NEW_PACKAGE = 'com.brickbahrain.playable.mobile'
OLD_GODOT_DISCOVERY = 'GODOT="$(find "$GODOT_DIR" -maxdepth 1 -type f -name \'Godot*\' | head -1)"'
NEW_GODOT_DISCOVERY = 'GODOT="$(find "$GODOT_DIR" -maxdepth 1 -type f -name \'Godot*\' ! -name \'*.zip\' | head -1)"'


def patch_exporter_text(text: str) -> str:
    override_count = text.count(DIAGNOSTIC_MAIN_SCENE_OVERRIDE)
    if override_count != 2:
        raise ValueError(
            f"expected exactly two diagnostic main-scene overrides, found {override_count}"
        )
    if text.count(OLD_MOBILE_APK) != 1:
        raise ValueError("expected exactly one retained Mobile APK output declaration")
    if text.count(OLD_GODOT_DISCOVERY) != 1:
        raise ValueError("expected exactly one Godot binary discovery line")
    package_count = text.count(OLD_PACKAGE)
    if package_count < 2:
        raise ValueError(
            f"expected retained Mobile package identity in exporter and manifest, found {package_count}"
        )

    patched = text.replace(DIAGNOSTIC_MAIN_SCENE_OVERRIDE, PRODUCTION_MAIN_SCENE_MARKER)
    patched = patched.replace(OLD_MOBILE_APK, NEW_MOBILE_APK)
    patched = patched.replace(OLD_PACKAGE, NEW_PACKAGE)
    patched = patched.replace(OLD_GODOT_DISCOVERY, NEW_GODOT_DISCOVERY)

    if "r1_renderer_runtime_debug.tscn" in patched:
        raise ValueError("diagnostic main-scene override remains after playable patch")
    if patched.count(PRODUCTION_MAIN_SCENE_MARKER) != 2:
        raise ValueError("production-main-scene preservation marker count is incorrect")
    if OLD_PACKAGE in patched:
        raise ValueError("diagnostic Mobile package identity remains after playable patch")
    if OLD_GODOT_DISCOVERY in patched or NEW_GODOT_DISCOVERY not in patched:
        raise ValueError("Godot binary discovery was not hardened against ZIP selection")
    return patched


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(
        patch_exporter_text(args.source.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    args.output.chmod(0o755)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
