#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-recovery/v14}"
WORKSPACE="$(pwd)"
ROOT_DIR="$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$ROOT_DIR")"
LOG_DIR="$ROOT_DIR/build/logs"
REPORT_DIR="$ROOT_DIR/build/reports"
VISUAL_DIR="$ROOT_DIR/build/visual_evidence"
TEST_DATA_ROOT="$ROOT_DIR/build/ci/test-user-data"
APK_NAME="bahrain_brick_v14.0.3-graphics-qa.apk"
APK_PATH="$ROOT_DIR/build/$APK_NAME"
PACKAGE_NAME="com.bahrainbrick.game.qa"
JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}"
export JAVA_HOME
mkdir -p "$LOG_DIR" "$REPORT_DIR" "$VISUAL_DIR"
rm -rf "$TEST_DATA_ROOT"
mkdir -p "$TEST_DATA_ROOT/runtime-smoke" "$TEST_DATA_ROOT/mobile-controls" "$TEST_DATA_ROOT/presentation"

log(){ printf '\n===== %s =====\n' "$1"; }

log "Reconstruct and verify accepted controls baseline"
APK_NAME="bahrain_brick_v14.0.2-controls-baseline.apk" \
PACKAGE_NAME="$PACKAGE_NAME" \
bash "$WORKSPACE/tools/run_bahrain_brick_controls_ci.sh" "$ROOT_DIR" \
  2>&1 | tee "$LOG_DIR/frozen-controls-baseline-build.log"
BASELINE_APK="$ROOT_DIR/build/bahrain_brick_v14.0.2-controls-baseline.apk"
[[ -s "$BASELINE_APK" ]]
BASELINE_APK_SHA="$(sha256sum "$BASELINE_APK" | awk '{print $1}')"
BASELINE_APK_BYTES="$(stat -c %s "$BASELINE_APK")"

log "Apply presentation-only graphics overlay"
python3 "$WORKSPACE/tools/apply_bahrain_brick_graphics_overlay.py" "$ROOT_DIR" \
  --report "$REPORT_DIR/BAHRAIN_BRICK_GRAPHICS_OVERLAY_REPORT.json" \
  2>&1 | tee "$LOG_DIR/graphics-overlay.log"

log "Enforce frozen mobile-control baseline"
python3 "$WORKSPACE/tools/verify_frozen_controls.py" "$ROOT_DIR" \
  --json-out "$REPORT_DIR/FROZEN_CONTROLS_VERIFICATION.json" \
  --markdown-out "$REPORT_DIR/FROZEN_CONTROLS_VERIFICATION.md" \
  2>&1 | tee "$LOG_DIR/frozen-controls-verification.log"

log "Generate graphics QA signing identity outside project tree"
KEYSTORE_DIR="${RUNNER_TEMP:-/tmp}/bahrain-brick-graphics-qa"
KEYSTORE_PATH="$KEYSTORE_DIR/debug.keystore"
mkdir -p "$KEYSTORE_DIR"
rm -f "$KEYSTORE_PATH"
keytool -genkeypair -noprompt \
  -keystore "$KEYSTORE_PATH" -storepass android \
  -alias androiddebugkey -keypass android \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -dname "CN=Bahrain Brick Graphics QA,O=Zanabal Gaming,C=BH" \
  2>&1 | tee "$LOG_DIR/keytool-graphics-qa.log"
python3 - "$ROOT_DIR/export_presets.cfg" "$KEYSTORE_PATH" <<'PY'
import pathlib,re,sys
path=pathlib.Path(sys.argv[1]); key=pathlib.Path(sys.argv[2]).resolve().as_posix()
text=path.read_text(encoding='utf-8')
text,count=re.subn(r'(?m)^keystore/debug=.*$', f'keystore/debug="{key}"', text)
if count != 1: raise SystemExit(f'keystore/debug replacements={count}')
path.write_text(text,encoding='utf-8')
PY

log "Import graphics and compile presentation scripts"
set -o pipefail
godot --headless --path "$ROOT_DIR" --editor --quit --verbose \
  2>&1 | tee "$LOG_DIR/godot-import-graphics.log"
status="${PIPESTATUS[0]}"; set +o pipefail
[[ "$status" -eq 0 ]]
if grep -E 'SCRIPT ERROR:|ERROR: Failed to load script|Failed to create an autoload' "$LOG_DIR/godot-import-graphics.log"; then
  echo "Godot graphics import contained script or autoload failures" >&2
  exit 1
fi

log "Run baseline project smoke after presentation integration"
set -o pipefail
env XDG_DATA_HOME="$TEST_DATA_ROOT/runtime-smoke" \
  timeout 500 godot --headless --path "$ROOT_DIR" --audio-driver Dummy \
  res://build/ci/runtime_smoke_runner_v14.tscn \
  2>&1 | tee "$LOG_DIR/runtime-smoke-after-graphics.log"
status="${PIPESTATUS[0]}"; set +o pipefail
[[ "$status" -eq 0 ]]
grep -q ', 0 failed' "$LOG_DIR/runtime-smoke-after-graphics.log"

log "Run unchanged 28-check mobile-control regression"
set -o pipefail
env XDG_DATA_HOME="$TEST_DATA_ROOT/mobile-controls" \
  timeout 500 godot --headless --path "$ROOT_DIR" --audio-driver Dummy \
  res://scenes/mobile_input_pipeline_test.tscn \
  2>&1 | tee "$LOG_DIR/mobile-input-regression-after-graphics.log"
status="${PIPESTATUS[0]}"; set +o pipefail
[[ "$status" -eq 0 ]]
grep -q 'Bahrain Brick mobile input pipeline test complete: 28 passed, 0 failed' \
  "$LOG_DIR/mobile-input-regression-after-graphics.log"

log "Run startup, menu, loading, settings and pause acceptance tests"
set -o pipefail
env XDG_DATA_HOME="$TEST_DATA_ROOT/presentation" \
  timeout 600 godot --headless --path "$ROOT_DIR" --audio-driver Dummy \
  res://scenes/presentation_flow_test.tscn -- --presentation-test \
  2>&1 | tee "$LOG_DIR/presentation-flow-test.log"
status="${PIPESTATUS[0]}"; set +o pipefail
[[ "$status" -eq 0 ]]
grep -q 'Bahrain Brick presentation flow test complete:' "$LOG_DIR/presentation-flow-test.log"
grep -q ', 0 failed' "$LOG_DIR/presentation-flow-test.log"
grep -q 'startup order is Zanabal Gaming then Mansoory Games' "$LOG_DIR/presentation-flow-test.log"
grep -q 'loading finishes at 100 percent' "$LOG_DIR/presentation-flow-test.log"
grep -q 'Android Back resumes from pause' "$LOG_DIR/presentation-flow-test.log"

log "Recheck controls hashes after all runtime tests"
python3 "$WORKSPACE/tools/verify_frozen_controls.py" "$ROOT_DIR" \
  --json-out "$REPORT_DIR/FROZEN_CONTROLS_POST_TEST_VERIFICATION.json" \
  --markdown-out "$REPORT_DIR/FROZEN_CONTROLS_POST_TEST_VERIFICATION.md" \
  2>&1 | tee "$LOG_DIR/frozen-controls-post-test-verification.log"

log "Export integrated Android graphics QA APK"
set -o pipefail
godot --headless --path "$ROOT_DIR" --verbose --export-debug Android "$APK_PATH" \
  2>&1 | tee "$LOG_DIR/android-export-graphics.log"
status="${PIPESTATUS[0]}"; set +o pipefail
[[ "$status" -eq 0 && -s "$APK_PATH" ]]

log "Verify final APK identity, privacy, orientation, archive and signature"
SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
if [[ -z "$SDK_ROOT" ]]; then
  AAPT_CANDIDATE="$(find /opt /root /usr/local /usr/lib -type f -path '*/build-tools/*/aapt' 2>/dev/null | sort -V | tail -1)"
  SDK_ROOT="${AAPT_CANDIDATE%%/build-tools/*}"
fi
export ANDROID_SDK_ROOT="$SDK_ROOT" ANDROID_HOME="$SDK_ROOT"
AAPT_BIN="$(command -v aapt || find "$SDK_ROOT" -type f -name aapt | sort -V | tail -1)"
APKSIGNER_BIN="$(command -v apksigner || find "$SDK_ROOT" -type f -name apksigner | sort -V | tail -1)"
ZIPALIGN_BIN="$(command -v zipalign || find "$SDK_ROOT" -type f -name zipalign | sort -V | tail -1)"
unzip -t "$APK_PATH" | tee "$LOG_DIR/apk-zip-integrity-graphics.txt"
sha256sum "$APK_PATH" | tee "$APK_PATH.sha256"
"$AAPT_BIN" dump badging "$APK_PATH" | tee "$LOG_DIR/aapt-badging-graphics.txt"
grep -q "package: name='$PACKAGE_NAME' versionCode='1403' versionName='1.4.0.3-graphics-qa'" \
  "$LOG_DIR/aapt-badging-graphics.txt"
grep -q "application-label:'Bahrain Brick'" "$LOG_DIR/aapt-badging-graphics.txt"
! grep -q 'android.permission.RECORD_AUDIO' "$LOG_DIR/aapt-badging-graphics.txt"
"$AAPT_BIN" dump xmltree "$APK_PATH" AndroidManifest.xml | tee "$LOG_DIR/aapt-manifest-graphics.txt"
grep -Eq 'android:screenOrientation.*(0xb|=11)' "$LOG_DIR/aapt-manifest-graphics.txt"
"$APKSIGNER_BIN" verify --verbose --print-certs "$APK_PATH" \
  | tee "$LOG_DIR/apksigner-graphics.txt"
"$ZIPALIGN_BIN" -c -v 4 "$APK_PATH" | tee "$LOG_DIR/zipalign-graphics.txt"

log "Generate size, change and build provenance reports"
python3 - "$ROOT_DIR" "$BASELINE_APK" "$APK_PATH" "$WORKSPACE/tools/bahrain_brick_graphics_manifest.json" <<'PY'
import hashlib,json,pathlib,sys,zipfile
root=pathlib.Path(sys.argv[1]); baseline=pathlib.Path(sys.argv[2]); apk=pathlib.Path(sys.argv[3]); manifest_path=pathlib.Path(sys.argv[4])
manifest=json.loads(manifest_path.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
with zipfile.ZipFile(apk) as z:
    names=z.namelist(); native=[n for n in names if n.startswith('lib/') and n.endswith('.so')]
    assets=[n for n in names if n.startswith('assets/') and not n.endswith('/')]
report={
  'evidence_class':'VERIFIED',
  'classification':'historical v1.4 graphics QA on frozen controls; not v15 authority',
  'frozen_controls_commit':'c5548465627942a2889a0bd09f8979c3a29fbcdd',
  'apk':apk.name,'apk_bytes':apk.stat().st_size,'apk_sha256':sha(apk),
  'package':'com.bahrainbrick.game.qa','version_code':1403,'version_name':'1.4.0.3-graphics-qa',
  'orientation':'sensorLandscape','app_label':'Bahrain Brick',
  'baseline_apk':baseline.name,'baseline_apk_bytes':baseline.stat().st_size,'baseline_apk_sha256':sha(baseline),
  'apk_size_delta_bytes':apk.stat().st_size-baseline.stat().st_size,
  'startup_sequence':['Zanabal Gaming','Mansoory Games','Bahrain Brick main menu'],
  'control_regression':'28 passed, 0 failed',
  'apk_entries':len(names),'native_libraries':len(native),'asset_entries':len(assets),
  'runtime_assets':manifest['runtime_assets'],
  'physical_android_tested':False,
  'signing':'ephemeral Android QA certificate; not production',
}
(root/'build/reports/BAHRAIN_BRICK_GRAPHICS_BUILD_PROVENANCE.json').write_text(json.dumps(report,indent=2)+'\n')
change={
  'modified_or_added':sorted(manifest['overlay_files']),
  'deleted':manifest['deleted_files'],
  'frozen_control_files_modified':False,
}
(root/'build/reports/GRAPHICS_FILE_CHANGE_MANIFEST.json').write_text(json.dumps(change,indent=2)+'\n')
print(json.dumps(report,indent=2))
PY

log "Sanitize source package and create complete integrated source ZIP"
rm -f "$ROOT_DIR/debug.keystore"
python3 - "$ROOT_DIR/export_presets.cfg" <<'PY'
import pathlib,re,sys
path=pathlib.Path(sys.argv[1]); text=path.read_text(encoding='utf-8')
text,count=re.subn(r'(?m)^keystore/debug=.*$', 'keystore/debug=""', text)
if count != 1: raise SystemExit(f'keystore/debug replacements={count}')
path.write_text(text,encoding='utf-8')
PY
python3 - "$ROOT_DIR" <<'PY'
import hashlib,pathlib,sys,zipfile
root=pathlib.Path(sys.argv[1]); out=root/'build'/'bahrain_brick_v14.0.3-graphics-source.zip'
exclude={'.git','.godot'}
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
    for path in sorted(root.rglob('*')):
        relative=path.relative_to(root)
        if not path.is_file() or any(part in exclude for part in relative.parts): continue
        if relative.parts[:1]==('build',) or path.name=='debug.keystore': continue
        archive.write(path,relative.as_posix())
digest=hashlib.sha256(out.read_bytes()).hexdigest()
out.with_suffix(out.suffix+'.sha256').write_text(f'{digest}  {out.name}\n')
print(f'{out.name} {out.stat().st_size} {digest}')
PY

log "Bahrain Brick graphics QA build complete"
