#!/usr/bin/env bash
set -euo pipefail
GODOT_BIN="$1"
GAME_ROOT="$2"
APK_OUTPUT="$3"
EXPECTED_PACKAGE="$4"
REPORT_ROOT="$5"
LOG_ROOT="$6"
EXPECTED_VERSION_CODE="${VERSION_CODE:-1404}"
EXPECTED_VERSION_NAME="${VERSION_NAME:-1.4.0.4-premium-visual-qa}"
SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
BUILD_TOOLS_DIR="$SDK_ROOT/build-tools/${ANDROID_BUILD_TOOLS:-34.0.0}"
AAPT="$BUILD_TOOLS_DIR/aapt"
APKSIGNER="$BUILD_TOOLS_DIR/apksigner"
ZIPALIGN="$BUILD_TOOLS_DIR/zipalign"
for tool in "$AAPT" "$APKSIGNER" "$ZIPALIGN"; do test -x "$tool"; done
mkdir -p "$(dirname "$APK_OUTPUT")" "$REPORT_ROOT" "$LOG_ROOT"
KEYSTORE="${RUNNER_TEMP:-/tmp}/bahrain-brick-asset-production-debug.keystore"
rm -f "$KEYSTORE"
keytool -genkeypair -noprompt -keystore "$KEYSTORE" -storepass android -alias androiddebugkey -keypass android -keyalg RSA -keysize 2048 -validity 10000 -dname 'CN=Bahrain Brick Asset Production CI,O=Zanabal Gaming,C=BH'
python3 - "$GAME_ROOT/export_presets.cfg" "$KEYSTORE" "$EXPECTED_PACKAGE" "$EXPECTED_VERSION_CODE" "$EXPECTED_VERSION_NAME" <<'PY'
from pathlib import Path
import re,sys
path=Path(sys.argv[1]); text=path.read_text(); key=Path(sys.argv[2]).resolve().as_posix(); package,code,name=sys.argv[3:]
replacements=[
 (r'(?m)^keystore/debug=.*$',f'keystore/debug="{key}"'),
 (r'(?m)^version/code=.*$',f'version/code={code}'),
 (r'(?m)^version/name=.*$',f'version/name="{name}"'),
 (r'(?m)^package/unique_name=.*$',f'package/unique_name="{package}"'),
]
for pattern,replacement in replacements:
    text,count=re.subn(pattern,replacement,text)
    if count != 1: raise SystemExit(f'export preset replacement count={count}: {pattern}')
path.write_text(text)
PY
"$GODOT_BIN" --headless --path "$GAME_ROOT" --verbose --export-debug Android "$APK_OUTPUT" 2>&1 | tee "$LOG_ROOT/android-export.log"
test -s "$APK_OUTPUT"
unzip -t "$APK_OUTPUT" > "$LOG_ROOT/apk-zip-integrity.txt"
sha256sum "$APK_OUTPUT" | tee "$REPORT_ROOT/APK_SHA256SUM.txt"
stat -c '%n %s' "$APK_OUTPUT" | tee "$REPORT_ROOT/APK_SIZE.txt"
"$AAPT" dump badging "$APK_OUTPUT" | tee "$REPORT_ROOT/APK_BADGING.txt"
grep -q "package: name='$EXPECTED_PACKAGE' versionCode='$EXPECTED_VERSION_CODE' versionName='$EXPECTED_VERSION_NAME'" "$REPORT_ROOT/APK_BADGING.txt"
"$AAPT" dump xmltree "$APK_OUTPUT" AndroidManifest.xml | tee "$REPORT_ROOT/APK_MANIFEST.txt"
grep -Eq 'android:screenOrientation.*(0xb|=11)' "$REPORT_ROOT/APK_MANIFEST.txt"
"$APKSIGNER" verify --verbose --print-certs "$APK_OUTPUT" | tee "$REPORT_ROOT/APK_SIGNING.txt"
"$ZIPALIGN" -c -v 4 "$APK_OUTPUT" | tee "$REPORT_ROOT/APK_ZIPALIGN.txt"
