#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:?repository root is required}"
SOURCE_ROOT="${2:?accepted reconstruction root is required}"
EVIDENCE="${3:?Gate 4 evidence directory is required}"
SLOT="${4:?export slot is required: primary or secondary}"
GAME="$SOURCE_ROOT/game"
RECON_EVIDENCE="$SOURCE_ROOT/evidence"
REPORTS="$EVIDENCE/reports"
LOGS="$EVIDENCE/logs"
DIAGNOSTICS="$EVIDENCE/diagnostics"
ARTIFACTS="$EVIDENCE/artifacts"
TOOL="$REPO_ROOT/tools/vertical_slice/manama_souq_apk_evidence.py"
SIGNING_KEYSTORE="$REPO_ROOT/debug.keystore"
GODOT_ARCHIVE="$SOURCE_ROOT/downloads/Godot_v4.3-stable_linux.x86_64.zip"
GODOT_DIR="$SOURCE_ROOT/godot-editor"
TEMPLATE_DIR="$SOURCE_ROOT/godot-template-download"
XDG_DATA_HOME="$SOURCE_ROOT/godot-user-data"
APK="$ARTIFACTS/bahrain-brick-pr59-${SLOT}-debug.apk"
PRESET_NAME="Android"

ACCEPTED_HEAD="b12e1e012e256036e71066260a4c6392d26c3839"
ACCEPTED_MANIFEST="ba937afa335170ccaa726297fc23712a44e3295689a86640e1c1dbe6165701ab"
ACCEPTED_TREE="e0cfa6604569c13e1d75b2439d6936b7e2423ad5ba3715f033200335e864bc4e"
ACCEPTED_FILE_COUNT=1502
ACCEPTED_SOURCE_BYTES=369162800
GODOT_EDITOR_SHA512="fd52bb4ba8acc30ca5accd1c566d470ad7282f891ccc0995dfafabcf92bcf76280ce182bf9d80ebd885f3ed2165d01e1fc3f2928436b15498dfbd98656c2a45a"
TEMPLATE_NAME="Godot_v4.3-stable_export_templates.tpz"
TEMPLATE_URL="https://github.com/godotengine/godot-builds/releases/download/4.3-stable/$TEMPLATE_NAME"
TEMPLATE_SUMS_URL="https://github.com/godotengine/godot-builds/releases/download/4.3-stable/SHA512-SUMS.txt"
EXPECTED_IMAGE_VERSION="20260714.240.1"

case "$SLOT" in primary|secondary) ;; *) echo "invalid export slot: $SLOT" >&2; exit 2 ;; esac
mkdir -p "$REPORTS" "$LOGS" "$DIAGNOSTICS" "$ARTIFACTS" "$GODOT_DIR" "$TEMPLATE_DIR"
for required in "$GAME/project.godot" "$GAME/export_presets.cfg" "$SIGNING_KEYSTORE" "$RECON_EVIDENCE/FINAL_TREE_MANIFEST.json" "$RECON_EVIDENCE/FINAL_TREE_AUTHORITY.json" "$GODOT_ARCHIVE" "$TOOL"; do
  test -f "$required"
done

test "${ImageVersion:-}" = "$EXPECTED_IMAGE_VERSION"
grep -q '^VERSION="24.04.4 LTS"' /etc/os-release

cp "$RECON_EVIDENCE/FINAL_TREE_MANIFEST.json" "$REPORTS/FINAL_TREE_MANIFEST.json"
cp "$RECON_EVIDENCE/FINAL_TREE_AUTHORITY.json" "$REPORTS/FINAL_TREE_AUTHORITY.json"
cp "$RECON_EVIDENCE/FROZEN_CONTROLS_PRE.json" "$REPORTS/FROZEN_CONTROLS_PRE.json"
cp "$RECON_EVIDENCE/FROZEN_CONTROLS_POST.json" "$REPORTS/FROZEN_CONTROLS_RECONSTRUCTION_POST.json"

python3 - "$REPORTS/FINAL_TREE_MANIFEST.json" "$REPORTS/FINAL_TREE_AUTHORITY.json" <<'PY'
from pathlib import Path
import hashlib,json,sys
manifest=Path(sys.argv[1]); authority=json.loads(Path(sys.argv[2]).read_text())
assert hashlib.sha256(manifest.read_bytes()).hexdigest() == 'ba937afa335170ccaa726297fc23712a44e3295689a86640e1c1dbe6165701ab'
assert authority['aggregate_tree_sha256'] == 'e0cfa6604569c13e1d75b2439d6936b7e2423ad5ba3715f033200335e864bc4e'
assert authority['file_count'] == 1502
assert authority['total_bytes'] == 369162800
PY

python3 "$TOOL" authority --game "$GAME" --manifest "$REPORTS/FINAL_TREE_MANIFEST.json" --output "$REPORTS/SOURCE_AUTHORITY_INITIAL.json"
python3 "$TOOL" preset --preset "$GAME/export_presets.cfg" --project "$GAME/project.godot" --output "$REPORTS/EXPORT_PRESET_INSPECTION.json"
sha256sum "$GAME/export_presets.cfg" > "$REPORTS/EXPORT_PRESET_SHA256.txt"
sha256sum "$SIGNING_KEYSTORE" > "$REPORTS/DEBUG_KEYSTORE_SHA256.txt"
python3 - "$SIGNING_KEYSTORE" "$REPORTS/SIGNING_AUTHORITY.json" <<'PY'
from pathlib import Path
import hashlib,json,sys
key=Path(sys.argv[1]); out=Path(sys.argv[2])
out.write_text(json.dumps({
 'classification':'repository-approved QA/debug signing identity external to accepted source authority',
 'repository_path':'debug.keystore',
 'bytes':key.stat().st_size,
 'sha256':hashlib.sha256(key.read_bytes()).hexdigest(),
 'godot_override':'GODOT_ANDROID_KEYSTORE_DEBUG_PATH',
 'source_tree_mutated':False,
 'production_signing':False,
},indent=2,sort_keys=True)+'\n')
PY

rm -rf "$GAME/.godot" "$GODOT_DIR" "$XDG_DATA_HOME"
mkdir -p "$GODOT_DIR" "$XDG_DATA_HOME"
printf '%s  %s\n' "$GODOT_EDITOR_SHA512" "$GODOT_ARCHIVE" | sha512sum -c -
unzip -q "$GODOT_ARCHIVE" -d "$GODOT_DIR"
GODOT="$(find "$GODOT_DIR" -maxdepth 1 -type f -name 'Godot*' | head -1)"
test -n "$GODOT"
chmod +x "$GODOT"
test "$($GODOT --version)" = "4.3.stable.official.77dcf97d8"
"$GODOT" --version > "$REPORTS/GODOT_VERSION.txt"
sha512sum "$GODOT_ARCHIVE" > "$REPORTS/GODOT_EDITOR_ARCHIVE_SHA512.txt"

run_bounded() {
  local name="$1" seconds="$2"; shift 2
  local command_file="$DIAGNOSTICS/${name}.command.txt"
  local log_file="$DIAGNOSTICS/${name}.log"
  local exit_file="$DIAGNOSTICS/${name}.exit-code.txt"
  local timeout_file="$DIAGNOSTICS/${name}.timeout.txt"
  printf '%q ' "$@" > "$command_file"; printf '\n' >> "$command_file"
  set +e
  set -o pipefail
  timeout --signal=TERM --kill-after=30s "${seconds}s" "$@" 2>&1 | tee "$log_file"
  local code=${PIPESTATUS[0]}
  set -e
  printf '%s\n' "$code" > "$exit_file"
  if [[ "$code" -eq 124 || "$code" -eq 137 ]]; then printf 'true\n' > "$timeout_file"; else printf 'false\n' > "$timeout_file"; fi
  return "$code"
}

run_bounded clean-import 900 env XDG_DATA_HOME="$XDG_DATA_HOME" "$GODOT" --headless --path "$GAME" --editor --import --quit --verbose
python3 - "$DIAGNOSTICS" "$REPORTS/CLEAN_IMPORT.json" <<'PY'
from pathlib import Path
import json,re,sys
root=Path(sys.argv[1]); out=Path(sys.argv[2])
text=(root/'clean-import.log').read_text(errors='replace')
code=int((root/'clean-import.exit-code.txt').read_text())
timed=(root/'clean-import.timeout.txt').read_text().strip()=='true'
patterns={'script_error':r'SCRIPT ERROR','parse_error':r'Parse Error|Parser Error','failed_script':r'Failed to load script','autoload_error':r'Failed to create an autoload','fatal':r'\bFATAL\b|Fatal signal'}
counts={k:len(re.findall(v,text,re.I)) for k,v in patterns.items()}
value={'passed':code==0 and not timed and sum(counts.values())==0,'exit_code':code,'timed_out':timed,'error_counts':counts}
out.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
if not value['passed']: raise SystemExit(1)
PY
python3 "$TOOL" authority --game "$GAME" --manifest "$REPORTS/FINAL_TREE_MANIFEST.json" --output "$REPORTS/SOURCE_AUTHORITY_PRE_EXPORT.json"

rm -rf "$TEMPLATE_DIR"; mkdir -p "$TEMPLATE_DIR"
curl --fail --location --retry 3 --retry-delay 5 "$TEMPLATE_SUMS_URL" -o "$TEMPLATE_DIR/SHA512-SUMS.txt"
curl --fail --location --retry 3 --retry-delay 5 "$TEMPLATE_URL" -o "$TEMPLATE_DIR/$TEMPLATE_NAME"
EXPECTED_TEMPLATE_SHA512="$(python3 - "$TEMPLATE_DIR/SHA512-SUMS.txt" "$TEMPLATE_NAME" <<'PY'
from pathlib import Path
import sys
name=sys.argv[2]
for line in Path(sys.argv[1]).read_text().splitlines():
    parts=line.split()
    if len(parts)>=2 and parts[-1].lstrip('*./')==name:
        print(parts[0]); break
else: raise SystemExit('template checksum missing from official release manifest')
PY
)"
test "${#EXPECTED_TEMPLATE_SHA512}" -eq 128
printf '%s  %s\n' "$EXPECTED_TEMPLATE_SHA512" "$TEMPLATE_DIR/$TEMPLATE_NAME" | sha512sum -c -
sha256sum "$TEMPLATE_DIR/SHA512-SUMS.txt" > "$REPORTS/GODOT_TEMPLATE_SUMS_SHA256.txt"
sha512sum "$TEMPLATE_DIR/$TEMPLATE_NAME" > "$REPORTS/GODOT_EXPORT_TEMPLATE_SHA512.txt"
printf '%s\n' "$TEMPLATE_URL" > "$REPORTS/GODOT_EXPORT_TEMPLATE_URL.txt"
TEMPLATE_INSTALL="$XDG_DATA_HOME/godot/export_templates/4.3.stable"
mkdir -p "$TEMPLATE_INSTALL" "$TEMPLATE_DIR/unpacked"
unzip -q "$TEMPLATE_DIR/$TEMPLATE_NAME" -d "$TEMPLATE_DIR/unpacked"
test -d "$TEMPLATE_DIR/unpacked/templates"
cp -a "$TEMPLATE_DIR/unpacked/templates/." "$TEMPLATE_INSTALL/"
test -f "$TEMPLATE_INSTALL/android_debug.apk"
test -f "$TEMPLATE_INSTALL/android_release.apk"

SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
test -n "$SDK_ROOT"
BUILD_TOOLS="$SDK_ROOT/build-tools/34.0.0"
AAPT="$BUILD_TOOLS/aapt"
AAPT2="$BUILD_TOOLS/aapt2"
APKSIGNER="$BUILD_TOOLS/apksigner"
ZIPALIGN="$BUILD_TOOLS/zipalign"
APKANALYZER="$(find "$SDK_ROOT/cmdline-tools" -type f -path '*/bin/apkanalyzer' | sort | tail -1)"
SDKMANAGER="$(find "$SDK_ROOT/cmdline-tools" -type f -path '*/bin/sdkmanager' | sort | tail -1)"
ADB="$SDK_ROOT/platform-tools/adb"
for tool in "$AAPT" "$AAPT2" "$APKSIGNER" "$ZIPALIGN" "$APKANALYZER" "$SDKMANAGER" "$ADB" "$JAVA_HOME/bin/java" "$JAVA_HOME/bin/keytool"; do test -x "$tool"; done

{
  echo "GITHUB_ACTIONS_IMAGE_OS=${ImageOS:-unknown}"
  echo "GITHUB_ACTIONS_IMAGE_VERSION=${ImageVersion:-unknown}"
  uname -a
  cat /etc/os-release
} > "$REPORTS/HOST_IDENTITY.txt"
"$JAVA_HOME/bin/java" -version > "$REPORTS/JAVA_VERSION.txt" 2>&1
"$JAVA_HOME/bin/javac" -version > "$REPORTS/JAVAC_VERSION.txt" 2>&1
"$SDKMANAGER" --version > "$REPORTS/ANDROID_CMDLINE_TOOLS_VERSION.txt"
"$SDKMANAGER" --list_installed > "$REPORTS/ANDROID_SDK_PACKAGES.txt"
"$AAPT" version > "$REPORTS/AAPT_VERSION.txt" 2>&1
"$AAPT2" version > "$REPORTS/AAPT2_VERSION.txt" 2>&1
"$APKSIGNER" version > "$REPORTS/APKSIGNER_VERSION.txt" 2>&1
"$APKANALYZER" --version > "$REPORTS/APKANALYZER_VERSION.txt" 2>&1
"$ADB" version > "$REPORTS/PLATFORM_TOOLS_VERSION.txt" 2>&1
set +e; "$ZIPALIGN" -h > "$REPORTS/ZIPALIGN_VERSION.txt" 2>&1; set -e
"$JAVA_HOME/bin/keytool" -list -v -keystore "$SIGNING_KEYSTORE" -storepass android -alias androiddebugkey > "$REPORTS/DEBUG_SIGNING_IDENTITY.txt" 2>&1

python3 - "$REPORTS" "$EXPECTED_TEMPLATE_SHA512" <<'PY'
from pathlib import Path
import json,os,re,sys
r=Path(sys.argv[1])
def text(name): return (r/name).read_text(errors='replace').strip()
def package_revision(name):
    match=re.search(rf'^{re.escape(name)}\s+\|\s+([^|\s]+)', text('ANDROID_SDK_PACKAGES.txt'), re.M)
    return match.group(1) if match else None
value={
 'godot_editor':{'version':text('GODOT_VERSION.txt'),'archive_sha512':text('GODOT_EDITOR_ARCHIVE_SHA512.txt').split()[0]},
 'godot_export_templates':{'version':'4.3.stable','filename':'Godot_v4.3-stable_export_templates.tpz','sha512':sys.argv[2],'official_sums_sha256':text('GODOT_TEMPLATE_SUMS_SHA256.txt').split()[0]},
 'android_toolchain':{
  'java':text('JAVA_VERSION.txt').splitlines()[0] if text('JAVA_VERSION.txt') else None,
  'javac':text('JAVAC_VERSION.txt'),
  'command_line_tools':text('ANDROID_CMDLINE_TOOLS_VERSION.txt'),
  'build_tools':package_revision('build-tools;34.0.0'),
  'android_platform':package_revision('platforms;android-34'),
  'platform_tools':package_revision('platform-tools'),
  'aapt':text('AAPT_VERSION.txt'),'aapt2':text('AAPT2_VERSION.txt'),'apksigner':text('APKSIGNER_VERSION.txt'),'apkanalyzer':text('APKANALYZER_VERSION.txt'),
  'gradle':None,'android_gradle_plugin':None,'ndk':None,'custom_gradle_build':False,
 },
 'host':{'image_os':os.environ.get('ImageOS'),'image_version':os.environ.get('ImageVersion'),'runner_os':os.environ.get('RUNNER_OS'),'runner_arch':os.environ.get('RUNNER_ARCH')},
}
(r/'TOOLCHAIN_IDENTITY.json').write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
required=(value['android_toolchain']['build_tools'],value['android_toolchain']['android_platform'],value['android_toolchain']['platform_tools'])
if any(x is None for x in required): raise SystemExit('required Android package identity missing')
PY

EXPORT_START="$(date -u +%FT%TZ)"
printf '%q ' env XDG_DATA_HOME="$XDG_DATA_HOME" GODOT_ANDROID_KEYSTORE_DEBUG_PATH="$SIGNING_KEYSTORE" GODOT_ANDROID_KEYSTORE_DEBUG_USER=androiddebugkey GODOT_ANDROID_KEYSTORE_DEBUG_PASSWORD=android "$GODOT" --headless --path "$GAME" --verbose --export-debug "$PRESET_NAME" "$APK" > "$REPORTS/EXPORT_COMMAND.txt"; printf '\n' >> "$REPORTS/EXPORT_COMMAND.txt"
set +e
set -o pipefail
/usr/bin/time -v timeout --signal=TERM --kill-after=30s 1800s env XDG_DATA_HOME="$XDG_DATA_HOME" GODOT_ANDROID_KEYSTORE_DEBUG_PATH="$SIGNING_KEYSTORE" GODOT_ANDROID_KEYSTORE_DEBUG_USER=androiddebugkey GODOT_ANDROID_KEYSTORE_DEBUG_PASSWORD=android "$GODOT" --headless --path "$GAME" --verbose --export-debug "$PRESET_NAME" "$APK" 2>&1 | tee "$LOGS/android-export.log"
EXPORT_CODE=${PIPESTATUS[0]}
set -e
EXPORT_END="$(date -u +%FT%TZ)"
printf '%s\n' "$EXPORT_CODE" > "$REPORTS/EXPORT_EXIT_CODE.txt"
printf '%s\n' "$EXPORT_START" > "$REPORTS/EXPORT_STARTED_UTC.txt"
printf '%s\n' "$EXPORT_END" > "$REPORTS/EXPORT_COMPLETED_UTC.txt"
test "$EXPORT_CODE" -eq 0
test -s "$APK"
if ! grep -Eq 'Maximum resident set size|Elapsed \(wall clock\)' "$LOGS/android-export.log"; then echo 'resource usage unavailable' > "$REPORTS/EXPORT_RESOURCE_USAGE_NOTE.txt"; fi
sha256sum "$APK" > "$REPORTS/APK_SHA256SUM.txt"
stat -c '%n %s' "$APK" > "$REPORTS/APK_SIZE.txt"

python3 "$TOOL" authority --game "$GAME" --manifest "$REPORTS/FINAL_TREE_MANIFEST.json" --output "$REPORTS/SOURCE_AUTHORITY_POST_EXPORT.json"
python3 - "$REPORTS/SOURCE_AUTHORITY_PRE_EXPORT.json" "$REPORTS/SOURCE_AUTHORITY_POST_EXPORT.json" <<'PY'
import json,sys
pre=json.load(open(sys.argv[1])); post=json.load(open(sys.argv[2]))
keys=('passed','manifest_sha256','aggregate_tree_sha256','expected_file_count','checked_file_count','expected_total_bytes','checked_total_bytes','failures')
assert {k:pre[k] for k in keys} == {k:post[k] for k in keys}
PY

unzip -tq "$APK" > "$LOGS/APK_ZIP_INTEGRITY.txt"
"$AAPT" dump badging "$APK" > "$REPORTS/APK_BADGING.txt"
"$AAPT" dump xmltree "$APK" AndroidManifest.xml > "$REPORTS/APK_MANIFEST_XMLTREE.txt"
"$APKANALYZER" manifest print "$APK" > "$REPORTS/APK_MANIFEST_DECODED.xml"
"$APKANALYZER" files list "$APK" > "$REPORTS/APKANALYZER_FILES.txt"
"$APKSIGNER" verify --verbose --print-certs "$APK" > "$REPORTS/APK_SIGNING.txt"
"$ZIPALIGN" -c -v 4 "$APK" > "$REPORTS/APK_ZIPALIGN.txt"

mkdir -p "$EVIDENCE/pck" "$EVIDENCE/pck-list-project"
python3 - "$APK" "$EVIDENCE/pck/payload.pck" "$REPORTS/PCK_APK_ENTRY.json" <<'PY'
from pathlib import Path
import hashlib,json,sys,zipfile
apk=Path(sys.argv[1]); out=Path(sys.argv[2]); report=Path(sys.argv[3])
found=[]
with zipfile.ZipFile(apk) as z:
    for info in z.infolist():
        if info.is_dir() or not info.filename.startswith('assets/'): continue
        with z.open(info) as f: magic=f.read(4)
        if info.filename.endswith('.pck') or info.filename.rsplit('/',1)[-1]=='_cl_' or magic==b'GDPC':
            found.append((info,magic.hex()))
    if len(found)!=1: raise SystemExit(f'expected exactly one Godot PCK payload, found {[x[0].filename for x in found]}')
    info,magic=found[0]
    out.write_bytes(z.read(info))
report.write_text(json.dumps({'apk_entry':info.filename,'compressed_bytes':info.compress_size,'uncompressed_bytes':info.file_size,'magic_hex':magic,'extracted_sha256':hashlib.sha256(out.read_bytes()).hexdigest()},indent=2,sort_keys=True)+'\n')
PY
cat > "$EVIDENCE/pck-list-project/project.godot" <<'EOF_PROJECT'
config_version=5
[application]
config/name="Gate4PckInventory"
EOF_PROJECT
cat > "$EVIDENCE/pck-list-project/list_pck.gd" <<'EOF_SCRIPT'
extends SceneTree
func _initialize() -> void:
    call_deferred("_run")
func _run() -> void:
    var args := OS.get_cmdline_user_args()
    if args.size() != 2:
        push_error("expected PCK path and output path")
        quit(2)
        return
    if not ProjectSettings.load_resource_pack(args[0], true):
        push_error("failed to load PCK")
        quit(3)
        return
    var files: Array[String] = []
    _walk("res://", files)
    files.sort()
    var output := FileAccess.open(args[1], FileAccess.WRITE)
    if output == null:
        push_error("failed to open inventory output")
        quit(4)
        return
    output.store_string(JSON.stringify({"files": files}, "  "))
    output.close()
    quit(0)
func _walk(path: String, files: Array[String]) -> void:
    var directory := DirAccess.open(path)
    if directory == null:
        return
    directory.list_dir_begin()
    while true:
        var name := directory.get_next()
        if name.is_empty():
            break
        if name == "." or name == "..":
            continue
        var child := path.path_join(name)
        if directory.current_is_dir():
            _walk(child, files)
        else:
            files.append(child)
    directory.list_dir_end()
EOF_SCRIPT
run_bounded pck-inventory 300 env XDG_DATA_HOME="$XDG_DATA_HOME" "$GODOT" --headless --path "$EVIDENCE/pck-list-project" --script res://list_pck.gd -- "$EVIDENCE/pck/payload.pck" "$REPORTS/PCK_CONTENTS.json"
test -s "$REPORTS/PCK_CONTENTS.json"

python3 "$TOOL" inspect --apk "$APK" --report-dir "$REPORTS" --source-root "$GAME" --badging "$REPORTS/APK_BADGING.txt" --manifest-xml "$REPORTS/APK_MANIFEST_XMLTREE.txt" --signing "$REPORTS/APK_SIGNING.txt" --pck-inventory "$REPORTS/PCK_CONTENTS.json"
python3 - "$REPORTS/APK_EXPORT_RECORD.json" "$REPORTS/EXPORT_COMMAND.txt" "$REPORTS/TOOLCHAIN_IDENTITY.json" "$REPORTS/EXPORT_PRESET_INSPECTION.json" "$SLOT" "$EXPORT_START" "$EXPORT_END" "$EXPORT_CODE" <<'PY'
from pathlib import Path
import json,os,sys
record=Path(sys.argv[1]); value=json.loads(record.read_text())
value.update({'slot':sys.argv[5],'export_command':Path(sys.argv[2]).read_text().strip(),'toolchain':json.loads(Path(sys.argv[3]).read_text()),'export_preset':json.loads(Path(sys.argv[4]).read_text()),'started_utc':sys.argv[6],'completed_utc':sys.argv[7],'exit_code':int(sys.argv[8]),'workflow_run_id':os.environ.get('GITHUB_RUN_ID'),'job_id':os.environ.get('GITHUB_JOB')})
record.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
PY

python3 - "$REPORTS" "$APK" "$SLOT" <<'PY'
from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1]); apk=Path(sys.argv[2])
files=[]
for path in sorted(root.rglob('*')):
    if path.is_file(): files.append({'path':path.relative_to(root).as_posix(),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
value={'slot':sys.argv[3],'apk':{'path':apk.name,'bytes':apk.stat().st_size,'sha256':hashlib.sha256(apk.read_bytes()).hexdigest()},'files':files}
(root/'GATE4_EXPORT_EVIDENCE_INVENTORY.json').write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
PY

echo "GATE4_${SLOT^^}_EXPORT_PASS apk=$(basename "$APK") sha256=$(sha256sum "$APK" | awk '{print $1}')"
