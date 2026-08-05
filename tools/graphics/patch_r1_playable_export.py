#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
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
DIAGNOSTIC_ASSET_COPY = (
    'cp "$REPO_ROOT/tests/graphics/r1_renderer_runtime_debug.tscn" '
    '"$GAME/tests/graphics/"'
)
VISUAL_UPGRADE_FILES = (
    "project.godot",
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
    "scripts/game_manager.gd",
    "scripts/save_manager.gd",
)
IMPORT_COMMAND_PATTERN = re.compile(
    r"timeout --signal=TERM --kill-after=30s 1800s "
    r"xvfb-run -a -s '-screen 0 1920x1080x24' \\(?:\r?\n)"
    r"[ \t]+\"\$GODOT\" --path \"\$GAME\" --editor --import --quit --verbose \\(?:\r?\n)"
    r"[ \t]+--rendering-method mobile --rendering-driver vulkan "
    r"2>&1 \| tee \"\$OUTPUT_ROOT/import\.log\""
)
NEW_IMPORT_COMMAND = "\n".join(
    [
        "timeout --signal=TERM --kill-after=30s 1800s \\",
        '  "$GODOT" --headless --path "$GAME" --editor --import --quit --verbose 2>&1 | tee "$OUTPUT_ROOT/import.log"',
    ]
)


def visual_upgrade_overlay_block() -> str:
    lines = [
        "# Overlay candidate visual-upgrade runtime files.",
        'VISUAL_UPGRADE_OVERLAY_SHA256SUMS="$OUTPUT_ROOT/VISUAL_UPGRADE_OVERLAY_SHA256SUMS.txt"',
        ': > "$VISUAL_UPGRADE_OVERLAY_SHA256SUMS"',
        "VISUAL_UPGRADE_FILES=(",
    ]
    lines.extend(f'  "{relative}"' for relative in VISUAL_UPGRADE_FILES)
    lines.extend(
        [
            ")",
            'for relative in "${VISUAL_UPGRADE_FILES[@]}"; do',
            '  source="$REPO_ROOT/$relative"',
            '  destination="$GAME/$relative"',
            '  test -f "$source"',
            '  mkdir -p "$(dirname "$destination")"',
            '  cp "$source" "$destination"',
            '  cmp "$source" "$destination"',
            '  sha256sum "$destination" >> "$VISUAL_UPGRADE_OVERLAY_SHA256SUMS"',
            "done",
            'python3 "$REPO_ROOT/tools/graphics/verify_visual_upgrade_slice_a.py" --root "$GAME"',
        ]
    )
    return "\n".join(lines)


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
    if text.count(DIAGNOSTIC_ASSET_COPY) != 1:
        raise ValueError("expected exactly one diagnostic scene-copy anchor")
    import_matches = list(IMPORT_COMMAND_PATTERN.finditer(text))
    if len(import_matches) != 1:
        raise ValueError(
            f"expected exactly one GPU-dependent Godot import command, found {len(import_matches)}"
        )
    package_count = text.count(OLD_PACKAGE)
    if package_count < 2:
        raise ValueError(
            f"expected retained Mobile package identity in exporter and manifest, found {package_count}"
        )

    patched = text.replace(DIAGNOSTIC_MAIN_SCENE_OVERRIDE, PRODUCTION_MAIN_SCENE_MARKER)
    patched = patched.replace(OLD_MOBILE_APK, NEW_MOBILE_APK)
    patched = patched.replace(OLD_PACKAGE, NEW_PACKAGE)
    patched = patched.replace(OLD_GODOT_DISCOVERY, NEW_GODOT_DISCOVERY)
    patched = patched.replace(
        DIAGNOSTIC_ASSET_COPY,
        DIAGNOSTIC_ASSET_COPY + "\n\n" + visual_upgrade_overlay_block(),
        1,
    )
    patched, import_replacements = IMPORT_COMMAND_PATTERN.subn(
        lambda _match: NEW_IMPORT_COMMAND,
        patched,
    )

    if import_replacements != 1:
        raise ValueError(
            f"expected one Godot import command replacement, made {import_replacements}"
        )
    if DIAGNOSTIC_MAIN_SCENE_OVERRIDE in patched:
        raise ValueError("diagnostic main-scene override remains after playable patch")
    if patched.count(PRODUCTION_MAIN_SCENE_MARKER) != 2:
        raise ValueError("production-main-scene preservation marker count is incorrect")
    if patched.count("Overlay candidate visual-upgrade runtime files") != 1:
        raise ValueError("visual-upgrade runtime overlay marker count is incorrect")
    for relative in VISUAL_UPGRADE_FILES:
        if f'  "{relative}"' not in patched:
            raise ValueError(f"visual-upgrade runtime overlay missing: {relative}")
    if OLD_PACKAGE in patched:
        raise ValueError("diagnostic Mobile package identity remains after playable patch")
    if OLD_GODOT_DISCOVERY in patched or NEW_GODOT_DISCOVERY not in patched:
        raise ValueError("Godot binary discovery was not hardened against ZIP selection")
    if IMPORT_COMMAND_PATTERN.search(patched) or NEW_IMPORT_COMMAND not in patched:
        raise ValueError("Godot import command was not made headless and GPU-independent")
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
