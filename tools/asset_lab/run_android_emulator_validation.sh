#!/usr/bin/env bash
set -euo pipefail

APK="$1"
PACKAGE="$2"
REPORTS="$3"
LOGS="$4"
ARTIFACTS="$5"
AVD_NAME="bahrain-brick-api34"
SYSTEM_IMAGE="system-images;android-34;google_apis;x86_64"
ACTIVITY="com.godot.game.GodotApp"
EXPECTED_APK_SHA256="${EXPECTED_APK_SHA256:-9b7edb8a9434bfa972b98ad183aa4b886ed6ab56bea14558bc4c3a4f3c0681b7}"
TRAVERSAL_SECONDS=600
SOAK_SECONDS=1800
REPORT="$REPORTS/ANDROID_EMULATOR_VALIDATION.json"
EMULATOR_LOG="$LOGS/android-emulator.log"
LOGCAT_CONTINUOUS="$LOGS/android-emulator-logcat-continuous.txt"
LOGCAT_FILTERED="$LOGS/android-emulator-logcat-filtered.txt"
INSTALL_LOG="$LOGS/android-emulator-install.txt"
LAUNCH_LOG="$LOGS/android-emulator-launch.txt"
AVD_CREATE_LOG="$LOGS/android-avd-create.txt"
HOST_LDD_BEFORE="$REPORTS/ANDROID_EMULATOR_LDD_BEFORE.txt"
HOST_LDD_AFTER="$REPORTS/ANDROID_EMULATOR_LDD_AFTER.txt"
UNRESOLVED_LIBRARIES="$REPORTS/ANDROID_EMULATOR_UNRESOLVED_LIBRARIES.txt"
KVM_REPORT="$REPORTS/ANDROID_EMULATOR_KVM.txt"
EMULATOR_COMMAND_REPORT="$REPORTS/ANDROID_EMULATOR_COMMAND.txt"
BOOT_PROPERTIES="$REPORTS/ANDROID_EMULATOR_BOOT_PROPERTIES.txt"
ORIENTATION="$REPORTS/ANDROID_EMULATOR_ORIENTATION.txt"
METRICS="$REPORTS/ANDROID_EMULATOR_RUNTIME_METRICS.csv"
TRAVERSAL_REPORT="$REPORTS/ANDROID_EMULATOR_10_MINUTE_TRAVERSAL.txt"
SOAK_REPORT="$REPORTS/ANDROID_EMULATOR_30_MINUTE_SOAK.txt"
STARTUP_SCREENSHOT="$ARTIFACTS/android-emulator-startup.png"
GAMEPLAY_SCREENSHOT="$ARTIFACTS/android-emulator-gameplay.png"
TRAVERSAL_MID_SCREENSHOT="$ARTIFACTS/android-emulator-traversal-midpoint.png"
FINAL_SCREENSHOT="$ARTIFACTS/android-emulator-final.png"
mkdir -p "$REPORTS" "$LOGS" "$ARTIFACTS"

APK_SHA256=""
APK_BYTES=0
EMULATOR_PID=""
LOGCAT_PID=""
BOOTED=false
PACKAGE_INSTALLED=false
PROCESS_ALIVE=false
WORLD_READY=false
PAUSE_RESUME=false
COLD_START=false
TRAVERSAL_PASS=false
SOAK_PASS=false
MEMORY_PASS=false
SCREENSHOT_WIDTH=0
SCREENSHOT_HEIGHT=0
KVM_PRESENT=false
KVM_READABLE=false
KVM_WRITABLE=false
ACCELERATION_MODE="software"

cleanup() {
  if [[ -n "$LOGCAT_PID" ]]; then
    kill "$LOGCAT_PID" >/dev/null 2>&1 || true
    wait "$LOGCAT_PID" >/dev/null 2>&1 || true
  fi
  adb emu kill >/dev/null 2>&1 || true
  if [[ -n "$EMULATOR_PID" ]]; then
    kill "$EMULATOR_PID" >/dev/null 2>&1 || true
    wait "$EMULATOR_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

write_report() {
  local status="$1"
  local classification="$2"
  local reason="$3"
  STATUS="$status" CLASSIFICATION="$classification" REASON="$reason" \
  APK_SHA256="$APK_SHA256" EXPECTED_APK_SHA256="$EXPECTED_APK_SHA256" APK_BYTES="$APK_BYTES" PACKAGE="$PACKAGE" ACTIVITY="$ACTIVITY" \
  BOOTED="$BOOTED" PACKAGE_INSTALLED="$PACKAGE_INSTALLED" PROCESS_ALIVE="$PROCESS_ALIVE" WORLD_READY="$WORLD_READY" \
  PAUSE_RESUME="$PAUSE_RESUME" COLD_START="$COLD_START" TRAVERSAL_PASS="$TRAVERSAL_PASS" SOAK_PASS="$SOAK_PASS" MEMORY_PASS="$MEMORY_PASS" \
  SCREENSHOT_WIDTH="$SCREENSHOT_WIDTH" SCREENSHOT_HEIGHT="$SCREENSHOT_HEIGHT" \
  KVM_PRESENT="$KVM_PRESENT" KVM_READABLE="$KVM_READABLE" KVM_WRITABLE="$KVM_WRITABLE" ACCELERATION_MODE="$ACCELERATION_MODE" \
  TRAVERSAL_SECONDS="$TRAVERSAL_SECONDS" SOAK_SECONDS="$SOAK_SECONDS" \
  python - "$REPORT" <<'PY'
import json, os, sys
boolean=lambda name: os.environ[name].lower() == 'true'
report={
    'status': os.environ['STATUS'],
    'classification': os.environ['CLASSIFICATION'],
    'reason': os.environ['REASON'],
    'api_level': 34,
    'abi': 'x86_64',
    'system_image': 'system-images;android-34;google_apis;x86_64',
    'resolution': {'width': 1280, 'height': 720, 'density': 240, 'orientation': 'landscape'},
    'package': os.environ['PACKAGE'],
    'activity': os.environ['ACTIVITY'],
    'apk_sha256': os.environ['APK_SHA256'],
    'expected_apk_sha256': os.environ['EXPECTED_APK_SHA256'],
    'apk_bytes': int(os.environ['APK_BYTES']),
    'booted': boolean('BOOTED'),
    'package_installed': boolean('PACKAGE_INSTALLED'),
    'process_alive': boolean('PROCESS_ALIVE'),
    'world_ready_log_observed': boolean('WORLD_READY'),
    'pause_resume_passed': boolean('PAUSE_RESUME'),
    'cold_start_passed': boolean('COLD_START'),
    'ten_minute_traversal': {'seconds': int(os.environ['TRAVERSAL_SECONDS']), 'passed': boolean('TRAVERSAL_PASS')},
    'thirty_minute_soak': {'seconds': int(os.environ['SOAK_SECONDS']), 'passed': boolean('SOAK_PASS')},
    'memory_growth_check_passed': boolean('MEMORY_PASS'),
    'host_virtualization': {
        'kvm_present': boolean('KVM_PRESENT'),
        'kvm_readable': boolean('KVM_READABLE'),
        'kvm_writable': boolean('KVM_WRITABLE'),
        'acceleration_mode': os.environ['ACCELERATION_MODE'],
    },
    'screenshots': [
        'build/asset-production/artifacts/android-emulator-startup.png',
        'build/asset-production/artifacts/android-emulator-gameplay.png',
        'build/asset-production/artifacts/android-emulator-traversal-midpoint.png',
        'build/asset-production/artifacts/android-emulator-final.png',
    ],
    'screenshot_dimensions': {
        'width': int(os.environ['SCREENSHOT_WIDTH']),
        'height': int(os.environ['SCREENSHOT_HEIGHT']),
        'landscape': int(os.environ['SCREENSHOT_WIDTH']) >= int(os.environ['SCREENSHOT_HEIGHT']) and int(os.environ['SCREENSHOT_HEIGHT']) > 0,
    },
    'evidence': {
        'emulator_command': 'build/asset-production/reports/ANDROID_EMULATOR_COMMAND.txt',
        'kvm': 'build/asset-production/reports/ANDROID_EMULATOR_KVM.txt',
        'ldd_before': 'build/asset-production/reports/ANDROID_EMULATOR_LDD_BEFORE.txt',
        'ldd_after': 'build/asset-production/reports/ANDROID_EMULATOR_LDD_AFTER.txt',
        'unresolved_libraries': 'build/asset-production/reports/ANDROID_EMULATOR_UNRESOLVED_LIBRARIES.txt',
        'boot_log': 'build/asset-production/logs/android-emulator.log',
        'continuous_logcat': 'build/asset-production/logs/android-emulator-logcat-continuous.txt',
        'filtered_logcat': 'build/asset-production/logs/android-emulator-logcat-filtered.txt',
        'metrics': 'build/asset-production/reports/ANDROID_EMULATOR_RUNTIME_METRICS.csv',
        'traversal': 'build/asset-production/reports/ANDROID_EMULATOR_10_MINUTE_TRAVERSAL.txt',
        'soak': 'build/asset-production/reports/ANDROID_EMULATOR_30_MINUTE_SOAK.txt',
    },
}
open(sys.argv[1], 'w', encoding='utf-8').write(json.dumps(report, indent=2, sort_keys=True)+'\n')
print(json.dumps(report, indent=2, sort_keys=True))
PY
}

blocked() {
  write_report "BLOCKED" "ANDROID_EMULATOR_RUNTIME_VERIFICATION_BLOCKED" "$1"
  exit 0
}

virtualization_blocked() {
  write_report "BLOCKED" "ANDROID EMULATOR RUNTIME VERIFICATION BLOCKED — HOSTED VIRTUALIZATION UNAVAILABLE" "$1"
  exit 0
}

failed() {
  if command -v adb >/dev/null 2>&1; then
    adb logcat -d -v threadtime >> "$LOGCAT_CONTINUOUS" 2>/dev/null || true
  fi
  if [[ -s "$LOGCAT_CONTINUOUS" ]]; then
    grep -Ei "$PACKAGE|Godot|BAHRAIN BRICK|Asset Lab|FATAL EXCEPTION|ANR in|am_crash|am_anr|Fatal signal" "$LOGCAT_CONTINUOUS" > "$LOGCAT_FILTERED" || true
  fi
  write_report "FAIL" "ANDROID_EMULATOR_RUNTIME_VERIFICATION_FAILED" "$1"
  exit 1
}

run_ldd_inventory() {
  local output="$1"
  local missing="$2"
  ldd "$EMULATOR" > "$output" 2>&1 || true
  awk '/=> not found/{print $1}' "$output" | sort -u > "$missing"
}

capture_screenshot() {
  local output="$1"
  adb exec-out screencap -p > "$output"
  test -s "$output" || failed "screenshot capture was empty: $output"
  read -r width height < <(python - "$output" <<'PY'
from PIL import Image
import sys
with Image.open(sys.argv[1]) as image:
    image.verify()
with Image.open(sys.argv[1]) as image:
    print(image.width, image.height)
PY
  )
  SCREENSHOT_WIDTH="$width"
  SCREENSHOT_HEIGHT="$height"
  [[ "$width" -ge "$height" ]] || failed "screenshot was not landscape: $output (${width}x${height})"
}

sample_memory() {
  local label="$1"
  local raw="$REPORTS/ANDROID_EMULATOR_MEMORY_${label}.txt"
  local pid total_pss total_rss
  pid="$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')"
  [[ -n "$pid" ]] || failed "application process was not alive at memory checkpoint $label"
  adb shell dumpsys meminfo "$PACKAGE" > "$raw"
  total_pss="$(awk '/TOTAL PSS:/{print $3; exit} /^ TOTAL[[:space:]]/{print $2; exit}' "$raw")"
  total_rss="$(awk '/TOTAL RSS:/{print $3; exit} /^ TOTAL[[:space:]]/{print $3; exit}' "$raw")"
  total_pss="${total_pss:-0}"
  total_rss="${total_rss:-0}"
  printf '%s,%s,%s,%s,%s\n' "$(date -u +%FT%TZ)" "$label" "$pid" "$total_pss" "$total_rss" >> "$METRICS"
}

exercise_runtime_input() {
  adb shell input swipe 190 600 190 390 700 >/dev/null 2>&1 || true
  adb shell input swipe 1060 500 1140 500 350 >/dev/null 2>&1 || true
  adb shell input keyevent KEYCODE_W >/dev/null 2>&1 || true
  adb shell input keyevent KEYCODE_D >/dev/null 2>&1 || true
}

wait_for_world_ready() {
  for _ in $(seq 1 60); do
    if grep -q 'BAHRAIN BRICK GAME ASSET LAB READY' "$LOGCAT_CONTINUOUS" 2>/dev/null; then
      WORLD_READY=true
      return 0
    fi
    [[ -n "$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')" ]] || return 1
    sleep 2
  done
  return 1
}

test -s "$APK"
APK_SHA256="$(sha256sum "$APK" | awk '{print $1}')"
APK_BYTES="$(stat -c '%s' "$APK")"
[[ "$APK_SHA256" == "$EXPECTED_APK_SHA256" ]] || failed "APK SHA-256 did not match the approved candidate: expected $EXPECTED_APK_SHA256, got $APK_SHA256"

SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
[[ -n "$SDK_ROOT" ]] || failed "ANDROID_SDK_ROOT and ANDROID_HOME are unset"
EMULATOR="$SDK_ROOT/emulator/emulator"
[[ -x "$EMULATOR" ]] || failed "emulator binary missing"
command -v avdmanager >/dev/null || failed "avdmanager missing"
command -v adb >/dev/null || failed "adb missing"

missing_before="$REPORTS/ANDROID_EMULATOR_UNRESOLVED_LIBRARIES_BEFORE.txt"
run_ldd_inventory "$HOST_LDD_BEFORE" "$missing_before"
if grep -qx 'libpulse.so.0' "$missing_before"; then
  if ! sudo apt-get update || ! sudo apt-get install -y --no-install-recommends libpulse0; then
    blocked "required emulator host library libpulse.so.0 could not be provisioned with libpulse0"
  fi
  sudo ldconfig
fi
run_ldd_inventory "$HOST_LDD_AFTER" "$UNRESOLVED_LIBRARIES"
ldconfig -p 2>/dev/null | grep 'libpulse\.so\.0' > "$REPORTS/ANDROID_EMULATOR_LIBPULSE_RESOLUTION.txt" || true
if grep -qx 'libpulse.so.0' "$UNRESOLVED_LIBRARIES" || ! grep -q 'libpulse\.so\.0' "$REPORTS/ANDROID_EMULATOR_LIBPULSE_RESOLUTION.txt"; then
  blocked "libpulse.so.0 did not resolve after libpulse0 installation"
fi
if [[ -s "$UNRESOLVED_LIBRARIES" ]]; then
  blocked "unresolved emulator host libraries: $(paste -sd, "$UNRESOLVED_LIBRARIES")"
fi

"$EMULATOR" -version > "$REPORTS/ANDROID_EMULATOR_VERSION.txt" 2>&1
{
  printf 'timestamp_utc=%s\n' "$(date -u +%FT%TZ)"
  uname -a
  id
  printf 'groups='; groups
  if [[ -e /dev/kvm ]]; then
    KVM_PRESENT=true
    ls -l /dev/kvm
    stat /dev/kvm
    [[ -r /dev/kvm ]] && KVM_READABLE=true || true
    [[ -w /dev/kvm ]] && KVM_WRITABLE=true || true
    if [[ "$KVM_WRITABLE" != true ]]; then
      sudo chmod a+rw /dev/kvm || true
      [[ -r /dev/kvm ]] && KVM_READABLE=true || true
      [[ -w /dev/kvm ]] && KVM_WRITABLE=true || true
      ls -l /dev/kvm
    fi
  else
    printf '/dev/kvm=missing\n'
  fi
  "$EMULATOR" -accel-check || true
} > "$KVM_REPORT" 2>&1

rm -rf "$HOME/.android/avd/${AVD_NAME}.avd" "$HOME/.android/avd/${AVD_NAME}.ini"
echo no | avdmanager create avd --force --name "$AVD_NAME" --package "$SYSTEM_IMAGE" --device pixel_6 > "$AVD_CREATE_LOG" 2>&1
cat >> "$HOME/.android/avd/${AVD_NAME}.avd/config.ini" <<'CFG'
hw.lcd.width=1280
hw.lcd.height=720
hw.lcd.density=240
hw.initialOrientation=landscape
hw.keyboard=yes
hw.gpu.enabled=yes
hw.gpu.mode=swiftshader_indirect
showDeviceFrame=no
skin.name=1280x720
CFG

ACCEL_ARGS=()
if [[ "$KVM_PRESENT" == true && "$KVM_READABLE" == true && "$KVM_WRITABLE" == true ]]; then
  ACCELERATION_MODE="kvm"
else
  ACCEL_ARGS=(-accel off)
  ACCELERATION_MODE="software"
fi
EMULATOR_COMMAND=(
  "$EMULATOR" -avd "$AVD_NAME"
  -no-window -no-audio -no-boot-anim -no-snapshot -wipe-data -no-metrics
  -gpu swiftshader_indirect -memory 3072 -cores 2
  -camera-back none -camera-front none
  "${ACCEL_ARGS[@]}"
)
printf '%q ' "${EMULATOR_COMMAND[@]}" > "$EMULATOR_COMMAND_REPORT"
printf '\n' >> "$EMULATOR_COMMAND_REPORT"
"${EMULATOR_COMMAND[@]}" > "$EMULATOR_LOG" 2>&1 &
EMULATOR_PID=$!

if ! timeout 420 adb wait-for-device; then
  if [[ "$ACCELERATION_MODE" == software ]]; then
    virtualization_blocked "adb device did not become available; /dev/kvm was unavailable or unusable and software emulation did not start"
  fi
  blocked "adb device did not become available on the hosted runner"
fi
for _ in $(seq 1 300); do
  {
    printf 'timestamp_utc=%s\n' "$(date -u +%FT%TZ)"
    adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r'
    adb shell getprop init.svc.bootanim 2>/dev/null | tr -d '\r'
  } >> "$BOOT_PROPERTIES"
  if [[ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == "1" ]]; then
    BOOTED=true
    break
  fi
  if ! kill -0 "$EMULATOR_PID" 2>/dev/null; then
    if [[ "$ACCELERATION_MODE" == software ]]; then
      virtualization_blocked "emulator process exited before Android completed boot; hosted KVM was unavailable or unusable"
    fi
    blocked "emulator process exited before Android completed boot"
  fi
  sleep 2
done
if [[ "$BOOTED" != true ]]; then
  if [[ "$ACCELERATION_MODE" == software ]]; then
    virtualization_blocked "Android API 34 emulator did not complete boot within 600 seconds without usable hosted KVM"
  fi
  blocked "Android API 34 emulator did not complete boot within 600 seconds"
fi

adb shell wm size 1280x720
adb shell wm density 240
adb shell settings put system accelerometer_rotation 0 || true
adb shell settings put system user_rotation 1 || true
adb shell input keyevent 82 || true
adb shell settings put system screen_off_timeout 2147483647 || true
adb logcat -c
adb logcat -v threadtime > "$LOGCAT_CONTINUOUS" 2>&1 &
LOGCAT_PID=$!

if ! timeout 360 adb install -r -t "$APK" > "$INSTALL_LOG" 2>&1; then
  failed "APK installation failed"
fi
adb shell pm path "$PACKAGE" | tee "$REPORTS/ANDROID_EMULATOR_PACKAGE_PATH.txt" | grep -q '^package:' || failed "package not present after installation"
adb shell dumpsys package "$PACKAGE" > "$REPORTS/ANDROID_EMULATOR_PACKAGE_DUMPSYS.txt"
PACKAGE_INSTALLED=true

if ! timeout 120 adb shell am start -W -n "$PACKAGE/$ACTIVITY" > "$LAUNCH_LOG" 2>&1; then
  failed "main activity launch command failed"
fi
sleep 8
capture_screenshot "$STARTUP_SCREENSHOT"
if ! wait_for_world_ready; then
  failed "integrated 3D world readiness marker was not observed after launch"
fi
PID="$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')"
[[ -n "$PID" ]] || failed "application process was not alive after launch"
PROCESS_ALIVE=true
adb shell input tap 640 620 || true
adb shell input keyevent KEYCODE_ENTER || true
sleep 8
capture_screenshot "$GAMEPLAY_SCREENSHOT"
{
  adb shell dumpsys input | grep -E 'SurfaceOrientation|orientation' | head -20 || true
  adb shell dumpsys window displays | grep -E 'mCurrentFocus|mFocusedApp|DisplayFrames|rotation' | head -60 || true
  printf 'screenshot_width=%s\nscreenshot_height=%s\n' "$SCREENSHOT_WIDTH" "$SCREENSHOT_HEIGHT"
} > "$ORIENTATION"

adb shell input keyevent KEYCODE_HOME
sleep 3
adb shell am start -W -n "$PACKAGE/$ACTIVITY" >> "$LAUNCH_LOG" 2>&1
sleep 8
[[ -n "$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')" ]] || failed "application process did not survive background and foreground lifecycle"
PAUSE_RESUME=true

adb shell am force-stop "$PACKAGE"
sleep 3
adb shell am start -W -n "$PACKAGE/$ACTIVITY" >> "$LAUNCH_LOG" 2>&1
sleep 12
[[ -n "$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')" ]] || failed "application process did not survive cold relaunch"
COLD_START=true
wait_for_world_ready || failed "integrated 3D world readiness marker was not observed after cold relaunch"

printf 'timestamp_utc,label,pid,total_pss_kb,total_rss_kb\n' > "$METRICS"
sample_memory "START"
traversal_iterations=$((TRAVERSAL_SECONDS / 10))
{
  printf 'started_utc=%s\n' "$(date -u +%FT%TZ)"
  printf 'duration_seconds=%s\n' "$TRAVERSAL_SECONDS"
  printf 'iterations=%s\n' "$traversal_iterations"
} > "$TRAVERSAL_REPORT"
for iteration in $(seq 1 "$traversal_iterations"); do
  exercise_runtime_input
  sleep 8
  [[ -n "$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')" ]] || failed "application process exited during the 10-minute active traversal at iteration $iteration"
  if [[ "$iteration" -eq $((traversal_iterations / 2)) ]]; then
    sample_memory "TRAVERSAL_MID"
    capture_screenshot "$TRAVERSAL_MID_SCREENSHOT"
  fi
  sleep 1
done
TRAVERSAL_PASS=true
printf 'completed_utc=%s\nresult=PASS\n' "$(date -u +%FT%TZ)" >> "$TRAVERSAL_REPORT"

soak_iterations=$((SOAK_SECONDS / 15))
{
  printf 'started_utc=%s\n' "$(date -u +%FT%TZ)"
  printf 'duration_seconds=%s\n' "$SOAK_SECONDS"
  printf 'iterations=%s\n' "$soak_iterations"
} > "$SOAK_REPORT"
for iteration in $(seq 1 "$soak_iterations"); do
  exercise_runtime_input
  sleep 14
  [[ -n "$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')" ]] || failed "application process exited during the 30-minute soak at iteration $iteration"
  if [[ "$iteration" -eq $((soak_iterations / 2)) ]]; then
    sample_memory "SOAK_MID"
  fi
done
sample_memory "END"
SOAK_PASS=true
printf 'completed_utc=%s\nresult=PASS\n' "$(date -u +%FT%TZ)" >> "$SOAK_REPORT"
capture_screenshot "$FINAL_SCREENSHOT"
sha256sum "$STARTUP_SCREENSHOT" "$GAMEPLAY_SCREENSHOT" "$TRAVERSAL_MID_SCREENSHOT" "$FINAL_SCREENSHOT" > "$REPORTS/ANDROID_EMULATOR_SCREENSHOT_SHA256SUMS.txt"

python - "$METRICS" "$REPORTS/ANDROID_EMULATOR_MEMORY_GROWTH.json" <<'PY'
import csv, json, sys
rows=list(csv.DictReader(open(sys.argv[1], encoding='utf-8')))
values={row['label']: int(row['total_pss_kb'] or 0) for row in rows}
start=values.get('START', 0)
mid=max(values.get('TRAVERSAL_MID', 0), values.get('SOAK_MID', 0))
end=values.get('END', 0)
growth=end-start
limit=max(131072, int(start*0.50))
runaway=bool(start > 0 and growth > limit and end > mid > start)
report={'start_pss_kb':start,'mid_peak_pss_kb':mid,'end_pss_kb':end,'growth_pss_kb':growth,'allowed_growth_pss_kb':limit,'runaway_growth':runaway}
open(sys.argv[2], 'w', encoding='utf-8').write(json.dumps(report, indent=2, sort_keys=True)+'\n')
print(json.dumps(report, sort_keys=True))
raise SystemExit(1 if runaway else 0)
PY
MEMORY_PASS=true

adb shell am force-stop "$PACKAGE"
sleep 2
if [[ -n "$LOGCAT_PID" ]]; then
  kill "$LOGCAT_PID" >/dev/null 2>&1 || true
  wait "$LOGCAT_PID" >/dev/null 2>&1 || true
  LOGCAT_PID=""
fi
grep -Ei "$PACKAGE|Godot|BAHRAIN BRICK|Asset Lab|FATAL EXCEPTION|ANR in|am_crash|am_anr|Fatal signal" "$LOGCAT_CONTINUOUS" > "$LOGCAT_FILTERED" || true
ERROR_PATTERN='FATAL EXCEPTION|ANR in|am_crash|am_anr|Fatal signal|Godot[^[:cntrl:]]*(CRASH|FATAL)|SCRIPT ERROR|Parse Error|Parser Error|Invalid get index|Invalid call|Failed to load resource|Error loading resource|Resource file not found|No loader found|Asset Lab resource pending|Asset Lab resource failed to load|missing[^[:cntrl:]]*\.glb|material[^[:cntrl:]]*(missing|failed|error)|shader[^[:cntrl:]]*(failed|error)|Navigation[^[:cntrl:]]*(failed|error)|protected[^[:cntrl:]]*(mismatch|failed|error)'
if grep -Eiq "$ERROR_PATTERN" "$LOGCAT_FILTERED"; then
  failed "runtime log scan found a crash, ANR, Godot script/resource/material/shader/navigation, or protected-control error"
fi

write_report "PASS" "ANDROID_EMULATOR_RUNTIME_VERIFICATION_PASSED" "API 34 x86_64 emulator booted, installed and launched the exact approved APK, reached the integrated 3D world, passed lifecycle and cold relaunch, completed a 10-minute active traversal and 30-minute soak, retained bounded memory, and produced clean screenshots, metrics, boot logs, host dependency evidence, and continuous logcat"
