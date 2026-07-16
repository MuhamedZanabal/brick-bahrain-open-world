#!/usr/bin/env bash
set -euo pipefail

GODOT="${1:?Godot binary is required}"
GAME="${2:?Game project path is required}"
LOGS="${3:?Log directory is required}"
REPORTS="${4:?Report directory is required}"
mkdir -p "$LOGS" "$REPORTS"

run_python_contract() {
  local test_name="$1"
  python3 "$GAME/tests/$test_name" 2>&1 | tee "$LOGS/${test_name%.py}.log"
}

run_godot_runtime() {
  local script_name="$1"
  local marker="$2"
  local log="$LOGS/${script_name%.gd}.log"
  "$GODOT" --headless --path "$GAME" --script "res://tests/$script_name" 2>&1 | tee "$log"
  grep -q "$marker" "$log"
}

for test_name in \
  test_manama_souq_layout_contract.py \
  test_karak_delivery_mission_contract.py \
  test_manama_souq_layout_loader.py \
  test_souq_population_contract.py \
  test_karak_delivery_hud_contract.py \
  test_manama_souq_slice_contract.py \
  test_manama_souq_source_gate.py; do
  run_python_contract "$test_name"
done

rm -rf "$GAME/.godot"
"$GODOT" --headless --path "$GAME" --editor --import --quit --verbose 2>&1 | tee "$LOGS/manama-souq-import.log"

if grep -Eiq 'SCRIPT ERROR|Parse Error|Failed to load script|Can.t open dynamic library|FATAL' "$LOGS/manama-souq-import.log"; then
  echo "Godot import contained a blocking error" >&2
  exit 1
fi

imported_glbs="$(find "$GAME/.godot/imported" -type f -name '*.md5' | grep -c 'glb' || true)"
[[ "$imported_glbs" -ge 436 ]] || { echo "Expected at least 436 imported GLBs, received $imported_glbs" >&2; exit 1; }

run_godot_runtime karak_delivery_mission_runtime.gd KARAK_DELIVERY_RUNTIME_PASS
run_godot_runtime manama_souq_layout_runtime.gd MANAMA_SOUQ_LAYOUT_RUNTIME_PASS
run_godot_runtime souq_population_runtime.gd SOUQ_POPULATION_RUNTIME_PASS
run_godot_runtime karak_delivery_hud_runtime.gd KARAK_DELIVERY_HUD_RUNTIME_PASS
run_godot_runtime manama_souq_slice_runtime.gd MANAMA_SOUQ_SLICE_RUNTIME_PASS

bash tools/asset_lab/run_game_regressions.sh "$GODOT" "$GAME" "$LOGS" "$REPORTS"

python3 - "$LOGS" "$REPORTS" "$imported_glbs" <<'PY'
from pathlib import Path
import json,re,sys
logs=Path(sys.argv[1]); reports=Path(sys.argv[2]); imported=int(sys.argv[3])
patterns={
    'script_error':re.compile(r'SCRIPT ERROR',re.I),
    'parse_error':re.compile(r'Parse Error',re.I),
    'failed_script':re.compile(r'Failed to load script',re.I),
    'dynamic_library':re.compile(r"Can.t open dynamic library",re.I),
    'fatal':re.compile(r'\bFATAL\b|Fatal signal|FATAL EXCEPTION|ANR in',re.I),
}
findings=[]
for path in sorted(logs.glob('*.log')):
    text=path.read_text(errors='replace')
    for name,pattern in patterns.items():
        matches=pattern.findall(text)
        if matches:
            findings.append({'log':path.name,'pattern':name,'count':len(matches)})
report={
    'passed':not findings,
    'imported_glb_md5_count':imported,
    'runtime_markers':[
        'KARAK_DELIVERY_RUNTIME_PASS',
        'MANAMA_SOUQ_LAYOUT_RUNTIME_PASS',
        'SOUQ_POPULATION_RUNTIME_PASS',
        'KARAK_DELIVERY_HUD_RUNTIME_PASS',
        'MANAMA_SOUQ_SLICE_RUNTIME_PASS',
    ],
    'findings':findings,
}
(reports/'MANAMA_SOUQ_SOURCE_GATE.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
if findings:
    raise SystemExit(json.dumps(findings,indent=2))
PY

printf 'MANAMA_SOUQ_SOURCE_GATE_PASS imported_glbs=%s\n' "$imported_glbs" | tee "$REPORTS/MANAMA_SOUQ_SOURCE_GATE_PASS.txt"
