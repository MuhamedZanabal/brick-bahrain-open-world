#!/usr/bin/env bash
set -uo pipefail

REPO_ROOT="${1:?repository root is required}"
SOURCE_ROOT="${2:?accepted reconstruction root is required}"
EVIDENCE="${3:?Gate 4 evidence directory is required}"
SLOT="${4:?export slot is required}"
REPORTS="$EVIDENCE/reports"
LOGS="$EVIDENCE/logs"
RUNNER="$REPO_ROOT/tools/vertical_slice/run_manama_souq_gate4_export.sh"
GAME="$SOURCE_ROOT/game"
RECON_EVIDENCE="$SOURCE_ROOT/evidence"
SIGNING_KEYSTORE="$REPO_ROOT/debug.keystore"
GODOT_ARCHIVE="$SOURCE_ROOT/downloads/Godot_v4.3-stable_linux.x86_64.zip"
TOOL="$REPO_ROOT/tools/vertical_slice/manama_souq_apk_evidence.py"

mkdir -p "$REPORTS" "$LOGS"
df -h > "$REPORTS/WORKSPACE_DISK_BEFORE.txt" 2>&1 || true
du -sh "$REPO_ROOT" "$SOURCE_ROOT" "$EVIDENCE" > "$REPORTS/WORKSPACE_USAGE_BEFORE.txt" 2>&1 || true

python3 - "$REPORTS/GATE4_PREREQUISITES.json" "$GAME/project.godot" "$GAME/export_presets.cfg" "$SIGNING_KEYSTORE" "$RECON_EVIDENCE/FINAL_TREE_MANIFEST.json" "$RECON_EVIDENCE/FINAL_TREE_AUTHORITY.json" "$RECON_EVIDENCE/FROZEN_CONTROLS_PRE.json" "$RECON_EVIDENCE/FROZEN_CONTROLS_POST.json" "$GODOT_ARCHIVE" "$TOOL" <<'PY'
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

TRACE="$LOGS/gate4-runner-xtrace.log"
PS4='+ ${BASH_SOURCE}:${LINENO}:${FUNCNAME[0]:-main}: '
export PS4
set +e
bash -x "$RUNNER" "$REPO_ROOT" "$SOURCE_ROOT" "$EVIDENCE" "$SLOT" > >(tee "$TRACE") 2>&1
CODE=${PIPESTATUS[0]}
set -e

if [[ "$CODE" -ne 0 ]]; then
  LAST_TRACE="$(tail -n 120 "$TRACE" 2>/dev/null || true)"
  python3 - "$REPORTS/GATE4_FAILURE.json" "$CODE" "$RUNNER" "$SLOT" "$TRACE" "$LAST_TRACE" <<'PY'
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
