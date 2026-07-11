#!/usr/bin/env bash
set -euo pipefail
GODOT_BIN="${GODOT_BIN:-godot}"
mkdir -p build/ci_logs
"$GODOT_BIN" --headless --path . --editor --quit 2>&1 | tee build/ci_logs/local-import-linux.log
"$GODOT_BIN" --headless --path . --script res://tests/runtime_smoke_test_v14.gd 2>&1 | tee build/ci_logs/local-runtime-linux.log
