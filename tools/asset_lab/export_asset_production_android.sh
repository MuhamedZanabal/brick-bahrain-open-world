#!/usr/bin/env bash
set -euo pipefail
GODOT_BIN="$1"
GAME_ROOT="$2"
APK_OUTPUT="$3"
EXPECTED_PACKAGE="$4"
REPORT_ROOT="$5"
LOG_ROOT="$6"
mkdir -p "$(dirname "$APK_OUTPUT")" "$REPORT_ROOT" "$LOG_ROOT"
KEYSTORE="${RUNNER_TEMP:-/tmp}/bahrain-brick-asset-production-debug.keystore"
rm -f "$KEYSTORE"
keytool -genkeypair -noprompt -keystore "$KEYSTORE" -storepass android -alias androiddebugkey -keypass android -keyalg RSA -keysize 2048 -validity 10000 -dname 'CN=Bahrain Brick Asset Production CI,O=Zanabal Gaming,C=BH'
python3 - "$GAME_ROOT/export_presets.cfg" "$KEYSTORE" <<'PY'
from pathlib import Path
import re,sys
path=Path(sys.argv[1]); text=path.read_text(); key=Path(sys.argv[2]).resolve().as_posix()
text,count=re.subn(r'(?m)^keystore/debug=.*$',f'keystore/debug="{key}"',text)
if count != 1: raise SystemExit(f'keystore replacement count={count}')
path.write_text(text)
PY
"$GODOT_BIN" --headless --path "$GAME_ROOT" --verbose --export-debug Android "$APK_OUTPUT" 2>&1 | tee "$LOG_ROOT/android-export.log"
test -s "$APK_OUTPUT"
unzip -t "$APK_OUTPUT" > "$LOG_ROOT/apk-zip-integrity.txt"
sha256sum "$APK_OUTPUT" | tee "$REPORT_ROOT/APK_SHA256SUM.txt"
stat -c '%n %s' "$APK_OUTPUT" | tee "$REPORT_ROOT/APK_SIZE.txt"
aapt dump badging "$APK_OUTPUT" | tee "$REPORT_ROOT/APK_BADGING.txt"
grep -q "package: name='$EXPECTED_PACKAGE' versionCode='1' versionName='1.0.0'" "$REPORT_ROOT/APK_BADGING.txt"
aapt dump xmltree "$APK_OUTPUT" AndroidManifest.xml | tee "$REPORT_ROOT/APK_MANIFEST.txt"
apksigner verify --verbose --print-certs "$APK_OUTPUT" | tee "$REPORT_ROOT/APK_SIGNING.txt"
zipalign -c -v 4 "$APK_OUTPUT" | tee "$REPORT_ROOT/APK_ZIPALIGN.txt"
