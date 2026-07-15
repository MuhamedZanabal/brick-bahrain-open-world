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
REPORT="$REPORTS/ANDROID_EMULATOR_VALIDATION.json"
EMULATOR_LOG="$LOGS/android-emulator.log"
LOGCAT_FULL="$LOGS/android-emulator-logcat.txt"
LOGCAT_FILTERED="$LOGS/android-emulator-logcat-filtered.txt"
SCREENSHOT="$ARTIFACTS/android-emulator-screenshot.png"
ORIENTATION="$REPORTS/ANDROID_EMULATOR_ORIENTATION.txt"
INSTALL_LOG="$LOGS/android-emulator-install.txt"
LAUNCH_LOG="$LOGS/android-emulator-launch.txt"
mkdir -p "$REPORTS" "$LOGS" "$ARTIFACTS"

test -s "$APK"
APK_SHA256="$(sha256sum "$APK" | awk '{print $1}')"
APK_BYTES="$(stat -c '%s' "$APK")"
EMULATOR_PID=""
BOOTED=false
PACKAGE_INSTALLED=false
PROCESS_ALIVE=false
PAUSE_RESUME=false
COLD_START=false
SCREENSHOT_WIDTH=0
SCREENSHOT_HEIGHT=0

cleanup() {
  adb emu kill >/dev/null 2>&1 || true
  if [[ -n "$EMULATOR_PID" ]]; then
    kill "$EMULATOR_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

write_report() {
  local status="$1"
  local classification="$2"
  local reason="$3"
  STATUS="$status" CLASSIFICATION="$classification" REASON="$reason" \
  APK_SHA256="$APK_SHA256" APK_BYTES="$APK_BYTES" PACKAGE="$PACKAGE" ACTIVITY="$ACTIVITY" \
  BOOTED="$BOOTED" PACKAGE_INSTALLED="$PACKAGE_INSTALLED" PROCESS_ALIVE="$PROCESS_ALIVE" \
  PAUSE_RESUME="$PAUSE_RESUME" COLD_START="$COLD_START" \
  SCREENSHOT_WIDTH="$SCREENSHOT_WIDTH" SCREENSHOT_HEIGHT="$SCREENSHOT_HEIGHT" \
  python - "$REPORT" <<'PY'
import json, os, sys
boolean=lambda name: os.environ[name].lower() == 'true'
report={
    'status': os.environ['STATUS'],
    'classification': os.environ['CLASSIFICATION'],
    'reason': os.environ['REASON'],
    'api_level': 34,
    'system_image': 'system-images;android-34;google_apis;x86_64',
    'package': os.environ['PACKAGE'],
    'activity': os.environ['ACTIVITY'],
    'apk_sha256': os.environ['APK_SHA256'],
    'apk_bytes': int(os.environ['APK_BYTES']),
    'booted': boolean('BOOTED'),
    'package_installed': boolean('PACKAGE_INSTALLED'),
    'process_alive': boolean('PROCESS_ALIVE'),
    'pause_resume_passed': boolean('PAUSE_RESUME'),
    'cold_start_passed': boolean('COLD_START'),
    'screenshot': {
        'path': 'build/asset-production/artifacts/android-emulator-screenshot.png',
        'width': int(os.environ['SCREENSHOT_WIDTH']),
        'height': int(os.environ['SCREENSHOT_HEIGHT']),
        'landscape': int(os.environ['SCREENSHOT_WIDTH']) >= int(os.environ['SCREENSHOT_HEIGHT']) and int(os.environ['SCREENSHOT_HEIGHT']) > 0,
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

failed() {
  adb logcat -d -v threadtime > "$LOGCAT_FULL" 2>/dev/null || true
  grep -Ei "$PACKAGE|Godot|FATAL EXCEPTION|ANR in|am_crash|am_anr|Fatal signal" "$LOGCAT_FULL" > "$LOGCAT_FILTERED" || true
  write_report "FAIL" "ANDROID_EMULATOR_RUNTIME_VERIFICATION_FAILED" "$1"
  exit 1
}

SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
[[ -n "$SDK_ROOT" ]] || failed "ANDROID_SDK_ROOT and ANDROID_HOME are unset"
EMULATOR="$SDK_ROOT/emulator/emulator"
[[ -x "$EMULATOR" ]] || failed "emulator binary missing"
command -v avdmanager >/dev/null || failed "avdmanager missing"
command -v adb >/dev/null || failed "adb missing"

"$EMULATOR" -version > "$REPORTS/ANDROID_EMULATOR_VERSION.txt" 2>&1
"$EMULATOR" -accel-check > "$REPORTS/ANDROID_EMULATOR_ACCELERATION.txt" 2>&1 || true
if [[ -e /dev/kvm ]]; then
  sudo chmod a+rw /dev/kvm || true
fi

echo no | avdmanager create avd --force --name "$AVD_NAME" --package "$SYSTEM_IMAGE" --device pixel_6 > "$LOGS/android-avd-create.txt" 2>&1

ACCEL_ARGS=()
if [[ ! -r /dev/kvm || ! -w /dev/kvm ]]; then
  ACCEL_ARGS=(-accel off)
fi
"$EMULATOR" -avd "$AVD_NAME" -no-window -no-audio -no-boot-anim -no-snapshot -wipe-data \
  -gpu swiftshader_indirect -memory 3072 -cores 2 -camera-back none -camera-front none \
  "${ACCEL_ARGS[@]}" > "$EMULATOR_LOG" 2>&1 &
EMULATOR_PID=$!

if ! timeout 240 adb wait-for-device; then
  blocked "adb device did not become available on the hosted runner"
fi
for _ in $(seq 1 180); do
  if [[ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == "1" ]]; then
    BOOTED=true
    break
  fi
  if ! kill -0 "$EMULATOR_PID" 2>/dev/null; then
    blocked "emulator process exited before Android completed boot"
  fi
  sleep 2
done
[[ "$BOOTED" == true ]] || blocked "Android API 34 emulator did not complete boot within 360 seconds"

adb shell input keyevent 82 || true
adb shell settings put system screen_off_timeout 2147483647 || true
adb logcat -c
if ! timeout 360 adb install -r -t "$APK" > "$INSTALL_LOG" 2>&1; then
  failed "APK installation failed"
fi
adb shell pm path "$PACKAGE" | tee "$REPORTS/ANDROID_EMULATOR_PACKAGE_PATH.txt" | grep -q '^package:' || failed "package not present after installation"
PACKAGE_INSTALLED=true

if ! timeout 120 adb shell am start -W -n "$PACKAGE/$ACTIVITY" > "$LAUNCH_LOG" 2>&1; then
  failed "main activity launch command failed"
fi
sleep 20
PID="$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')"
[[ -n "$PID" ]] || failed "application process was not alive after launch"
PROCESS_ALIVE=true

adb exec-out screencap -p > "$SCREENSHOT"
test -s "$SCREENSHOT" || failed "screenshot capture was empty"
read -r SCREENSHOT_WIDTH SCREENSHOT_HEIGHT < <(python - "$SCREENSHOT" <<'PY'
from PIL import Image
import sys
with Image.open(sys.argv[1]) as image:
    image.verify()
with Image.open(sys.argv[1]) as image:
    print(image.width, image.height)
PY
)
[[ "$SCREENSHOT_WIDTH" -ge "$SCREENSHOT_HEIGHT" ]] || failed "launched activity screenshot was not landscape"
{
  adb shell dumpsys input | grep -E 'SurfaceOrientation|orientation' | head -20 || true
  adb shell dumpsys window displays | grep -E 'mCurrentFocus|mFocusedApp|DisplayFrames|rotation' | head -40 || true
  printf 'screenshot_width=%s\nscreenshot_height=%s\n' "$SCREENSHOT_WIDTH" "$SCREENSHOT_HEIGHT"
} > "$ORIENTATION"

adb shell input keyevent KEYCODE_HOME
sleep 3
adb shell am start -W -n "$PACKAGE/$ACTIVITY" >> "$LAUNCH_LOG" 2>&1
sleep 8
[[ -n "$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')" ]] || failed "application process did not survive pause/resume"
PAUSE_RESUME=true

adb shell am force-stop "$PACKAGE"
sleep 3
adb shell am start -W -n "$PACKAGE/$ACTIVITY" >> "$LAUNCH_LOG" 2>&1
sleep 12
[[ -n "$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')" ]] || failed "application process did not survive cold start"
COLD_START=true

adb logcat -d -v threadtime > "$LOGCAT_FULL"
grep -Ei "$PACKAGE|Godot|FATAL EXCEPTION|ANR in|am_crash|am_anr|Fatal signal" "$LOGCAT_FULL" > "$LOGCAT_FILTERED" || true
if grep -Eiq 'FATAL EXCEPTION|ANR in|am_crash|am_anr|Fatal signal|Godot[^\n]*(CRASH|FATAL)' "$LOGCAT_FILTERED"; then
  failed "crash, ANR, fatal signal, or Godot fatal signature detected"
fi

write_report "PASS" "ANDROID_EMULATOR_RUNTIME_VERIFICATION_PASSED" "API 34 emulator booted, installed and launched the exact APK, remained alive, resumed, cold-started, and produced clean runtime evidence"
