#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:?repository root is required}"
SOURCE_ROOT="${2:?single reconstruction root is required}"
OUTPUT_ROOT="${3:?Tier B output root is required}"
GAME="$SOURCE_ROOT/game"
REPORTS="$OUTPUT_ROOT/reports/graphics/g0"
SHARED="$OUTPUT_ROOT/shared-import"
GL_PROJECT="$OUTPUT_ROOT/android_gl_compatibility"
MOBILE_PROJECT="$OUTPUT_ROOT/android_mobile_vulkan"
APK_DIR="$OUTPUT_ROOT/apks"
TOOLS="$REPO_ROOT/tools/graphics"
GODOT_DIR="$OUTPUT_ROOT/godot"
XDG_DATA_HOME="$OUTPUT_ROOT/godot-user-data"
TEMPLATE_DIR="$OUTPUT_ROOT/templates"
AVD_HOME="$OUTPUT_ROOT/avd-home"
AVD_NAME="bahrain_brick_g0_api34"
GL_PACKAGE="com.brickbahrain.g0gl"
MOBILE_PACKAGE="com.brickbahrain.g0mobile"
GL_APK="$APK_DIR/bahrain-brick-g0-gl-compatibility-x86_64.apk"
MOBILE_APK="$APK_DIR/bahrain-brick-g0-mobile-vulkan-x86_64.apk"

mkdir -p "$REPORTS/gl_compatibility" "$REPORTS/mobile_vulkan" "$APK_DIR" "$GODOT_DIR" "$XDG_DATA_HOME" "$TEMPLATE_DIR" "$AVD_HOME"
for required in \
  "$GAME/project.godot" \
  "$GAME/export_presets.cfg" \
  "$SOURCE_ROOT/downloads/Godot_v4.3-stable_linux.x86_64.zip" \
  "$REPO_ROOT/debug.keystore" \
  "$REPO_ROOT/tests/graphics/android_renderer_evidence.gd" \
  "$REPO_ROOT/tests/graphics/android_renderer_evidence.tscn" \
  "$TOOLS/prepare_android_renderer_variant.py" \
  "$TOOLS/finalize_android_emulator_evidence.py"; do
  test -f "$required"
done

SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
test -n "$SDK_ROOT"
ADB="$SDK_ROOT/platform-tools/adb"
EMULATOR="$SDK_ROOT/emulator/emulator"
AVDMANAGER="$(find "$SDK_ROOT/cmdline-tools" -type f -path '*/bin/avdmanager' | sort | tail -1)"
SDKMANAGER="$(find "$SDK_ROOT/cmdline-tools" -type f -path '*/bin/sdkmanager' | sort | tail -1)"
AAPT="$SDK_ROOT/build-tools/34.0.0/aapt"
APKSIGNER="$SDK_ROOT/build-tools/34.0.0/apksigner"
for tool in "$ADB" "$EMULATOR" "$AVDMANAGER" "$SDKMANAGER" "$AAPT" "$APKSIGNER"; do test -x "$tool"; done

# Inject the test-only Android evidence scene before the single import.
mkdir -p "$GAME/tests/graphics"
cp "$REPO_ROOT/tests/graphics/android_renderer_evidence.gd" "$GAME/tests/graphics/android_renderer_evidence.gd"
cp "$REPO_ROOT/tests/graphics/android_renderer_evidence.tscn" "$GAME/tests/graphics/android_renderer_evidence.tscn"
python3 - "$REPO_ROOT" "$GAME" "$OUTPUT_ROOT/HARNESS_INJECTION.json" <<'PY'
from pathlib import Path
import hashlib,json,sys
repo=Path(sys.argv[1]); game=Path(sys.argv[2]); out=Path(sys.argv[3]); items=[]
for name in ('android_renderer_evidence.gd','android_renderer_evidence.tscn'):
    source=repo/'tests/graphics'/name; injected=game/'tests/graphics'/name
    a=source.read_bytes(); b=injected.read_bytes()
    items.append({'path':f'tests/graphics/{name}','source_sha256':hashlib.sha256(a).hexdigest(),'injected_sha256':hashlib.sha256(b).hexdigest(),'equal':a==b,'test_only':True})
value={'schema_version':1,'items':items,'all_equal':all(x['equal'] for x in items)}
out.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
if not value['all_equal']: raise SystemExit(1)
PY

# Use the checksum-pinned Godot editor already materialized by reconstruction.
unzip -q "$SOURCE_ROOT/downloads/Godot_v4.3-stable_linux.x86_64.zip" -d "$GODOT_DIR"
GODOT="$(find "$GODOT_DIR" -maxdepth 1 -type f -name 'Godot*' | head -1)"
test -n "$GODOT"
chmod +x "$GODOT"
"$GODOT" --version > "$OUTPUT_ROOT/GODOT_VERSION.txt"

# Materialize exactly one imported project state, then clone it byte-for-byte.
rm -rf "$GAME/.godot" "$SHARED" "$GL_PROJECT" "$MOBILE_PROJECT"
LIBGL_ALWAYS_SOFTWARE=1 timeout --signal=TERM --kill-after=30s 1200s \
  xvfb-run -a -s '-screen 0 2400x1080x24' \
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
root=Path(sys.argv[1])
items=[json.loads((root/name).read_text()) for name in ('IMPORTED_STATE_MANIFEST.json','GL_CLONE_PRE_OVERRIDE.json','MOBILE_CLONE_PRE_OVERRIDE.json')]
passed=len({item['aggregate_sha256'] for item in items})==1
(root/'CLONE_IDENTITY.json').write_text(json.dumps({'schema_version':1,'passed':passed,'roots':items},indent=2,sort_keys=True)+'\n')
if not passed: raise SystemExit(1)
PY

python3 "$TOOLS/prepare_android_renderer_variant.py" \
  --project "$GL_PROJECT/project.godot" \
  --preset "$GL_PROJECT/export_presets.cfg" \
  --renderer gl_compatibility \
  --package-name "$GL_PACKAGE" \
  --report "$OUTPUT_ROOT/GL_VARIANT_OVERRIDE.json"
python3 "$TOOLS/prepare_android_renderer_variant.py" \
  --project "$MOBILE_PROJECT/project.godot" \
  --preset "$MOBILE_PROJECT/export_presets.cfg" \
  --renderer mobile \
  --package-name "$MOBILE_PACKAGE" \
  --report "$OUTPUT_ROOT/MOBILE_VARIANT_OVERRIDE.json"

# Install checksum-verified official Godot 4.3 export templates.
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
  "$AAPT" dump badging "$apk" > "${log%.log}-badging.txt"
}
export_apk "$GL_PROJECT" "$GL_APK" "$OUTPUT_ROOT/gl-export.log"
export_apk "$MOBILE_PROJECT" "$MOBILE_APK" "$OUTPUT_ROOT/mobile-export.log"
sha256sum "$GL_APK" "$MOBILE_APK" > "$OUTPUT_ROOT/APK_SHA256SUMS.txt"

# Start one API 34 AOSP x86_64 emulator. Both variants use this exact emulator state sequentially.
export ANDROID_AVD_HOME="$AVD_HOME"
export ANDROID_EMULATOR_HOME="$OUTPUT_ROOT/emulator-home"
mkdir -p "$ANDROID_EMULATOR_HOME"
"$EMULATOR" -accel-check > "$OUTPUT_ROOT/EMULATOR_ACCELERATION.txt" 2>&1 || true
rm -rf "$ANDROID_AVD_HOME/$AVD_NAME.avd" "$ANDROID_AVD_HOME/$AVD_NAME.ini"
echo no | "$AVDMANAGER" create avd --force --name "$AVD_NAME" --package 'system-images;android-34;default;x86_64' --device 'pixel_6'
nohup "$EMULATOR" "@$AVD_NAME" \
  -no-window -no-audio -no-boot-anim -no-snapshot -wipe-data \
  -gpu swiftshader -accel auto -memory 4096 -cores 4 \
  -camera-back none -camera-front none \
  > "$OUTPUT_ROOT/emulator.log" 2>&1 &
EMULATOR_PID=$!
printf '%s\n' "$EMULATOR_PID" > "$OUTPUT_ROOT/EMULATOR_PID.txt"
cleanup() {
  "$ADB" emu kill >/dev/null 2>&1 || true
  kill "$EMULATOR_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT
"$ADB" wait-for-device
booted=false
for _attempt in $(seq 1 240); do
  if [[ "$("$ADB" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == "1" ]]; then booted=true; break; fi
  sleep 2
done
test "$booted" = true
"$ADB" shell settings put system accelerometer_rotation 0
"$ADB" shell settings put system user_rotation 1
"$ADB" shell wm size 2400x1080
"$ADB" shell wm density 420
"$ADB" shell input keyevent 82 || true

python3 - "$ADB" "$OUTPUT_ROOT/DEVICE_BASELINE.json" <<'PY'
import json,subprocess,sys
adb=sys.argv[1]
def shell(*args):
    return subprocess.run([adb,'shell',*args],text=True,capture_output=True,check=False).stdout.strip()
value={
 'schema_version':1,'evidence_tier':'B','performance_acceptance':False,
 'manufacturer':shell('getprop','ro.product.manufacturer'),'model':shell('getprop','ro.product.model'),
 'device':shell('getprop','ro.product.device'),'android_version':shell('getprop','ro.build.version.release'),
 'api_level':int(shell('getprop','ro.build.version.sdk') or 0),'abi':shell('getprop','ro.product.cpu.abi'),
 'build_fingerprint':shell('getprop','ro.build.fingerprint'),'resolution':shell('wm','size').split('Override size:')[-1].strip(),
 'density':shell('wm','density'),'gpu':shell('dumpsys','SurfaceFlinger'),
}
open(sys.argv[2],'w').write(json.dumps(value,indent=2,sort_keys=True)+'\n')
PY

run_variant() {
  local key="$1" expected="$2" package="$3" apk="$4"
  local out="$REPORTS/$key"
  mkdir -p "$out"
  cp "$OUTPUT_ROOT/DEVICE_BASELINE.json" "$out/device.json"
  cp "$apk" "$out/$(basename "$apk")"
  "$ADB" uninstall "$package" > "$out/uninstall-before.txt" 2>&1 || true
  "$ADB" logcat -c
  set +e
  "$ADB" install -r -t "$apk" > "$out/install.txt" 2>&1
  install_code=$?
  set -e
  printf '%s\n' "$install_code" > "$out/install-exit-code.txt"
  test "$install_code" -eq 0
  "$ADB" shell am force-stop "$package" || true
  "$ADB" shell dumpsys gfxinfo "$package" reset > "$out/gfxinfo-reset.txt" 2>&1 || true
  start_epoch="$(date +%s)"
  set +e
  "$ADB" shell monkey -p "$package" -c android.intent.category.LAUNCHER 1 > "$out/launch.txt" 2>&1
  launch_code=$?
  set -e
  printf '%s\n' "$launch_code" > "$out/launch-exit-code.txt"
  test "$launch_code" -eq 0

  capture=false
  failure=false
  for _attempt in $(seq 1 240); do
    "$ADB" logcat -d -v threadtime > "$out/runtime.log"
    if grep -q 'G0_ANDROID_EVIDENCE_FAILURE' "$out/runtime.log"; then failure=true; break; fi
    if grep -q 'G0_ANDROID_CAPTURE_FRAME frame=300' "$out/runtime.log" && \
       grep -q 'BAHRAIN_BRICK_SOUQ_SLICE_READY assets=35 pedestrians=12 traffic=6' "$out/runtime.log" && \
       grep -q 'BAHRAIN_BRICK_KARAK_MISSION_STARTED' "$out/runtime.log"; then capture=true; break; fi
    sleep 2
  done
  test "$failure" = false
  test "$capture" = true
  "$ADB" exec-out screencap -p > "$out/screenshot.png"
  "$ADB" shell dumpsys gfxinfo "$package" framestats > "$out/gfxinfo.txt" 2>&1 || true
  "$ADB" shell dumpsys meminfo "$package" > "$out/meminfo.txt" 2>&1 || true
  "$ADB" shell dumpsys thermalservice > "$out/thermal.txt" 2>&1 || true
  "$ADB" shell dumpsys activity activities > "$out/activity-before-pause.txt" 2>&1 || true

  "$ADB" shell input keyevent 3
  sleep 4
  "$ADB" logcat -d -v threadtime > "$out/runtime.log"
  pause_observed=false
  grep -q 'G0_ANDROID_LIFECYCLE_PAUSED' "$out/runtime.log" && pause_observed=true || true
  "$ADB" shell monkey -p "$package" -c android.intent.category.LAUNCHER 1 > "$out/resume.txt" 2>&1
  resume_observed=false
  for _attempt in $(seq 1 60); do
    "$ADB" logcat -d -v threadtime > "$out/runtime.log"
    if grep -q 'G0_ANDROID_LIFECYCLE_RESUMED' "$out/runtime.log"; then resume_observed=true; break; fi
    sleep 2
  done
  process_alive=false
  pid_value="$("$ADB" shell pidof "$package" 2>/dev/null | tr -d '\r')"
  [[ -n "$pid_value" ]] && process_alive=true
  completed_epoch="$(date +%s)"
  python3 - "$out/lifecycle.json" "$pause_observed" "$resume_observed" "$process_alive" "$start_epoch" "$completed_epoch" "$pid_value" <<'PY'
import json,sys
value={'pause_observed':sys.argv[2]=='true','resume_observed':sys.argv[3]=='true','process_alive':sys.argv[4]=='true','cold_start_result':'PASS','started_epoch':int(sys.argv[5]),'completed_epoch':int(sys.argv[6]),'duration_seconds':int(sys.argv[6])-int(sys.argv[5]),'pid':sys.argv[7] or None}
open(sys.argv[1],'w').write(json.dumps(value,indent=2,sort_keys=True)+'\n')
PY
  "$ADB" logcat -d -v threadtime > "$out/runtime.log"
  python3 "$TOOLS/finalize_android_emulator_evidence.py" \
    --evidence-dir "$out" --expected-renderer "$expected" --apk "$apk" --package-name "$package"
  "$ADB" uninstall "$package" > "$out/uninstall-after.txt" 2>&1 || true
}

run_variant gl_compatibility gl_compatibility "$GL_PACKAGE" "$GL_APK"
run_variant mobile_vulkan mobile "$MOBILE_PACKAGE" "$MOBILE_APK"

python3 - "$OUTPUT_ROOT" "$REPORTS" <<'PY'
from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1]); reports=Path(sys.argv[2])
gl=json.loads((reports/'gl_compatibility/runtime.json').read_text())
mobile=json.loads((reports/'mobile_vulkan/runtime.json').read_text())
clone=json.loads((root/'CLONE_IDENTITY.json').read_text())
comparison={
 'schema_version':1,'evidence_tier':'B','performance_acceptance':False,
 'same_imported_state':clone['passed'],
 'imported_state_aggregate_sha256':clone['roots'][0]['aggregate_sha256'],
 'emulator_identity':json.loads((root/'DEVICE_BASELINE.json').read_text()),
 'gl_compatibility':gl,'mobile_vulkan':mobile,
 'both_functionally_complete':bool(gl.get('evidence_complete') and mobile.get('evidence_complete')),
 'conclusion':'API 34 Android emulator functional evidence only; emulator frame-rate results are diagnostic and cannot satisfy physical-device performance acceptance.',
}
(reports/'TIER_B_COMPARISON.json').write_text(json.dumps(comparison,indent=2,sort_keys=True)+'\n')

handoff={
 'schema_version':1,'status':'READY_FOR_NAMED_PHYSICAL_DEVICE_EXECUTION',
 'gate_effect':'G0 remains EVIDENCE INSUFFICIENT until named physical-device results are attached.',
 'required_device_fields':['manufacturer','exact_model','soc','gpu','ram','android_version','display_resolution','renderer','quality_preset','apk_sha256','cold_start_result','five_minute_traversal_metrics','peak_memory','thermal_state','fatal_anr_native_crash_scan'],
 'apk_variants':[
   {'renderer':'gl_compatibility','package_name':gl['package_name'],'path':gl['apk']['path'],'sha256':gl['apk']['sha256']},
   {'renderer':'mobile','package_name':mobile['package_name'],'path':mobile['apk']['path'],'sha256':mobile['apk']['sha256']},
 ],
 'protocol_markers':['BAHRAIN_BRICK_SOUQ_SLICE_READY assets=35 pedestrians=12 traffic=6','BAHRAIN_BRICK_KARAK_MISSION_STARTED','G0_ANDROID_RENDERER_READY','G0_ANDROID_CAPTURE_FRAME frame=300'],
}
(reports/'PHYSICAL_DEVICE_HANDOFF.json').write_text(json.dumps(handoff,indent=2,sort_keys=True)+'\n')
(reports/'PHYSICAL_DEVICE_HANDOFF.md').write_text('# G0 Physical-Device Evidence Handoff\n\nStatus: **READY FOR NAMED PHYSICAL-DEVICE EXECUTION**\n\nGate G0 remains **EVIDENCE INSUFFICIENT** until the required named-device fields, five-minute traversal, memory, thermal, and fatal/ANR/native-crash evidence are attached.\n')

inventory=[]; output=root/'TIER_B_EVIDENCE_INVENTORY.json'
for path in sorted(root.rglob('*')):
    if not path.is_file() or path==output or path.is_relative_to(root/'shared-import') or path.is_relative_to(root/'android_gl_compatibility') or path.is_relative_to(root/'android_mobile_vulkan') or path.is_relative_to(root/'godot') or path.is_relative_to(root/'templates') or path.is_relative_to(root/'avd-home'):
        continue
    data=path.read_bytes(); inventory.append({'path':path.relative_to(root).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
output.write_text(json.dumps({'schema_version':1,'files':inventory},indent=2,sort_keys=True)+'\n')
if not comparison['both_functionally_complete']: raise SystemExit(1)
PY

echo "G0_TIER_B_PASS gl=$(sha256sum "$GL_APK" | awk '{print $1}') mobile=$(sha256sum "$MOBILE_APK" | awk '{print $1}')"
