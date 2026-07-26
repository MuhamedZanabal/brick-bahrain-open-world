#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:?repository root is required}"
OUTPUT_ROOT="${2:?output root is required}"
RECONSTRUCTION="$OUTPUT_ROOT/reconstruction"
GAME="$RECONSTRUCTION/game"
RAW="$OUTPUT_ROOT/raw"
GL_OUT="$RAW/gl_production"
MOBILE_OUT="$RAW/mobile_baseline"
GL_PROJECT="$OUTPUT_ROOT/gl-project"
MOBILE_PROJECT="$OUTPUT_ROOT/mobile-project"
GODOT_DIR="$OUTPUT_ROOT/godot-4.7.1"
TEMPLATE_DIR="$OUTPUT_ROOT/templates-4.7.1"
XDG_DATA_HOME="$OUTPUT_ROOT/godot-user-data"
APK_DIR="$OUTPUT_ROOT/apks"
AVD_HOME="$OUTPUT_ROOT/avd-home"
EMULATOR_HOME="$OUTPUT_ROOT/emulator-home"
AVD_NAME="bahrain_brick_r1_fix_api34"
GL_PACKAGE="com.brickbahrain.r1fixgl"
MOBILE_PACKAGE="com.brickbahrain.r1fixmobile"
GL_APK="$APK_DIR/bahrain-brick-r1-fix-gl-x86_64.apk"
MOBILE_APK="$APK_DIR/bahrain-brick-r1-fix-mobile-x86_64.apk"
GODOT_RELEASE="4.7.1-stable"
GODOT_VERSION="4.7.1"
GODOT_ZIP="Godot_v${GODOT_RELEASE}_linux.x86_64.zip"
TEMPLATE_ARCHIVE="Godot_v${GODOT_RELEASE}_export_templates.tpz"
RELEASE_ROOT="https://github.com/godotengine/godot-builds/releases/download/${GODOT_RELEASE}"

mkdir -p "$OUTPUT_ROOT" "$RAW" "$GL_OUT" "$MOBILE_OUT" "$GODOT_DIR" "$TEMPLATE_DIR" "$XDG_DATA_HOME" "$APK_DIR" "$AVD_HOME" "$EMULATOR_HOME"

for required in \
  "$REPO_ROOT/authority/manama_souq_composite_source.json" \
  "$REPO_ROOT/tools/vertical_slice/reconstruct_manama_souq_composite.sh" \
  "$REPO_ROOT/tools/graphics/patch_r1_reconstruction_preflight.py" \
  "$REPO_ROOT/tools/graphics/prepare_r1_android_variant.py" \
  "$REPO_ROOT/tests/graphics/r1_renderer_runtime_debug.gd" \
  "$REPO_ROOT/tests/graphics/r1_renderer_runtime_debug.tscn" \
  "$REPO_ROOT/debug.keystore"; do
  test -f "$required"
done

SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
test -n "$SDK_ROOT"
ADB="$SDK_ROOT/platform-tools/adb"
EMULATOR="$SDK_ROOT/emulator/emulator"
AVDMANAGER="$(find "$SDK_ROOT/cmdline-tools" -type f -path '*/bin/avdmanager' | sort | tail -1)"
APKSIGNER="$SDK_ROOT/build-tools/34.0.0/apksigner"
for tool in "$ADB" "$EMULATOR" "$AVDMANAGER" "$APKSIGNER"; do test -x "$tool"; done

# Reconstruct accepted production source; alter only the obsolete hosted-runner assertion
# in a temporary script, then reverify the output against FINAL_TREE_MANIFEST.
rm -rf "$RECONSTRUCTION"
RECONSTRUCTION_SCRIPT="$OUTPUT_ROOT/reconstruct_manama_souq_composite.r1.sh"
python3 - "$REPO_ROOT/tools/vertical_slice/reconstruct_manama_souq_composite.sh" "$RECONSTRUCTION_SCRIPT" "$OUTPUT_ROOT/R1_RECONSTRUCTION_ENVIRONMENT.json" <<'PY'
from pathlib import Path
import json, os, sys
source=Path(sys.argv[1]); target=Path(sys.argv[2]); report=Path(sys.argv[3])
text=source.read_text()
old='test "${ImageVersion:-}" = "20260714.240.1"'
new='test "${ImageVersion:-}" = "${R1_ACTUAL_IMAGE_VERSION:?R1 actual image version required}"'
if text.count(old) != 1: raise SystemExit('historical runner-image assertion not found exactly once')
target.write_text(text.replace(old,new)); target.chmod(0o755)
actual=os.environ.get('ImageVersion','')
report.write_text(json.dumps({'schema_version':1,'historical_expected':'20260714.240.1','actual':actual,'production_source_modified':False},indent=2,sort_keys=True)+'\n')
if not actual: raise SystemExit('ImageVersion is unavailable')
PY
R1_ACTUAL_IMAGE_VERSION="${ImageVersion:-}" bash "$RECONSTRUCTION_SCRIPT" \
  A "$RECONSTRUCTION" "$REPO_ROOT/authority/manama_souq_composite_source.json" "$(git -C "$REPO_ROOT" rev-parse HEAD)"
python3 "$REPO_ROOT/tools/graphics/patch_r1_reconstruction_preflight.py" \
  --manifest "$RECONSTRUCTION/evidence/FINAL_TREE_MANIFEST.json" --game "$GAME" --output "$OUTPUT_ROOT/SOURCE_TREE_EQUIVALENCE.json"

mkdir -p "$GAME/tests/graphics"
cp "$REPO_ROOT/tests/graphics/r1_renderer_runtime_debug.gd" "$GAME/tests/graphics/"
cp "$REPO_ROOT/tests/graphics/r1_renderer_runtime_debug.tscn" "$GAME/tests/graphics/"

# Production runtime/export correction: current stable Godot 4.7.1, verified against official SHA-512 sums.
curl --fail --location --retry 5 --retry-all-errors "$RELEASE_ROOT/SHA512-SUMS.txt" -o "$OUTPUT_ROOT/SHA512-SUMS.txt"
curl --fail --location --retry 5 --retry-all-errors "$RELEASE_ROOT/$GODOT_ZIP" -o "$OUTPUT_ROOT/$GODOT_ZIP"
curl --fail --location --retry 5 --retry-all-errors "$RELEASE_ROOT/$TEMPLATE_ARCHIVE" -o "$OUTPUT_ROOT/$TEMPLATE_ARCHIVE"
for artifact in "$GODOT_ZIP" "$TEMPLATE_ARCHIVE"; do
  expected="$(awk -v name="$artifact" '$NF == name || $NF == "*" name {print $1; exit}' "$OUTPUT_ROOT/SHA512-SUMS.txt")"
  test -n "$expected"
  printf '%s  %s\n' "$expected" "$OUTPUT_ROOT/$artifact" | sha512sum -c -
done
unzip -q "$OUTPUT_ROOT/$GODOT_ZIP" -d "$GODOT_DIR"
GODOT="$(find "$GODOT_DIR" -maxdepth 1 -type f -name 'Godot*' | head -1)"
test -n "$GODOT"; chmod +x "$GODOT"
"$GODOT" --version | tee "$OUTPUT_ROOT/GODOT_VERSION.txt"
grep -q '^4\.7\.1\.' "$OUTPUT_ROOT/GODOT_VERSION.txt"

rm -rf "$GAME/.godot" "$GL_PROJECT" "$MOBILE_PROJECT"
LIBGL_ALWAYS_SOFTWARE=1 timeout --signal=TERM --kill-after=30s 1800s \
  xvfb-run -a -s '-screen 0 1920x1080x24' "$GODOT" --path "$GAME" --editor --import --quit --verbose \
  --rendering-method gl_compatibility --rendering-driver opengl3 2>&1 | tee "$OUTPUT_ROOT/shared-import.log"
test -d "$GAME/.godot/imported"
cp -a "$GAME" "$GL_PROJECT"
cp -a "$GAME" "$MOBILE_PROJECT"
python3 "$REPO_ROOT/tools/graphics/prepare_r1_android_variant.py" --project "$GL_PROJECT/project.godot" --preset "$GL_PROJECT/export_presets.cfg" --renderer gl_compatibility --package-name "$GL_PACKAGE" --report "$OUTPUT_ROOT/GL_VARIANT_OVERRIDE.json"
python3 "$REPO_ROOT/tools/graphics/prepare_r1_android_variant.py" --project "$MOBILE_PROJECT/project.godot" --preset "$MOBILE_PROJECT/export_presets.cfg" --renderer mobile --package-name "$MOBILE_PACKAGE" --report "$OUTPUT_ROOT/MOBILE_VARIANT_OVERRIDE.json"

rm -rf "$TEMPLATE_DIR/unpacked"; mkdir -p "$TEMPLATE_DIR/unpacked"
unzip -q "$OUTPUT_ROOT/$TEMPLATE_ARCHIVE" -d "$TEMPLATE_DIR/unpacked"
TEMPLATE_VERSION="$(cut -d. -f1-4 "$OUTPUT_ROOT/GODOT_VERSION.txt")"
TEMPLATE_INSTALL="$XDG_DATA_HOME/godot/export_templates/$TEMPLATE_VERSION"
mkdir -p "$TEMPLATE_INSTALL"
cp -a "$TEMPLATE_DIR/unpacked/templates/." "$TEMPLATE_INSTALL/"
test -f "$TEMPLATE_INSTALL/android_debug.apk"

export_apk() {
  local project="$1" apk="$2" log="$3"
  rm -f "$apk"
  XDG_DATA_HOME="$XDG_DATA_HOME" GODOT_ANDROID_KEYSTORE_DEBUG_PATH="$REPO_ROOT/debug.keystore" \
  GODOT_ANDROID_KEYSTORE_DEBUG_USER=androiddebugkey GODOT_ANDROID_KEYSTORE_DEBUG_PASSWORD=android \
  timeout --signal=TERM --kill-after=30s 1800s "$GODOT" --headless --path "$project" --verbose --export-debug Android "$apk" 2>&1 | tee "$log"
  test -s "$apk"
  "$APKSIGNER" verify --verbose --print-certs "$apk" > "${log%.log}-signing.txt"
}
export_apk "$GL_PROJECT" "$GL_APK" "$OUTPUT_ROOT/gl-export.log"
export_apk "$MOBILE_PROJECT" "$MOBILE_APK" "$OUTPUT_ROOT/mobile-export.log"
sha256sum "$GL_APK" "$MOBILE_APK" > "$OUTPUT_ROOT/APK_SHA256SUMS.txt"

export ANDROID_AVD_HOME="$AVD_HOME" ANDROID_EMULATOR_HOME="$EMULATOR_HOME"
rm -rf "$AVD_HOME"/* "$EMULATOR_HOME"/*
echo no | "$AVDMANAGER" create avd --force --name "$AVD_NAME" --package 'system-images;android-34;default;x86_64' --device 'pixel_6' > "$OUTPUT_ROOT/avd-create.txt" 2>&1
nohup "$EMULATOR" "@$AVD_NAME" -no-window -no-audio -no-boot-anim -no-snapshot -wipe-data -gpu swiftshader -accel auto -memory 4096 -cores 4 -camera-back none -camera-front none > "$OUTPUT_ROOT/emulator.log" 2>&1 &
EMULATOR_PID=$!
cleanup() { "$ADB" emu kill >/dev/null 2>&1 || true; kill "$EMULATOR_PID" >/dev/null 2>&1 || true; }
trap cleanup EXIT
"$ADB" wait-for-device
booted=false
for _attempt in $(seq 1 240); do
  if [[ "$("$ADB" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == 1 ]]; then booted=true; break; fi
  sleep 2
done
test "$booted" = true
"$ADB" shell settings put system accelerometer_rotation 0 >/dev/null
"$ADB" shell settings put system user_rotation 1 >/dev/null
"$ADB" shell wm size 1920x1080 >/dev/null
"$ADB" shell wm density 420 >/dev/null

write_mode_file() {
  local package="$1" mode="$2" local_file="$OUTPUT_ROOT/r1-mode-${package//./_}.txt"
  printf '%s' "$mode" > "$local_file"
  "$ADB" push "$local_file" /data/local/tmp/r1_mode.txt >/dev/null
  "$ADB" shell run-as "$package" mkdir -p files
  "$ADB" shell run-as "$package" cp /data/local/tmp/r1_mode.txt files/r1_mode.txt
  "$ADB" exec-out run-as "$package" cat files/r1_mode.txt > "$local_file.verified"
  cmp -s "$local_file" "$local_file.verified"
  "$ADB" shell rm -f /data/local/tmp/r1_mode.txt
}
validate_png() {
  python3 - "$1" <<'PY'
from pathlib import Path
import struct,sys
p=Path(sys.argv[1]); data=p.read_bytes()
if len(data)<24 or data[:8]!=b'\x89PNG\r\n\x1a\n': raise SystemExit(1)
w,h=struct.unpack('>II',data[16:24])
if w<320 or h<240: raise SystemExit(1)
print(f'{w}x{h} bytes={len(data)}')
PY
}
run_target() {
  local name="$1" mode="$2" package="$3" apk="$4" marker="$5" timeout_seconds="$6" out="$7"
  "$ADB" uninstall "$package" > "$out/uninstall.txt" 2>&1 || true
  "$ADB" install -r -t "$apk" > "$out/install.txt" 2>&1
  "$ADB" shell pm clear "$package" > "$out/pm-clear.txt" 2>&1 || true
  write_mode_file "$package" "$mode"
  "$ADB" logcat -c
  "$ADB" logcat -v threadtime > "$out/logcat_full.txt" 2>&1 &
  local logcat_pid=$!; sleep 2
  local resolved completed=false elapsed=0
  resolved="$("$ADB" shell cmd package resolve-activity --brief "$package" | tail -1 | tr -d '\r')"
  printf '%s\n' "$resolved" > "$out/resolve-activity.txt"
  "$ADB" shell am start -W -S -n "$resolved" > "$out/am-start.txt" 2>&1 || true
  while (( elapsed < timeout_seconds )); do
    if grep -q "$marker" "$out/logcat_full.txt"; then completed=true; break; fi
    if grep -Eq 'SCRIPT ERROR|Parse Error|FATAL EXCEPTION|Fatal signal|VK_ERROR_DEVICE_LOST|R1_RUNTIME_DEBUG_FAILURE' "$out/logcat_full.txt"; then break; fi
    sleep 2; elapsed=$((elapsed+2))
  done
  "$ADB" exec-out screencap -p > "$out/screenshot.png" 2>/dev/null || true
  validate_png "$out/screenshot.png" > "$out/screenshot-validation.txt"
  local pid alive=false overflow_count critical_count last_frame
  pid="$("$ADB" shell pidof "$package" 2>/dev/null | tr -d '\r')"; test -n "$pid" && alive=true
  printf '%s\n' "$pid" > "$out/pid-final.txt"
  kill "$logcat_pid" >/dev/null 2>&1 || true; wait "$logcat_pid" >/dev/null 2>&1 || true
  grep -Ei 'SCRIPT ERROR|Parse Error|Invalid call|FATAL EXCEPTION|Fatal signal|VK_ERROR_DEVICE_LOST|GPU hang|ANR in |SceneShaderGLES3|Program linking failed|GL_MAX_FRAGMENT_UNIFORM_VECTORS' "$out/logcat_full.txt" > "$out/critical_log.txt" || true
  overflow_count="$(grep -c 'Fragment shader active uniforms exceed GL_MAX_FRAGMENT_UNIFORM_VECTORS' "$out/logcat_full.txt" || true)"
  critical_count="$(wc -l < "$out/critical_log.txt" | tr -d ' ')"
  last_frame="$(grep -oE 'local_frame=[0-9]+' "$out/logcat_full.txt" | tail -1 | cut -d= -f2 || true)"
  python3 - "$out/result.json" "$name" "$mode" "$completed" "$elapsed" "$alive" "$overflow_count" "$critical_count" "${last_frame:-0}" <<'PY'
from pathlib import Path
import json,sys
Path(sys.argv[1]).write_text(json.dumps({'schema_version':1,'target':sys.argv[2],'mode':sys.argv[3],'marker_reached':sys.argv[4]=='true','elapsed_seconds':int(sys.argv[5]),'process_alive':sys.argv[6]=='true','shader_uniform_overflow_count':int(sys.argv[7]),'critical_log_line_count':int(sys.argv[8]),'last_mobile_frame':int(sys.argv[9])},indent=2,sort_keys=True)+'\n')
PY
}

run_target GL gl_production "$GL_PACKAGE" "$GL_APK" 'R1_GL_SCENARIO_COMPLETE mode=gl_production' 300 "$GL_OUT"
run_target MOBILE mobile_baseline "$MOBILE_PACKAGE" "$MOBILE_APK" 'R1_MOBILE_CAPTURE_FRAME frame=300' 900 "$MOBILE_OUT"
python3 - "$OUTPUT_ROOT" <<'PY'
from pathlib import Path
import json,sys
root=Path(sys.argv[1]); gl=json.loads((root/'raw/gl_production/result.json').read_text()); mobile=json.loads((root/'raw/mobile_baseline/result.json').read_text())
result={'schema_version':1,'engine_fix':'GODOT_4_7_1_RUNTIME_UPGRADE','renderer_defaults_modified':False,'gameplay_modified':False,'gl':gl,'mobile':mobile}
result['gl_passed']=gl['marker_reached'] and gl['process_alive'] and gl['shader_uniform_overflow_count']==0 and gl['critical_log_line_count']==0
result['mobile_passed']=mobile['marker_reached'] and mobile['process_alive'] and mobile['last_mobile_frame']>=300 and mobile['critical_log_line_count']==0
result['passed']=result['gl_passed'] and result['mobile_passed']
(root/'R1_ENGINE_UPGRADE_RESULT.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
if not result['passed']: raise SystemExit(json.dumps(result,sort_keys=True))
PY
