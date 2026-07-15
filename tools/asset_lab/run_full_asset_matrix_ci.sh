#!/usr/bin/env bash
set -euo pipefail

ROOT="$PWD"
BUILD="$ROOT/build/full-asset-matrix"
REPORTS="$BUILD/reports"
LOGS="$BUILD/logs"
ARTIFACTS="$BUILD/artifacts"
DOWNLOADS="$BUILD/downloads"
GAME="$BUILD/game"
ASSET_REPO="$BUILD/asset-authority"
GENERATED="$BUILD/generated/full_matrix"
mkdir -p "$REPORTS" "$LOGS" "$ARTIFACTS" "$DOWNLOADS"
mark() { printf '\n===== %s =====\n' "$1"; }

mark "Verify exact full-matrix integration ancestry"
test "$(git rev-parse HEAD)" = "${EXPECTED_INTEGRATION_SHA}"
git merge-base --is-ancestor "${FROZEN_PREMIUM_AUTHORITY}" HEAD
git merge-base --is-ancestor "${BATCH1_AUTHORITY}" HEAD
git rev-parse HEAD | tee "$REPORTS/INTEGRATION_HEAD.txt"
for protected in scripts/world.gd scripts/player_controller.gd scripts/touch_input.gd; do
  git rev-parse "HEAD:$protected"
done | tee "$REPORTS/PROTECTED_REPOSITORY_BLOBS.txt"

mark "Recover checksum-locked game source"
mkdir -p "$GAME"
curl --fail --location --retry 8 --retry-all-errors --proto '=https' "$GAME_SOURCE_URL" -o "$DOWNLOADS/game-source.zip"
echo "$GAME_SOURCE_SHA256  $DOWNLOADS/game-source.zip" | sha256sum -c -
unzip -tq "$DOWNLOADS/game-source.zip"
unzip -q "$DOWNLOADS/game-source.zip" -d "$GAME"
test -f "$GAME/project.godot"

mark "Protected-control pre-check"
python3 tools/verify_frozen_controls.py "$GAME" --json-out "$REPORTS/FROZEN_CONTROLS_PRE.json" --markdown-out "$REPORTS/FROZEN_CONTROLS_PRE.md"
python3 - "$REPORTS/FROZEN_CONTROLS_PRE.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1])); assert r['checks']==25 and r['failures']==[], r
PY

mark "Verify corrected asset source integrity"
git clone --filter=blob:none --no-checkout https://github.com/MuhamedZanabal/Bahrain_bricks_Assets.git "$ASSET_REPO"
git -C "$ASSET_REPO" checkout --detach "$ASSET_CORRECTIVE_COMMIT"
test "$(git -C "$ASSET_REPO" rev-parse HEAD)" = "$ASSET_CORRECTIVE_COMMIT"
git -C "$ASSET_REPO" merge-base --is-ancestor "$ASSET_AUTHORITY_COMMIT" HEAD
(
  cd "$ASSET_REPO"
  python3 tools/source_integrity.py verify --root . --ledger SHA256SUMS | tee "$REPORTS/ASSET_SOURCE_INTEGRITY.json"
  sha256sum -c SHA256SUMS | tee "$LOGS/asset-sha256-direct.log"
  ! grep -q ': FAILED' "$LOGS/asset-sha256-direct.log"
  python3 -m unittest discover -s tests -v 2>&1 | tee "$LOGS/asset-python-tests.log"
  grep -q 'Ran 20 tests' "$LOGS/asset-python-tests.log"
  python3 tools/validate_manifests.py | tee "$LOGS/asset-manifest-validation.log"
  grep -q '98 master assets' "$LOGS/asset-manifest-validation.log"
  python3 tools/check_signing_material.py . | tee "$LOGS/asset-signing-scan.log"
  grep -q 'passed' "$LOGS/asset-signing-scan.log"
)

mark "Run full-matrix contract tests"
python3 -m unittest \
  tests.test_full_asset_matrix_v1 \
  tests.test_asset_production_workflow \
  tests.test_asset_lab_runtime_integration \
  tests.test_golden_master_contract \
  tests.test_golden_master_materials \
  tests.test_golden_master_generation_plan \
  tests.test_golden_master_runtime_contract \
  tests.test_golden_master_v3_towers \
  tests.test_golden_master_v31_hero -v 2>&1 | tee "$LOGS/full-matrix-python-tests.log"
python3 -m py_compile tools/asset_lab/*.py tests/*.py

mark "Resolve Android build tools"
SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
test -n "$SDK_ROOT"
BUILD_TOOLS_DIR="$SDK_ROOT/build-tools/$ANDROID_BUILD_TOOLS"
for tool in aapt apksigner zipalign; do test -x "$BUILD_TOOLS_DIR/$tool"; done
test -x "$SDK_ROOT/platform-tools/adb"
export PATH="$BUILD_TOOLS_DIR:$SDK_ROOT/platform-tools:$PATH"

mark "Install official checksum-verified Blender and Godot"
cd "$DOWNLOADS"
blender_archive="blender-${BLENDER_VERSION}-linux-x64.tar.xz"
blender_base="https://download.blender.org/release/Blender4.3"
curl --fail --location --retry 8 --retry-all-errors --proto '=https' "$blender_base/$blender_archive" -o "$blender_archive"
curl --fail --location --retry 8 --retry-all-errors --proto '=https' "$blender_base/blender-${BLENDER_VERSION}.sha256" -o blender.sha256
grep " $blender_archive$" blender.sha256 | sha256sum -c -
tar -xf "$blender_archive"
BLENDER="$DOWNLOADS/blender-${BLENDER_VERSION}-linux-x64/blender"
godot_base="https://github.com/godotengine/godot/releases/download/4.3-stable"
godot_archive="Godot_v${GODOT_VERSION}-stable_linux.x86_64.zip"
templates_archive="Godot_v${GODOT_VERSION}-stable_export_templates.tpz"
curl --fail --location --retry 8 --retry-all-errors --proto '=https' "$godot_base/SHA512-SUMS.txt" -o godot-SHA512-SUMS.txt
curl --fail --location --retry 8 --retry-all-errors --proto '=https' "$godot_base/$godot_archive" -o "$godot_archive"
curl --fail --location --retry 8 --retry-all-errors --proto '=https' "$godot_base/$templates_archive" -o "$templates_archive"
grep " $godot_archive$" godot-SHA512-SUMS.txt | sha512sum -c -
grep " $templates_archive$" godot-SHA512-SUMS.txt | sha512sum -c -
unzip -q "$godot_archive" -d godot-bin
GODOT="$DOWNLOADS/godot-bin/Godot_v${GODOT_VERSION}-stable_linux.x86_64"
rm -rf godot-templates
unzip -q "$templates_archive" -d godot-templates
mkdir -p "$HOME/.local/share/godot/export_templates/4.3.stable"
cp -a godot-templates/templates/. "$HOME/.local/share/godot/export_templates/4.3.stable/"
cd "$ROOT"
"$BLENDER" --version | tee "$REPORTS/BLENDER_VERSION.txt"
grep -q '^Blender 4.3.2' "$REPORTS/BLENDER_VERSION.txt"
"$GODOT" --version | tee "$REPORTS/GODOT_VERSION.txt"
grep -q '^4.3.stable.official.77dcf97d8' "$REPORTS/GODOT_VERSION.txt"

mark "Install Khronos glTF Validator"
GLTF_VALIDATOR_ROOT="$BUILD/gltf-validator"
mkdir -p "$GLTF_VALIDATOR_ROOT"
npm install --prefix "$GLTF_VALIDATOR_ROOT" --ignore-scripts --no-audit --no-fund "gltf-validator@$GLTF_VALIDATOR_VERSION"
export GLTF_VALIDATOR_ROOT

mark "Generate shared mobile texture authority"
python3 tools/asset_lab/generate_golden_master_textures.py \
  --seed 140500 \
  --output-dir "$BUILD/generated/textures" \
  --report "$REPORTS/FULL_MATRIX_TEXTURES.json"
test "$(find "$BUILD/generated/textures" -type f -name '*.png' | wc -l)" -eq 24

mark "Generate exact textured 436-GLB production matrix"
"$BLENDER" --background --factory-startup --python-exit-code 1 \
  --python tools/asset_lab/generate_full_asset_matrix_v1.py -- generate \
  --seed 1405 \
  --texture-dir "$BUILD/generated/textures" \
  --output-dir "$GENERATED" \
  --report "$REPORTS/FULL_ASSET_MATRIX_GENERATION.json" \
  --runtime-manifest "$REPORTS/FULL_ASSET_MATRIX_RUNTIME_MANIFEST.json"
test "$(find "$GENERATED" -type f -name '*.glb' | wc -l)" -eq 436

mark "Validate textured matrix, LODs, profiles, collisions, hashes and manifest"
python3 tools/asset_lab/validate_full_asset_matrix_v1.py \
  --architecture-root "$GENERATED/architecture" \
  --commercial-root "$GENERATED/commercial" \
  --manifest docs/assets/ASSET_MASTER_MANIFEST.csv \
  --report "$REPORTS/FULL_ASSET_MATRIX_VALIDATION.json"
python3 - "$REPORTS/FULL_ASSET_MATRIX_VALIDATION.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1])); assert r['passed']; assert r['total_derivatives']==436; assert r['textured_asset_count']==436; assert r['unique_sha256_count']==436; assert r['collision_present_total']==148
PY

mark "Run Khronos validation for every textured GLB"
validated=0
while IFS= read -r -d '' glb; do
  relative="${glb#"$GENERATED/"}"
  report_name="${relative//\//__}"
  node tools/asset_lab/validate_gltf_khronos.js "$glb" "$REPORTS/full-${report_name%.glb}.json"
  validated=$((validated + 1))
done < <(find "$GENERATED" -name '*.glb' -type f -print0 | sort -z)
test "$validated" -eq 436
printf '%s\n' "$validated" | tee "$REPORTS/KHRONOS_FULL_MATRIX_VALIDATED_COUNT.txt"

mark "Install complete matrix into recovered real game source"
cp -a assets/. "$GAME/assets/"
mkdir -p "$GAME/assets/generated/full_matrix" "$GAME/asset_lab/runtime" "$GAME/scripts" "$GAME/tests"
cp -a "$GENERATED/." "$GAME/assets/generated/full_matrix/"
cp "$REPORTS/FULL_ASSET_MATRIX_RUNTIME_MANIFEST.json" "$GAME/asset_lab/runtime/full_asset_matrix_manifest.json"
cp scripts/asset_lab_runtime.gd "$GAME/scripts/asset_lab_runtime.gd"
cp scripts/golden_master_quality.gd "$GAME/scripts/golden_master_quality.gd"
cp scripts/golden_master_lod_instance.gd "$GAME/scripts/golden_master_lod_instance.gd"
cp scripts/full_asset_matrix_runtime.gd "$GAME/scripts/full_asset_matrix_runtime.gd"
cp scenes/world.tscn "$GAME/scenes/world.tscn"
cp tests/test_asset_lab_runtime_integration.py "$GAME/tests/test_asset_lab_runtime_integration.py"
cp tests/test_full_asset_matrix_runtime.py "$GAME/tests/test_full_asset_matrix_runtime.py"
cp -a "$GENERATED/architecture/balanced/traditional/." "$GAME/assets/environment/architecture/traditional/"
cp -a "$GENERATED/architecture/balanced/souq/." "$GAME/assets/environment/architecture/souq/"
cp -a "$GENERATED/architecture/balanced/waterfront/." "$GAME/assets/environment/architecture/waterfront/"
cp -a "$GENERATED/commercial/." "$GAME/assets/environment/architecture/commercial/"

mark "Run clean Godot import for all runtime profiles"
rm -rf "$GAME/.godot"
"$GODOT" --headless --path "$GAME" --editor --import --quit --verbose 2>&1 | tee "$LOGS/godot-full-matrix-import.log"
! grep -Eiq 'SCRIPT ERROR|Parse Error|ERROR:.*(failed|missing|invalid)' "$LOGS/godot-full-matrix-import.log"
test "$(find "$GAME/.godot/imported" -type f -name '*.md5' | grep -c 'glb')" -ge 436

mark "Validate manifest-driven real-world integration"
python3 tests/test_asset_lab_runtime_integration.py 2>&1 | tee "$LOGS/asset-runtime-integration.log"
python3 tests/test_full_asset_matrix_runtime.py 2>&1 | tee "$LOGS/full-matrix-runtime-contract.log"
grep -q 'full_asset_matrix_runtime.gd' "$GAME/scenes/world.tscn"

mark "Apply verified premium validation overlay"
python3 tools/apply_premium_overlay_resilient.py "$GAME" --report "$REPORTS/PREMIUM_WORLD_OVERLAY_REPORT.json"
python3 tools/apply_premium_validation_corrections.py "$GAME" --report "$REPORTS/RUNTIME_DEFECT_CORRECTIONS.json"
"$GODOT" --headless --path "$GAME" --editor --import --quit --verbose 2>&1 | tee "$LOGS/godot-full-matrix-post-overlay-import.log"
! grep -Eiq 'SCRIPT ERROR|Parse Error|ERROR:.*(failed|missing|invalid)' "$LOGS/godot-full-matrix-post-overlay-import.log"

mark "Run gameplay regression suites"
bash tools/asset_lab/run_game_regressions.sh "$GODOT" "$GAME" "$LOGS" "$REPORTS"

mark "Protected-control post-check"
python3 tools/verify_frozen_controls.py "$GAME" --json-out "$REPORTS/FROZEN_CONTROLS_POST.json" --markdown-out "$REPORTS/FROZEN_CONTROLS_POST.md"
cmp "$REPORTS/FROZEN_CONTROLS_PRE.json" "$REPORTS/FROZEN_CONTROLS_POST.json"

mark "Export full-matrix Android APK"
ANDROID_BUILD_TOOLS="$ANDROID_BUILD_TOOLS" VERSION_CODE="$VERSION_CODE" VERSION_NAME="$VERSION_NAME" \
  bash tools/asset_lab/export_asset_production_android.sh "$GODOT" "$GAME" "$ARTIFACTS/$APK_NAME" "$PACKAGE_NAME" "$REPORTS" "$LOGS"

test -s "$ARTIFACTS/$APK_NAME"
grep -q "package: name='$PACKAGE_NAME' versionCode='$VERSION_CODE' versionName='$VERSION_NAME'" "$REPORTS/APK_BADGING.txt"
test -s "$REPORTS/APK_SIGNING.txt"
sha256sum "$ARTIFACTS/$APK_NAME" | tee "$REPORTS/APK_SHA256SUM.txt"

mark "Build final production summary"
python3 - "$REPORTS" "$ARTIFACTS/$APK_NAME" <<'PY'
from pathlib import Path
import hashlib,json,sys
reports=Path(sys.argv[1]); apk=Path(sys.argv[2])
validation=json.loads((reports/'FULL_ASSET_MATRIX_VALIDATION.json').read_text())
summary={
 'passed': validation['passed'],
 'architecture_sources':48,
 'architecture_derivatives':432,
 'commercial_outputs':4,
 'total_glbs':436,
 'textured_glbs':validation['textured_asset_count'],
 'unique_glb_hashes':validation['unique_sha256_count'],
 'khronos_validated':int((reports/'KHRONOS_FULL_MATRIX_VALIDATED_COUNT.txt').read_text().strip()),
 'protected_pre_post_identical': True,
 'apk':{'path':apk.as_posix(),'bytes':apk.stat().st_size,'sha256':hashlib.sha256(apk.read_bytes()).hexdigest()},
}
(reports/'FULL_ASSET_MATRIX_COMPLETION.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
PY
