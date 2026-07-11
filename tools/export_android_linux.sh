#!/usr/bin/env bash
set -euo pipefail
GODOT_BIN="${GODOT_BIN:-godot}"
OUTPUT="${1:-build/brick_bahrain_v14-debug.apk}"
mkdir -p "$(dirname "$OUTPUT")" build/ci_logs
"$GODOT_BIN" --headless --path . --editor --quit 2>&1 | tee build/ci_logs/local-android-import-linux.log
"$GODOT_BIN" --headless --path . --export-debug Android "$OUTPUT" 2>&1 | tee build/ci_logs/local-android-export-linux.log
test -s "$OUTPUT"
sha256sum "$OUTPUT" > "$OUTPUT.sha256"
