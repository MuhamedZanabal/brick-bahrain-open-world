#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-recovery/v14}"
BASELINE="${2:-baseline/v14}"
APK_NAME="${APK_NAME:-bahrain_brick_v14.0.4-premium-visual-qa.apk}"
PACKAGE_NAME="${PACKAGE_NAME:-com.bahrainbrick.game.qa}"
LOG="$ROOT/build/logs"
REPORT="$ROOT/build/reports"
VIS="$ROOT/build/visual_evidence"
PREMIUM_VIS="$ROOT/build/premium_visual_evidence"
mkdir -p "$LOG" "$REPORT" "$VIS" "$PREMIUM_VIS"

run_godot() {
  local name="$1"; shift
  set -o pipefail
  "$@" 2>&1 | tee "$LOG/$name.log"
  local status="${PIPESTATUS[0]}"
  set +o pipefail
  test "$status" -eq 0
}

python3 tools/verify_frozen_controls.py "$ROOT" \
  --json-out "$REPORT/FROZEN_CONTROLS_RECOVERED_SOURCE.json" \
  --markdown-out "$REPORT/FROZEN_CONTROLS_RECOVERED_SOURCE.md"

mkdir -p "$BASELINE/build/premium_visual_evidence/before" "$BASELINE/build/logs"
python3 tools/apply_bahrain_brick_premium_world_overlay.py "$BASELINE" --evidence-only \
  --report "$BASELINE/build/premium_visual_evidence/BASELINE_EVIDENCE_HARNESS_REPORT.json"
godot --headless --path "$BASELINE" --editor --quit \
  2>&1 | tee "$BASELINE/build/logs/godot-import-before.log"
set -o pipefail
timeout 1500 xvfb-run -a -s "-screen 0 1280x720x24" \
  godot --path "$BASELINE" --audio-driver Dummy --display-driver x11 \
  --rendering-method gl_compatibility res://scenes/premium_world_visual_evidence.tscn -- \
  --output=res://build/premium_visual_evidence/before \
  2>&1 | tee "$BASELINE/build/logs/world-evidence-before.log"
status="${PIPESTATUS[0]}"; set +o pipefail
test "$status" -eq 0
grep -q 'PREMIUM WORLD VISUAL EVIDENCE COMPLETE' "$BASELINE/build/logs/world-evidence-before.log"

python3 tools/apply_premium_overlay_resilient.py "$ROOT" \
  --report "$REPORT/PREMIUM_WORLD_OVERLAY_REPORT.json" \
  2>&1 | tee "$LOG/premium-world-overlay.log"
python3 tools/apply_premium_validation_corrections.py "$ROOT" \
  --report "$REPORT/RUNTIME_DEFECT_CORRECTIONS.json"
python3 tools/verify_frozen_controls.py "$ROOT" \
  --json-out "$REPORT/FROZEN_CONTROLS_PRE_TEST.json" \
  --markdown-out "$REPORT/FROZEN_CONTROLS_PRE_TEST.md"

mkdir -p "$ROOT/build/ci/test-user-data"/{smoke,controls,presentation,premium-world,premium-presentation}
run_godot godot-import-premium godot --headless --path "$ROOT" --editor --quit --verbose
run_godot runtime-smoke-premium env XDG_DATA_HOME="$PWD/$ROOT/build/ci/test-user-data/smoke" \
  timeout 700 godot --headless --path "$ROOT" --audio-driver Dummy res://build/ci/runtime_smoke_runner_v14.tscn
grep -q '43 passed, 0 failed' "$LOG/runtime-smoke-premium.log"
run_godot mobile-input-regression-premium env XDG_DATA_HOME="$PWD/$ROOT/build/ci/test-user-data/controls" \
  timeout 700 godot --headless --path "$ROOT" --audio-driver Dummy res://scenes/mobile_input_pipeline_test.tscn
grep -q '28 passed, 0 failed' "$LOG/mobile-input-regression-premium.log"
run_godot presentation-flow-premium env XDG_DATA_HOME="$PWD/$ROOT/build/ci/test-user-data/presentation" \
  timeout 700 godot --headless --path "$ROOT" --audio-driver Dummy \
  res://scenes/presentation_flow_test.tscn -- --presentation-test
grep -q '10 passed, 0 failed' "$LOG/presentation-flow-premium.log"
run_godot premium-world-acceptance env XDG_DATA_HOME="$PWD/$ROOT/build/ci/test-user-data/premium-world" \
  timeout 700 godot --headless --path "$ROOT" --audio-driver Dummy res://scenes/premium_world_acceptance_test.tscn
grep -q '12 passed, 0 failed' "$LOG/premium-world-acceptance.log"
PREMIUM_PRESENTATION_SCENE='res://scenes/premium_presentation_acceptance_test.tscn'
test -f "$ROOT/scenes/premium_presentation_acceptance_test.tscn"
run_godot premium-presentation-acceptance env XDG_DATA_HOME="$PWD/$ROOT/build/ci/test-user-data/premium-presentation" \
  timeout 700 godot --headless --path "$ROOT" --audio-driver Dummy "$PREMIUM_PRESENTATION_SCENE"
PREMIUM_SUMMARY="$(grep -Eo '[0-9]+ passed, [0-9]+ failed' "$LOG/premium-presentation-acceptance.log" | tail -1)"
[[ "$PREMIUM_SUMMARY" =~ ^([0-9]+)\ passed,\ 0\ failed$ ]] || {
  echo "premium-presentation summary missing or failed: $PREMIUM_SUMMARY" >&2; exit 1; }
PREMIUM_COUNT="${BASH_REMATCH[1]}"
python3 - "$REPORT/PREMIUM_PRESENTATION_RESULT.json" "$PREMIUM_PRESENTATION_SCENE" "$PREMIUM_COUNT" <<'PY'
import json,sys
from pathlib import Path
out,scene,count=sys.argv[1:]
Path(out).write_text(json.dumps({'scene':scene,'configured_assertion_count':int(count),'passed':int(count),'failed':0,'process_exit_code':0},indent=2)+'\n')
PY

python3 tools/scan_godot_runtime_errors.py "$LOG" \
  --json-out "$REPORT/CRITICAL_RUNTIME_ERROR_SCAN_PRE_EVIDENCE.json" \
  --markdown-out "$REPORT/CRITICAL_RUNTIME_ERROR_SCAN_PRE_EVIDENCE.md"

mkdir -p "$PREMIUM_VIS/after" "$VIS/startup_frames" "$VIS/frames" "$VIS/screenshots"
run_godot world-evidence-after timeout 1500 xvfb-run -a -s "-screen 0 1280x720x24" \
  godot --path "$ROOT" --audio-driver Dummy --display-driver x11 --rendering-method gl_compatibility \
  res://scenes/premium_world_visual_evidence.tscn -- --output=res://build/premium_visual_evidence/after
grep -q 'PREMIUM WORLD VISUAL EVIDENCE COMPLETE' "$LOG/world-evidence-after.log"
run_godot presentation-visual-premium timeout 1200 xvfb-run -a -s "-screen 0 1280x720x24" \
  godot --path "$ROOT" --audio-driver Dummy --display-driver x11 --rendering-method gl_compatibility \
  res://scenes/presentation_visual_evidence.tscn -- --presentation-test
grep -q 'presentation visual evidence complete' "$LOG/presentation-visual-premium.log"
run_godot mobile-input-visual-premium timeout 1200 xvfb-run -a -s "-screen 0 1280x720x24" \
  godot --path "$ROOT" --audio-driver Dummy --display-driver x11 --rendering-method gl_compatibility \
  res://scenes/mobile_input_visual_evidence.tscn
grep -q 'rendered control evidence complete' "$LOG/mobile-input-visual-premium.log"
ffmpeg -y -framerate 15 -i "$VIS/startup_frames/frame_%04d.png" \
  -vf 'scale=1280:-2:flags=lanczos' -c:v libx264 -preset medium -crf 21 -pix_fmt yuv420p \
  "$VIS/bahrain_brick_v14.0.4_startup.mp4" >/dev/null 2>&1
ffmpeg -y -framerate 12 -i "$VIS/frames/frame_%04d.png" \
  -vf 'scale=1280:-2:flags=lanczos' -c:v libx264 -preset medium -crf 22 -pix_fmt yuv420p \
  "$VIS/bahrain_brick_v14.0.4_gameplay.mp4" >/dev/null 2>&1

python3 tools/scan_godot_runtime_errors.py "$LOG" \
  --json-out "$REPORT/CRITICAL_RUNTIME_ERROR_SCAN.json" \
  --markdown-out "$REPORT/CRITICAL_RUNTIME_ERROR_SCAN.md"

python3 - "$BASELINE" "$ROOT" <<'PY'
from pathlib import Path
from PIL import Image,ImageDraw,ImageStat
import json,sys
baseline,root=map(Path,sys.argv[1:])
before=baseline/'build/premium_visual_evidence/before'; after=root/'build/premium_visual_evidence/after'
out=root/'build/premium_visual_evidence/comparisons'; out.mkdir(parents=True,exist_ok=True)
names=['city_road','waterfront','building_area','daylight','player_character','vehicle','hud_walking','hud_vehicle']
metrics=[]
for name in names:
 b=Image.open(before/f'{name}.png').convert('RGB'); a=Image.open(after/f'{name}.png').convert('RGB')
 if b.size!=(1280,720) or a.size!=(1280,720): raise SystemExit(f'bad dimensions {name}: {b.size}/{a.size}')
 c=Image.new('RGB',(2560,760),(18,18,22)); c.paste(b,(0,40)); c.paste(a,(1280,40)); d=ImageDraw.Draw(c)
 d.text((20,12),f'BEFORE — v1.4.0.3 — {name}',fill='white'); d.text((1300,12),f'AFTER — v1.4.0.4 — {name}',fill='white'); c.save(out/f'{name}_before_after.png',optimize=True)
 def stat(im):
  s=im.resize((160,90)); px=list(s.getdata()); total=len(px)
  return {'mean_luminance':round(sum(ImageStat.Stat(s).mean)/3,3),'near_white_ratio':round(sum(1 for r,g,b in px if min(r,g,b)>246)/total,6),'near_black_ratio':round(sum(1 for r,g,b in px if max(r,g,b)<12)/total,6)}
 metrics.append({'view':name,'before':stat(b),'after':stat(a)})
report={'classification':'hosted GL Compatibility/software rendering; not physical Android performance','views':metrics,'baseline_runtime':json.loads((before/'PREMIUM_WORLD_VISUAL_EVIDENCE.json').read_text()),'premium_runtime':json.loads((after/'PREMIUM_WORLD_VISUAL_EVIDENCE.json').read_text()),'physical_android_tested':False}
(root/'build/reports/PREMIUM_VISUAL_COMPARISON_AND_PERFORMANCE.json').write_text(json.dumps(report,indent=2)+'\n')
PY
python3 tools/verify_frozen_controls.py "$ROOT" \
  --json-out "$REPORT/FROZEN_CONTROLS_POST_TEST.json" \
  --markdown-out "$REPORT/FROZEN_CONTROLS_POST_TEST.md"

bash tools/install_godot_43_templates.sh "$REPORT/GODOT_EXPORT_TEMPLATE_REPORT.json" "$ROOT"
KEYSTORE_DIR="${RUNNER_TEMP:-/tmp}/bahrain-brick-premium-qa"; mkdir -p "$KEYSTORE_DIR"
KEYSTORE_PATH="$KEYSTORE_DIR/debug.keystore"; rm -f "$KEYSTORE_PATH"
keytool -genkeypair -noprompt -keystore "$KEYSTORE_PATH" -storepass android -alias androiddebugkey \
  -keypass android -keyalg RSA -keysize 2048 -validity 10000 \
  -dname 'CN=Bahrain Brick Premium Visual QA,O=Zanabal Gaming,C=BH'
python3 - "$ROOT/export_presets.cfg" "$KEYSTORE_PATH" <<'PY'
from pathlib import Path
import re,sys
p=Path(sys.argv[1]); t=p.read_text(); key=Path(sys.argv[2]).resolve().as_posix()
t,n=re.subn(r'(?m)^keystore/debug=.*$',f'keystore/debug="{key}"',t)
if n!=1: raise SystemExit(f'keystore replacement count={n}')
p.write_text(t)
PY
run_godot android-export-premium godot --headless --path "$ROOT" --verbose --export-debug Android "$ROOT/build/$APK_NAME"
test -s "$ROOT/build/$APK_NAME"
SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
if [[ -z "$SDK_ROOT" ]]; then C="$(find /opt /root /usr/local /usr/lib -type f -path '*/build-tools/*/aapt' 2>/dev/null | sort -V | tail -1)"; SDK_ROOT="${C%%/build-tools/*}"; fi
AAPT="$(command -v aapt || find "$SDK_ROOT" -type f -name aapt | sort -V | tail -1)"
APKSIGNER="$(command -v apksigner || find "$SDK_ROOT" -type f -name apksigner | sort -V | tail -1)"
ZIPALIGN="$(command -v zipalign || find "$SDK_ROOT" -type f -name zipalign | sort -V | tail -1)"
for tool in "$AAPT" "$APKSIGNER" "$ZIPALIGN"; do test -x "$tool"; done
unzip -t "$ROOT/build/$APK_NAME" > "$LOG/apk-zip-integrity-premium.txt"
sha256sum "$ROOT/build/$APK_NAME" | tee "$ROOT/build/$APK_NAME.sha256"
"$AAPT" dump badging "$ROOT/build/$APK_NAME" | tee "$LOG/aapt-badging-premium.txt"
grep -q "package: name='$PACKAGE_NAME' versionCode='1404' versionName='1.4.0.4-premium-visual-qa'" "$LOG/aapt-badging-premium.txt"
grep -q "application-label:'Bahrain Brick'" "$LOG/aapt-badging-premium.txt"
! grep -q 'android.permission.RECORD_AUDIO' "$LOG/aapt-badging-premium.txt"
"$AAPT" dump xmltree "$ROOT/build/$APK_NAME" AndroidManifest.xml | tee "$LOG/aapt-manifest-premium.txt"
grep -Eq 'android:screenOrientation.*(0xb|=11)' "$LOG/aapt-manifest-premium.txt"
"$APKSIGNER" verify --verbose --print-certs "$ROOT/build/$APK_NAME" | tee "$LOG/apksigner-premium.txt"
"$ZIPALIGN" -c -v 4 "$ROOT/build/$APK_NAME" | tee "$LOG/zipalign-premium.txt"
python3 - "$ROOT/build/$APK_NAME" "$LOG/aapt-badging-premium.txt" "$LOG/aapt-manifest-premium.txt" "$LOG/apksigner-premium.txt" "$REPORT/APK_METADATA_REPORT.json" <<'PY'
from pathlib import Path
import hashlib,json,re,sys,zipfile
apk,badging,manifest,signing,out=map(Path,sys.argv[1:]); b=badging.read_text(); s=signing.read_text()
def one(pattern,text,label):
 x=re.search(pattern,text,re.M)
 if not x: raise SystemExit(f'APK metadata missing {label}')
 return x.group(1)
abis=[]
x=re.search(r"native-code:.*",b)
if x: abis=re.findall(r"'([^']+)'",x.group(0))
report={'filename':apk.name,'size_bytes':apk.stat().st_size,'sha256':hashlib.sha256(apk.read_bytes()).hexdigest(),'package_name':one(r"package: name='([^']+)'",b,'package'),'version_code':int(one(r"versionCode='([^']+)'",b,'version code')),'version_name':one(r"versionName='([^']+)'",b,'version name'),'application_label':one(r"application-label:'([^']+)'",b,'label'),'minimum_sdk':one(r"sdkVersion:'([^']+)'",b,'min SDK'),'target_sdk':one(r"targetSdkVersion:'([^']+)'",b,'target SDK'),'orientation':'sensorLandscape','supported_abis':abis,'debug_or_release':'debug','signing_state':'verified ephemeral QA certificate','signer_report':s.strip(),'alignment':'verified 4-byte zip alignment','zip_entries':len(zipfile.ZipFile(apk).namelist())}
out.write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report,indent=2))
PY
python3 tools/verify_frozen_controls.py "$ROOT" \
  --json-out "$REPORT/FROZEN_CONTROLS_POST_EXPORT.json" \
  --markdown-out "$REPORT/FROZEN_CONTROLS_POST_EXPORT.md"

python3 tools/package_premium_validation_artifacts.py "$ROOT" \
  --apk-name "$APK_NAME" --premium-authority "${PREMIUM_AUTHORITY_SHA:-unknown}" \
  --validation-head "${VALIDATION_HEAD_SHA:-unknown}"
python3 tools/verify_frozen_controls.py "$ROOT" \
  --json-out "$REPORT/FROZEN_CONTROLS_POST_PACKAGE.json" \
  --markdown-out "$REPORT/FROZEN_CONTROLS_POST_PACKAGE.md"
