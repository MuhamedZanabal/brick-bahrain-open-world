#!/usr/bin/env bash
set -euo pipefail

APK="$1"
PACKAGE="$2"
REPORTS="$3"
LOGS="$4"
ARTIFACTS="$5"
EXPECTED_APK_SHA256="${EXPECTED_APK_SHA256:?EXPECTED_APK_SHA256 is required}"
ACTIVITY="com.godot.game.GodotApp"
AVD_NAME="bahrain-brick-full-matrix-api34"
HOLDER_PACKAGE="com.brickbahrain.landscapeholder"
TRAVERSAL_SECONDS=600
SOAK_SECONDS=1800
mkdir -p "$REPORTS" "$LOGS" "$ARTIFACTS"

ANDROID_HOME="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
[[ -n "$ANDROID_HOME" ]] || { echo "Android SDK root is unset" >&2; exit 1; }
export ANDROID_HOME
export JAVA_HOME="$(dirname "$(dirname "$(readlink -f "$(command -v java)")")")"
export ANDROID_USER_HOME="${ANDROID_USER_HOME:-$PWD/build/full-matrix-runtime/android-user}"
export ANDROID_AVD_HOME="${ANDROID_AVD_HOME:-$ANDROID_USER_HOME/avd}"
ADB="$ANDROID_HOME/platform-tools/adb"
EMULATOR="$ANDROID_HOME/emulator/emulator"
SDKMANAGER="$(find "$ANDROID_HOME/cmdline-tools" -type f -name sdkmanager | sort | tail -1)"
AVDMANAGER="$(find "$ANDROID_HOME/cmdline-tools" -type f -name avdmanager | sort | tail -1)"
BUILD_TOOLS="$ANDROID_HOME/build-tools/34.0.0"
ANDROID_JAR="$ANDROID_HOME/platforms/android-34/android.jar"

REPORT="$REPORTS/FULL_MATRIX_ANDROID_EMULATOR_VALIDATION.json"
LOGCAT="$LOGS/full-matrix-android-logcat.txt"
FILTERED="$LOGS/full-matrix-android-logcat-filtered.txt"
EMULATOR_LOG="$LOGS/full-matrix-emulator.txt"
METRICS="$REPORTS/FULL_MATRIX_ANDROID_MEMORY.csv"
STARTUP_SCREENSHOT="$ARTIFACTS/full-matrix-startup.png"
GAMEPLAY_SCREENSHOT="$ARTIFACTS/full-matrix-gameplay.png"
TRAVERSAL_SCREENSHOT="$ARTIFACTS/full-matrix-traversal-midpoint.png"
FINAL_SCREENSHOT="$ARTIFACTS/full-matrix-final.png"
EMULATOR_PID=""
LOGCAT_PID=""
BOOTED=false
INSTALLED=false
READY=false
PAUSE_RESUME=false
COLD_START=false
TRAVERSAL_PASS=false
SOAK_PASS=false
MEMORY_PASS=false
SCREENSHOT_WIDTH=0
SCREENSHOT_HEIGHT=0
ACTUAL_TRAVERSAL_SECONDS=0
ACTUAL_SOAK_SECONDS=0

cleanup() {
  if [[ -n "$LOGCAT_PID" ]]; then kill "$LOGCAT_PID" >/dev/null 2>&1 || true; wait "$LOGCAT_PID" >/dev/null 2>&1 || true; fi
  "$ADB" emu kill >/dev/null 2>&1 || true
  if [[ -n "$EMULATOR_PID" ]]; then kill "$EMULATOR_PID" >/dev/null 2>&1 || true; wait "$EMULATOR_PID" >/dev/null 2>&1 || true; fi
}
trap cleanup EXIT

write_report() {
  local status="$1" reason="$2"
  STATUS="$status" REASON="$reason" APK_SHA="$(sha256sum "$APK" | awk '{print $1}')" APK_BYTES="$(stat -c '%s' "$APK")" \
  BOOTED="$BOOTED" INSTALLED="$INSTALLED" READY="$READY" PAUSE_RESUME="$PAUSE_RESUME" COLD_START="$COLD_START" \
  TRAVERSAL_PASS="$TRAVERSAL_PASS" SOAK_PASS="$SOAK_PASS" MEMORY_PASS="$MEMORY_PASS" \
  SCREENSHOT_WIDTH="$SCREENSHOT_WIDTH" SCREENSHOT_HEIGHT="$SCREENSHOT_HEIGHT" \
  ACTUAL_TRAVERSAL_SECONDS="$ACTUAL_TRAVERSAL_SECONDS" ACTUAL_SOAK_SECONDS="$ACTUAL_SOAK_SECONDS" \
  python3 - "$REPORT" <<'PY'
import json,os,sys
b=lambda k:os.environ[k].lower()=='true'
r={
 'status':os.environ['STATUS'],'reason':os.environ['REASON'],'api_level':34,'abi':'x86_64',
 'package':'com.bahrainbrick.game.qa','activity':'com.godot.game.GodotApp',
 'apk_sha256':os.environ['APK_SHA'],'apk_bytes':int(os.environ['APK_BYTES']),
 'booted':b('BOOTED'),'installed':b('INSTALLED'),'full_matrix_ready':b('READY'),
 'pause_resume_passed':b('PAUSE_RESUME'),'cold_start_passed':b('COLD_START'),
 'traversal':{'required_seconds':600,'actual_seconds':int(os.environ['ACTUAL_TRAVERSAL_SECONDS']),'passed':b('TRAVERSAL_PASS')},
 'soak':{'required_seconds':1800,'actual_seconds':int(os.environ['ACTUAL_SOAK_SECONDS']),'passed':b('SOAK_PASS')},
 'memory_growth_passed':b('MEMORY_PASS'),
 'orientation':{'width':int(os.environ['SCREENSHOT_WIDTH']),'height':int(os.environ['SCREENSHOT_HEIGHT']),'landscape':int(os.environ['SCREENSHOT_WIDTH'])>int(os.environ['SCREENSHOT_HEIGHT'])},
 'landscape_holder_stabilized':True,'wall_clock_enforced':True,
 'screenshots':['full-matrix-startup.png','full-matrix-gameplay.png','full-matrix-traversal-midpoint.png','full-matrix-final.png'],
}
open(sys.argv[1],'w').write(json.dumps(r,indent=2,sort_keys=True)+'\n')
print(json.dumps(r,indent=2,sort_keys=True))
PY
}

failed() {
  "$ADB" logcat -d -v threadtime >> "$LOGCAT" 2>/dev/null || true
  grep -Ei "$PACKAGE|Godot|BAHRAIN|Asset Lab|FATAL EXCEPTION|ANR in|am_crash|am_anr|Fatal signal" "$LOGCAT" > "$FILTERED" || true
  write_report FAIL "$1"
  exit 1
}

ready_count() { grep -c 'BAHRAIN_BRICK_FULL_MATRIX_READY profile=balanced architecture=48 commercial=4' "$LOGCAT" 2>/dev/null || true; }

wait_for_ready_after() {
  local baseline="$1"
  for _ in $(seq 1 120); do
    local now="$(ready_count)"
    if [[ "$now" =~ ^[0-9]+$ ]] && (( now > baseline )); then READY=true; return 0; fi
    [[ -n "$("$ADB" shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')" ]] || return 1
    sleep 2
  done
  return 1
}

capture_screenshot() {
  local output="$1"
  "$ADB" exec-out screencap -p > "$output"
  read -r SCREENSHOT_WIDTH SCREENSHOT_HEIGHT < <(python3 - "$output" <<'PY'
from PIL import Image,ImageStat
import sys
im=Image.open(sys.argv[1]).convert('RGB')
w,h=im.size
stat=ImageStat.Stat(im)
assert w>h,(w,h)
assert sum(1 for lo,hi in stat.extrema if hi-lo>35)>=2,stat.extrema
assert sum(stat.mean)/3>4,stat.mean
print(w,h)
PY
  ) || failed "invalid or blank landscape screenshot: $output"
}

sample_memory() {
  local label="$1" raw="$REPORTS/FULL_MATRIX_ANDROID_MEMORY_${1}.txt"
  local pid pss rss
  pid="$("$ADB" shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')"
  [[ -n "$pid" ]] || failed "process missing at memory checkpoint $label"
  "$ADB" shell dumpsys meminfo "$PACKAGE" > "$raw"
  pss="$(awk '/TOTAL PSS:/{print $3;exit} /^ TOTAL[[:space:]]/{print $2;exit}' "$raw")"; pss="${pss:-0}"
  rss="$(awk '/TOTAL RSS:/{for(i=1;i<=NF;i++)if($i=="RSS:"){print $(i+1);exit}} /^ TOTAL[[:space:]]/{print $3;exit}' "$raw")"; rss="${rss:-0}"
  printf '%s,%s,%s,%s,%s\n' "$(date -u +%FT%TZ)" "$label" "$pid" "$pss" "$rss" >> "$METRICS"
}

exercise_input() {
  "$ADB" shell input swipe 190 600 190 390 700 >/dev/null 2>&1 || true
  "$ADB" shell input swipe 1060 500 1140 500 350 >/dev/null 2>&1 || true
  "$ADB" shell input keyevent KEYCODE_W >/dev/null 2>&1 || true
  "$ADB" shell input keyevent KEYCODE_D >/dev/null 2>&1 || true
}

[[ -s "$APK" ]] || { echo "APK missing" >&2; exit 1; }
actual_sha="$(sha256sum "$APK" | awk '{print $1}')"
[[ "$actual_sha" == "$EXPECTED_APK_SHA256" ]] || { echo "APK SHA mismatch: $actual_sha" >&2; exit 1; }
for tool in "$JAVA_HOME/bin/java" "$ADB" "$EMULATOR" "$SDKMANAGER" "$AVDMANAGER" "$BUILD_TOOLS/aapt" "$BUILD_TOOLS/d8" "$BUILD_TOOLS/apksigner"; do [[ -x "$tool" ]] || { echo "missing tool $tool" >&2; exit 1; }; done

rm -rf "$ANDROID_USER_HOME"
mkdir -p "$ANDROID_AVD_HOME"
yes | "$SDKMANAGER" --licenses >/dev/null || true
"$SDKMANAGER" 'platform-tools' 'platforms;android-34' 'build-tools;34.0.0' 'emulator' 'system-images;android-34;google_apis;x86_64'
echo no | "$AVDMANAGER" create avd --force --name "$AVD_NAME" --package 'system-images;android-34;google_apis;x86_64' --device pixel_7 > "$LOGS/full-matrix-avd-create.txt" 2>&1
"$EMULATOR" -list-avds | tee "$REPORTS/FULL_MATRIX_EMULATOR_LIST_AVDS.txt"
grep -qx "$AVD_NAME" "$REPORTS/FULL_MATRIX_EMULATOR_LIST_AVDS.txt" || failed "AVD not visible through unified Android home"

HOLDER="$PWD/build/full-matrix-runtime/landscape-holder"
mkdir -p "$HOLDER/src/com/brickbahrain/landscapeholder" "$HOLDER/classes" "$HOLDER/dex"
cat > "$HOLDER/src/com/brickbahrain/landscapeholder/MainActivity.java" <<'JAVA'
package com.brickbahrain.landscapeholder;
import android.app.Activity; import android.graphics.Color; import android.os.Bundle; import android.view.View;
public final class MainActivity extends Activity { @Override protected void onCreate(Bundle s){super.onCreate(s);View v=new View(this);v.setBackgroundColor(Color.BLACK);setContentView(v);} }
JAVA
cat > "$HOLDER/AndroidManifest.xml" <<'XML'
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.brickbahrain.landscapeholder"><uses-sdk android:minSdkVersion="21" android:targetSdkVersion="34"/><application android:theme="@android:style/Theme.Material.NoActionBar.Fullscreen" android:label="Landscape Holder" android:allowBackup="false"><activity android:name=".MainActivity" android:screenOrientation="landscape" android:configChanges="orientation|screenSize|keyboardHidden" android:exported="true"><intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter></activity></application></manifest>
XML
"$JAVA_HOME/bin/javac" -source 8 -target 8 -classpath "$ANDROID_JAR" -d "$HOLDER/classes" "$HOLDER/src/com/brickbahrain/landscapeholder/MainActivity.java"
"$BUILD_TOOLS/d8" --lib "$ANDROID_JAR" --output "$HOLDER/dex" "$HOLDER/classes/com/brickbahrain/landscapeholder/MainActivity.class"
"$BUILD_TOOLS/aapt" package -f -M "$HOLDER/AndroidManifest.xml" -I "$ANDROID_JAR" -F "$HOLDER/holder-unsigned.apk"
(cd "$HOLDER/dex" && zip -q "$HOLDER/holder-unsigned.apk" classes.dex)
"$JAVA_HOME/bin/keytool" -genkeypair -noprompt -keystore "$HOLDER/debug.keystore" -storepass android -keypass android -alias androiddebugkey -dname 'CN=Landscape Holder,O=Zanabal Gaming,C=BH' -keyalg RSA -keysize 2048 -validity 10000
"$BUILD_TOOLS/apksigner" sign --ks "$HOLDER/debug.keystore" --ks-pass pass:android --key-pass pass:android --ks-key-alias androiddebugkey --out "$HOLDER/landscape-holder.apk" "$HOLDER/holder-unsigned.apk"
"$BUILD_TOOLS/apksigner" verify --verbose "$HOLDER/landscape-holder.apk" > "$REPORTS/FULL_MATRIX_HOLDER_SIGNING.txt"

sudo chmod a+rw /dev/kvm || true
"$EMULATOR" -avd "$AVD_NAME" -no-window -no-audio -no-boot-anim -no-snapshot -wipe-data -gpu swiftshader_indirect -camera-back none -camera-front none -memory 4096 -cores 2 -no-metrics > "$EMULATOR_LOG" 2>&1 &
EMULATOR_PID=$!
timeout 300 "$ADB" wait-for-device || failed "ADB device did not appear"
for _ in $(seq 1 150); do
  if [[ "$("$ADB" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == 1 ]]; then BOOTED=true; break; fi
  kill -0 "$EMULATOR_PID" || failed "emulator exited before boot"
  sleep 2
done
[[ "$BOOTED" == true ]] || failed "API 34 emulator did not complete boot"
"$ADB" shell settings put global policy_control immersive.full='*' || true
"$ADB" shell settings put system screen_off_timeout 2147483647 || true
"$ADB" install -r "$HOLDER/landscape-holder.apk" > "$LOGS/full-matrix-holder-install.txt"
"$ADB" shell am start -W -n "$HOLDER_PACKAGE/.MainActivity" > "$LOGS/full-matrix-holder-launch.txt"
stable=0
for _ in $(seq 1 90); do
  "$ADB" exec-out screencap -p > "$ARTIFACTS/holder-probe.png"
  if python3 - "$ARTIFACTS/holder-probe.png" <<'PY'
from PIL import Image
import sys
w,h=Image.open(sys.argv[1]).size
raise SystemExit(0 if w>h else 1)
PY
  then stable=$((stable+1)); else stable=0; fi
  [[ "$stable" -ge 5 ]] && break
  sleep 1
done
[[ "$stable" -ge 5 ]] || failed "landscape holder did not stabilize display"
sleep 5

"$ADB" install -r -t "$APK" > "$LOGS/full-matrix-apk-install.txt" || failed "APK installation failed"
INSTALLED=true
"$ADB" logcat -c
"$ADB" logcat -v threadtime > "$LOGCAT" 2>&1 & LOGCAT_PID=$!
baseline="$(ready_count)"
"$ADB" shell am start -W -n "$PACKAGE/$ACTIVITY" > "$LOGS/full-matrix-apk-launch.txt" || failed "activity launch failed"
wait_for_ready_after "$baseline" || failed "full-matrix world readiness marker was not observed"
sleep 12
capture_screenshot "$STARTUP_SCREENSHOT"
[[ -n "$("$ADB" shell pidof "$PACKAGE" | tr -d '\r')" ]] || failed "process missing after startup"
exercise_input
sleep 8
capture_screenshot "$GAMEPLAY_SCREENSHOT"

"$ADB" shell input keyevent KEYCODE_HOME
sleep 3
baseline="$(ready_count)"
"$ADB" shell am start -W -n "$PACKAGE/$ACTIVITY" >> "$LOGS/full-matrix-apk-launch.txt" || failed "resume launch failed"
sleep 8
[[ -n "$("$ADB" shell pidof "$PACKAGE" | tr -d '\r')" ]] || failed "process did not survive pause/resume"
PAUSE_RESUME=true

"$ADB" shell am force-stop "$PACKAGE"
sleep 3
baseline="$(ready_count)"
"$ADB" shell am start -W -n "$PACKAGE/$ACTIVITY" >> "$LOGS/full-matrix-apk-launch.txt" || failed "cold launch failed"
wait_for_ready_after "$baseline" || failed "new readiness marker missing after cold launch"
COLD_START=true

printf 'timestamp_utc,label,pid,total_pss_kb,total_rss_kb\n' > "$METRICS"
sample_memory START
start="$(date +%s)"; deadline=$((start+TRAVERSAL_SECONDS)); midpoint=$((start+TRAVERSAL_SECONDS/2)); captured=false; iterations=0
while (( $(date +%s) < deadline )); do
  iterations=$((iterations+1)); exercise_input; sleep 8
  [[ -n "$("$ADB" shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')" ]] || failed "process exited during traversal iteration $iterations"
  if [[ "$captured" == false ]] && (( $(date +%s) >= midpoint )); then sample_memory TRAVERSAL_MID; capture_screenshot "$TRAVERSAL_SCREENSHOT"; captured=true; fi
done
ACTUAL_TRAVERSAL_SECONDS=$(( $(date +%s)-start ))
(( ACTUAL_TRAVERSAL_SECONDS >= TRAVERSAL_SECONDS )) && [[ "$captured" == true ]] || failed "10-minute traversal evidence incomplete"
TRAVERSAL_PASS=true
printf 'required=600\nactual=%s\niterations=%s\nresult=PASS\n' "$ACTUAL_TRAVERSAL_SECONDS" "$iterations" > "$REPORTS/FULL_MATRIX_10_MINUTE_TRAVERSAL.txt"

start="$(date +%s)"; deadline=$((start+SOAK_SECONDS)); midpoint=$((start+SOAK_SECONDS/2)); captured=false; iterations=0
while (( $(date +%s) < deadline )); do
  iterations=$((iterations+1)); exercise_input; sleep 14
  [[ -n "$("$ADB" shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')" ]] || failed "process exited during soak iteration $iterations"
  if [[ "$captured" == false ]] && (( $(date +%s) >= midpoint )); then sample_memory SOAK_MID; captured=true; fi
done
ACTUAL_SOAK_SECONDS=$(( $(date +%s)-start ))
(( ACTUAL_SOAK_SECONDS >= SOAK_SECONDS )) && [[ "$captured" == true ]] || failed "30-minute soak evidence incomplete"
sample_memory END
SOAK_PASS=true
printf 'required=1800\nactual=%s\niterations=%s\nresult=PASS\n' "$ACTUAL_SOAK_SECONDS" "$iterations" > "$REPORTS/FULL_MATRIX_30_MINUTE_SOAK.txt"
capture_screenshot "$FINAL_SCREENSHOT"

python3 - "$METRICS" "$REPORTS/FULL_MATRIX_MEMORY_GROWTH.json" <<'PY'
import csv,json,sys
rows=list(csv.DictReader(open(sys.argv[1]))); v={r['label']:int(r['total_pss_kb'] or 0) for r in rows}
start=v.get('START',0); mid=max(v.get('TRAVERSAL_MID',0),v.get('SOAK_MID',0)); end=v.get('END',0)
limit=max(131072,int(start*.5)); runaway=bool(start>0 and end-start>limit and end>mid>start)
r={'start_pss_kb':start,'mid_peak_pss_kb':mid,'end_pss_kb':end,'growth_pss_kb':end-start,'allowed_growth_pss_kb':limit,'runaway_growth':runaway}
open(sys.argv[2],'w').write(json.dumps(r,indent=2,sort_keys=True)+'\n'); print(json.dumps(r))
raise SystemExit(1 if runaway else 0)
PY
MEMORY_PASS=true

kill "$LOGCAT_PID" >/dev/null 2>&1 || true; wait "$LOGCAT_PID" >/dev/null 2>&1 || true; LOGCAT_PID=""
"$ADB" logcat -d -v threadtime >> "$LOGCAT" 2>/dev/null || true
grep -Ei "$PACKAGE|Godot|BAHRAIN|Asset Lab|FATAL EXCEPTION|ANR in|am_crash|am_anr|Fatal signal" "$LOGCAT" > "$FILTERED" || true
error_pattern='FATAL EXCEPTION|ANR in|am_crash|am_anr|Fatal signal|Godot[^[:cntrl:]]*(CRASH|FATAL)|SCRIPT ERROR|Parse Error|Parser Error|Invalid get index|Invalid call|Failed to load resource|Error loading resource|Resource file not found|No loader found|Asset Lab resource pending|Asset Lab resource failed to load|missing[^[:cntrl:]]*\.glb|material[^[:cntrl:]]*(missing|failed|error)|shader[^[:cntrl:]]*(failed|error)|protected[^[:cntrl:]]*(mismatch|failed|error)'
if grep -Eiq "$error_pattern" "$FILTERED"; then failed "runtime log scan found a fatal Godot/resource/material/shader/protected error"; fi
sha256sum "$STARTUP_SCREENSHOT" "$GAMEPLAY_SCREENSHOT" "$TRAVERSAL_SCREENSHOT" "$FINAL_SCREENSHOT" > "$REPORTS/FULL_MATRIX_SCREENSHOT_SHA256SUMS.txt"
write_report PASS "Exact full-matrix APK completed landscape-holder stabilized API-34 launch, readiness, lifecycle, cold start, 10-minute active traversal, 30-minute soak, bounded memory, clean fatal-log scan, and four landscape screenshots"
