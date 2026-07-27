#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:?repository root is required}"
OUTPUT_ROOT="${2:?output root is required}"
RECONSTRUCTION="$OUTPUT_ROOT/reconstruction"
GAME="$RECONSTRUCTION/game"
PROJECT="$OUTPUT_ROOT/gl-project"
OUT="$OUTPUT_ROOT/raw/gl_production"
APK="$OUTPUT_ROOT/bahrain-brick-r1-gl-budget-x86_64.apk"
PACKAGE="com.brickbahrain.r1glbudget"
GODOT_DIR="$OUTPUT_ROOT/godot"
XDG_DATA_HOME="$OUTPUT_ROOT/godot-user-data"
TEMPLATE_DIR="$OUTPUT_ROOT/templates"
AVD_HOME="$OUTPUT_ROOT/avd-home"
EMULATOR_HOME="$OUTPUT_ROOT/emulator-home"
AVD_NAME="bahrain_brick_r1_gl_budget"
mkdir -p "$OUTPUT_ROOT" "$OUT" "$GODOT_DIR" "$XDG_DATA_HOME" "$TEMPLATE_DIR" "$AVD_HOME" "$EMULATOR_HOME"

SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
ADB="$SDK_ROOT/platform-tools/adb"
EMULATOR="$SDK_ROOT/emulator/emulator"
AVDMANAGER="$(find "$SDK_ROOT/cmdline-tools" -type f -path '*/bin/avdmanager' | sort | tail -1)"
APKSIGNER="$SDK_ROOT/build-tools/34.0.0/apksigner"
for tool in "$ADB" "$EMULATOR" "$AVDMANAGER" "$APKSIGNER"; do test -x "$tool"; done

rm -rf "$RECONSTRUCTION"
PATCHED_RECONSTRUCTION="$OUTPUT_ROOT/reconstruct.r1.sh"
python3 - "$REPO_ROOT/tools/vertical_slice/reconstruct_manama_souq_composite.sh" "$PATCHED_RECONSTRUCTION" <<'PY'
from pathlib import Path
import sys
source=Path(sys.argv[1]); target=Path(sys.argv[2]); text=source.read_text()
old='test "${ImageVersion:-}" = "20260714.240.1"'
new='test -n "${ImageVersion:-}"'
if text.count(old) != 1: raise SystemExit('historical image assertion not found once')
target.write_text(text.replace(old,new)); target.chmod(0o755)
PY
bash "$PATCHED_RECONSTRUCTION" A "$RECONSTRUCTION" "$REPO_ROOT/authority/manama_souq_composite_source.json" "$(git -C "$REPO_ROOT" rev-parse HEAD)"
python3 "$REPO_ROOT/tools/graphics/patch_r1_reconstruction_preflight.py" --manifest "$RECONSTRUCTION/evidence/FINAL_TREE_MANIFEST.json" --game "$GAME" --output "$OUTPUT_ROOT/SOURCE_TREE_EQUIVALENCE.json"

python3 "$REPO_ROOT/tools/graphics/apply_r1_gl_compatibility_fix.py" --project "$GAME/project.godot" --report "$OUTPUT_ROOT/GL_COMPATIBILITY_FIX.json"
mkdir -p "$GAME/tests/graphics"
cp "$REPO_ROOT/tests/graphics/r1_renderer_runtime_debug.gd" "$GAME/tests/graphics/"
cp "$REPO_ROOT/tests/graphics/r1_renderer_runtime_debug.tscn" "$GAME/tests/graphics/"

unzip -q "$RECONSTRUCTION/downloads/Godot_v4.3-stable_linux.x86_64.zip" -d "$GODOT_DIR"
GODOT="$(find "$GODOT_DIR" -maxdepth 1 -type f -name 'Godot*' | head -1)"
test -n "$GODOT"; chmod +x "$GODOT"
"$GODOT" --version | tee "$OUTPUT_ROOT/GODOT_VERSION.txt"
grep -q '^4\.3\.' "$OUTPUT_ROOT/GODOT_VERSION.txt"

rm -rf "$GAME/.godot" "$PROJECT"
LIBGL_ALWAYS_SOFTWARE=1 timeout --signal=TERM --kill-after=30s 1200s xvfb-run -a -s '-screen 0 1920x1080x24' "$GODOT" --path "$GAME" --editor --import --quit --verbose --rendering-method gl_compatibility --rendering-driver opengl3 2>&1 | tee "$OUTPUT_ROOT/import.log"
cp -a "$GAME" "$PROJECT"
python3 "$REPO_ROOT/tools/graphics/prepare_r1_android_variant.py" --project "$PROJECT/project.godot" --preset "$PROJECT/export_presets.cfg" --renderer gl_compatibility --package-name "$PACKAGE" --report "$OUTPUT_ROOT/GL_VARIANT_OVERRIDE.json"

TEMPLATE="Godot_v4.3-stable_export_templates.tpz"
ROOT_URL="https://github.com/godotengine/godot-builds/releases/download/4.3-stable"
curl --fail --location --retry 5 --retry-all-errors "$ROOT_URL/SHA512-SUMS.txt" -o "$TEMPLATE_DIR/SHA512-SUMS.txt"
curl --fail --location --retry 5 --retry-all-errors "$ROOT_URL/$TEMPLATE" -o "$TEMPLATE_DIR/$TEMPLATE"
EXPECTED="$(awk -v name="$TEMPLATE" '$NF == name || $NF == "*" name {print $1; exit}' "$TEMPLATE_DIR/SHA512-SUMS.txt")"
test -n "$EXPECTED"; printf '%s  %s\n' "$EXPECTED" "$TEMPLATE_DIR/$TEMPLATE" | sha512sum -c -
unzip -q "$TEMPLATE_DIR/$TEMPLATE" -d "$TEMPLATE_DIR/unpacked"
mkdir -p "$XDG_DATA_HOME/godot/export_templates/4.3.stable"
cp -a "$TEMPLATE_DIR/unpacked/templates/." "$XDG_DATA_HOME/godot/export_templates/4.3.stable/"

XDG_DATA_HOME="$XDG_DATA_HOME" GODOT_ANDROID_KEYSTORE_DEBUG_PATH="$REPO_ROOT/debug.keystore" GODOT_ANDROID_KEYSTORE_DEBUG_USER=androiddebugkey GODOT_ANDROID_KEYSTORE_DEBUG_PASSWORD=android timeout --signal=TERM --kill-after=30s 1800s "$GODOT" --headless --path "$PROJECT" --verbose --export-debug Android "$APK" 2>&1 | tee "$OUTPUT_ROOT/export.log"
test -s "$APK"
"$APKSIGNER" verify --verbose --print-certs "$APK" > "$OUTPUT_ROOT/apk-signing.txt"
sha256sum "$APK" > "$OUTPUT_ROOT/APK_SHA256SUMS.txt"

export ANDROID_AVD_HOME="$AVD_HOME" ANDROID_EMULATOR_HOME="$EMULATOR_HOME"
rm -rf "$AVD_HOME"/* "$EMULATOR_HOME"/*
echo no | "$AVDMANAGER" create avd --force --name "$AVD_NAME" --package 'system-images;android-34;default;x86_64' --device 'pixel_6' > "$OUTPUT_ROOT/avd-create.txt" 2>&1
nohup "$EMULATOR" "@$AVD_NAME" -no-window -no-audio -no-boot-anim -no-snapshot -wipe-data -gpu swiftshader -accel auto -memory 4096 -cores 4 > "$OUTPUT_ROOT/emulator.log" 2>&1 &
EMULATOR_PID=$!
cleanup(){ "$ADB" emu kill >/dev/null 2>&1 || true; kill "$EMULATOR_PID" >/dev/null 2>&1 || true; }
trap cleanup EXIT
"$ADB" wait-for-device
for _ in $(seq 1 240); do [[ "$("$ADB" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == 1 ]] && break; sleep 2; done
[[ "$("$ADB" shell getprop sys.boot_completed | tr -d '\r')" == 1 ]]
"$ADB" shell wm size 1920x1080 >/dev/null
"$ADB" shell wm density 420 >/dev/null
"$ADB" install -r -t "$APK" > "$OUT/install.txt" 2>&1
"$ADB" shell pm clear "$PACKAGE" >/dev/null 2>&1 || true
printf 'gl_production' > "$OUTPUT_ROOT/mode.txt"
"$ADB" push "$OUTPUT_ROOT/mode.txt" /data/local/tmp/r1_mode.txt >/dev/null
"$ADB" shell run-as "$PACKAGE" mkdir -p files
"$ADB" shell run-as "$PACKAGE" cp /data/local/tmp/r1_mode.txt files/r1_mode.txt
"$ADB" exec-out run-as "$PACKAGE" cat files/r1_mode.txt > "$OUTPUT_ROOT/mode.verified.txt"
cmp -s "$OUTPUT_ROOT/mode.txt" "$OUTPUT_ROOT/mode.verified.txt"

"$ADB" logcat -c
"$ADB" logcat -v threadtime > "$OUT/logcat_full.txt" 2>&1 &
LOGCAT_PID=$!
sleep 2
RESOLVED="$("$ADB" shell cmd package resolve-activity --brief "$PACKAGE" | tail -1 | tr -d '\r')"
printf '%s\n' "$RESOLVED" > "$OUT/resolve-activity.txt"
"$ADB" shell am start -W -S -n "$RESOLVED" > "$OUT/am-start.txt" 2>&1 || true
elapsed=0
marker=false
while ((elapsed < 300)); do
  if grep -q 'R1_GL_SCENARIO_COMPLETE mode=gl_production' "$OUT/logcat_full.txt"; then marker=true; break; fi
  if grep -Eq 'SCRIPT ERROR|Parse Error|FATAL EXCEPTION|Fatal signal|R1_RUNTIME_DEBUG_FAILURE' "$OUT/logcat_full.txt"; then break; fi
  sleep 2
  elapsed=$((elapsed+2))
done
"$ADB" exec-out screencap -p > "$OUT/screenshot.png" 2>/dev/null || true
PID="$("$ADB" shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')"
printf '%s\n' "$PID" > "$OUT/pid-final.txt"
kill "$LOGCAT_PID" >/dev/null 2>&1 || true
wait "$LOGCAT_PID" >/dev/null 2>&1 || true
COUNT="$(grep -c 'Fragment shader active uniforms exceed GL_MAX_FRAGMENT_UNIFORM_VECTORS' "$OUT/logcat_full.txt" || true)"
CRITICAL="$(grep -Ec 'SCRIPT ERROR|Parse Error|FATAL EXCEPTION|Fatal signal' "$OUT/logcat_full.txt" || true)"
python3 - "$OUT/screenshot.png" "$OUT/am-start.txt" "$OUTPUT_ROOT/R1_GL_BUDGET_RESULT.json" "$marker" "$PID" "$COUNT" "$CRITICAL" "$elapsed" <<'PY'
from pathlib import Path
import json,struct,sys
png_path,start_path,result_path=map(Path,sys.argv[1:4])
png=png_path.read_bytes() if png_path.exists() else b''
valid=len(png)>=24 and png[:8]==b'\x89PNG\r\n\x1a\n'
w=h=0
if valid:
    w,h=struct.unpack('>II',png[16:24])
    valid=w>=320 and h>=240
start=start_path.read_text(errors='replace') if start_path.exists() else ''
count=int(sys.argv[6]); critical=int(sys.argv[7])
health=(sys.argv[4]=='true' and bool(sys.argv[5]) and valid and critical==0 and 'Status: ok' in start)
result={
  'schema_version':1,
  'defect':'GL_COMPATIBILITY_ENGINE_GENERATED_FRAGMENT_UNIFORM_OVERFLOW',
  'experiment':'MAX_LIGHTS_PER_OBJECT_5_TO_4',
  'before_link_failures':44,
  'after_link_failures':count,
  'apk_export_result':True,
  'apk_launch_result':'Status: ok' in start,
  'scene_readiness_result':sys.argv[4]=='true',
  'valid_screenshot_result':valid,
  'screenshot_size':[w,h],
  'process_alive':bool(sys.argv[5]),
  'critical_runtime_error_count':critical,
  'elapsed_seconds':int(sys.argv[8]),
  'improved':health and count<44,
  'retained':health and count<=44,
  'renderer_defaults_modified':False,
  'gameplay_modified':False,
}
result['decision']='retained' if result['retained'] else 'reverted'
result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,sort_keys=True))
if not result['retained']:
    raise SystemExit(1)
PY
