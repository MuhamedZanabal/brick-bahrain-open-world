#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:?repository root is required}"
OUTPUT_ROOT="${2:?output root is required}"
RECONSTRUCTION="$OUTPUT_ROOT/reconstruction"
GAME="$RECONSTRUCTION/game"
PROJECT="$OUTPUT_ROOT/mobile-project"
OUT="$OUTPUT_ROOT/raw/mobile_shadow_distance"
APK="$OUTPUT_ROOT/bahrain-brick-r1-mobile-shadow-distance-x86_64.apk"
PACKAGE="com.brickbahrain.r1mobileshadowdistance"
GODOT_DIR="$OUTPUT_ROOT/godot"
XDG_DATA_HOME="$OUTPUT_ROOT/godot-user-data"
TEMPLATE_DIR="$OUTPUT_ROOT/templates"
AVD_HOME="$OUTPUT_ROOT/avd-home"
EMULATOR_HOME="$OUTPUT_ROOT/emulator-home"
AVD_NAME="bahrain_brick_r1_mobile_shadow_distance"
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

python3 "$REPO_ROOT/tools/graphics/apply_r1_mobile_shadow_distance_fix.py" --script "$GAME/scripts/manama_souq_vertical_slice.gd" --report "$OUTPUT_ROOT/MOBILE_SHADOW_DISTANCE_FIX.json"
mkdir -p "$GAME/tests/graphics"
cp "$REPO_ROOT/tests/graphics/r1_renderer_runtime_debug.gd" "$GAME/tests/graphics/"
cp "$REPO_ROOT/tests/graphics/r1_renderer_runtime_debug.tscn" "$GAME/tests/graphics/"
python3 - "$GAME/tests/graphics/r1_renderer_runtime_debug.gd" <<'PY'
from pathlib import Path
import sys
path=Path(sys.argv[1]); text=path.read_text()
old='\t_write_scene_tree_inventory(_slice)\n\t_write_wait_inventory()\n'
if text.count(old) != 1: raise SystemExit('targeted mobile inventory calls not found once')
path.write_text(text.replace(old, ''))
PY

unzip -q "$RECONSTRUCTION/downloads/Godot_v4.3-stable_linux.x86_64.zip" -d "$GODOT_DIR"
GODOT="$(find "$GODOT_DIR" -maxdepth 1 -type f -name 'Godot*' | head -1)"
test -n "$GODOT"; chmod +x "$GODOT"
"$GODOT" --version | tee "$OUTPUT_ROOT/GODOT_VERSION.txt"
grep -q '^4\.3\.' "$OUTPUT_ROOT/GODOT_VERSION.txt"

rm -rf "$GAME/.godot" "$PROJECT"
timeout --signal=TERM --kill-after=30s 1200s xvfb-run -a -s '-screen 0 1920x1080x24' "$GODOT" --path "$GAME" --editor --import --quit --verbose --rendering-method mobile --rendering-driver vulkan 2>&1 | tee "$OUTPUT_ROOT/import.log"
cp -a "$GAME" "$PROJECT"
python3 "$REPO_ROOT/tools/graphics/prepare_r1_android_variant.py" --project "$PROJECT/project.godot" --preset "$PROJECT/export_presets.cfg" --renderer mobile --package-name "$PACKAGE" --report "$OUTPUT_ROOT/MOBILE_VARIANT_OVERRIDE.json"

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
printf 'mobile_baseline' > "$OUTPUT_ROOT/mode.txt"
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
while (( elapsed < 240 )); do
  "$ADB" exec-out run-as "$PACKAGE" cat files/r1_mobile_progress.json > "$OUT/mobile_progress.json.tmp" 2>/dev/null || true
  if test -s "$OUT/mobile_progress.json.tmp"; then mv "$OUT/mobile_progress.json.tmp" "$OUT/mobile_progress.json"; fi
  if grep -q 'R1_MOBILE_CAPTURE_FRAME frame=300' "$OUT/logcat_full.txt"; then break; fi
  if grep -Eq 'SCRIPT ERROR|Parse Error|FATAL EXCEPTION|Fatal signal|R1_RUNTIME_DEBUG_FAILURE|VK_ERROR_DEVICE_LOST|ANR in' "$OUT/logcat_full.txt"; then break; fi
  sleep 5
  elapsed=$((elapsed+5))
done
"$ADB" exec-out run-as "$PACKAGE" cat files/r1_mobile_progress.json > "$OUT/mobile_progress.final.json" 2>/dev/null || true
if test -s "$OUT/mobile_progress.final.json"; then cp "$OUT/mobile_progress.final.json" "$OUT/mobile_progress.json"; fi
"$ADB" exec-out screencap -p > "$OUT/screenshot.png" 2>/dev/null || true
PID_BEFORE="$("$ADB" shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')"
printf '%s\n' "$PID_BEFORE" > "$OUT/pid-before-resume.txt"
PAUSE_RESUME=false
if test -n "$PID_BEFORE"; then
  "$ADB" shell input keyevent KEYCODE_HOME >/dev/null 2>&1 || true
  sleep 3
  "$ADB" shell am start -W -n "$RESOLVED" > "$OUT/resume.txt" 2>&1 || true
  sleep 5
  PID_AFTER="$("$ADB" shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')"
  printf '%s\n' "$PID_AFTER" > "$OUT/pid-after-resume.txt"
  if test -n "$PID_AFTER" && grep -q 'Status: ok' "$OUT/resume.txt"; then PAUSE_RESUME=true; fi
else
  : > "$OUT/resume.txt"
  : > "$OUT/pid-after-resume.txt"
fi
kill "$LOGCAT_PID" >/dev/null 2>&1 || true
wait "$LOGCAT_PID" >/dev/null 2>&1 || true

CRITICAL="$(grep -Ec 'SCRIPT ERROR|Parse Error|FATAL EXCEPTION|Fatal signal|VK_ERROR_DEVICE_LOST|ANR in|linker:.*(error|cannot)|R1_RUNTIME_DEBUG_FAILURE' "$OUT/logcat_full.txt" || true)"
SCENE_READY=false
grep -q 'R1_PRODUCTION_SCENE_READY' "$OUT/logcat_full.txt" && SCENE_READY=true
python3 - "$OUT/mobile_progress.json" "$OUT/screenshot.png" "$OUT/am-start.txt" "$OUTPUT_ROOT/R1_MOBILE_SHADOW_DISTANCE_RESULT.json" "$PID_BEFORE" "$CRITICAL" "$PAUSE_RESUME" "$SCENE_READY" "$elapsed" <<'PY'
from pathlib import Path
import json,sys
from PIL import Image, ImageStat

progress_path, screenshot_path, start_path, result_path = map(Path, sys.argv[1:5])
records=[]
if progress_path.exists() and progress_path.stat().st_size:
    try: records=json.loads(progress_path.read_text()).get('records', [])
    except Exception: records=[]
last=max((int(r.get('local_frame',0)) for r in records), default=0)
def first_time(frame):
    values=[int(r.get('wall_ms',0)) for r in records if int(r.get('local_frame',0))>=frame]
    return min(values) if values else None
valid=False; non_black=False; size=[0,0]; avg_luma=0.0; black_ratio=1.0
try:
    with Image.open(screenshot_path) as image:
        image=image.convert('RGB'); size=list(image.size)
        stat=ImageStat.Stat(image.convert('L')); avg_luma=float(stat.mean[0])
        pixels=list(image.resize((160,90)).getdata())
        black=sum(1 for r,g,b in pixels if r<=3 and g<=3 and b<=3)
        black_ratio=black/len(pixels)
        valid=size==[1920,1080]
        non_black=valid and avg_luma>1.0 and black_ratio<0.99
except Exception:
    pass
start=start_path.read_text(errors='replace') if start_path.exists() else ''
critical=int(sys.argv[6]); process_alive=bool(sys.argv[5]); pause_resume=sys.argv[7]=='true'; scene_ready=sys.argv[8]=='true'
reached_300=last>=300
improved=last>90
passed=(reached_300 and non_black and process_alive and pause_resume and critical==0 and scene_ready and 'Status: ok' in start)
result={
  'schema_version':1,
  'defect':'RENDER_PIPELINE_STALL',
  'experiment':'DIRECTIONAL_SHADOW_MAX_DISTANCE_150_TO_75',
  'before_last_completed_frame':90,
  'last_completed_frame':last,
  'time_to_frame_180_ms':first_time(180),
  'time_to_frame_300_ms':first_time(300),
  'apk_export_result':True,
  'apk_launch_result':'Status: ok' in start,
  'scene_readiness_result':scene_ready,
  'valid_screenshot_result':valid,
  'non_black_screenshot_result':non_black,
  'screenshot_size':size,
  'average_luminance':avg_luma,
  'black_pixel_ratio':black_ratio,
  'process_alive':process_alive,
  'critical_runtime_error_count':critical,
  'pause_resume_result':pause_resume,
  'bounded_window_seconds':int(sys.argv[9]),
  'progression_improved':improved,
  'r1_mobile_pass':passed,
  'renderer_default_modified':False,
  'gameplay_modified':False,
}
result['decision']='retained' if passed or improved else 'reverted'
result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,sort_keys=True))
if not (passed or improved): raise SystemExit(1)
PY
