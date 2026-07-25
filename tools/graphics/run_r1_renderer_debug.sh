#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:?repository root is required}"
OUTPUT_ROOT="${2:?output root is required}"
RECONSTRUCTION="$OUTPUT_ROOT/reconstruction"
GAME="$RECONSTRUCTION/game"
RAW="$OUTPUT_ROOT/raw"
REPORTS="$OUTPUT_ROOT/reports/graphics/r1"
SHARED="$OUTPUT_ROOT/shared-import"
GL_PROJECT="$OUTPUT_ROOT/gl-project"
MOBILE_PROJECT="$OUTPUT_ROOT/mobile-project"
APK_DIR="$OUTPUT_ROOT/apks"
GODOT_DIR="$OUTPUT_ROOT/godot"
TEMPLATE_DIR="$OUTPUT_ROOT/templates"
XDG_DATA_HOME="$OUTPUT_ROOT/godot-user-data"
AVD_HOME="$OUTPUT_ROOT/avd-home"
EMULATOR_HOME="$OUTPUT_ROOT/emulator-home"
AVD_NAME="bahrain_brick_r1_api34"
GL_PACKAGE="com.brickbahrain.r1gl"
MOBILE_PACKAGE="com.brickbahrain.r1mobile"
GL_APK="$APK_DIR/bahrain-brick-r1-gl-debug-x86_64.apk"
MOBILE_APK="$APK_DIR/bahrain-brick-r1-mobile-debug-x86_64.apk"
GL_MODES=(gl_unshaded gl_empty gl_sun gl_sun_shadow gl_two_directional gl_two_directional_shadow gl_production)
MOBILE_MODES=(mobile_baseline mobile_render_disabled_control)

mkdir -p "$OUTPUT_ROOT" "$RAW/track_a" "$RAW/track_b" "$REPORTS" "$APK_DIR" "$GODOT_DIR" "$TEMPLATE_DIR" "$XDG_DATA_HOME" "$AVD_HOME" "$EMULATOR_HOME"

for required in \
  "$REPO_ROOT/authority/manama_souq_composite_source.json" \
  "$REPO_ROOT/tools/vertical_slice/reconstruct_manama_souq_composite.sh" \
  "$REPO_ROOT/tests/graphics/r1_renderer_runtime_debug.gd" \
  "$REPO_ROOT/tests/graphics/r1_renderer_runtime_debug.tscn" \
  "$REPO_ROOT/tools/graphics/prepare_r1_android_variant.py" \
  "$REPO_ROOT/tools/graphics/finalize_r1_renderer_debug.py" \
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

# Reconstruct the accepted source authority exactly once. R1 adds only a test harness before import.
rm -rf "$RECONSTRUCTION"
bash "$REPO_ROOT/tools/vertical_slice/reconstruct_manama_souq_composite.sh" \
  A "$RECONSTRUCTION" "$REPO_ROOT/authority/manama_souq_composite_source.json" "$(git -C "$REPO_ROOT" rev-parse HEAD)"
test -f "$GAME/project.godot"
test -f "$GAME/export_presets.cfg"

mkdir -p "$GAME/tests/graphics"
cp "$REPO_ROOT/tests/graphics/r1_renderer_runtime_debug.gd" "$GAME/tests/graphics/"
cp "$REPO_ROOT/tests/graphics/r1_renderer_runtime_debug.tscn" "$GAME/tests/graphics/"
python3 - "$REPO_ROOT" "$GAME" "$OUTPUT_ROOT/HARNESS_INJECTION.json" <<'PY'
from pathlib import Path
import hashlib,json,sys
repo=Path(sys.argv[1]); game=Path(sys.argv[2]); out=Path(sys.argv[3]); items=[]
for name in ('r1_renderer_runtime_debug.gd','r1_renderer_runtime_debug.tscn'):
    source=repo/'tests/graphics'/name; injected=game/'tests/graphics'/name
    a=source.read_bytes(); b=injected.read_bytes()
    items.append({'path':f'tests/graphics/{name}','source_sha256':hashlib.sha256(a).hexdigest(),'injected_sha256':hashlib.sha256(b).hexdigest(),'equal':a==b,'test_only':True})
payload={'schema_version':1,'items':items,'all_equal':all(item['equal'] for item in items),'production_source_modified':False}
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
if not payload['all_equal']: raise SystemExit(1)
PY

unzip -q "$RECONSTRUCTION/downloads/Godot_v4.3-stable_linux.x86_64.zip" -d "$GODOT_DIR"
GODOT="$(find "$GODOT_DIR" -maxdepth 1 -type f -name 'Godot*' | head -1)"
test -n "$GODOT"
chmod +x "$GODOT"
"$GODOT" --version > "$OUTPUT_ROOT/GODOT_VERSION.txt"

# One imported state, then byte-identical renderer clones.
rm -rf "$GAME/.godot" "$SHARED" "$GL_PROJECT" "$MOBILE_PROJECT"
LIBGL_ALWAYS_SOFTWARE=1 timeout --signal=TERM --kill-after=30s 1200s \
  xvfb-run -a -s '-screen 0 1920x1080x24' \
  "$GODOT" --path "$GAME" --editor --import --quit --verbose \
  --rendering-method gl_compatibility --rendering-driver opengl3 \
  2>&1 | tee "$OUTPUT_ROOT/shared-import.log"
test -d "$GAME/.godot/imported"
cp -a "$GAME" "$SHARED"
cp -a "$SHARED" "$GL_PROJECT"
cp -a "$SHARED" "$MOBILE_PROJECT"

manifest_tree() {
  python3 - "$1" "$2" <<'PY'
from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1]); out=Path(sys.argv[2]); files=[]; aggregate=hashlib.sha256()
for path in sorted(p for p in root.rglob('*') if p.is_file()):
    data=path.read_bytes(); rel=path.relative_to(root).as_posix(); sha=hashlib.sha256(data).hexdigest()
    files.append({'path':rel,'bytes':len(data),'sha256':sha})
    aggregate.update(rel.encode()); aggregate.update(b'\0'); aggregate.update(sha.encode()); aggregate.update(b'\n')
out.write_text(json.dumps({'schema_version':1,'file_count':len(files),'aggregate_bytes':sum(x['bytes'] for x in files),'aggregate_sha256':aggregate.hexdigest(),'files':files},indent=2,sort_keys=True)+'\n')
PY
}
manifest_tree "$SHARED" "$OUTPUT_ROOT/IMPORTED_STATE_MANIFEST.json"
manifest_tree "$GL_PROJECT" "$OUTPUT_ROOT/GL_CLONE_PRE_OVERRIDE.json"
manifest_tree "$MOBILE_PROJECT" "$OUTPUT_ROOT/MOBILE_CLONE_PRE_OVERRIDE.json"
python3 - "$OUTPUT_ROOT" <<'PY'
from pathlib import Path
import json,sys
root=Path(sys.argv[1]); names=('IMPORTED_STATE_MANIFEST.json','GL_CLONE_PRE_OVERRIDE.json','MOBILE_CLONE_PRE_OVERRIDE.json')
items=[json.loads((root/name).read_text()) for name in names]
passed=len({item['aggregate_sha256'] for item in items})==1
(root/'CLONE_IDENTITY.json').write_text(json.dumps({'schema_version':1,'passed':passed,'roots':items},indent=2,sort_keys=True)+'\n')
if not passed: raise SystemExit(1)
PY

python3 "$REPO_ROOT/tools/graphics/prepare_r1_android_variant.py" \
  --project "$GL_PROJECT/project.godot" --preset "$GL_PROJECT/export_presets.cfg" \
  --renderer gl_compatibility --package-name "$GL_PACKAGE" --report "$OUTPUT_ROOT/GL_VARIANT_OVERRIDE.json"
python3 "$REPO_ROOT/tools/graphics/prepare_r1_android_variant.py" \
  --project "$MOBILE_PROJECT/project.godot" --preset "$MOBILE_PROJECT/export_presets.cfg" \
  --renderer mobile --package-name "$MOBILE_PACKAGE" --report "$OUTPUT_ROOT/MOBILE_VARIANT_OVERRIDE.json"

# Install official checksum-verified Godot 4.3 export templates.
TEMPLATE_NAME="Godot_v4.3-stable_export_templates.tpz"
TEMPLATE_URL="https://github.com/godotengine/godot-builds/releases/download/4.3-stable/$TEMPLATE_NAME"
SUMS_URL="https://github.com/godotengine/godot-builds/releases/download/4.3-stable/SHA512-SUMS.txt"
curl --fail --location --retry 5 --retry-all-errors "$SUMS_URL" -o "$TEMPLATE_DIR/SHA512-SUMS.txt"
curl --fail --location --retry 5 --retry-all-errors "$TEMPLATE_URL" -o "$TEMPLATE_DIR/$TEMPLATE_NAME"
EXPECTED_TEMPLATE_SHA512="$(python3 - "$TEMPLATE_DIR/SHA512-SUMS.txt" "$TEMPLATE_NAME" <<'PY'
from pathlib import Path
import sys
for line in Path(sys.argv[1]).read_text().splitlines():
    parts=line.split()
    if len(parts)>=2 and parts[-1].lstrip('*./')==sys.argv[2]:
        print(parts[0]); break
else: raise SystemExit('template checksum missing')
PY
)"
printf '%s  %s\n' "$EXPECTED_TEMPLATE_SHA512" "$TEMPLATE_DIR/$TEMPLATE_NAME" | sha512sum -c -
mkdir -p "$TEMPLATE_DIR/unpacked"
unzip -q "$TEMPLATE_DIR/$TEMPLATE_NAME" -d "$TEMPLATE_DIR/unpacked"
TEMPLATE_INSTALL="$XDG_DATA_HOME/godot/export_templates/4.3.stable"
mkdir -p "$TEMPLATE_INSTALL"
cp -a "$TEMPLATE_DIR/unpacked/templates/." "$TEMPLATE_INSTALL/"
test -f "$TEMPLATE_INSTALL/android_debug.apk"

export_apk() {
  local project="$1" apk="$2" log="$3"
  rm -f "$apk"
  set +e
  XDG_DATA_HOME="$XDG_DATA_HOME" \
  GODOT_ANDROID_KEYSTORE_DEBUG_PATH="$REPO_ROOT/debug.keystore" \
  GODOT_ANDROID_KEYSTORE_DEBUG_USER=androiddebugkey \
  GODOT_ANDROID_KEYSTORE_DEBUG_PASSWORD=android \
  timeout --signal=TERM --kill-after=30s 1800s \
  "$GODOT" --headless --path "$project" --verbose --export-debug Android "$apk" \
    2>&1 | tee "$log"
  local code=${PIPESTATUS[0]}
  set -e
  test "$code" -eq 0
  test -s "$apk"
  "$APKSIGNER" verify --verbose --print-certs "$apk" > "${log%.log}-signing.txt"
}
export_apk "$GL_PROJECT" "$GL_APK" "$OUTPUT_ROOT/gl-export.log"
export_apk "$MOBILE_PROJECT" "$MOBILE_APK" "$OUTPUT_ROOT/mobile-export.log"
sha256sum "$GL_APK" "$MOBILE_APK" > "$OUTPUT_ROOT/APK_SHA256SUMS.txt"

export ANDROID_AVD_HOME="$AVD_HOME"
export ANDROID_EMULATOR_HOME="$EMULATOR_HOME"
rm -rf "$AVD_HOME"/* "$EMULATOR_HOME"/*
echo no | "$AVDMANAGER" create avd --force --name "$AVD_NAME" --package 'system-images;android-34;default;x86_64' --device 'pixel_6' > "$OUTPUT_ROOT/avd-create.txt" 2>&1
nohup "$EMULATOR" "@$AVD_NAME" -no-window -no-audio -no-boot-anim -no-snapshot -wipe-data \
  -gpu swiftshader -accel auto -memory 4096 -cores 4 -camera-back none -camera-front none \
  > "$OUTPUT_ROOT/emulator.log" 2>&1 &
EMULATOR_PID=$!
cleanup() {
  "$ADB" emu kill >/dev/null 2>&1 || true
  kill "$EMULATOR_PID" >/dev/null 2>&1 || true
}
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
"$ADB" shell wm size 1920x1080 > "$OUTPUT_ROOT/wm-size.txt"
"$ADB" shell wm density 420 > "$OUTPUT_ROOT/wm-density.txt"
"$ADB" shell dumpsys SurfaceFlinger > "$OUTPUT_ROOT/surfaceflinger.txt" 2>&1 || true

write_mode_file() {
  local package="$1" mode="$2"
  "$ADB" shell run-as "$package" sh -c "mkdir -p files && printf '%s' '$mode' > files/r1_mode.txt"
}

pull_user_file() {
  local package="$1" remote_name="$2" local_path="$3"
  "$ADB" exec-out run-as "$package" cat "files/$remote_name" > "$local_path" 2>/dev/null || true
  [[ -s "$local_path" ]] || rm -f "$local_path"
}

capture_process_diagnostics() {
  local package="$1" out="$2" label="$3"
  local pid
  pid="$("$ADB" shell pidof "$package" 2>/dev/null | tr -d '\r')"
  printf '%s\n' "$pid" > "$out/pid-${label}.txt"
  "$ADB" shell dumpsys activity processes > "$out/activity-processes-${label}.txt" 2>&1 || true
  "$ADB" shell dumpsys activity activities > "$out/activity-${label}.txt" 2>&1 || true
  "$ADB" shell dumpsys window windows > "$out/window-${label}.txt" 2>&1 || true
  "$ADB" shell dumpsys gfxinfo "$package" framestats > "$out/gfxinfo-${label}.txt" 2>&1 || true
  "$ADB" shell dumpsys meminfo "$package" > "$out/meminfo-${label}.txt" 2>&1 || true
  if [[ -n "$pid" ]]; then
    "$ADB" shell top -H -b -n 1 -p "$pid" > "$out/top-threads-${label}.txt" 2>&1 || true
    "$ADB" shell debuggerd -b "$pid" > "$out/debuggerd-${label}.txt" 2>&1 || \
      "$ADB" shell /system/bin/debuggerd -b "$pid" > "$out/debuggerd-${label}.txt" 2>&1 || true
  fi
}

run_mode() {
  local track="$1" mode="$2" package="$3" apk="$4" completion_marker="$5" timeout_seconds="$6"
  local out="$RAW/$track/$mode"
  mkdir -p "$out"
  "$ADB" uninstall "$package" > "$out/uninstall.txt" 2>&1 || true
  "$ADB" install -r -t "$apk" > "$out/install.txt" 2>&1
  "$ADB" shell pm clear "$package" > "$out/pm-clear.txt" 2>&1 || true
  write_mode_file "$package" "$mode"
  "$ADB" logcat -c
  "$ADB" logcat -v threadtime > "$out/logcat_full.txt" 2>&1 &
  local logcat_pid=$!
  sleep 2
  local resolved
  resolved="$("$ADB" shell cmd package resolve-activity --brief "$package" | tail -1 | tr -d '\r')"
  printf '%s\n' "$resolved" > "$out/resolve-activity.txt"
  "$ADB" shell am start -W -S -n "$resolved" > "$out/am-start.txt" 2>&1 || true
  local completed=false
  local elapsed=0
  while (( elapsed < timeout_seconds )); do
    if grep -q "$completion_marker" "$out/logcat_full.txt"; then completed=true; break; fi
    if grep -q 'R1_RUNTIME_DEBUG_FAILURE' "$out/logcat_full.txt"; then break; fi
    if (( elapsed > 0 && elapsed % 30 == 0 )); then
      capture_process_diagnostics "$package" "$out" "${elapsed}s"
    fi
    sleep 2
    elapsed=$((elapsed+2))
  done
  printf '{"schema_version":1,"mode":"%s","completion_marker":"%s","completed":%s,"timeout_seconds":%s,"elapsed_seconds":%s}\n' \
    "$mode" "$completion_marker" "$completed" "$timeout_seconds" "$elapsed" > "$out/watchdog.json"
  capture_process_diagnostics "$package" "$out" final
  local pid
  pid="$(cat "$out/pid-final.txt" 2>/dev/null || true)"
  if [[ -n "$pid" && -s "$out/debuggerd-final.txt" ]]; then cp "$out/debuggerd-final.txt" "$out/debuggerd-backtrace.txt"; fi
  "$ADB" exec-out screencap -p > "$out/screenshot.png" 2>/dev/null || true
  pull_user_file "$package" r1_material_inventory.json "$out/r1_material_inventory.json"
  pull_user_file "$package" r1_mobile_progress.json "$out/r1_mobile_progress.json"
  pull_user_file "$package" r1_scene_tree.json "$out/r1_scene_tree.json"
  pull_user_file "$package" r1_wait_inventory.json "$out/r1_wait_inventory.json"
  kill "$logcat_pid" >/dev/null 2>&1 || true
  wait "$logcat_pid" >/dev/null 2>&1 || true
  python3 - "$out/logcat_full.txt" "$out/compile_log.txt" "$out/critical_log.txt" <<'PY'
from pathlib import Path
import re,sys
text=Path(sys.argv[1]).read_text(errors='replace')
compile_lines=[]; critical=[]
patterns=(r'SceneShaderGLES3',r'Program linking failed',r'GL_MAX_FRAGMENT_UNIFORM_VECTORS',r'shader failed to compile',r'_compile_specialization')
for line in text.splitlines():
    if any(re.search(pattern,line,re.I) for pattern in patterns): compile_lines.append(line)
    if re.search(r'SCRIPT ERROR|Parse Error|Invalid call|Fatal signal|FATAL EXCEPTION|VK_ERROR_DEVICE_LOST|GPU hang|ANR in |SceneShaderGLES3',line,re.I): critical.append(line)
Path(sys.argv[2]).write_text('\n'.join(compile_lines)+('\n' if compile_lines else ''))
Path(sys.argv[3]).write_text('\n'.join(critical)+('\n' if critical else ''))
PY
}

for mode in "${GL_MODES[@]}"; do
  run_mode track_a "$mode" "$GL_PACKAGE" "$GL_APK" "R1_GL_SCENARIO_COMPLETE mode=$mode" 150
done

run_mode track_b mobile_baseline "$MOBILE_PACKAGE" "$MOBILE_APK" 'R1_MOBILE_CAPTURE_FRAME frame=300' 240
run_mode track_b mobile_render_disabled_control "$MOBILE_PACKAGE" "$MOBILE_APK" 'R1_MOBILE_CONTROL_COMPLETE frames=300' 120

python3 - "$RAW/track_a" "$REPORTS/gl_limit_probe.json" <<'PY'
from pathlib import Path
import json,re,sys
root=Path(sys.argv[1]); counts=[]; occurrences=0
for log in root.glob('*/logcat_full.txt'):
    text=log.read_text(errors='replace')
    matches=re.findall(r'Fragment shader active uniforms exceed GL_MAX_FRAGMENT_UNIFORM_VECTORS(?:\s*\((\d+)\))?',text)
    occurrences+=len(matches); counts.extend(int(value) for value in matches if value)
payload={
 'schema_version':1,
 'constant':'GL_MAX_FRAGMENT_UNIFORM_VECTORS',
 'query_method':'driver program-link diagnostic',
 'exact_error':'Fragment shader active uniforms exceed GL_MAX_FRAGMENT_UNIFORM_VECTORS',
 'uniform_overflow_occurrences':occurrences,
 'observed_active_uniform_vectors':sorted(set(counts)),
 'numeric_device_limit_directly_queried':False,
}
Path(sys.argv[2]).write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
PY

python3 "$REPO_ROOT/tools/graphics/finalize_r1_renderer_debug.py" --raw "$RAW" --output "$REPORTS"
cp "$OUTPUT_ROOT/IMPORTED_STATE_MANIFEST.json" "$REPORTS/IMPORTED_STATE_MANIFEST.json"
cp "$OUTPUT_ROOT/CLONE_IDENTITY.json" "$REPORTS/CLONE_IDENTITY.json"
cp "$OUTPUT_ROOT/HARNESS_INJECTION.json" "$REPORTS/HARNESS_INJECTION.json"
cp "$OUTPUT_ROOT/APK_SHA256SUMS.txt" "$REPORTS/APK_SHA256SUMS.txt"

# Diagnostic collection succeeds when all eight independent modes have terminal watchdog records and reports exist.
for mode in "${GL_MODES[@]}"; do test -s "$RAW/track_a/$mode/watchdog.json"; done
for mode in "${MOBILE_MODES[@]}"; do test -s "$RAW/track_b/$mode/watchdog.json"; done
test -s "$REPORTS/R1_DIAGNOSTIC_REPORT.json"
