#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:?repository root is required}"
SOURCE_ROOT="${2:?accepted reconstruction root is required}"
EVIDENCE="${3:?Gate 2 evidence directory is required}"
BASE="$REPO_ROOT/tools/vertical_slice/run_manama_souq_gate2_source_runtime.sh"
PATCHED="$SOURCE_ROOT/run_manama_souq_gate2_source_runtime_patched.sh"

python3 - "$BASE" "$PATCHED" <<'PY'
from pathlib import Path
import sys
base=Path(sys.argv[1]); out=Path(sys.argv[2])
text=base.read_text(encoding='utf-8')
old_copy='''cp "$REPO_ROOT/tests/gate2/souq_population_project_context_runtime.gd" "$GAME/tests/gate2/"
cp "$REPO_ROOT/tests/gate2/souq_population_project_context_runtime.tscn" "$GAME/tests/gate2/"'''
new_copy=old_copy+'''\ncp "$REPO_ROOT/tests/gate2/manama_souq_slice_project_context_runtime.gd" "$GAME/tests/gate2/"
cp "$REPO_ROOT/tests/gate2/manama_souq_slice_project_context_runtime.tscn" "$GAME/tests/gate2/"'''
if old_copy not in text:
    raise SystemExit('population harness copy boundary missing from base runner')
text=text.replace(old_copy,new_copy,1)
old_paths="paths=['tests/gate2/souq_population_project_context_runtime.gd','tests/gate2/souq_population_project_context_runtime.tscn']"
new_paths="paths=['tests/gate2/souq_population_project_context_runtime.gd','tests/gate2/souq_population_project_context_runtime.tscn','tests/gate2/manama_souq_slice_project_context_runtime.gd','tests/gate2/manama_souq_slice_project_context_runtime.tscn']"
if old_paths not in text:
    raise SystemExit('harness injection ledger boundary missing from base runner')
text=text.replace(old_paths,new_paths,1)
old_slice='require_marker manama-souq-slice 900 MANAMA_SOUQ_SLICE_RUNTIME_PASS "$GODOT" --headless --path "$GAME" --script "res://tests/manama_souq_slice_runtime.gd"'
new_slice=r'''run_process "$DIAGNOSTICS" manama-souq-slice-script-mode 300 "$GODOT" --headless --path "$GAME" --script "res://tests/manama_souq_slice_runtime.gd"
run_process "$DIAGNOSTICS" manama-souq-slice-project-context 900 "$GODOT" --headless --path "$GAME" "res://tests/gate2/manama_souq_slice_project_context_runtime.tscn"
python3 - "$DIAGNOSTICS" "$REPORTS/MANAMA_SOUQ_SLICE_HARNESS_CLASSIFICATION.json" <<'PY_SLICE'
from pathlib import Path
import json,re,sys
root=Path(sys.argv[1]); out=Path(sys.argv[2])
def read(name, marker):
 text=(root/f'{name}.log').read_text(errors='replace')
 return {
  'command':(root/f'{name}.command.txt').read_text().strip(),
  'exit_code':int((root/f'{name}.exit-code.txt').read_text()),
  'timed_out':(root/f'{name}.timeout.txt').read_text().strip()=='true',
  'touch_input_identifier_error_count':len(re.findall(r'Identifier not found: TouchInput',text,re.I)),
  'script_error_count':len(re.findall(r'SCRIPT ERROR|Parse Error|Parser Error|Failed to load script',text,re.I)),
  'pass_marker':marker in text,
 }
h=read('manama-souq-slice-script-mode','MANAMA_SOUQ_SLICE_RUNTIME_PASS')
p=read('manama-souq-slice-project-context','MANAMA_SOUQ_SLICE_PROJECT_CONTEXT_PASS')
hpass=h['exit_code']==0 and not h['timed_out'] and h['pass_marker']
ppass=p['exit_code']==0 and not p['timed_out'] and p['pass_marker']
if h['touch_input_identifier_error_count']>0 and ppass:
 classification='A'; conclusion='complete-slice script-mode autoload harness defect'
elif p['touch_input_identifier_error_count']>0:
 classification='B'; conclusion='product-source TouchInput resolution defect'
elif hpass and ppass:
 classification='C'; conclusion='historical complete-slice harness failure not reproducible'
else:
 classification='D'; conclusion='different complete-slice downstream blocker'
out.write_text(json.dumps({'classification':classification,'conclusion':conclusion,'historical_script_mode':h,'normal_project_context':p},indent=2,sort_keys=True)+'\n')
if classification in ('B','D'):
 raise SystemExit(21)
PY_SLICE
require_marker manama-souq-slice 900 MANAMA_SOUQ_SLICE_PROJECT_CONTEXT_PASS "$GODOT" --headless --path "$GAME" "res://tests/gate2/manama_souq_slice_project_context_runtime.tscn"'''
if old_slice not in text:
    raise SystemExit('complete-slice script harness boundary missing from base runner')
text=text.replace(old_slice,new_slice,1)
out.write_text(text,encoding='utf-8')
PY
chmod +x "$PATCHED"
printf '%s\n' 'Gate 2 harness wrapper: population and complete-slice project-context execution enabled.'
bash "$PATCHED" "$REPO_ROOT" "$SOURCE_ROOT" "$EVIDENCE"
