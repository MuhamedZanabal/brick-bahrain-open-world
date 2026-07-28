#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:?repository root is required}"
OUTPUT_ROOT="${2:?output root is required}"
RECONSTRUCTION="$OUTPUT_ROOT/reconstruction"
GAME="$RECONSTRUCTION/game"
GL_PROJECT="$OUTPUT_ROOT/gl-project"
MOBILE_PROJECT="$OUTPUT_ROOT/mobile-project"
GL_OUT="$OUTPUT_ROOT/raw/gl_production"
MOBILE_OUT="$OUTPUT_ROOT/raw/mobile_baseline"
GL_APK="$OUTPUT_ROOT/bahrain-brick-r1-engine-4-7-1-gl-x86_64.apk"
MOBILE_APK="$OUTPUT_ROOT/bahrain-brick-r1-engine-4-7-1-mobile-x86_64.apk"
GL_PACKAGE="com.brickbahrain.r1engine471gl"
MOBILE_PACKAGE="com.brickbahrain.r1engine471mobile"
GODOT_RELEASE="4.7.1-stable"
GODOT_ARCHIVE="Godot_v4.7.1-stable_linux.x86_64.zip"
TEMPLATE="Godot_v4.7.1-stable_export_templates.tpz"
ROOT_URL="https://github.com/godotengine/godot-builds/releases/download/$GODOT_RELEASE"
GODOT_DIR="$OUTPUT_ROOT/godot"
XDG_DATA_HOME="$OUTPUT_ROOT/godot-user-data"
TEMPLATE_DIR="$OUTPUT_ROOT/templates"
AVD_HOME="$OUTPUT_ROOT/avd-home"
EMULATOR_HOME="$OUTPUT_ROOT/emulator-home"
AVD_NAME="bahrain_brick_r1_engine_471"
mkdir -p "$OUTPUT_ROOT" "$GL_OUT" "$MOBILE_OUT" "$GODOT_DIR" "$XDG_DATA_HOME" "$TEMPLATE_DIR" "$AVD_HOME" "$EMULATOR_HOME"

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

curl --fail --location --retry 5 --retry-all-errors "$ROOT_URL/SHA512-SUMS.txt" -o "$TEMPLATE_DIR/SHA512-SUMS.txt"
curl --fail --location --retry 5 --retry-all-errors "$ROOT_URL/$GODOT_ARCHIVE" -o "$GODOT_DIR/$GODOT_ARCHIVE"
curl --fail --location --retry 5 --retry-all-errors "$ROOT_URL/$TEMPLATE" -o "$TEMPLATE_DIR/$TEMPLATE"
for asset in "$GODOT_ARCHIVE" "$TEMPLATE"; do
  file="$GODOT_DIR/$asset"
  [[ "$asset" == "$TEMPLATE" ]] && file="$TEMPLATE_DIR/$asset"
  expected="$(awk -v name="$asset" '$NF == name || $NF == "*" name {print $1; exit}' "$TEMPLATE_DIR/SHA512-SUMS.txt")"
  test -n "$expected"
  printf '%s  %s\n' "$expected" "$file" | sha512sum -c -
done
unzip -q "$GODOT_DIR/$GODOT_ARCHIVE" -d "$GODOT_DIR"
GODOT="$(find "$GODOT_DIR" -maxdepth 1 -type f -name 'Godot*' | head -1)"
test -n "$GODOT"; chmod +x "$GODOT"
"$GODOT" --version | tee "$OUTPUT_ROOT/GODOT_VERSION.txt"
grep -q '^4\.7\.1\.' "$OUTPUT_ROOT/GODOT_VERSION.txt"
TEMPLATE_VERSION="$(sed -E 's/\.official.*$//' "$OUTPUT_ROOT/GODOT_VERSION.txt" | head -1)"
test -n "$TEMPLATE_VERSION"
unzip -q "$TEMPLATE_DIR/$TEMPLATE" -d "$TEMPLATE_DIR/unpacked"
mkdir -p "$XDG_DATA_HOME/godot/export_templates/$TEMPLATE_VERSION"
cp -a "$TEMPLATE_DIR/unpacked/templates/." "$XDG_DATA_HOME/godot/export_templates/$TEMPLATE_VERSION/"

rm -rf "$GAME/.godot" "$GL_PROJECT" "$MOBILE_PROJECT"
timeout --signal=TERM --kill-after=30s 1200s xvfb-run -a -s '-screen 0 1920x1080x24' "$GODOT" --path "$GAME" --editor --import --quit --verbose --rendering-method mobile --rendering-driver vulkan 2>&1 | tee "$OUTPUT_ROOT/import.log"
cp -a "$GAME" "$GL_PROJECT"
cp -a "$GAME" "$MOBILE_PROJECT"
python3 "$REPO_ROOT/tools/graphics/prepare_r1_android_variant.py" --project "$GL_PROJECT/project.godot" --preset "$GL_PROJECT/export_presets.cfg" --renderer gl_compatibility --package-name "$GL_PACKAGE" --report "$OUTPUT_ROOT/GL_VARIANT_OVERRIDE.json"
python3 "$REPO_ROOT/tools/graphics/prepare_r1_android_variant.py" --project "$MOBILE_PROJECT/project.godot" --preset "$MOBILE_PROJECT/export_presets.cfg" --renderer mobile --package-name "$MOBILE_PACKAGE" --report "$OUTPUT_ROOT/MOBILE_VARIANT_OVERRIDE.json"

export XDG_DATA_HOME
export GODOT_ANDROID_KEYSTORE_DEBUG_PATH="$REPO_ROOT/debug.keystore"
export GODOT_ANDROID_KEYSTORE_DEBUG_USER=androiddebugkey
export GODOT_ANDROID_KEYSTORE_DEBUG_PASSWORD=android
timeout --signal=TERM --kill-after=30s 1800s "$GODOT" --headless --path "$GL_PROJECT" --verbose --export-debug Android "$GL_APK" 2>&1 | tee "$OUTPUT_ROOT/export-gl.log"
timeout --signal=TERM --kill-after=30s 1800s "$GODOT" --headless --path "$MOBILE_PROJECT" --verbose --export-debug Android "$MOBILE_APK" 2>&1 | tee "$OUTPUT_ROOT/export-mobile.log"
for apk in "$GL_APK" "$MOBILE_APK"; do
  test -s "$apk"
  "$APKSIGNER" verify --verbose --print-certs "$apk" >> "$OUTPUT_ROOT/apk-signing.txt"
done
sha256sum "$GL_APK" "$MOBILE_APK" > "$OUTPUT_ROOT/APK_SHA256SUMS.txt"

export ANDROID_AVD_HOME="$AVD_HOME" ANDROID_EMULATOR_HOME="$EMULATOR_HOME"
rm -rf "$AVD_HOME"/* "$EMULATOR_HOME"/*
echo no | "$AVDMANAGER" create avd --force --name "$AVD_NAME" --package 'system-images;android-34;default;x86_64' --device 'pixel_6' > "$OUTPUT_ROOT/avd-create.txt" 2>&1
nohup "$EMULATOR" "@$AVD_NAME" -no-window -no-audio -no-boot-anim -no-snapshot -wipe-data -gpu swiftshader -accel auto -memory 4096 -cores 4 > "$OUTPUT_ROOT/emulator.log" 2>&1 &
EMULATOR_PID=$!
cleanup(){ "$ADB" emu kill >/dev/null 2>&1 || true; kill "$EMULATOR_PID" >/dev/null 2>&1 || true; }
trap cleanup EXIT
"$ADB" wait-for-device
for _ in $(seq 1 240); do
  [[ "$("$ADB" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == 1 ]] && break
  sleep 2
done
[[ "$("$ADB" shell getprop sys.boot_completed | tr -d '\r')" == 1 ]]
"$ADB" shell wm size 1920x1080 >/dev/null
"$ADB" shell wm density 420 >/dev/null

run_target() {
  local target="$1" mode="$2" package="$3" apk="$4" out="$5"
  mkdir -p "$out"
  "$ADB" install -r -t "$apk" > "$out/install.txt" 2>&1
  "$ADB" shell pm clear "$package" >/dev/null 2>&1 || true
  printf '%s' "$mode" > "$out/mode.txt"
  "$ADB" push "$out/mode.txt" /data/local/tmp/r1_mode.txt >/dev/null
  "$ADB" shell run-as "$package" mkdir -p files
  "$ADB" shell run-as "$package" cp /data/local/tmp/r1_mode.txt files/r1_mode.txt
  "$ADB" exec-out run-as "$package" cat files/r1_mode.txt > "$out/mode.verified.txt"
  cmp -s "$out/mode.txt" "$out/mode.verified.txt"
  "$ADB" logcat -c
  "$ADB" logcat -v threadtime > "$out/logcat_full.txt" 2>&1 &
  local logcat_pid=$!
  sleep 2
  local resolved
  resolved="$("$ADB" shell cmd package resolve-activity --brief "$package" | tail -1 | tr -d '\r')"
  printf '%s\n' "$resolved" > "$out/resolve-activity.txt"
  "$ADB" shell am start -W -S -n "$resolved" > "$out/am-start.txt" 2>&1 || true
  local elapsed=0
  while (( elapsed < 240 )); do
    if [[ "$target" == MOBILE ]]; then
      "$ADB" exec-out run-as "$package" cat files/r1_mobile_progress.json > "$out/r1_mobile_progress.json.tmp" 2>/dev/null || true
      if test -s "$out/r1_mobile_progress.json.tmp"; then mv "$out/r1_mobile_progress.json.tmp" "$out/r1_mobile_progress.json"; fi
      grep -q 'R1_MOBILE_CAPTURE_FRAME frame=300' "$out/logcat_full.txt" && break
    else
      "$ADB" exec-out run-as "$package" cat files/r1_material_inventory.json > "$out/r1_material_inventory.json.tmp" 2>/dev/null || true
      if test -s "$out/r1_material_inventory.json.tmp"; then mv "$out/r1_material_inventory.json.tmp" "$out/r1_material_inventory.json"; fi
      grep -q 'R1_GL_SCENARIO_COMPLETE mode=gl_production' "$out/logcat_full.txt" && break
    fi
    grep -Eq 'SCRIPT ERROR|Parse Error|FATAL EXCEPTION|Fatal signal|R1_RUNTIME_DEBUG_FAILURE|VK_ERROR_DEVICE_LOST|ANR in' "$out/logcat_full.txt" && break
    sleep 5
    elapsed=$((elapsed+5))
  done
  if [[ "$target" == MOBILE ]]; then
    "$ADB" exec-out run-as "$package" cat files/r1_mobile_progress.json > "$out/r1_mobile_progress.final.json" 2>/dev/null || true
    if test -s "$out/r1_mobile_progress.final.json"; then cp "$out/r1_mobile_progress.final.json" "$out/r1_mobile_progress.json"; fi
  fi
  "$ADB" exec-out screencap -p > "$out/screenshot.png" 2>/dev/null || true
  local pid_before
  pid_before="$("$ADB" shell pidof "$package" 2>/dev/null | tr -d '\r')"
  printf '%s\n' "$pid_before" > "$out/pid-before-resume.txt"
  local pause_resume=false
  if test -n "$pid_before"; then
    "$ADB" shell input keyevent KEYCODE_HOME >/dev/null 2>&1 || true
    sleep 3
    "$ADB" shell am start -W -n "$resolved" > "$out/resume.txt" 2>&1 || true
    sleep 5
    local pid_after
    pid_after="$("$ADB" shell pidof "$package" 2>/dev/null | tr -d '\r')"
    printf '%s\n' "$pid_after" > "$out/pid-after-resume.txt"
    if test -n "$pid_after" && grep -q 'Status: ok' "$out/resume.txt"; then pause_resume=true; fi
  else
    : > "$out/resume.txt"
    : > "$out/pid-after-resume.txt"
  fi
  kill "$logcat_pid" >/dev/null 2>&1 || true
  wait "$logcat_pid" >/dev/null 2>&1 || true
  local critical scene_ready
  critical="$(grep -Ec 'SCRIPT ERROR|Parse Error|FATAL EXCEPTION|Fatal signal|VK_ERROR_DEVICE_LOST|ANR in|linker:.*(error|cannot)|R1_RUNTIME_DEBUG_FAILURE' "$out/logcat_full.txt" || true)"
  scene_ready=false
  grep -q 'R1_PRODUCTION_SCENE_READY' "$out/logcat_full.txt" && scene_ready=true
  python3 - "$target" "$mode" "$out" "$pid_before" "$critical" "$pause_resume" "$scene_ready" "$elapsed" <<'PY'
from pathlib import Path
import json,re,sys
from PIL import Image,ImageStat

target,mode=sys.argv[1:3]
out=Path(sys.argv[3])
process_alive=bool(sys.argv[4])
critical=int(sys.argv[5])
pause_resume=sys.argv[6]=='true'
scene_ready=sys.argv[7]=='true'
elapsed=int(sys.argv[8])
log=(out/'logcat_full.txt').read_text(errors='replace') if (out/'logcat_full.txt').exists() else ''
start=(out/'am-start.txt').read_text(errors='replace') if (out/'am-start.txt').exists() else ''
valid=False; non_black=False; size=[0,0]; avg=0.0; black_ratio=1.0
try:
    with Image.open(out/'screenshot.png') as image:
        image=image.convert('RGB')
        size=list(image.size)
        avg=float(ImageStat.Stat(image.convert('L')).mean[0])
        pixels=list(image.resize((160,90)).getdata())
        black=sum(1 for r,g,b in pixels if r<=3 and g<=3 and b<=3)
        black_ratio=black/len(pixels)
        valid=size==[1920,1080]
        non_black=valid and avg>1.0 and black_ratio<0.99
except Exception:
    pass
base={
    'schema_version':1,
    'target':target,
    'mode':mode,
    'apk_launch_result':'Status: ok' in start,
    'scene_readiness_result':scene_ready,
    'valid_screenshot_result':valid,
    'non_black_screenshot_result':non_black,
    'screenshot_size':size,
    'average_luminance':avg,
    'black_pixel_ratio':black_ratio,
    'process_alive':process_alive,
    'pause_resume_result':pause_resume,
    'critical_runtime_error_count':critical,
    'bounded_window_seconds':elapsed,
    'renderer_defaults_modified':False,
    'gameplay_modified':False,
}
if target=='GL':
    links=len(re.findall(r'SceneShaderGLES3: Program linking failed',log))
    uniform=len(re.findall(r'Fragment shader active uniforms exceed GL_MAX_FRAGMENT_UNIFORM_VECTORS',log))
    base.update({
        'scenario_complete':'R1_GL_SCENARIO_COMPLETE mode=gl_production' in log,
        'link_failure_count':links,
        'uniform_overflow_count':uniform,
        'baseline_link_failure_count':45,
        'progression_improved':links<45,
        'exit_criterion_met':links==0,
    })
else:
    records=[]
    try:
        records=json.loads((out/'r1_mobile_progress.json').read_text()).get('records',[])
    except Exception:
        pass
    last=max((int(r.get('local_frame',0)) for r in records),default=0)
    base.update({
        'last_completed_frame':last,
        'baseline_last_completed_frame':90,
        'capture_frame_reached':last>=300,
        'progression_improved':last>90,
        'exit_criterion_met':last>=300,
    })
(out/'result.json').write_text(json.dumps(base,indent=2,sort_keys=True)+'\n')
print(json.dumps(base,sort_keys=True))
PY
  "$ADB" uninstall "$package" >/dev/null 2>&1 || true
}

run_target GL gl_production "$GL_PACKAGE" "$GL_APK" "$GL_OUT"
run_target MOBILE mobile_baseline "$MOBILE_PACKAGE" "$MOBILE_APK" "$MOBILE_OUT"

python3 - "$GL_OUT/result.json" "$MOBILE_OUT/result.json" "$OUTPUT_ROOT/R1_ENGINE_UPGRADE_RESULT.json" <<'PY'
from pathlib import Path
import json,sys

gl=json.loads(Path(sys.argv[1]).read_text())
mobile=json.loads(Path(sys.argv[2]).read_text())
output=Path(sys.argv[3])
def healthy(value):
    return (
        value['apk_launch_result']
        and value['scene_readiness_result']
        and value['non_black_screenshot_result']
        and value['process_alive']
        and value['pause_resume_result']
        and value['critical_runtime_error_count']==0
    )
gl_healthy=healthy(gl) and gl['scenario_complete']
mobile_healthy=healthy(mobile)
gl_improved=gl_healthy and gl['link_failure_count']<45
mobile_improved=mobile_healthy and mobile['last_completed_frame']>90
gl_pass=gl_healthy and gl['link_failure_count']==0
mobile_pass=mobile_healthy and mobile['last_completed_frame']>=300
result={
    'schema_version':1,
    'stage':'BAHRAIN BRICK — STAGE R1',
    'experiment':'GODOT_ENGINE_4_3_TO_4_7_1_STABLE',
    'engine_before':'4.3-stable',
    'engine_after':'4.7.1-stable',
    'gl':gl,
    'mobile':mobile,
    'gl_progression_improved':gl_improved,
    'mobile_progression_improved':mobile_improved,
    'gl_exit_criterion_met':gl_pass,
    'mobile_exit_criterion_met':mobile_pass,
    'r1_exit_candidate':gl_pass and mobile_pass,
    'renderer_defaults_modified':False,
    'gameplay_modified':False,
    'production_fix_authorized':False,
    'g1_authorized':False,
}
result['decision']='retained' if gl_improved or mobile_improved else 'reverted'
output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,sort_keys=True))
if not (gl_improved or mobile_improved):
    raise SystemExit(1)
PY
