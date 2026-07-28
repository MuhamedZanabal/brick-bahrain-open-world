#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:?repository root is required}"
OUTPUT_ROOT="${2:?output root is required}"
BASE_RUNNER="$REPO_ROOT/tools/graphics/run_r1_renderer_debug.sh"
PATCHED_RUNNER="$OUTPUT_ROOT/run_r1_engine_retry.patched.sh"
mkdir -p "$OUTPUT_ROOT"

python3 - "$BASE_RUNNER" "$PATCHED_RUNNER" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
target = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")

anchor = 'for tool in "$ADB" "$EMULATOR" "$AVDMANAGER" "$APKSIGNER"; do test -x "$tool"; done\n'
status_block = r'''

HARNESS_STATUS="$OUTPUT_ROOT/R1_ENGINE_HARNESS_STATUS.json"
write_harness_status() {
  local phase="$1" status="$2"
  python3 - "$HARNESS_STATUS" "$phase" "$status" <<'PY_STATUS'
from pathlib import Path
import json,sys
path=Path(sys.argv[1]); phase=sys.argv[2]; status=int(sys.argv[3])
payload={
    'schema_version':1,
    'experiment':'GODOT_ENGINE_4_3_TO_4_7_1_STABLE',
    'phase':phase,
    'phase_exit_status':status,
    'complete':phase=='complete' and status==0,
    'renderer_defaults_modified':False,
    'gameplay_modified':False,
}
path.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
print(json.dumps(payload,sort_keys=True))
PY_STATUS
}
write_harness_status setup 0
'''
if text.count(anchor) != 1:
    raise SystemExit("tool anchor not found exactly once")
text = text.replace(anchor, anchor + status_block, 1)

old_import = '''timeout --signal=TERM --kill-after=30s 1200s xvfb-run -a -s '-screen 0 1920x1080x24' "$GODOT" --path "$GAME" --editor --import --quit --verbose --rendering-method mobile --rendering-driver vulkan 2>&1 | tee "$OUTPUT_ROOT/import.log"\ncp -a "$GAME" "$GL_PROJECT"'''
new_import = '''set +e\ntimeout --signal=TERM --kill-after=30s 3600s xvfb-run -a -s '-screen 0 1920x1080x24' "$GODOT" --path "$GAME" --editor --import --quit --verbose --rendering-method mobile --rendering-driver vulkan 2>&1 | tee "$OUTPUT_ROOT/import.log"\nIMPORT_STATUS=${PIPESTATUS[0]}\nset -e\nwrite_harness_status import "$IMPORT_STATUS"\nif (( IMPORT_STATUS != 0 )); then exit "$IMPORT_STATUS"; fi\nprintf 'complete\\n' > "$OUTPUT_ROOT/IMPORT_COMPLETE.txt"\ncp -a "$GAME" "$GL_PROJECT"'''
if text.count(old_import) != 1:
    raise SystemExit("import command not found exactly once")
text = text.replace(old_import, new_import, 1)

old_exports = '''timeout --signal=TERM --kill-after=30s 1800s "$GODOT" --headless --path "$GL_PROJECT" --verbose --export-debug Android "$GL_APK" 2>&1 | tee "$OUTPUT_ROOT/export-gl.log"\ntimeout --signal=TERM --kill-after=30s 1800s "$GODOT" --headless --path "$MOBILE_PROJECT" --verbose --export-debug Android "$MOBILE_APK" 2>&1 | tee "$OUTPUT_ROOT/export-mobile.log"'''
new_exports = '''set +e\ntimeout --signal=TERM --kill-after=30s 1800s "$GODOT" --headless --path "$GL_PROJECT" --verbose --export-debug Android "$GL_APK" 2>&1 | tee "$OUTPUT_ROOT/export-gl.log"\nGL_EXPORT_STATUS=${PIPESTATUS[0]}\nset -e\nwrite_harness_status export_gl "$GL_EXPORT_STATUS"\nif (( GL_EXPORT_STATUS != 0 )); then exit "$GL_EXPORT_STATUS"; fi\nset +e\ntimeout --signal=TERM --kill-after=30s 1800s "$GODOT" --headless --path "$MOBILE_PROJECT" --verbose --export-debug Android "$MOBILE_APK" 2>&1 | tee "$OUTPUT_ROOT/export-mobile.log"\nMOBILE_EXPORT_STATUS=${PIPESTATUS[0]}\nset -e\nwrite_harness_status export_mobile "$MOBILE_EXPORT_STATUS"\nif (( MOBILE_EXPORT_STATUS != 0 )); then exit "$MOBILE_EXPORT_STATUS"; fi'''
if text.count(old_exports) != 1:
    raise SystemExit("export commands not found exactly once")
text = text.replace(old_exports, new_exports, 1)

text += '\nwrite_harness_status complete 0\n'
target.write_text(text, encoding="utf-8")
target.chmod(0o755)
PY

bash "$PATCHED_RUNNER" "$REPO_ROOT" "$OUTPUT_ROOT"
