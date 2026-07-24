#!/usr/bin/env bash
set -euo pipefail
APK="${1:?APK path required}"
PACKAGE="${2:?package required}"
RENDERER="${3:?renderer required}"
OUT="${4:?output directory required}"
QUALITY="${5:-frozen_baseline}"
ADB="${ADB:-adb}"
mkdir -p "$OUT"
"$ADB" get-state | grep -q device
APK_SHA="$(sha256sum "$APK" | awk '{print $1}')"
printf '%s\n' "$APK_SHA" > "$OUT/apk.sha256"
{
  echo "manufacturer=$($ADB shell getprop ro.product.manufacturer | tr -d '\r')"
  echo "model=$($ADB shell getprop ro.product.model | tr -d '\r')"
  echo "soc=$($ADB shell getprop ro.soc.model | tr -d '\r')"
  echo "hardware=$($ADB shell getprop ro.hardware | tr -d '\r')"
  echo "android=$($ADB shell getprop ro.build.version.release | tr -d '\r')"
  echo "api=$($ADB shell getprop ro.build.version.sdk | tr -d '\r')"
  echo "abi=$($ADB shell getprop ro.product.cpu.abi | tr -d '\r')"
  echo "fingerprint=$($ADB shell getprop ro.build.fingerprint | tr -d '\r')"
  echo "resolution=$($ADB shell wm size | tr -d '\r')"
  echo "density=$($ADB shell wm density | tr -d '\r')"
  echo "renderer=$RENDERER"
  echo "quality=$QUALITY"
} > "$OUT/device.properties"
"$ADB" shell cat /proc/meminfo > "$OUT/device-meminfo.txt" || true
"$ADB" shell dumpsys SurfaceFlinger > "$OUT/surfaceflinger.txt" || true
"$ADB" shell dumpsys thermalservice > "$OUT/thermal-start.txt" || true
"$ADB" uninstall "$PACKAGE" > "$OUT/uninstall-before.txt" 2>&1 || true
"$ADB" install -r -t "$APK" > "$OUT/install.txt" 2>&1
"$ADB" logcat -c
START_MS="$(date +%s%3N)"
"$ADB" shell monkey -p "$PACKAGE" -c android.intent.category.LAUNCHER 1 > "$OUT/launch.txt" 2>&1
PID=""
for _ in $(seq 1 60); do PID="$($ADB shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')"; test -n "$PID" && break; sleep 1; done
END_MS="$(date +%s%3N)"
printf '%s\n' "$PID" > "$OUT/pid.txt"
printf '%s\n' "$((END_MS-START_MS))" > "$OUT/cold-start-ms.txt"
"$ADB" logcat -d -v threadtime > "$OUT/logcat-startup.txt"
for _ in $(seq 1 300); do
  "$ADB" logcat -d -v threadtime > "$OUT/logcat-runtime.txt"
  grep -q 'G0_ANDROID_CAPTURE_FRAME frame=300' "$OUT/logcat-runtime.txt" && break
  sleep 2
done
"$ADB" exec-out screencap -p > "$OUT/screenshot.png" || true
"$ADB" shell dumpsys gfxinfo "$PACKAGE" reset > "$OUT/gfxinfo-reset.txt" 2>&1 || true
echo "Perform the required traversal on the device for five minutes now."
sleep 300
"$ADB" shell dumpsys gfxinfo "$PACKAGE" framestats > "$OUT/gfxinfo-framestats.txt" 2>&1 || true
"$ADB" shell dumpsys meminfo "$PACKAGE" > "$OUT/app-meminfo.txt" 2>&1 || true
"$ADB" shell dumpsys thermalservice > "$OUT/thermal-end.txt" 2>&1 || true
"$ADB" shell input keyevent 3
sleep 4
"$ADB" shell monkey -p "$PACKAGE" -c android.intent.category.LAUNCHER 1 > "$OUT/resume.txt" 2>&1 || true
sleep 8
"$ADB" logcat -d -v threadtime > "$OUT/logcat-final.txt"
grep -Ei 'FATAL EXCEPTION|ANR in |am_anr|Fatal signal|SIGSEGV|DEBUG.*backtrace|tombstone' "$OUT/logcat-final.txt" > "$OUT/crash-scan.txt" || true
python3 - "$OUT" "$APK_SHA" "$RENDERER" "$QUALITY" <<'PY'
import json,re,sys
from pathlib import Path
out=Path(sys.argv[1]); prop={}
for line in (out/'device.properties').read_text(errors='replace').splitlines():
    if '=' in line: k,v=line.split('=',1); prop[k]=v
log=(out/'logcat-final.txt').read_text(errors='replace')
result={'schema_version':1,'test_status':'INCOMPLETE','device':{'manufacturer':prop.get('manufacturer',''),'exact_model':prop.get('model',''),'soc':prop.get('soc') or prop.get('hardware',''),'gpu':'See surfaceflinger.txt','ram_bytes':None,'android_version':prop.get('android',''),'api_level':int(prop.get('api') or 0),'screen_resolution':prop.get('resolution',''),'build_fingerprint':prop.get('fingerprint','')},'renderer':sys.argv[3],'quality_preset':sys.argv[4],'apk_sha256':sys.argv[2],'cold_start':{'launch_exit_code':0,'process_alive':bool((out/'pid.txt').read_text().strip()),'milliseconds':int((out/'cold-start-ms.txt').read_text())},'scene_readiness':{'ready_marker':'BAHRAIN_BRICK_SOUQ_SLICE_READY assets=35 pedestrians=12 traffic=6' in log,'mission_marker':'BAHRAIN_BRICK_KARAK_MISSION_STARTED' in log,'seconds':None},'traversal':{'duration_seconds':300,'completed':False,'frame_metrics_file':'gfxinfo-framestats.txt'},'memory':{'peak_pss_kb':None,'peak_rss_kb':None},'thermal':{'start_state':'thermal-start.txt','end_state':'thermal-end.txt'},'lifecycle':{'pause_observed':'G0_ANDROID_LIFECYCLE_PAUSED' in log,'resume_observed':'G0_ANDROID_LIFECYCLE_RESUMED' in log,'process_alive_after_resume':False},'crash_scan':{'fatal_count':len(re.findall(r'FATAL EXCEPTION|Fatal signal|SIGSEGV',log,re.I)),'anr_count':len(re.findall(r'ANR in |am_anr',log,re.I)),'native_crash_count':len(re.findall(r'tombstone|DEBUG.*backtrace',log,re.I)),'log_file':'logcat-final.txt'},'notes':['Human must confirm traversal completion, thermal acceptability, and device tier.']}
(out/'device_result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
PY
printf 'Raw device evidence written to %s\n' "$OUT"
