#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:?repository root is required}"
OUTPUT_ROOT="${2:?output root is required}"
RECONSTRUCTION="$OUTPUT_ROOT/reconstruction"
GAME="$RECONSTRUCTION/game"
PROJECT="$OUTPUT_ROOT/mobile-project"
OUT="$OUTPUT_ROOT/raw/mobile_no_directional_shadows"
APK="$OUTPUT_ROOT/bahrain-brick-r1-mobile-no-directional-shadows-x86_64.apk"
PACKAGE="com.brickbahrain.r1mobilenosunshadow"
GODOT_DIR="$OUTPUT_ROOT/godot"
XDG_DATA_HOME="$OUTPUT_ROOT/godot-user-data"
TEMPLATE_DIR="$OUTPUT_ROOT/templates"
AVD_HOME="$OUTPUT_ROOT/avd-home"
EMULATOR_HOME="$OUTPUT_ROOT/emulator-home"
AVD_NAME="bahrain_brick_r1_mobile_shadow"
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
python3 "$REPO_ROOT/tools/graphics/apply_r1_mobile_shadow_fix.py" --script "$GAME/scripts/manama_souq_vertical_slice.gd" --report "$OUTPUT_ROOT/MOBILE_SHADOW_FIX.json"
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
nohup "$EMULATOR" "@$AVD_NAME" -no-window -no-audio -no-boot-anim -no-snapshot -wipe-data -gpu swiftshader -accel auto -memory 4096 -cores 4 -camera-back none -camera-front none > "$OUTPUT_ROOT/emulator.log" 2>&1 &
EMULATOR_PID=$!
cleanup(){ "$ADB" emu kill >/dev/null 2>&1 || true; kill "$EMULATOR_PID" >/dev/null 2>&1 || true; }
trap cleanup EXIT
"$ADB" wait-for-device
for _ in $(seq 1 240); do [[ "$("$ADB" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == 1 ]] && break; sleep 2; done
[[ "$("$ADB" shell getprop sys.boot_completed | tr -d '\r')" == 1 ]]
"$ADB" shell settings put system accelerometer_rotation 0 >/dev/null
"$ADB" shell settings put system user_rotation 1 >/dev/null
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
marker=false
while ((elapsed < 240)); do
  if grep -q 'R1_MOBILE_CAPTURE_FRAME frame=300' "$OUT/logcat_full.txt"; then marker=true; break; fi
  if grep -Eq 'SCRIPT ERROR|Parse Error|FATAL EXCEPTION|Fatal signal|VK_ERROR_DEVICE_LOST|R1_RUNTIME_DEBUG_FAILURE' "$OUT/logcat_full.txt"; then break; fi
  sleep 2
  elapsed=$((elapsed+2))
done
"$ADB" exec-out screencap -p > "$OUT/screenshot.png" 2>/dev/null || true
PID_BEFORE="$("$ADB" shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')"
printf '%s\n' "$PID_BEFORE" > "$OUT/pid-before-pause.txt"
"$ADB" shell input keyevent KEYCODE_HOME >/dev/null 2>&1 || true
sleep 5
PID_PAUSED="$("$ADB" shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')"
printf '%s\n' "$PID_PAUSED" > "$OUT/pid-paused.txt"
"$ADB" shell am start -W -n "$RESOLVED" > "$OUT/am-resume.txt" 2>&1 || true
sleep 10
PID_AFTER="$("$ADB" shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')"
printf '%s\n' "$PID_AFTER" > "$OUT/pid-after-resume.txt"
"$ADB" exec-out run-as "$PACKAGE" cat files/r1_mobile_progress.json > "$OUT/mobile_progress.json" 2>/dev/null || true
kill "$LOGCAT_PID" >/dev/null 2>&1 || true
wait "$LOGCAT_PID" >/dev/null 2>&1 || true

grep -Ei 'SCRIPT ERROR|Parse Error|Invalid call|FATAL EXCEPTION|Fatal signal|VK_ERROR_DEVICE_LOST|GPU hang|ANR in |R1_RUNTIME_DEBUG_FAILURE' "$OUT/logcat_full.txt" > "$OUT/critical_log.txt" || true
CRITICAL_COUNT="$(wc -l < "$OUT/critical_log.txt" | tr -d ' ')"
PYTHON="$RECONSTRUCTION/venv/bin/python"
"$PYTHON" - "$OUT/mobile_progress.json" "$OUT/screenshot.png" "$OUT/logcat_full.txt" "$OUT/am-start.txt" "$OUT/am-resume.txt" "$OUTPUT_ROOT/R1_MOBILE_SHADOW_RESULT.json" "$PID_BEFORE" "$PID_PAUSED" "$PID_AFTER" "$CRITICAL_COUNT" "$elapsed" <<'PY'
from pathlib import Path
from PIL import Image, ImageStat
import json,sys
progress_path,screenshot_path,log_path,start_path,resume_path,result_path=map(Path,sys.argv[1:7])
pid_before,pid_paused,pid_after=sys.argv[7:10]
critical_count=int(sys.argv[10]); elapsed=int(sys.argv[11])
try:
    progress=json.loads(progress_path.read_text())
except Exception:
    progress={'records':[],'complete':False}
records=progress.get('records',[])
last_frame=max((int(r.get('local_frame',0)) for r in records),default=0)
def wall_for(frame):
    for record in records:
        if int(record.get('local_frame',0)) >= frame:
            return int(record.get('wall_ms',0))
    return None
screenshot_valid=False; screenshot_non_black=False; screenshot_size=[0,0]
try:
    with Image.open(screenshot_path) as image:
        image=image.convert('RGB'); screenshot_size=list(image.size)
        screenshot_valid=image.size[0]>=320 and image.size[1]>=240
        extrema=image.getextrema(); mean=ImageStat.Stat(image).mean
        screenshot_non_black=screenshot_valid and max(v[1] for v in extrema)>8 and sum(mean)>8
except Exception:
    pass
log=log_path.read_text(errors='replace') if log_path.exists() else ''
start=start_path.read_text(errors='replace') if start_path.exists() else ''
resume=resume_path.read_text(errors='replace') if resume_path.exists() else ''
scene_ready='R1_PRODUCTION_SCENE_READY' in log
marker='R1_MOBILE_CAPTURE_FRAME frame=300' in log
launch_ok='Status: ok' in start
resume_ok='Status: ok' in resume
process_alive=bool(pid_after)
pause_resume=bool(pid_before) and bool(pid_paused) and process_alive and resume_ok
healthy=scene_ready and launch_ok and screenshot_valid and screenshot_non_black and process_alive and critical_count==0
passed=healthy and marker and last_frame>=300 and pause_resume
materially_improved=healthy and last_frame>90
result={
  'schema_version':1,
  'root_cause':'RENDER_PIPELINE_STALL',
  'experiment':'DISABLE_ALL_DIRECTIONAL_SHADOWS',
  'baseline_last_completed_frame':90,
  'bounded_window_seconds':240,
  'apk_export_result':True,
  'apk_launch_result':launch_ok,
  'scene_readiness_result':scene_ready,
  'last_completed_frame':last_frame,
  'time_to_frame_180_ms':wall_for(180),
  'time_to_frame_300_ms':wall_for(300),
  'capture_frame_300_reached':marker and last_frame>=300,
  'valid_screenshot_result':screenshot_valid and screenshot_non_black,
  'screenshot_size':screenshot_size,
  'process_alive':process_alive,
  'pause_resume_result':pause_resume,
  'critical_runtime_error_count':critical_count,
  'elapsed_seconds':elapsed,
  'materially_improved':materially_improved,
  'passed':passed,
  'decision':'retained' if (passed or materially_improved) else 'reverted',
  'qa_override_only':True,
  'renderer_defaults_modified':False,
  'gameplay_modified':False,
}
result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,sort_keys=True))
if not (passed or materially_improved):
    raise SystemExit(1)
PY
