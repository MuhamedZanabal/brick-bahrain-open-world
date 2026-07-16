#!/usr/bin/env bash
set -euo pipefail
GODOT_BIN="$1"
GAME_ROOT="$2"
LOG_ROOT="$3"
REPORT_ROOT="$4"
mkdir -p "$LOG_ROOT" "$REPORT_ROOT" "$GAME_ROOT/build/ci/test-user-data"/{smoke,controls,presentation,premium-world,premium-presentation,lifecycle,resource-repeat}
run_godot() {
  local name="$1"; shift
  set -o pipefail
  "$@" 2>&1 | tee "$LOG_ROOT/$name.log"
  test "${PIPESTATUS[0]}" -eq 0
}
run_godot runtime-smoke env XDG_DATA_HOME="$PWD/$GAME_ROOT/build/ci/test-user-data/smoke" timeout 700 "$GODOT_BIN" --headless --path "$GAME_ROOT" --audio-driver Dummy res://build/ci/runtime_smoke_runner_v14.tscn
grep -q '43 passed, 0 failed' "$LOG_ROOT/runtime-smoke.log"
run_godot controls env XDG_DATA_HOME="$PWD/$GAME_ROOT/build/ci/test-user-data/controls" timeout 700 "$GODOT_BIN" --headless --path "$GAME_ROOT" --audio-driver Dummy res://scenes/mobile_input_pipeline_test.tscn
grep -q '28 passed, 0 failed' "$LOG_ROOT/controls.log"
run_godot presentation env XDG_DATA_HOME="$PWD/$GAME_ROOT/build/ci/test-user-data/presentation" timeout 700 "$GODOT_BIN" --headless --path "$GAME_ROOT" --audio-driver Dummy res://scenes/presentation_flow_test.tscn -- --presentation-test
grep -q '10 passed, 0 failed' "$LOG_ROOT/presentation.log"
run_godot premium-world env XDG_DATA_HOME="$PWD/$GAME_ROOT/build/ci/test-user-data/premium-world" timeout 700 "$GODOT_BIN" --headless --path "$GAME_ROOT" --audio-driver Dummy res://scenes/premium_world_acceptance_test.tscn
grep -q '12 passed, 0 failed' "$LOG_ROOT/premium-world.log"
run_godot premium-presentation env XDG_DATA_HOME="$PWD/$GAME_ROOT/build/ci/test-user-data/premium-presentation" timeout 700 "$GODOT_BIN" --headless --path "$GAME_ROOT" --audio-driver Dummy res://scenes/premium_presentation_acceptance_test.tscn -- --presentation-test
grep -Eq '[0-9]+ passed, 0 failed' "$LOG_ROOT/premium-presentation.log"
run_godot lifecycle env XDG_DATA_HOME="$PWD/$GAME_ROOT/build/ci/test-user-data/lifecycle" timeout 700 "$GODOT_BIN" --headless --path "$GAME_ROOT" --audio-driver Dummy res://scenes/world_lifecycle_guard_test.tscn
grep -Eq 'World lifecycle guard complete: 12 passed, 0 failed|12 passed, 0 failed' "$LOG_ROOT/lifecycle.log"
run_godot resource-repeat env XDG_DATA_HOME="$PWD/$GAME_ROOT/build/ci/test-user-data/resource-repeat" timeout 700 "$GODOT_BIN" --headless --path "$GAME_ROOT" --audio-driver Dummy res://scenes/world_resource_repeat_test.tscn
grep -Eq 'World resource repeat complete: 21 passed, 0 failed|21 passed, 0 failed' "$LOG_ROOT/resource-repeat.log"
python3 tools/scan_godot_runtime_errors.py "$LOG_ROOT" --json-out "$REPORT_ROOT/CRITICAL_RUNTIME_ERROR_SCAN.json" --markdown-out "$REPORT_ROOT/CRITICAL_RUNTIME_ERROR_SCAN.md"
