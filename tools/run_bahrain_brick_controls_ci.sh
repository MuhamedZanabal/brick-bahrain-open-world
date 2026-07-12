#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-recovery/v14}"
APK_NAME="${APK_NAME:-bahrain_brick_v14.0.2-controls-qa.apk}"
PACKAGE_NAME="${PACKAGE_NAME:-com.bahrainbrick.game.qa}"
JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}"
export JAVA_HOME
ROOT_DIR="$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$ROOT_DIR")"
WORKSPACE="$(pwd)"
LOG_DIR="$ROOT_DIR/build/logs"
CI_DIR="$ROOT_DIR/build/ci"
APK_PATH="$ROOT_DIR/build/$APK_NAME"
mkdir -p "$LOG_DIR" "$CI_DIR"

log(){ printf '\n===== %s =====\n' "$1"; }

log "Resolve Android SDK and Godot export templates"
SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
if [[ -z "$SDK_ROOT" ]]; then
  AAPT_CANDIDATE="$(find /opt /root /usr/local /usr/lib -type f -path '*/build-tools/*/aapt' 2>/dev/null | sort -V | tail -1)"
  [[ -x "$AAPT_CANDIDATE" ]]
  SDK_ROOT="${AAPT_CANDIDATE%%/build-tools/*}"
fi
export ANDROID_SDK_ROOT="$SDK_ROOT" ANDROID_HOME="$SDK_ROOT"
mkdir -p "$HOME/.local/share/godot/export_templates" "$HOME/.config/godot"
rm -rf "$HOME/.local/share/godot/export_templates/4.3.stable"
cp -a /root/.local/share/godot/export_templates/4.3.stable "$HOME/.local/share/godot/export_templates/4.3.stable"
[[ ! -d /root/.config/godot ]] || cp -a /root/.config/godot/. "$HOME/.config/godot/"

log "Reconstruct source and apply Bahrain Brick overlay"
python3 "$WORKSPACE/tools/prepare_v14_fallback.py" "$ROOT_DIR" \
  --provenance-out "$ROOT_DIR/build/v14-source-provenance.json" | tee "$LOG_DIR/fallback-preparation.log"
python3 "$WORKSPACE/tools/apply_bahrain_brick_overlay.py" "$ROOT_DIR" \
  --report "$ROOT_DIR/build/BAHRAIN_BRICK_OVERLAY_REPORT.json" | tee "$LOG_DIR/overlay-application.log"

log "Generate ephemeral QA signing identity"
KEYSTORE_DIR="${RUNNER_TEMP:-/tmp}/bahrain-brick-controls-qa"
KEYSTORE_PATH="$KEYSTORE_DIR/debug.keystore"
mkdir -p "$KEYSTORE_DIR" && rm -f "$KEYSTORE_PATH"
keytool -genkeypair -noprompt -keystore "$KEYSTORE_PATH" -storepass android \
  -alias androiddebugkey -keypass android -keyalg RSA -keysize 2048 -validity 10000 \
  -dname "CN=Bahrain Brick Controls QA,O=Zanabal Gaming,C=BH" \
  2>&1 | tee "$LOG_DIR/keytool-generation.log"
python3 - "$ROOT_DIR/export_presets.cfg" "$KEYSTORE_PATH" <<'PY'
import pathlib,re,sys
p=pathlib.Path(sys.argv[1]); k=pathlib.Path(sys.argv[2]).resolve().as_posix(); s=p.read_text()
s,n=re.subn(r'(?m)^keystore/debug=.*$', f'keystore/debug="{k}"', s)
assert n==1, n
p.write_text(s)
PY

log "Configure Godot Android editor paths"
cp "$WORKSPACE/tools/configure_godot_android_editor.gd" "$CI_DIR/configure_godot_android_editor.gd"
set -o pipefail
godot --headless --editor --path "$ROOT_DIR" --script res://build/ci/configure_godot_android_editor.gd \
  2>&1 | tee "$LOG_DIR/android-editor-configuration.log"
status="${PIPESTATUS[0]}"; set +o pipefail; [[ "$status" -eq 0 ]]

log "Import and compile"
set -o pipefail
godot --headless --path "$ROOT_DIR" --editor --quit --verbose 2>&1 | tee "$LOG_DIR/godot-import.log"
status="${PIPESTATUS[0]}"; set +o pipefail; [[ "$status" -eq 0 ]]
! grep -E 'SCRIPT ERROR:|ERROR: Failed to load script|Failed to create an autoload' "$LOG_DIR/godot-import.log"

log "Run baseline runtime smoke"
set -o pipefail
timeout 420 godot --headless --path "$ROOT_DIR" --audio-driver Dummy res://build/ci/runtime_smoke_runner_v14.tscn \
  2>&1 | tee "$LOG_DIR/runtime-smoke-baseline.log"
status="${PIPESTATUS[0]}"; set +o pipefail; [[ "$status" -eq 0 ]]
grep -q ', 0 failed' "$LOG_DIR/runtime-smoke-baseline.log"

log "Run actual mobile touch pipeline test"
set -o pipefail
timeout 420 godot --headless --path "$ROOT_DIR" --audio-driver Dummy res://scenes/mobile_input_pipeline_test.tscn \
  2>&1 | tee "$LOG_DIR/mobile-input-pipeline.log"
status="${PIPESTATUS[0]}"; set +o pipefail; [[ "$status" -eq 0 ]]
grep -q 'Bahrain Brick mobile input pipeline test complete:' "$LOG_DIR/mobile-input-pipeline.log"
grep -q ', 0 failed' "$LOG_DIR/mobile-input-pipeline.log"

log "Export Android QA APK"
set -o pipefail
godot --headless --path "$ROOT_DIR" --verbose --export-debug Android "$APK_PATH" \
  2>&1 | tee "$LOG_DIR/android-export.log"
status="${PIPESTATUS[0]}"; set +o pipefail; [[ "$status" -eq 0 && -s "$APK_PATH" ]]

log "Verify APK"
AAPT_BIN="$(command -v aapt || find "$ANDROID_SDK_ROOT" -type f -name aapt | sort -V | tail -1)"
APKSIGNER_BIN="$(command -v apksigner || find "$ANDROID_SDK_ROOT" -type f -name apksigner | sort -V | tail -1)"
ZIPALIGN_BIN="$(command -v zipalign || find "$ANDROID_SDK_ROOT" -type f -name zipalign | sort -V | tail -1)"
unzip -t "$APK_PATH" | tee "$LOG_DIR/apk-zip-integrity.txt"
sha256sum "$APK_PATH" | tee "$APK_PATH.sha256"
"$AAPT_BIN" dump badging "$APK_PATH" | tee "$LOG_DIR/aapt-badging.txt"
grep -q "package: name='$PACKAGE_NAME' versionCode='1402' versionName='1.4.0.2-controls-qa'" "$LOG_DIR/aapt-badging.txt"
grep -q "application-label:'Bahrain Brick'" "$LOG_DIR/aapt-badging.txt"
! grep -q 'android.permission.RECORD_AUDIO' "$LOG_DIR/aapt-badging.txt"
"$AAPT_BIN" dump xmltree "$APK_PATH" AndroidManifest.xml | tee "$LOG_DIR/aapt-manifest.txt"
grep -Eq 'android:screenOrientation.*(0xb|=11)' "$LOG_DIR/aapt-manifest.txt"
"$APKSIGNER_BIN" verify --verbose --print-certs "$APK_PATH" | tee "$LOG_DIR/apksigner-verification.txt"
"$ZIPALIGN_BIN" -c -v 4 "$APK_PATH" | tee "$LOG_DIR/zipalign-verification.txt"

log "Package patched source"
python3 - "$ROOT_DIR" <<'PY'
import hashlib,json,pathlib,zipfile,sys
root=pathlib.Path(sys.argv[1]); out=root/'build'/'bahrain_brick_v14.0.2-controls-source.zip'
exclude={'.git','.godot'}
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in sorted(root.rglob('*')):
    rel=p.relative_to(root)
    if not p.is_file() or any(part in exclude for part in rel.parts) or rel.parts[:1]==('build',): continue
    z.write(p,rel.as_posix())
sha=hashlib.sha256(out.read_bytes()).hexdigest()
(out.with_suffix(out.suffix+'.sha256')).write_text(f'{sha}  {out.name}\n')
print(json.dumps({'source_zip':out.name,'bytes':out.stat().st_size,'sha256':sha},indent=2))
PY

log "Bahrain Brick controls QA complete"
