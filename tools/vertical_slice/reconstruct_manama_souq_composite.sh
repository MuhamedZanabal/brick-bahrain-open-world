#!/usr/bin/env bash
set -euo pipefail

RUN_LABEL="${1:?run label A or B is required}"
ROOT="${2:?independent reconstruction root is required}"
CONTRACT="${3:?authority contract path is required}"
CANDIDATE_COMMIT="${4:?candidate commit is required}"
REPO_ROOT="${GITHUB_WORKSPACE:-$PWD}"
TOOL="$REPO_ROOT/tools/vertical_slice/composite_source_authority.py"
GAME="$ROOT/game"
SOURCE="$ROOT/source"
DOWNLOADS="$ROOT/downloads"
REPORTS="$ROOT/reports"
EVIDENCE="$ROOT/evidence"
STATE="$ROOT/ORIGIN_STATE.json"
PYTHON="$ROOT/venv/bin/python"

case "$RUN_LABEL" in A|B) ;; *) echo "run label must be A or B" >&2; exit 2;; esac
rm -rf "$ROOT"
mkdir -p "$GAME" "$SOURCE" "$DOWNLOADS" "$REPORTS" "$EVIDENCE"

stage_log() {
  python3 - "$EVIDENCE/RECONSTRUCTION_LOG.json" "$1" <<'PY'
from pathlib import Path
import json,sys
path=Path(sys.argv[1]); stage=sys.argv[2]
if path.exists(): value=json.loads(path.read_text())
else: value={'schema_version':1,'stages':[]}
value['stages'].append(stage)
path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')
PY
}

track_origin() {
  local category="$1"
  python3 - "$GAME" "$STATE" "$category" <<'PY'
from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1]); state_path=Path(sys.argv[2]); category=sys.argv[3]
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
files={}
for path in sorted(root.rglob('*')):
    if path.is_symlink(): raise SystemExit(f'symbolic link introduced during reconstruction: {path}')
    if path.is_file(): files[path.relative_to(root).as_posix()]=digest(path)
if state_path.exists():
    state=json.loads(state_path.read_text())
else:
    state={'schema_version':1,'hashes':{},'origins':{}}
old=state['hashes']; origins=state['origins']
for relative,sha in files.items():
    if old.get(relative)!=sha: origins[relative]=category
for relative in list(origins):
    if relative not in files: origins.pop(relative,None)
state={'schema_version':1,'hashes':files,'origins':origins}
state_path.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
PY
}

readarray -t INPUTS < <(python3 - "$CONTRACT" <<'PY'
import json,sys
c=json.load(open(sys.argv[1]))
for item in c['external_inputs']:
 print('\t'.join([item['id'],item['immutable_locator'],item['sha256'],str(item['bytes']),item['provenance_authority'],item['extraction_destination']]))
PY
)
for row in "${INPUTS[@]}"; do
  IFS=$'\t' read -r id locator digest bytes provenance destination <<<"$row"
  case "$id" in
    assets436) ASSET_URL="$locator"; ASSET_SHA="$digest"; ASSET_BYTES="$bytes"; ASSET_PROVENANCE="$provenance"; ASSET_DEST="$destination" ;;
    historical_source) HISTORICAL_URL="$locator"; HISTORICAL_SHA="$digest"; HISTORICAL_BYTES="$bytes"; HISTORICAL_PROVENANCE="$provenance"; HISTORICAL_DEST="$destination" ;;
    *) echo "unknown external input id: $id" >&2; exit 2 ;;
  esac
done
: "${ASSET_URL:?assets436 input missing from contract}"
: "${HISTORICAL_URL:?historical_source input missing from contract}"

python3 "$TOOL" validate-contract --contract "$CONTRACT" --repo-root "$REPO_ROOT" > "$REPORTS/CONTRACT_VALIDATION.json"
stage_log contract_validated

test "${ImageVersion:-}" = "20260714.240.1"
test "$(. /etc/os-release; printf '%s' "$PRETTY_NAME")" = "Ubuntu 24.04.4 LTS"
test "$(python3 -c 'import platform; print(platform.python_version())')" = "3.12.3"
sudo apt-get update
sudo apt-get install -y --no-install-recommends librsvg2-bin=2.58.0+dfsg-1build1
test "$(dpkg-query -W -f='${Version}' librsvg2-bin)" = "2.58.0+dfsg-1build1"
python3 -m venv "$ROOT/venv"
"$ROOT/venv/bin/python" -m pip install --disable-pip-version-check --no-cache-dir Pillow==12.3.0
test "$("$ROOT/venv/bin/python" -c 'from importlib.metadata import version; print(version("Pillow"))')" = "12.3.0"

GODOT_ARCHIVE="$DOWNLOADS/Godot_v4.3-stable_linux.x86_64.zip"
curl --fail --location --retry 8 --retry-all-errors --proto '=https' \
  https://github.com/godotengine/godot/releases/download/4.3-stable/Godot_v4.3-stable_linux.x86_64.zip \
  -o "$GODOT_ARCHIVE"
EXPECTED_GODOT_SHA512="$(python3 - "$CONTRACT" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))['toolchain']['godot_archive_sha512'])
PY
)"
echo "$EXPECTED_GODOT_SHA512  $GODOT_ARCHIVE" | sha512sum -c -
python3 - "$CONTRACT" "$EVIDENCE/TOOLCHAIN_ENVIRONMENT_LEDGER.json" "$GODOT_ARCHIVE" <<'PY'
from pathlib import Path
import hashlib,json,os,platform,subprocess,sys
contract=json.load(open(sys.argv[1])); out=Path(sys.argv[2]); godot=Path(sys.argv[3]); t=contract['toolchain']
value={
 'schema_version':1,
 'runner_image':t['runner_image'],
 'runner_image_version':os.environ.get('ImageVersion'),
 'os_release':t['os_release'],
 'python':platform.python_version(),
 'pillow':t['pillow'],
 'librsvg2_bin':subprocess.check_output(['dpkg-query','-W','-f=${Version}','librsvg2-bin'],text=True),
 'rsvg_convert':subprocess.check_output(['rsvg-convert','--version'],text=True).strip(),
 'godot_version':t['godot_version'],
 'godot_archive_bytes':godot.stat().st_size,
 'godot_archive_sha512':hashlib.sha512(godot.read_bytes()).hexdigest(),
 'reconstruction_scripts':contract['reconstruction_scripts'],
}
out.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
PY
stage_log toolchain_verified

ASSET_ZIP="$DOWNLOADS/assets436.zip"
HISTORICAL_ZIP="$DOWNLOADS/historical-source.zip"
curl --fail --location --retry 8 --retry-all-errors --proto '=https' "$ASSET_URL" -o "$ASSET_ZIP"
python3 "$TOOL" verify-input --file "$ASSET_ZIP" --expected-sha256 "$ASSET_SHA" --expected-bytes "$ASSET_BYTES" --id assets436 --output "$REPORTS/assets436.json"
curl --fail --location --retry 8 --retry-all-errors --proto '=https' "$HISTORICAL_URL" -o "$HISTORICAL_ZIP"
python3 "$TOOL" verify-input --file "$HISTORICAL_ZIP" --expected-sha256 "$HISTORICAL_SHA" --expected-bytes "$HISTORICAL_BYTES" --id historical_source --output "$REPORTS/historical_source.json"
unzip -tq "$ASSET_ZIP"
unzip -tq "$HISTORICAL_ZIP"
unzip -q "$ASSET_ZIP" -d "$SOURCE"
unzip -q "$HISTORICAL_ZIP" -d "$GAME"
test -f "$GAME/project.godot"
test "$(find "$SOURCE/generated/full_matrix" -type f -name '*.glb' | wc -l)" -eq 436
python3 - "$CONTRACT" "$REPORTS/assets436.json" "$REPORTS/historical_source.json" "$EVIDENCE/INPUT_AUTHORITY_LEDGER.json" <<'PY'
from pathlib import Path
import json,sys
contract=json.load(open(sys.argv[1])); actual={}
for p in sys.argv[2:4]:
 r=json.load(open(p)); actual[r['id']]=r
items=[]
for item in contract['external_inputs']:
 a=actual[item['id']]
 items.append({**item,'actual_sha256':a['sha256'],'actual_bytes':a['bytes'],'verified':True})
Path(sys.argv[4]).write_text(json.dumps({'schema_version':1,'passed':True,'inputs':items},indent=2,sort_keys=True)+'\n')
PY
track_origin "historical source"
stage_log external_inputs_verified_and_extracted

mkdir -p "$GAME/assets" "$GAME/assets/generated/full_matrix" "$GAME/asset_lab/runtime" "$GAME/scripts" "$GAME/scenes" "$GAME/tests" "$GAME/tools/vertical_slice" "$GAME/.github/workflows"
cp -a "$REPO_ROOT/assets/." "$GAME/assets/"
track_origin "PR #59 checkout"
cp -a "$SOURCE/generated/full_matrix/." "$GAME/assets/generated/full_matrix/"
cp "$SOURCE/reports/FULL_ASSET_MATRIX_RUNTIME_MANIFEST.json" "$GAME/asset_lab/runtime/full_asset_matrix_manifest.json"
track_origin "436-asset authority"
test "$(find "$GAME/assets/generated/full_matrix" -type f -name '*.glb' | wc -l)" -eq 436

python3 "$REPO_ROOT/tools/verify_frozen_controls.py" "$GAME" --json-out "$EVIDENCE/FROZEN_CONTROLS_PRE.json" --markdown-out "$EVIDENCE/FROZEN_CONTROLS_PRE.md"

"$PYTHON" "$REPO_ROOT/tools/apply_premium_overlay_resilient.py" "$GAME" --report "$EVIDENCE/PREMIUM_SOUQ_OVERLAY_REPORT.json" | tee "$REPORTS/premium-overlay.log"
track_origin "premium overlay"
python3 - "$STATE" "$EVIDENCE/PREMIUM_SOUQ_OVERLAY_REPORT.json" <<'PY'
from pathlib import Path
import json,sys
state=json.load(open(sys.argv[1])); report=json.load(open(sys.argv[2]))
for relative in report.get('generated_binary_artwork',[]):
 if relative in state['origins']: state['origins'][relative]='deterministically generated output'
Path(sys.argv[1]).write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
PY

"$PYTHON" "$REPO_ROOT/tools/apply_premium_validation_corrections.py" "$GAME" --report "$EVIDENCE/PREMIUM_SOUQ_CORRECTIONS.json" | tee "$REPORTS/premium-corrections.log"
track_origin "validation correction"

cp "$REPO_ROOT/asset_lab/runtime/manama_souq_layout_v1.json" "$GAME/asset_lab/runtime/"
cp "$REPO_ROOT/scripts/golden_master_quality.gd" "$REPO_ROOT/scripts/golden_master_lod_instance.gd" "$GAME/scripts/"
cp "$REPO_ROOT/scripts/karak_delivery_mission.gd" "$REPO_ROOT/scripts/manama_souq_layout_loader.gd" "$REPO_ROOT/scripts/souq_population_controller.gd" "$REPO_ROOT/scripts/karak_delivery_hud.gd" "$REPO_ROOT/scripts/manama_souq_vertical_slice.gd" "$GAME/scripts/"
cp "$REPO_ROOT/scenes/karak_delivery_hud.tscn" "$REPO_ROOT/scenes/manama_souq_vertical_slice.tscn" "$GAME/scenes/"
cp "$REPO_ROOT/tests/test_manama_souq_layout_contract.py" "$REPO_ROOT/tests/test_karak_delivery_mission_contract.py" "$REPO_ROOT/tests/test_manama_souq_layout_loader.py" "$REPO_ROOT/tests/test_souq_population_contract.py" "$REPO_ROOT/tests/test_karak_delivery_hud_contract.py" "$REPO_ROOT/tests/test_manama_souq_slice_contract.py" "$REPO_ROOT/tests/test_manama_souq_source_gate.py" "$REPO_ROOT/tests/test_manama_souq_composite_authority.py" "$GAME/tests/"
cp "$REPO_ROOT/tests/karak_delivery_mission_runtime.gd" "$REPO_ROOT/tests/manama_souq_layout_runtime.gd" "$REPO_ROOT/tests/souq_population_runtime.gd" "$REPO_ROOT/tests/karak_delivery_hud_runtime.gd" "$REPO_ROOT/tests/manama_souq_slice_runtime.gd" "$GAME/tests/"
cp "$REPO_ROOT/tools/vertical_slice/run_manama_souq_source_gate.sh" "$REPO_ROOT/tools/vertical_slice/reconstruct_manama_souq_composite.sh" "$REPO_ROOT/tools/vertical_slice/composite_source_authority.py" "$GAME/tools/vertical_slice/"
cp "$REPO_ROOT/.github/workflows/manama-souq-vertical-slice.yml" "$GAME/.github/workflows/"
chmod +x "$GAME/tools/vertical_slice/run_manama_souq_source_gate.sh" "$GAME/tools/vertical_slice/reconstruct_manama_souq_composite.sh" "$GAME/tools/vertical_slice/composite_source_authority.py"
track_origin "PR #59 checkout"

python3 "$REPO_ROOT/tools/verify_frozen_controls.py" "$GAME" --json-out "$EVIDENCE/FROZEN_CONTROLS_POST.json" --markdown-out "$EVIDENCE/FROZEN_CONTROLS_POST.md"
cmp "$EVIDENCE/FROZEN_CONTROLS_PRE.json" "$EVIDENCE/FROZEN_CONTROLS_POST.json"

python3 - "$STATE" "$EVIDENCE/ORIGIN_LEDGER.json" <<'PY'
from pathlib import Path
import json,sys
state=json.load(open(sys.argv[1]))
files=[{'path':p,'origin':state['origins'][p]} for p in sorted(state['origins'],key=lambda x:x.encode())]
Path(sys.argv[2]).write_text(json.dumps({'schema_version':1,'files':files},indent=2,sort_keys=True)+'\n')
PY
python3 "$TOOL" manifest --contract "$CONTRACT" --repo-root "$REPO_ROOT" --game-root "$GAME" --origin-ledger "$EVIDENCE/ORIGIN_LEDGER.json" --candidate-commit "$CANDIDATE_COMMIT" --output "$EVIDENCE/FINAL_TREE_MANIFEST.json" --report "$EVIDENCE/FINAL_TREE_AUTHORITY.json"
python3 "$TOOL" archive --game-root "$GAME" --manifest "$EVIDENCE/FINAL_TREE_MANIFEST.json" --output "$EVIDENCE/MANAMA_SOUQ_COMPOSITE_SOURCE.zip" --report "$EVIDENCE/SOURCE_ARCHIVE_REPORT.json"
cp "$CONTRACT" "$EVIDENCE/AUTHORITY_CONTRACT.json"
cp "$REPORTS/CONTRACT_VALIDATION.json" "$EVIDENCE/CONTRACT_VALIDATION.json"
stage_log final_tree_manifested_and_archived
python3 "$TOOL" inventory --root "$EVIDENCE" --output "$EVIDENCE/EVIDENCE_INVENTORY.json"
python3 "$TOOL" verify-inventory --root "$EVIDENCE" --inventory "$EVIDENCE/EVIDENCE_INVENTORY.json" > "$REPORTS/EVIDENCE_INVENTORY_VERIFICATION.json"
printf 'PR59_GATE1_RECONSTRUCTION_%s_PASS\n' "$RUN_LABEL"
