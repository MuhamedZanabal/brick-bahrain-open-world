#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:?repository root is required}"
OUTPUT_ROOT="${2:?output root is required}"
BASE_EXPORTER="$REPO_ROOT/tools/graphics/export_r1_physical_device_apks.sh"
PATCHED_EXPORTER="$OUTPUT_ROOT/export_r1_playable_mobile_apk.patched.sh"
PLAYABLE_APK="$OUTPUT_ROOT/bahrain-brick-playable-mobile-arm64.apk"

mkdir -p "$OUTPUT_ROOT"
python3 "$REPO_ROOT/tools/graphics/patch_r1_playable_export.py" \
  --source "$BASE_EXPORTER" \
  --output "$PATCHED_EXPORTER"

grep -q 'Production main scene intentionally preserved for playable export' "$PATCHED_EXPORTER"
if grep -q 'r1_renderer_runtime_debug.tscn' "$PATCHED_EXPORTER"; then
  printf '%s\n' 'diagnostic main-scene override remains in playable exporter' >&2
  exit 1
fi

bash "$PATCHED_EXPORTER" "$REPO_ROOT" "$OUTPUT_ROOT"
test -s "$PLAYABLE_APK"
