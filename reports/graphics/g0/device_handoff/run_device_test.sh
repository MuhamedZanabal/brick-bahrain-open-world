#!/usr/bin/env bash
set -euo pipefail
GL_APK="${1:?GL APK path required}"
MOBILE_APK="${2:?Mobile APK path required}"
OUT_DIR="${3:-device-results}"
run_variant() {
  local key="$1" package="$2" apk="$3" out="$OUT_DIR/$key"
  mkdir -p "$out"
  adb install -r -t "$apk" | tee "$out/install.txt"
  adb shell pm path "$package" | tee "$out/pm-path.txt"
  component="$(adb shell cmd package resolve-activity --brief "$package" | tr -d '\r' | tail -1)"
  printf '%s\n' "$component" > "$out/resolved-component.txt"
  adb logcat -c
  adb logcat -v threadtime > "$out/logcat_full.txt" 2>&1 & logcat_pid=$!
  adb shell am force-stop "$package"; adb shell pm clear "$package"
  adb shell am start -W -S -n "$component" | tee "$out/am-start.txt"
  sleep 60
  adb shell pidof "$package" | tee "$out/pid.txt"
  adb shell dumpsys activity activities > "$out/activity.txt"
  adb shell dumpsys window windows > "$out/window.txt"
  adb exec-out screencap -p > "$out/screenshot.png"
  adb shell dumpsys gfxinfo "$package" framestats > "$out/gfxinfo.txt"
  adb shell dumpsys meminfo "$package" > "$out/meminfo.txt"
  adb shell dumpsys thermalservice > "$out/thermal.txt"
  adb shell input keyevent 3; sleep 4; adb shell am start -W -n "$component" > "$out/resume.txt"
  sleep 5; kill "$logcat_pid" || true
}
run_variant gl_compatibility com.brickbahrain.g0gl "$GL_APK"
run_variant mobile_vulkan com.brickbahrain.g0mobile "$MOBILE_APK"
echo 'Template capture completed. tests_performed remains false until reviewed and signed.'
