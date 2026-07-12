#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-recovery/v14}"
APK_NAME="${APK_NAME:-brick_bahrain_v14.0.1-landscape-fallback-qa.apk}"
PACKAGE_NAME="${PACKAGE_NAME:-com.brickbahrain.openworld.fallbackqa}"
JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}"
export JAVA_HOME

ROOT_DIR="$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$ROOT_DIR")"
WORKSPACE="$(pwd)"
LOG_DIR="$ROOT_DIR/build/logs"
CI_DIR="$ROOT_DIR/build/ci"
APK_PATH="$ROOT_DIR/build/$APK_NAME"
mkdir -p "$LOG_DIR" "$CI_DIR"

log() {
  printf '\n===== %s =====\n' "$1"
}

log "Resolve Android SDK and Godot export templates"
SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
if [[ -z "$SDK_ROOT" ]]; then
  AAPT_CANDIDATE="$(find /opt /root /usr/local /usr/lib -type f -path '*/build-tools/*/aapt' 2>/dev/null | sort -V | tail -1)"
  [[ -x "$AAPT_CANDIDATE" ]]
  SDK_ROOT="${AAPT_CANDIDATE%%/build-tools/*}"
fi
[[ -d "$SDK_ROOT" ]]
export ANDROID_SDK_ROOT="$SDK_ROOT"
export ANDROID_HOME="$SDK_ROOT"

mkdir -p "$HOME/.local/share/godot/export_templates" "$HOME/.config/godot"
[[ -d /root/.local/share/godot/export_templates/4.3.stable ]]
rm -rf "$HOME/.local/share/godot/export_templates/4.3.stable"
cp -a /root/.local/share/godot/export_templates/4.3.stable \
  "$HOME/.local/share/godot/export_templates/4.3.stable"
if [[ -d /root/.config/godot ]]; then
  cp -a /root/.config/godot/. "$HOME/.config/godot/"
fi

{
  printf 'HOME=%s\n' "$HOME"
  printf 'JAVA_HOME=%s\n' "$JAVA_HOME"
  printf 'ANDROID_SDK_ROOT=%s\n' "$ANDROID_SDK_ROOT"
  printf 'GODOT=%s\n' "$(godot --version)"
  java -version 2>&1
} | tee "$LOG_DIR/export-environment.txt"
find "$HOME/.local/share/godot/export_templates/4.3.stable" -maxdepth 1 -type f \
  -printf '%f\n' | sort | tee "$LOG_DIR/export-templates.txt"

grep -qx 'android_debug.apk' "$LOG_DIR/export-templates.txt"
grep -qx 'android_release.apk' "$LOG_DIR/export-templates.txt"

log "Reconstruct and prepare isolated fallback source"
python3 "$WORKSPACE/tools/prepare_v14_fallback.py" "$ROOT_DIR" \
  --provenance-out "$ROOT_DIR/build/v14-source-provenance.json" \
  | tee "$LOG_DIR/fallback-preparation.log"

log "Generate ephemeral QA signing identity outside project tree"
KEYSTORE_DIR="${RUNNER_TEMP:-/tmp}/brick-bahrain-v14-fallback"
KEYSTORE_PATH="$KEYSTORE_DIR/debug.keystore"
mkdir -p "$KEYSTORE_DIR"
rm -f "$KEYSTORE_PATH"
keytool -genkeypair -noprompt \
  -keystore "$KEYSTORE_PATH" \
  -storepass android \
  -alias androiddebugkey \
  -keypass android \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000 \
  -dname "CN=Brick Bahrain Fallback QA,O=Zanabal Gaming,C=BH" \
  2>&1 | tee "$LOG_DIR/keytool-generation.log"

python3 - "$ROOT_DIR/export_presets.cfg" "$KEYSTORE_PATH" <<'PY'
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
keystore = pathlib.Path(sys.argv[2]).resolve().as_posix()
text = path.read_text(encoding="utf-8")
text, count = re.subn(r'(?m)^keystore/debug=.*$', f'keystore/debug="{keystore}"', text)
if count != 1:
    raise SystemExit(f"keystore/debug replacements={count}")
path.write_text(text, encoding="utf-8")
PY

log "Configure Godot Android editor paths"
cp "$WORKSPACE/tools/configure_godot_android_editor.gd" \
  "$CI_DIR/configure_godot_android_editor.gd"
set -o pipefail
godot --headless --editor --path "$ROOT_DIR" \
  --script res://build/ci/configure_godot_android_editor.gd \
  2>&1 | tee "$LOG_DIR/android-editor-configuration.log"
status="${PIPESTATUS[0]}"
set +o pipefail
[[ "$status" -eq 0 ]]
grep -Fq "configured_java_sdk=$JAVA_HOME" "$LOG_DIR/android-editor-configuration.log"
grep -Fq "configured_android_sdk=$ANDROID_SDK_ROOT" "$LOG_DIR/android-editor-configuration.log"

log "Import project and compile scripts/resources"
set -o pipefail
godot --headless --path "$ROOT_DIR" --editor --quit --verbose \
  2>&1 | tee "$LOG_DIR/godot-import.log"
status="${PIPESTATUS[0]}"
set +o pipefail
[[ "$status" -eq 0 ]]
if grep -E 'SCRIPT ERROR:|ERROR: Failed to load script|Failed to create an autoload' "$LOG_DIR/godot-import.log"; then
  echo 'Godot import contained script or autoload failures.' >&2
  exit 1
fi

log "Run project-loaded runtime smoke test"
set -o pipefail
timeout 420 godot --headless --path "$ROOT_DIR" --audio-driver Dummy \
  res://build/ci/runtime_smoke_runner_v14.tscn \
  2>&1 | tee "$LOG_DIR/runtime-smoke-v14-project-loaded.log"
status="${PIPESTATUS[0]}"
set +o pipefail
printf 'runtime_exit=%s\n' "$status" | tee "$LOG_DIR/runtime-exit.txt"
[[ "$status" -eq 0 ]]
grep -q 'Brick Bahrain v1.4 runtime smoke test complete:' \
  "$LOG_DIR/runtime-smoke-v14-project-loaded.log"
grep -q ', 0 failed' "$LOG_DIR/runtime-smoke-v14-project-loaded.log"

log "Export Android fallback QA APK"
set -o pipefail
godot --headless --path "$ROOT_DIR" --verbose \
  --export-debug "Android" "$APK_PATH" \
  2>&1 | tee "$LOG_DIR/android-export.log"
status="${PIPESTATUS[0]}"
set +o pipefail
[[ "$status" -eq 0 ]]
[[ -s "$APK_PATH" ]]

log "Verify APK archive, identity, orientation, alignment, and signature"
unzip -t "$APK_PATH" | tee "$LOG_DIR/apk-zip-integrity.txt"
sha256sum "$APK_PATH" | tee "$APK_PATH.sha256"

AAPT_BIN="$(command -v aapt || true)"
APKSIGNER_BIN="$(command -v apksigner || true)"
ZIPALIGN_BIN="$(command -v zipalign || true)"
[[ -n "$AAPT_BIN" ]] || AAPT_BIN="$(find "$ANDROID_SDK_ROOT" -type f -name aapt 2>/dev/null | sort -V | tail -1)"
[[ -n "$APKSIGNER_BIN" ]] || APKSIGNER_BIN="$(find "$ANDROID_SDK_ROOT" -type f -name apksigner 2>/dev/null | sort -V | tail -1)"
[[ -n "$ZIPALIGN_BIN" ]] || ZIPALIGN_BIN="$(find "$ANDROID_SDK_ROOT" -type f -name zipalign 2>/dev/null | sort -V | tail -1)"
[[ -x "$AAPT_BIN" ]]
[[ -x "$APKSIGNER_BIN" ]]
[[ -x "$ZIPALIGN_BIN" ]]

"$AAPT_BIN" dump badging "$APK_PATH" | tee "$LOG_DIR/aapt-badging.txt"
grep -q "package: name='$PACKAGE_NAME' versionCode='1401' versionName='1.4.0.1-fallback-qa'" \
  "$LOG_DIR/aapt-badging.txt"
"$AAPT_BIN" dump xmltree "$APK_PATH" AndroidManifest.xml | tee "$LOG_DIR/aapt-manifest.txt"
grep -Eq 'android:screenOrientation.*(0xb|=11)' "$LOG_DIR/aapt-manifest.txt"
"$APKSIGNER_BIN" verify --verbose --print-certs "$APK_PATH" \
  | tee "$LOG_DIR/apksigner-verification.txt"
"$ZIPALIGN_BIN" -c -v 4 "$APK_PATH" | tee "$LOG_DIR/zipalign-verification.txt"

python3 - "$APK_PATH" <<'PY' | tee "$LOG_DIR/apk-content-verification.txt"
import json
import sys
import zipfile

apk = sys.argv[1]
with zipfile.ZipFile(apk) as archive:
    names = archive.namelist()
    native = [name for name in names if name.startswith("lib/") and name.endswith(".so")]
    assets = [name for name in names if name.startswith("assets/") and not name.endswith("/")]
    result = {
        "entries": len(names),
        "native_libraries": len(native),
        "asset_entries": len(assets),
        "manifest_present": "AndroidManifest.xml" in names,
    }
    if not result["manifest_present"] or not native or not assets:
        raise SystemExit(json.dumps(result))
    print(json.dumps(result, indent=2))
PY

log "Generate build provenance"
python3 - "$ROOT_DIR" "$APK_PATH" <<'PY'
import hashlib
import json
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
apk = pathlib.Path(sys.argv[2])
runtime = (root / "build/logs/runtime-smoke-v14-project-loaded.log").read_text(
    encoding="utf-8", errors="replace"
)
match = re.search(r"complete: (\d+) passed, (\d+) failed", runtime)
if not match:
    raise SystemExit("runtime result summary missing")
provenance = json.loads((root / "build/v14-source-provenance.json").read_text())
provenance.update({
    "apk": apk.name,
    "apk_bytes": apk.stat().st_size,
    "apk_sha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
    "package": "com.brickbahrain.openworld.fallbackqa",
    "version_code": 1401,
    "version_name": "1.4.0.1-fallback-qa",
    "orientation": "sensorLandscape",
    "runtime_passed": int(match.group(1)),
    "runtime_failed": int(match.group(2)),
    "signing": "ephemeral Android debug certificate; controlled QA only",
    "signing_keystore_packaged": False,
    "physical_device_tested": False,
    "authority_warning": "historical fallback; must not replace v15.0.1 authority",
})
(root / "build/V14_FALLBACK_BUILD_PROVENANCE.json").write_text(
    json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(provenance, indent=2))
PY

log "Fallback QA build complete"
