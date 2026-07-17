#!/usr/bin/env bash
set -uo pipefail

REPO_ROOT="${1:?repository root is required}"
SOURCE_ROOT="${2:?accepted reconstruction root is required}"
EVIDENCE="${3:?Gate 4 evidence directory is required}"
SLOT="${4:?export slot is required}"
REPORTS="$EVIDENCE/reports"
LOGS="$EVIDENCE/logs"
BASE_RUNNER="$REPO_ROOT/tools/vertical_slice/run_manama_souq_gate4_export.sh"
PATCHED_RUNNER="$SOURCE_ROOT/run_manama_souq_gate4_export_patched.sh"
GAME="$SOURCE_ROOT/game"
RECON_EVIDENCE="$SOURCE_ROOT/evidence"
SIGNING_KEYSTORE="$REPO_ROOT/debug.keystore"
GODOT_ARCHIVE="$SOURCE_ROOT/downloads/Godot_v4.3-stable_linux.x86_64.zip"
TOOL="$REPO_ROOT/tools/vertical_slice/manama_souq_apk_evidence.py"
PRESET_INSPECTOR="$REPO_ROOT/tools/vertical_slice/inspect_manama_souq_android_preset.py"
ASSET_INVENTORY="$REPO_ROOT/tools/vertical_slice/inventory_godot_android_apk_assets.py"

mkdir -p "$REPORTS" "$LOGS"
df -h > "$REPORTS/WORKSPACE_DISK_BEFORE.txt" 2>&1 || true
du -sh "$REPO_ROOT" "$SOURCE_ROOT" "$EVIDENCE" > "$REPORTS/WORKSPACE_USAGE_BEFORE.txt" 2>&1 || true

python3 - "$REPORTS/GATE4_PREREQUISITES.json" "$GAME/project.godot" "$GAME/export_presets.cfg" "$SIGNING_KEYSTORE" "$RECON_EVIDENCE/FINAL_TREE_MANIFEST.json" "$RECON_EVIDENCE/FINAL_TREE_AUTHORITY.json" "$RECON_EVIDENCE/FROZEN_CONTROLS_PRE.json" "$RECON_EVIDENCE/FROZEN_CONTROLS_POST.json" "$GODOT_ARCHIVE" "$TOOL" "$PRESET_INSPECTOR" "$ASSET_INVENTORY" <<'PY'
from pathlib import Path
import hashlib,json,os,platform,sys
out=Path(sys.argv[1])
items=[]
for raw in sys.argv[2:]:
    path=Path(raw)
    item={'path':str(path),'exists':path.exists(),'is_file':path.is_file()}
    if path.is_file():
        item['bytes']=path.stat().st_size
        h=hashlib.sha256()
        with path.open('rb') as handle:
            for chunk in iter(lambda:handle.read(1024*1024),b''): h.update(chunk)
        item['sha256']=h.hexdigest()
    items.append(item)
value={
 'slot':os.environ.get('GITHUB_JOB'),
 'image_version':os.environ.get('ImageVersion'),
 'image_os':os.environ.get('ImageOS'),
 'runner_os':os.environ.get('RUNNER_OS'),
 'runner_arch':os.environ.get('RUNNER_ARCH'),
 'python':platform.python_version(),
 'items':items,
 'passed':all(item['is_file'] for item in items),
}
out.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
PY

python3 - "$BASE_RUNNER" "$PATCHED_RUNNER" "$REPORTS/GATE4_HARNESS_CORRECTION.json" "$PRESET_INSPECTOR" "$ASSET_INVENTORY" <<'PATCH_PY'
from pathlib import Path
import hashlib,json,sys
source=Path(sys.argv[1]); target=Path(sys.argv[2]); report=Path(sys.argv[3]); inspector=Path(sys.argv[4]); asset_inventory=Path(sys.argv[5])
text=source.read_text(encoding='utf-8')
host_old="grep -q '^VERSION=\"24.04.4 LTS\"' /etc/os-release"
host_new="test \"$(. /etc/os-release; printf '%s' \"$PRETTY_NAME\")\" = \"Ubuntu 24.04.4 LTS\""
preset_old='python3 "$TOOL" preset --preset "$GAME/export_presets.cfg" --project "$GAME/project.godot" --output "$REPORTS/EXPORT_PRESET_INSPECTION.json"'
preset_new='python3 "$REPO_ROOT/tools/vertical_slice/inspect_manama_souq_android_preset.py" --preset "$GAME/export_presets.cfg" --project "$GAME/project.godot" --output "$REPORTS/EXPORT_PRESET_INSPECTION.json"'
sdk_old="match=re.search(rf'^{re.escape(name)}\\s+\\|\\s+([^|\\s]+)', text('ANDROID_SDK_PACKAGES.txt'), re.M)"
sdk_new="match=re.search(rf'^\\s*{re.escape(name)}\\s+\\|\\s+([^|\\s]+)', text('ANDROID_SDK_PACKAGES.txt'), re.M)"
asset_packaging_old='''mkdir -p "$EVIDENCE/pck" "$EVIDENCE/pck-list-project"
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
test -s "$REPORTS/PCK_CONTENTS.json"'''
asset_packaging_new='''# Godot 4.3 default Android APK assets are not a PCK. Inventory the exported assets/ tree directly.
python3 "$REPO_ROOT/tools/vertical_slice/inventory_godot_android_apk_assets.py" \
  --apk "$APK" \
  --source-root "$GAME" \
  --output "$REPORTS/APK_PROJECT_ASSETS.json" \
  --compat-output "$REPORTS/PCK_CONTENTS.json"
test -s "$REPORTS/APK_PROJECT_ASSETS.json"
test -s "$REPORTS/PCK_CONTENTS.json"'''
host_count=text.count(host_old)
preset_count=text.count(preset_old)
sdk_count=text.count(sdk_old)
asset_count=text.count(asset_packaging_old)
if host_count != 1:
    raise SystemExit(f'host OS identity assertion replacement count={host_count}')
if preset_count != 1:
    raise SystemExit(f'accepted preset inspector replacement count={preset_count}')
if sdk_count != 1:
    raise SystemExit(f'SDK package identity parser replacement count={sdk_count}')
if asset_count != 1:
    raise SystemExit(f'Android asset packaging replacement count={asset_count}')
if not inspector.is_file():
    raise SystemExit(f'accepted preset inspector missing: {inspector}')
if not asset_inventory.is_file():
    raise SystemExit(f'Android APK asset inventory tool missing: {asset_inventory}')
patched=(text.replace(host_old,host_new,1)
    .replace(preset_old,preset_new,1)
    .replace(sdk_old,sdk_new,1)
    .replace(asset_packaging_old,asset_packaging_new,1))
target.write_text(patched,encoding='utf-8')
target.chmod(0o755)
report.write_text(json.dumps({
 'classification':'Gate 4 harness host-identity, stale preset-inspector, SDK package identity parser indentation, and default Android asset-packaging inspection defects',
 'corrections':[
  {'first_causal_command':host_old,'correction':host_new,'replacement_count':host_count},
  {'first_causal_command':preset_old,'correction':preset_new,'replacement_count':preset_count},
  {'classification':'SDK package identity parser indentation defect','first_causal_command':sdk_old,'correction':sdk_new,'replacement_count':sdk_count},
  {'classification':'default Android APK assets are not a PCK','first_causal_command':'ProjectSettings.load_resource_pack on assets/_cl_','correction':'inventory APK assets/ directly and verify compiled/imported logical mappings','replacement_count':asset_count},
 ],
 'base_runner_sha256':hashlib.sha256(text.encode()).hexdigest(),
 'patched_runner_sha256':hashlib.sha256(patched.encode()).hexdigest(),
 'accepted_preset_inspector_sha256':hashlib.sha256(inspector.read_bytes()).hexdigest(),
 'asset_inventory_tool_sha256':hashlib.sha256(asset_inventory.read_bytes()).hexdigest(),
 'product_source_modified':False,
 'export_preset_modified':False,
},indent=2,sort_keys=True)+'\n')
PATCH_PY

TRACE="$LOGS/gate4-runner-xtrace.log"
PS4='+ ${BASH_SOURCE}:${LINENO}:${FUNCNAME[0]:-main}: '
export PS4
set +e
bash -x "$PATCHED_RUNNER" "$REPO_ROOT" "$SOURCE_ROOT" "$EVIDENCE" "$SLOT" > >(tee "$TRACE") 2>&1
CODE=${PIPESTATUS[0]}
set -e

if [[ "$CODE" -ne 0 ]]; then
  LAST_TRACE="$(tail -n 200 "$TRACE" 2>/dev/null || true)"
  python3 - "$REPORTS/GATE4_FAILURE.json" "$CODE" "$PATCHED_RUNNER" "$SLOT" "$TRACE" "$LAST_TRACE" <<'PY'
from pathlib import Path
import json,os,sys
out=Path(sys.argv[1])
value={
 'passed':False,
 'exit_code':int(sys.argv[2]),
 'runner':sys.argv[3],
 'slot':sys.argv[4],
 'trace_path':sys.argv[5],
 'last_trace_lines':sys.argv[6].splitlines(),
 'BASH_COMMAND':'bash -x '+sys.argv[3],
 'workflow_run_id':os.environ.get('GITHUB_RUN_ID'),
 'workflow_job':os.environ.get('GITHUB_JOB'),
}
out.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
PY
  df -h > "$REPORTS/WORKSPACE_DISK_FAILURE.txt" 2>&1 || true
  du -sh "$REPO_ROOT" "$SOURCE_ROOT" "$EVIDENCE" > "$REPORTS/WORKSPACE_USAGE_FAILURE.txt" 2>&1 || true
  exit "$CODE"
fi

python3 - "$REPORTS/GATE4_FAILURE.json" "$SLOT" <<'PY'
from pathlib import Path
import json,sys
Path(sys.argv[1]).write_text(json.dumps({'passed':True,'slot':sys.argv[2],'failure':None},indent=2,sort_keys=True)+'\n')
PY
exit 0
