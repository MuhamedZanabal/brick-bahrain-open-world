#!/usr/bin/env bash
set -Eeuo pipefail

APK_PATH="${1:-}"
EVIDENCE_ROOT="${QA_EVIDENCE_DIR:-qa-evidence}"
SCREENSHOTS_DIR="$EVIDENCE_ROOT/screenshots"
VIDEO_DIR="$EVIDENCE_ROOT/video"
LOGS_DIR="$EVIDENCE_ROOT/logs"
MIN_SCENE_MEAN_DIFFERENCE=5.0

mkdir -p "$SCREENSHOTS_DIR" "$VIDEO_DIR" "$LOGS_DIR"
: > "$EVIDENCE_ROOT/01-install.txt"
: > "$EVIDENCE_ROOT/02-launch.txt"
: > "$EVIDENCE_ROOT/adb-devices.txt"
: > "$EVIDENCE_ROOT/screenshot-transitions.txt"
: > "$LOGS_DIR/logcat.txt"
: > "$LOGS_DIR/crash-logcat.txt"

BOOT_STATUS="not-run"
INSTALL_STATUS="not-run"
LAUNCH_STATUS="not-run"
OVERLAY_STATUS="not-run"
GAMEPLAY_STATE="not-run"
SCREENSHOT_STATUS="not-run"
VIDEO_STATUS="not-run"
LOGCAT_STATUS="not-run"
PACKAGE_NAME=""
LAUNCH_ACTIVITY=""
LAUNCH_COMPONENT=""
MIN_SDK=""
TARGET_SDK=""
ORIENTATION=""
SUPPORTED_ABIS=""
APK_SHA256=""
SCREEN_W=0
SCREEN_H=0
PROBE_FAILURE=0
SCREENRECORD_PID=""

find_android_tool() {
  local tool="$1"
  local root="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
  [[ -n "$root" ]] || return 1
  if [[ "$tool" == "apkanalyzer" ]]; then
    find "$root/cmdline-tools" -type f -name "$tool" -perm -u+x 2>/dev/null | sort -V | tail -n 1
  else
    find "$root/build-tools" -type f -name "$tool" -perm -u+x 2>/dev/null | sort -V | tail -n 1
  fi
}

capture_runtime_evidence() {
  set +e
  adb devices -l > "$EVIDENCE_ROOT/adb-devices.txt" 2>&1
  adb shell dumpsys window windows > "$EVIDENCE_ROOT/window-state.txt" 2>&1
  if [[ -n "$PACKAGE_NAME" ]]; then
    adb shell pidof "$PACKAGE_NAME" > "$EVIDENCE_ROOT/process-state.txt" 2>&1
    adb shell dumpsys package "$PACKAGE_NAME" > "$EVIDENCE_ROOT/package-state.txt" 2>&1
  else
    : > "$EVIDENCE_ROOT/process-state.txt"
    : > "$EVIDENCE_ROOT/package-state.txt"
  fi
  adb logcat -d -v threadtime > "$LOGS_DIR/logcat.txt" 2>&1
  local logcat_code=$?
  adb logcat -b crash -d -v threadtime > "$LOGS_DIR/crash-logcat.txt" 2>&1
  local crash_code=$?
  if (( logcat_code == 0 && crash_code == 0 )); then
    LOGCAT_STATUS="success"
  else
    LOGCAT_STATUS="failed"
  fi
  set -e
}

write_report() {
  local exit_code="$1"
  local required_screenshot_count video_bytes logcat_bytes crash_bytes
  required_screenshot_count=0
  for screenshot in \
    "$SCREENSHOTS_DIR/01-after-launch.png" \
    "$SCREENSHOTS_DIR/02-after-first-tap.png" \
    "$SCREENSHOTS_DIR/03-after-second-tap.png" \
    "$SCREENSHOTS_DIR/04-gameplay-probe.png" \
    "$SCREENSHOTS_DIR/05-after-keyevents.png"; do
    [[ -s "$screenshot" ]] && required_screenshot_count=$((required_screenshot_count + 1))
  done
  video_bytes="$(stat -c '%s' "$VIDEO_DIR/gameplay-qa.mp4" 2>/dev/null || printf '0')"
  logcat_bytes="$(stat -c '%s' "$LOGS_DIR/logcat.txt" 2>/dev/null || printf '0')"
  crash_bytes="$(stat -c '%s' "$LOGS_DIR/crash-logcat.txt" 2>/dev/null || printf '0')"
  cat > "$EVIDENCE_ROOT/report.md" <<REPORT
# APK Gameplay QA Report

- Exit code: \`$exit_code\`
- APK path: \`$APK_PATH\`
- APK SHA-256: \`$APK_SHA256\`
- Package: \`$PACKAGE_NAME\`
- Launch activity: \`$LAUNCH_ACTIVITY\`
- Launch component: \`$LAUNCH_COMPONENT\`
- Supported ABIs: \`$SUPPORTED_ABIS\`
- Minimum SDK: \`$MIN_SDK\`
- Target SDK: \`$TARGET_SDK\`
- Orientation: \`$ORIENTATION\`
- Emulator boot: **$BOOT_STATUS**
- APK install: **$INSTALL_STATUS**
- App launch: **$LAUNCH_STATUS**
- Android system overlay: **$OVERLAY_STATUS**
- Gameplay navigation: **$GAMEPLAY_STATE**
- Screenshots: **$SCREENSHOT_STATUS** ($required_screenshot_count/5 required files; world-entry captured separately)
- Gameplay video: **$VIDEO_STATUS** ($video_bytes bytes)
- Logcat capture: **$LOGCAT_STATUS** ($logcat_bytes bytes; crash buffer $crash_bytes bytes)

## Evidence

- \`01-install.txt\`
- \`02-launch.txt\`
- \`adb-devices.txt\`
- \`gameplay-state.txt\`
- \`system-overlay-status.txt\`
- \`ui-tree-after-overlay-dismiss.xml\`
- \`screenshot-transitions.txt\`
- \`screenshots/01-after-launch.png\`
- \`screenshots/02-after-first-tap.png\`
- \`screenshots/03-after-second-tap.png\`
- \`screenshots/world-entry.png\`
- \`screenshots/04-gameplay-probe.png\`
- \`screenshots/05-after-keyevents.png\`
- \`video/gameplay-qa.mp4\`
- \`logs/logcat.txt\`
- \`logs/crash-logcat.txt\`
REPORT
}

finalize() {
  local exit_code=$?
  trap - EXIT
  if [[ -n "$SCREENRECORD_PID" ]]; then
    kill "$SCREENRECORD_PID" >/dev/null 2>&1 || true
  fi
  capture_runtime_evidence
  write_report "$exit_code"
  exit "$exit_code"
}
trap finalize EXIT

capture_screenshot() {
  local output="$1"
  set +e
  adb exec-out screencap -p > "$output"
  local code=$?
  set -e
  if (( code != 0 )) || [[ ! -s "$output" ]]; then
    return 1
  fi
  python3 - "$output" <<'PY'
from pathlib import Path
import struct
import sys

path = Path(sys.argv[1])
data = path.read_bytes()
if len(data) < 24 or data[:8] != b'\x89PNG\r\n\x1a\n':
    raise SystemExit(1)
width, height = struct.unpack('>II', data[16:24])
if width < 320 or height < 240:
    raise SystemExit(1)
PY
}

tap_fraction() {
  local x_pct="$1"
  local y_pct="$2"
  if (( SCREEN_W <= 0 || SCREEN_H <= 0 )); then
    printf '%s\n' 'Screen dimensions are unavailable for fractional tap.' >&2
    return 1
  fi
  adb shell input tap $((SCREEN_W * x_pct / 100)) $((SCREEN_H * y_pct / 100))
}

dismiss_system_overlays() {
  local xml="$EVIDENCE_ROOT/ui-tree-after-overlay-dismiss.xml"
  local attempt coords x y
  adb shell settings put secure immersive_mode_confirmations confirmed || true

  for attempt in 1 2 3 4; do
    set +e
    adb exec-out uiautomator dump /dev/tty > "$xml" 2>&1
    set -e
    coords="$(python3 - "$xml" <<'PY'
import re
import sys
import xml.etree.ElementTree as ET

text = open(sys.argv[1], encoding='utf-8', errors='ignore').read()
start = text.find('<?xml')
if start < 0:
    raise SystemExit(0)
try:
    root = ET.fromstring(text[start:])
except ET.ParseError:
    raise SystemExit(0)
for node in root.iter('node'):
    label = ' '.join((node.attrib.get('text', ''), node.attrib.get('content-desc', ''))).strip().lower()
    if label == 'got it' or 'got it' in label:
        match = re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', node.attrib.get('bounds', ''))
        if match:
            x1, y1, x2, y2 = map(int, match.groups())
            print((x1 + x2) // 2, (y1 + y2) // 2)
            break
PY
)"
    if [[ "$coords" =~ ^[0-9]+[[:space:]][0-9]+$ ]]; then
      read -r x y <<< "$coords"
      adb shell input tap "$x" "$y" || true
      sleep 2
      continue
    fi
    break
  done

  set +e
  adb exec-out uiautomator dump /dev/tty > "$xml" 2>&1
  set -e
  if grep -Eiq 'got it|viewing (this app in )?full screen|viewing full screen' "$xml"; then
    OVERLAY_STATUS="failed"
    PROBE_FAILURE=1
  else
    OVERLAY_STATUS="success"
  fi
  printf 'overlay_status=%s\n' "$OVERLAY_STATUS" > "$EVIDENCE_ROOT/system-overlay-status.txt"
}

verify_perceptual_transition() {
  local before="$1"
  local after="$2"
  local transition_name="$3"
  python3 - "$before" "$after" "$transition_name" "$MIN_SCENE_MEAN_DIFFERENCE" \
    >> "$EVIDENCE_ROOT/screenshot-transitions.txt" <<'PY'
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
import sys

before_path = Path(sys.argv[1])
after_path = Path(sys.argv[2])
transition_name = sys.argv[3]
minimum = float(sys.argv[4])

before = Image.open(before_path).convert('RGB')
after = Image.open(after_path).convert('RGB')
if before.size != after.size:
    raise SystemExit(f'{transition_name}: screenshot dimensions differ: {before.size} vs {after.size}')

difference = ImageChops.difference(before, after)
mean_difference = sum(ImageStat.Stat(difference).mean) / 3.0
changed_bbox = difference.getbbox()
print(f'{transition_name}_mean_difference={mean_difference:.4f}')
print(f'{transition_name}_changed_bbox={changed_bbox}')
if changed_bbox is None or mean_difference < minimum:
    raise SystemExit(
        f'{transition_name}: perceptual difference {mean_difference:.4f} is below required {minimum:.4f}'
    )
print(f'{transition_name}=success')
PY
}

if [[ -z "$APK_PATH" ]]; then
  printf '%s\n' 'Usage: ci/apk-gameplay-probe.sh <apk-path>' >&2
  exit 2
fi
if [[ ! -s "$APK_PATH" ]]; then
  printf 'APK not found or empty: %s\n' "$APK_PATH" >&2
  exit 2
fi

APK_SHA256="$(sha256sum "$APK_PATH" | awk '{print $1}')"
printf '%s  %s\n' "$APK_SHA256" "$APK_PATH" > "$EVIDENCE_ROOT/apk-sha256.txt"
unzip -Z1 "$APK_PATH" > "$EVIDENCE_ROOT/apk-inventory.txt"
SUPPORTED_ABIS="$(awk -F/ '/^lib\/[^/]+\/.*\.so$/ {print $2}' "$EVIDENCE_ROOT/apk-inventory.txt" | sort -u | paste -sd, -)"

AAPT="$(find_android_tool aapt || true)"
APKANALYZER="$(find_android_tool apkanalyzer || true)"
if [[ -n "$AAPT" ]]; then
  set +e
  "$AAPT" dump badging "$APK_PATH" > "$EVIDENCE_ROOT/apk-badging.txt" 2>&1
  set -e
  PACKAGE_NAME="$(sed -n "s/^package: name='\([^']*\)'.*/\1/p" "$EVIDENCE_ROOT/apk-badging.txt" | head -n 1)"
  LAUNCH_ACTIVITY="$(sed -n "s/^launchable-activity: name='\([^']*\)'.*/\1/p" "$EVIDENCE_ROOT/apk-badging.txt" | head -n 1)"
  MIN_SDK="$(sed -n "s/^sdkVersion:'\([^']*\)'.*/\1/p" "$EVIDENCE_ROOT/apk-badging.txt" | head -n 1)"
  TARGET_SDK="$(sed -n "s/^targetSdkVersion:'\([^']*\)'.*/\1/p" "$EVIDENCE_ROOT/apk-badging.txt" | head -n 1)"
else
  : > "$EVIDENCE_ROOT/apk-badging.txt"
fi
if [[ -n "$APKANALYZER" ]]; then
  "$APKANALYZER" manifest print "$APK_PATH" > "$EVIDENCE_ROOT/apk-manifest.xml" 2>&1 || true
  [[ -n "$PACKAGE_NAME" ]] || PACKAGE_NAME="$("$APKANALYZER" manifest application-id "$APK_PATH" 2>/dev/null | tr -d '\r\n' || true)"
  [[ -n "$MIN_SDK" ]] || MIN_SDK="$("$APKANALYZER" manifest min-sdk "$APK_PATH" 2>/dev/null | tr -d '\r\n' || true)"
  [[ -n "$TARGET_SDK" ]] || TARGET_SDK="$("$APKANALYZER" manifest target-sdk "$APK_PATH" 2>/dev/null | tr -d '\r\n' || true)"
  ORIENTATION="$(grep -o 'android:screenOrientation="[^"]*"' "$EVIDENCE_ROOT/apk-manifest.xml" | head -n 1 | cut -d'"' -f2 || true)"
  case "$ORIENTATION" in
    0) ORIENTATION="landscape" ;;
    6) ORIENTATION="sensorLandscape" ;;
    8) ORIENTATION="reverseLandscape" ;;
    11) ORIENTATION="userLandscape" ;;
  esac
else
  : > "$EVIDENCE_ROOT/apk-manifest.xml"
fi

if [[ -z "$PACKAGE_NAME" ]]; then
  printf '%s\n' 'Unable to extract package name from APK.' >&2
  exit 3
fi

adb wait-for-device
for _ in $(seq 1 180); do
  if [[ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == "1" ]]; then
    BOOT_STATUS="success"
    break
  fi
  sleep 2
done
if [[ "$BOOT_STATUS" != "success" ]]; then
  BOOT_STATUS="failed"
  printf '%s\n' 'Emulator did not finish booting.' >&2
  exit 4
fi
adb shell input keyevent 82 || true
adb shell settings put secure immersive_mode_confirmations confirmed || true
adb devices -l > "$EVIDENCE_ROOT/adb-devices.txt" 2>&1
adb logcat -c || true

set +e
adb install -r -g "$APK_PATH" > "$EVIDENCE_ROOT/01-install.txt" 2>&1
INSTALL_CODE=$?
set -e
if (( INSTALL_CODE == 0 )) && grep -q 'Success' "$EVIDENCE_ROOT/01-install.txt"; then
  INSTALL_STATUS="success"
else
  INSTALL_STATUS="failed"
  PROBE_FAILURE=1
fi

RESOLVED_COMPONENT="$(adb shell cmd package resolve-activity --brief "$PACKAGE_NAME" 2>/dev/null | tr -d '\r' | tail -n 1 || true)"
if [[ "$RESOLVED_COMPONENT" == */* && "$RESOLVED_COMPONENT" != *"No activity found"* ]]; then
  LAUNCH_COMPONENT="$RESOLVED_COMPONENT"
  LAUNCH_ACTIVITY="${RESOLVED_COMPONENT#*/}"
elif [[ -n "$LAUNCH_ACTIVITY" ]]; then
  if [[ "$LAUNCH_ACTIVITY" == .* ]]; then
    LAUNCH_COMPONENT="$PACKAGE_NAME/$PACKAGE_NAME$LAUNCH_ACTIVITY"
  elif [[ "$LAUNCH_ACTIVITY" == *.* ]]; then
    LAUNCH_COMPONENT="$PACKAGE_NAME/$LAUNCH_ACTIVITY"
  else
    LAUNCH_COMPONENT="$PACKAGE_NAME/$PACKAGE_NAME.$LAUNCH_ACTIVITY"
  fi
fi

{
  printf 'package=%s\n' "$PACKAGE_NAME"
  printf 'aapt_launch_activity=%s\n' "$LAUNCH_ACTIVITY"
  printf 'resolved_component=%s\n' "$RESOLVED_COMPONENT"
  printf 'selected_component=%s\n' "$LAUNCH_COMPONENT"
  adb shell am force-stop "$PACKAGE_NAME" || true
  if [[ -n "$LAUNCH_COMPONENT" ]]; then
    adb shell am start -W -S -n "$LAUNCH_COMPONENT"
  else
    printf '%s\n' 'No launch activity resolved; using monkey fallback.'
    adb shell monkey -p "$PACKAGE_NAME" -c android.intent.category.LAUNCHER 1
  fi
} > "$EVIDENCE_ROOT/02-launch.txt" 2>&1 || LAUNCH_CODE=$?
LAUNCH_CODE="${LAUNCH_CODE:-0}"
sleep 8
if (( LAUNCH_CODE == 0 )) && adb shell pidof "$PACKAGE_NAME" >/dev/null 2>&1; then
  LAUNCH_STATUS="success"
else
  LAUNCH_STATUS="failed"
  PROBE_FAILURE=1
fi

dismiss_system_overlays
capture_screenshot "$SCREENSHOTS_DIR/01-after-launch.png" || PROBE_FAILURE=1
read -r SCREEN_W SCREEN_H < <(python3 - "$SCREENSHOTS_DIR/01-after-launch.png" <<'PY'
import struct
import sys
with open(sys.argv[1], 'rb') as stream:
    data = stream.read(24)
print(*struct.unpack('>II', data[16:24]))
PY
)
if [[ -z "$ORIENTATION" ]]; then
  if (( SCREEN_W > SCREEN_H )); then ORIENTATION="landscape-runtime"; else ORIENTATION="portrait-runtime"; fi
fi

# Splash screen source places "TAP TO CONTINUE" at the lower center.
tap_fraction 50 82 || PROBE_FAILURE=1
sleep 10
dismiss_system_overlays
capture_screenshot "$SCREENSHOTS_DIR/02-after-first-tap.png" || PROBE_FAILURE=1
verify_perceptual_transition \
  "$SCREENSHOTS_DIR/01-after-launch.png" \
  "$SCREENSHOTS_DIR/02-after-first-tap.png" \
  "splash_to_main_menu" || PROBE_FAILURE=1

# Main-menu source anchors Character Select in the right-side action stack.
tap_fraction 88 31 || PROBE_FAILURE=1
sleep 12
dismiss_system_overlays
capture_screenshot "$SCREENSHOTS_DIR/03-after-second-tap.png" || PROBE_FAILURE=1
verify_perceptual_transition \
  "$SCREENSHOTS_DIR/02-after-first-tap.png" \
  "$SCREENSHOTS_DIR/03-after-second-tap.png" \
  "main_menu_to_character_select" || PROBE_FAILURE=1

# Character-selection source anchors Play at the lower center.
GAMEPLAY_STATE="world-probe-attempted"
printf 'state=world-probe-attempted\n' > "$EVIDENCE_ROOT/gameplay-state.txt"
tap_fraction 50 93 || PROBE_FAILURE=1
sleep 35
dismiss_system_overlays
capture_screenshot "$SCREENSHOTS_DIR/world-entry.png" || PROBE_FAILURE=1
if verify_perceptual_transition \
  "$SCREENSHOTS_DIR/03-after-second-tap.png" \
  "$SCREENSHOTS_DIR/world-entry.png" \
  "character_select_to_world" \
  && adb shell pidof "$PACKAGE_NAME" >/dev/null 2>&1; then
  GAMEPLAY_STATE="world-transition-observed"
  printf 'state=world-transition-observed\n' >> "$EVIDENCE_ROOT/gameplay-state.txt"
else
  GAMEPLAY_STATE="world-transition-not-observed"
  printf 'state=world-transition-not-observed\n' >> "$EVIDENCE_ROOT/gameplay-state.txt"
  PROBE_FAILURE=1
fi

# Record only after the world transition is proven.
adb shell rm -f /sdcard/gameplay-qa.mp4 || true
set +e
adb shell screenrecord --bit-rate 8000000 --time-limit 30 /sdcard/gameplay-qa.mp4 > "$EVIDENCE_ROOT/screenrecord.txt" 2>&1 &
SCREENRECORD_PID=$!
set -e
sleep 2

adb shell input swipe $((SCREEN_W * 20 / 100)) $((SCREEN_H * 75 / 100)) $((SCREEN_W * 38 / 100)) $((SCREEN_H * 75 / 100)) 900 || true
adb shell input swipe $((SCREEN_W * 22 / 100)) $((SCREEN_H * 78 / 100)) $((SCREEN_W * 22 / 100)) $((SCREEN_H * 55 / 100)) 900 || true
adb shell input tap $((SCREEN_W * 84 / 100)) $((SCREEN_H * 74 / 100)) || true
sleep 6
capture_screenshot "$SCREENSHOTS_DIR/04-gameplay-probe.png" || PROBE_FAILURE=1

for key in KEYCODE_DPAD_UP KEYCODE_DPAD_RIGHT KEYCODE_BUTTON_A KEYCODE_SPACE KEYCODE_ENTER; do
  adb shell input keyevent "$key" || true
  sleep 1
done
sleep 4
capture_screenshot "$SCREENSHOTS_DIR/05-after-keyevents.png" || PROBE_FAILURE=1

set +e
wait "$SCREENRECORD_PID"
SCREENRECORD_CODE=$?
SCREENRECORD_PID=""
adb pull /sdcard/gameplay-qa.mp4 "$VIDEO_DIR/gameplay-qa.mp4" >> "$EVIDENCE_ROOT/screenrecord.txt" 2>&1
PULL_CODE=$?
set -e
if (( SCREENRECORD_CODE == 0 && PULL_CODE == 0 )) && [[ -s "$VIDEO_DIR/gameplay-qa.mp4" ]]; then
  VIDEO_STATUS="success"
else
  VIDEO_STATUS="failed"
  PROBE_FAILURE=1
fi

required_screenshots=(
  "$SCREENSHOTS_DIR/01-after-launch.png"
  "$SCREENSHOTS_DIR/02-after-first-tap.png"
  "$SCREENSHOTS_DIR/03-after-second-tap.png"
  "$SCREENSHOTS_DIR/04-gameplay-probe.png"
  "$SCREENSHOTS_DIR/05-after-keyevents.png"
  "$SCREENSHOTS_DIR/world-entry.png"
)
SCREENSHOT_STATUS="success"
for screenshot in "${required_screenshots[@]}"; do
  if [[ ! -s "$screenshot" ]] || (( $(stat -c '%s' "$screenshot") <= 1024 )); then
    SCREENSHOT_STATUS="failed"
    PROBE_FAILURE=1
  fi
done
for transition in splash_to_main_menu main_menu_to_character_select character_select_to_world; do
  if ! grep -Fq "${transition}=success" "$EVIDENCE_ROOT/screenshot-transitions.txt"; then
    SCREENSHOT_STATUS="failed"
    PROBE_FAILURE=1
  fi
done

capture_runtime_evidence
if [[ "$LOGCAT_STATUS" != "success" ]]; then
  PROBE_FAILURE=1
fi

exit "$PROBE_FAILURE"
