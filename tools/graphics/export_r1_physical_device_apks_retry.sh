#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:?repository root is required}"
OUTPUT_ROOT="${2:?output root is required}"
BASE_EXPORTER="$REPO_ROOT/tools/graphics/export_r1_physical_device_apks.sh"
PATCHED_EXPORTER="$OUTPUT_ROOT/export_r1_physical_device_apks.patched.sh"
mkdir -p "$OUTPUT_ROOT"

python3 - "$BASE_EXPORTER" "$PATCHED_EXPORTER" <<'PY'
from pathlib import Path
import sys
source = Path(sys.argv[1])
target = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
old = 'GODOT="$(find "$GODOT_DIR" -maxdepth 1 -type f -name \'Godot*\' | head -1)"'
new = 'GODOT="$(find "$GODOT_DIR" -maxdepth 1 -type f -name \'Godot*\' ! -name \'*.zip\' | head -1)"'
if text.count(old) != 1:
    raise SystemExit("Godot binary discovery anchor not found exactly once")
target.write_text(text.replace(old, new), encoding="utf-8")
target.chmod(0o755)
PY

bash "$PATCHED_EXPORTER" "$REPO_ROOT" "$OUTPUT_ROOT"
