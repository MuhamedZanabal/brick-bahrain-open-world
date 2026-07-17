#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:?repository root is required}"
SOURCE_ROOT="${2:?accepted reconstruction root is required}"
EVIDENCE="${3:?Gate 2 evidence directory is required}"
GAME="$SOURCE_ROOT/game"
RECON_EVIDENCE="$SOURCE_ROOT/evidence"
GODOT_ARCHIVE="$SOURCE_ROOT/downloads/Godot_v4.3-stable_linux.x86_64.zip"
GODOT_DIR="$SOURCE_ROOT/godot"
DIAGNOSTICS="$EVIDENCE/diagnostics"
RUNTIME_LOGS="$EVIDENCE/runtime-logs"
REPORTS="$EVIDENCE/reports"

ACCEPTED_HEAD="b12e1e012e256036e71066260a4c6392d26c3839"
ACCEPTED_MANIFEST="ba937afa335170ccaa726297fc23712a44e3295689a86640e1c1dbe6165701ab"
ACCEPTED_TREE="e0cfa6604569c13e1d75b2439d6936b7e2423ad5ba3715f033200335e864bc4e"
ACCEPTED_FILE_COUNT=1502
ACCEPTED_SOURCE_BYTES=369162800
ACCEPTED_GODOT_SHA512="fd52bb4ba8acc30ca5accd1c566d470ad7282f891ccc0995dfafabcf92bcf76280ce182bf9d80ebd885f3ed2165d01e1fc3f2928436b15498dfbd98656c2a45a"

mkdir -p "$EVIDENCE" "$DIAGNOSTICS" "$RUNTIME_LOGS" "$REPORTS" "$GODOT_DIR"
cp -a "$RECON_EVIDENCE/." "$EVIDENCE/reconstruction/"

python3 - "$RECON_EVIDENCE" "$REPORTS/GATE1_ACCEPTED_VERIFICATION.json" <<'PY'
from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1]); out=Path(sys.argv[2])
manifest=root/'FINAL_TREE_MANIFEST.json'
report=json.loads((root/'FINAL_TREE_AUTHORITY.json').read_text())
frozen=json.loads((root/'FROZEN_CONTROLS_PRE.json').read_text())
actual={
 'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
 'aggregate_tree_sha256':report['aggregate_tree_sha256'],
 'file_count':report['file_count'],
 'total_bytes':report['total_bytes'],
 'frozen_check_count':frozen['checks'],
 'frozen_failures':frozen['failures'],
 'frozen_all_results_passed':all(item['pass'] for item in frozen['results']),
}
expected={
 'manifest_sha256':'ba937afa335170ccaa726297fc23712a44e3295689a86640e1c1dbe6165701ab',
 'aggregate_tree_sha256':'e0cfa6604569c13e1d75b2439d6936b7e2423ad5ba3715f033200335e864bc4e',
 'file_count':1502,
 'total_bytes':369162800,
 'frozen_check_count':25,
 'frozen_failures':[],
 'frozen_all_results_passed':True,
}
passed=actual==expected
out.write_text(json.dumps({'passed':passed,'accepted_head':'b12e1e012e256036e71066260a4c6392d26c3839','expected':expected,'actual':actual},indent=2,sort_keys=True)+'\n')
if not passed: raise SystemExit('accepted Gate 1 authority mismatch')
PY

printf '%s  %s\n' "$ACCEPTED_GODOT_SHA512" "$GODOT_ARCHIVE" | sha512sum -c -
unzip -q "$GODOT_ARCHIVE" -d "$GODOT_DIR"
GODOT="$(find "$GODOT_DIR" -maxdepth 1 -type f -name 'Godot*' | head -1)"
chmod +x "$GODOT"
test "$($GODOT --version)" = "4.3.stable.official.77dcf97d8"
printf '%s\n' "$GODOT" > "$REPORTS/GODOT_PATH.txt"
"$GODOT" --version > "$REPORTS/GODOT_VERSION.txt"
sha512sum "$GODOT_ARCHIVE" > "$REPORTS/GODOT_ARCHIVE_SHA512.txt"

python3 - "$GAME" "$REPORTS/PRODUCT_SOURCE_PRE.json" <<'PY'
from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1]); out=Path(sys.argv[2])
paths=['project.godot','scripts/brick_factory.gd','scripts/souq_population_controller.gd','tests/souq_population_runtime.gd']
value={p:{'bytes':(root/p).stat().st_size,'sha256':hashlib.sha256((root/p).read_bytes()).hexdigest()} for p in paths}
out.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
PY

run_process() {
  local out_dir="$1" name="$2" seconds="$3"; shift 3
  mkdir -p "$out_dir"
  local command_file="$out_dir/${name}.command.txt"
  local log_file="$out_dir/${name}.log"
  local exit_file="$out_dir/${name}.exit-code.txt"
  local timeout_file="$out_dir/${name}.timeout.txt"
  printf '%q ' "$@" > "$command_file"
  printf '\n' >> "$command_file"
  set +e
  set -o pipefail
  timeout --signal=TERM --kill-after=20s "${seconds}s" "$@" 2>&1 | tee "$log_file"
  local code=${PIPESTATUS[0]}
  set -e
  printf '%s\n' "$code" > "$exit_file"
  if [[ "$code" -eq 124 || "$code" -eq 137 ]]; then
    printf 'true\n' > "$timeout_file"
  else
    printf 'false\n' > "$timeout_file"
  fi
}

require_marker() {
  local name="$1" seconds="$2" marker="$3"; shift 3
  run_process "$RUNTIME_LOGS" "$name" "$seconds" "$@"
  test "$(cat "$RUNTIME_LOGS/${name}.exit-code.txt")" -eq 0
  test "$(cat "$RUNTIME_LOGS/${name}.timeout.txt")" = false
  grep -Fq "$marker" "$RUNTIME_LOGS/${name}.log"
}

require_regex() {
  local name="$1" seconds="$2" pattern="$3"; shift 3
  run_process "$RUNTIME_LOGS" "$name" "$seconds" "$@"
  test "$(cat "$RUNTIME_LOGS/${name}.exit-code.txt")" -eq 0
  test "$(cat "$RUNTIME_LOGS/${name}.timeout.txt")" = false
  grep -Eq "$pattern" "$RUNTIME_LOGS/${name}.log"
}

rm -rf "$GAME/.godot"
run_process "$DIAGNOSTICS" clean-import 900 "$GODOT" --headless --path "$GAME" --editor --import --quit --verbose
python3 - "$DIAGNOSTICS" "$GAME" "$REPORTS/CLEAN_IMPORT.json" <<'PY'
from pathlib import Path
import json,re,sys
logs=Path(sys.argv[1]); game=Path(sys.argv[2]); out=Path(sys.argv[3])
text=(logs/'clean-import.log').read_text(errors='replace')
code=int((logs/'clean-import.exit-code.txt').read_text())
timed=(logs/'clean-import.timeout.txt').read_text().strip()=='true'
patterns={
 'script_error':r'SCRIPT ERROR', 'parse_error':r'Parse Error|Parser Error',
 'failed_script':r'Failed to load script', 'autoload_error':r'Failed to create an autoload',
 'fatal':r'\bFATAL\b|Fatal signal',
}
counts={k:len(re.findall(v,text,re.I)) for k,v in patterns.items()}
imported=sum(1 for p in (game/'.godot/imported').glob('*.md5') if 'glb' in p.name)
passed=code==0 and not timed and sum(counts.values())==0 and imported>=436
out.write_text(json.dumps({'passed':passed,'exit_code':code,'timed_out':timed,'error_counts':counts,'imported_glb_md5_count':imported},indent=2,sort_keys=True)+'\n')
if not passed: raise SystemExit('clean Godot import failed')
PY

mkdir -p "$GAME/tests/gate2"
cp "$REPO_ROOT/tests/gate2/souq_population_project_context_runtime.gd" "$GAME/tests/gate2/"
cp "$REPO_ROOT/tests/gate2/souq_population_project_context_runtime.tscn" "$GAME/tests/gate2/"
python3 - "$REPO_ROOT" "$GAME" "$REPORTS/HARNESS_INJECTION_LEDGER.json" <<'PY'
from pathlib import Path
import hashlib,json,sys
repo=Path(sys.argv[1]); game=Path(sys.argv[2]); out=Path(sys.argv[3])
paths=['tests/gate2/souq_population_project_context_runtime.gd','tests/gate2/souq_population_project_context_runtime.tscn']
items=[]
for p in paths:
 source=repo/p; target=game/p
 items.append({'path':p,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'target_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'test_only':True})
out.write_text(json.dumps({'passed':all(x['source_sha256']==x['target_sha256'] for x in items),'files':items},indent=2,sort_keys=True)+'\n')
PY

cat > "$REPORTS/HISTORICAL_COMMAND_PROVENANCE.json" <<'EOF_PROVENANCE'
{
  "historical_workflow_run": 29513852863,
  "source_runner": "tools/vertical_slice/run_manama_souq_source_gate.sh",
  "source_line": 21,
  "command_form": "godot --headless --path $GAME --script res://tests/souq_population_runtime.gd"
}
EOF_PROVENANCE

run_process "$DIAGNOSTICS" historical-script-mode 180 "$GODOT" --headless --path "$GAME" --script "res://tests/souq_population_runtime.gd"
run_process "$DIAGNOSTICS" project-context 300 "$GODOT" --headless --path "$GAME" "res://tests/gate2/souq_population_project_context_runtime.tscn"
cp "$DIAGNOSTICS/historical-script-mode.exit-code.txt" "$REPORTS/HISTORICAL_SCRIPT_MODE_EXIT_CODE.txt"
cp "$DIAGNOSTICS/historical-script-mode.timeout.txt" "$REPORTS/HISTORICAL_SCRIPT_MODE_TIMEOUT.txt"
cp "$DIAGNOSTICS/project-context.exit-code.txt" "$REPORTS/PROJECT_CONTEXT_EXIT_CODE.txt"
cp "$DIAGNOSTICS/project-context.timeout.txt" "$REPORTS/PROJECT_CONTEXT_TIMEOUT.txt"

python3 - "$DIAGNOSTICS" "$REPORTS/BRICK_FACTORY_CLASSIFICATION.json" <<'PY'
from pathlib import Path
import json,re,sys
root=Path(sys.argv[1]); out=Path(sys.argv[2])
def read(name):
 text=(root/f'{name}.log').read_text(errors='replace')
 return {
  'command':(root/f'{name}.command.txt').read_text().strip(),
  'exit_code':int((root/f'{name}.exit-code.txt').read_text()),
  'timed_out':(root/f'{name}.timeout.txt').read_text().strip()=='true',
  'identifier_error_count':len(re.findall(r'Identifier not found: BrickFactory',text,re.I)),
  'population_script_new_failure_count':len(re.findall(r"Nonexistent function 'new'.*GDScript",text,re.I)),
  'brick_factory_autoload_error_count':len(re.findall(r'Failed to create an autoload.*BrickFactory',text,re.I)),
  'script_error_count':len(re.findall(r'SCRIPT ERROR|Parse Error|Parser Error|Failed to load script',text,re.I)),
  'historical_pass_marker':'SOUQ_POPULATION_RUNTIME_PASS' in text,
  'project_pass_marker':'SOUQ_POPULATION_PROJECT_CONTEXT_PASS' in text,
 }
h=read('historical-script-mode'); p=read('project-context')
hpass=h['exit_code']==0 and not h['timed_out'] and h['historical_pass_marker']
ppass=p['exit_code']==0 and not p['timed_out'] and p['project_pass_marker']
if h['identifier_error_count']>0 and ppass:
 classification='A'; conclusion='test-harness execution-context defect'
elif p['identifier_error_count']>0:
 classification='B'; conclusion='product-source BrickFactory resolution defect'
elif hpass and ppass:
 classification='C'; conclusion='historical BrickFactory failure not reproducible'
else:
 classification='D'; conclusion='different downstream blocker'
value={'classification':classification,'conclusion':conclusion,'historical_script_mode':h,'normal_project_context':p}
out.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
print(classification)
PY
CLASSIFICATION="$(python3 -c 'import json;print(json.load(open("'"$REPORTS/BRICK_FACTORY_CLASSIFICATION.json"'"))["classification"])')"
case "$CLASSIFICATION" in
  A)
    cat > "$REPORTS/HARNESS_CORRECTION.json" <<'EOF_CORRECTION'
{
  "classification": "A",
  "correction": "Use a normal project-context scene for the population runtime gate so project autoloads are initialized.",
  "product_source_changed": false,
  "historical_script_retained_for_diagnostic_comparison": true
}
EOF_CORRECTION
    run_process "$DIAGNOSTICS" historical-script-mode-post-correction 180 "$GODOT" --headless --path "$GAME" --script "res://tests/souq_population_runtime.gd"
    run_process "$DIAGNOSTICS" project-context-post-correction 300 "$GODOT" --headless --path "$GAME" "res://tests/gate2/souq_population_project_context_runtime.tscn"
    grep -Eiq 'Identifier not found: BrickFactory' "$DIAGNOSTICS/historical-script-mode-post-correction.log"
    test "$(cat "$DIAGNOSTICS/project-context-post-correction.exit-code.txt")" -eq 0
    grep -Fq 'SOUQ_POPULATION_PROJECT_CONTEXT_PASS' "$DIAGNOSTICS/project-context-post-correction.log"
    ;;
  C)
    cat > "$REPORTS/HARNESS_CORRECTION.json" <<'EOF_CORRECTION'
{
  "classification": "C",
  "correction": null,
  "product_source_changed": false,
  "historical_result_disposition": "stale, environment-specific, or superseded"
}
EOF_CORRECTION
    ;;
  B|D)
    printf '%s\n' "$CLASSIFICATION" > "$REPORTS/FIRST_PRODUCT_BLOCKER_CLASSIFICATION.txt"
    exit 20
    ;;
esac

require_marker karak-delivery-mission 300 KARAK_DELIVERY_RUNTIME_PASS "$GODOT" --headless --path "$GAME" --script "res://tests/karak_delivery_mission_runtime.gd"
require_marker manama-souq-layout 600 MANAMA_SOUQ_LAYOUT_RUNTIME_PASS "$GODOT" --headless --path "$GAME" --script "res://tests/manama_souq_layout_runtime.gd"
require_marker souq-population-project-context 300 SOUQ_POPULATION_PROJECT_CONTEXT_PASS "$GODOT" --headless --path "$GAME" "res://tests/gate2/souq_population_project_context_runtime.tscn"
require_marker karak-delivery-hud 300 KARAK_DELIVERY_HUD_RUNTIME_PASS "$GODOT" --headless --path "$GAME" --script "res://tests/karak_delivery_hud_runtime.gd"
require_marker manama-souq-slice 900 MANAMA_SOUQ_SLICE_RUNTIME_PASS "$GODOT" --headless --path "$GAME" --script "res://tests/manama_souq_slice_runtime.gd"

mkdir -p "$GAME/build/ci/test-user-data"/{smoke,controls,presentation,premium-world,premium-presentation,lifecycle,resource-repeat}
require_marker inherited-runtime-smoke 700 '43 passed, 0 failed' env XDG_DATA_HOME="$GAME/build/ci/test-user-data/smoke" "$GODOT" --headless --path "$GAME" --audio-driver Dummy res://build/ci/runtime_smoke_runner_v14.tscn
require_marker inherited-controls 700 '28 passed, 0 failed' env XDG_DATA_HOME="$GAME/build/ci/test-user-data/controls" "$GODOT" --headless --path "$GAME" --audio-driver Dummy res://scenes/mobile_input_pipeline_test.tscn
require_marker inherited-presentation 700 '10 passed, 0 failed' env XDG_DATA_HOME="$GAME/build/ci/test-user-data/presentation" "$GODOT" --headless --path "$GAME" --audio-driver Dummy res://scenes/presentation_flow_test.tscn -- --presentation-test
require_marker inherited-premium-world 700 '12 passed, 0 failed' env XDG_DATA_HOME="$GAME/build/ci/test-user-data/premium-world" "$GODOT" --headless --path "$GAME" --audio-driver Dummy res://scenes/premium_world_acceptance_test.tscn
require_regex inherited-premium-presentation 700 '[0-9]+ passed, 0 failed' env XDG_DATA_HOME="$GAME/build/ci/test-user-data/premium-presentation" "$GODOT" --headless --path "$GAME" --audio-driver Dummy res://scenes/premium_presentation_acceptance_test.tscn -- --presentation-test
require_regex inherited-lifecycle 700 'World lifecycle guard complete: 12 passed, 0 failed|12 passed, 0 failed' env XDG_DATA_HOME="$GAME/build/ci/test-user-data/lifecycle" "$GODOT" --headless --path "$GAME" --audio-driver Dummy res://scenes/world_lifecycle_guard_test.tscn
require_regex inherited-resource-repeat 700 'World resource repeat complete: 21 passed, 0 failed|21 passed, 0 failed' env XDG_DATA_HOME="$GAME/build/ci/test-user-data/resource-repeat" "$GODOT" --headless --path "$GAME" --audio-driver Dummy res://scenes/world_resource_repeat_test.tscn

python3 "$REPO_ROOT/tools/scan_godot_runtime_errors.py" "$RUNTIME_LOGS" --json-out "$REPORTS/CRITICAL_RUNTIME_ERROR_SCAN.json" --markdown-out "$REPORTS/CRITICAL_RUNTIME_ERROR_SCAN.md"
python3 "$REPO_ROOT/tools/verify_frozen_controls.py" "$GAME" --json-out "$REPORTS/FROZEN_CONTROLS_POST.json" --markdown-out "$REPORTS/FROZEN_CONTROLS_POST.md"
cmp "$RECON_EVIDENCE/FROZEN_CONTROLS_PRE.json" "$REPORTS/FROZEN_CONTROLS_POST.json"

python3 - "$GAME" "$REPORTS/PRODUCT_SOURCE_PRE.json" "$REPORTS/PRODUCT_SOURCE_POST.json" "$REPORTS/PRODUCT_SOURCE_PRESERVATION.json" <<'PY'
from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1]); pre=json.loads(Path(sys.argv[2]).read_text()); post_path=Path(sys.argv[3]); report_path=Path(sys.argv[4])
post={p:{'bytes':(root/p).stat().st_size,'sha256':hashlib.sha256((root/p).read_bytes()).hexdigest()} for p in pre}
post_path.write_text(json.dumps(post,indent=2,sort_keys=True)+'\n')
passed=pre==post
report_path.write_text(json.dumps({'passed':passed,'product_source_changed':not passed,'pre':pre,'post':post},indent=2,sort_keys=True)+'\n')
if not passed: raise SystemExit('product source changed during Gate 2')
PY

python3 - "$REPORTS" <<'PY'
from pathlib import Path
import json,sys
r=Path(sys.argv[1])
classification=json.loads((r/'BRICK_FACTORY_CLASSIFICATION.json').read_text())
critical=json.loads((r/'CRITICAL_RUNTIME_ERROR_SCAN.json').read_text())
summary={
 'gate2_clean_reconstruction':'pass',
 'gate3_clean_import':'pass',
 'brick_factory_classification':classification['classification'],
 'brick_factory_conclusion':classification['conclusion'],
 'population_runtime':'pass',
 'critical_unresolved_count':critical['unresolved_count'],
 'frozen_controls':'pass',
 'product_source_changed':False,
 'later_gate_boundary':'stopped before export',
}
(r/'GATE2_GATE3_SUMMARY.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
PY
