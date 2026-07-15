#!/usr/bin/env bash
set -euo pipefail

ROOT="$PWD"
BUILD="$ROOT/build/asset-production"
REPORTS="$BUILD/reports"
LOGS="$BUILD/logs"
ARTIFACTS="$BUILD/artifacts"
DOWNLOADS="$BUILD/downloads"
GAME="$BUILD/game"
ASSET_REPO="$BUILD/asset-authority"
mkdir -p "$REPORTS" "$LOGS" "$ARTIFACTS" "$DOWNLOADS"

mark() { printf '\n===== %s =====\n' "$1"; }

mark "Verify exact integration ancestry"
test "$(git rev-parse HEAD)" = "${GITHUB_SHA}"
git merge-base --is-ancestor "${FROZEN_PREMIUM_AUTHORITY}" HEAD
git merge-base --is-ancestor "${EXPECTED_CHECKPOINT}" HEAD
git rev-parse HEAD | tee "$REPORTS/INTEGRATION_HEAD.txt"

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
)

mark "Run corrected asset repository tests"
(
  cd "$ASSET_REPO"
  python3 -m unittest discover -s tests -v 2>&1 | tee "$LOGS/asset-python-tests.log"
  grep -q 'Ran 20 tests' "$LOGS/asset-python-tests.log"
  python3 tools/validate_manifests.py | tee "$LOGS/asset-manifest-validation.log"
  grep -q '98 master assets' "$LOGS/asset-manifest-validation.log"
  python3 tools/check_signing_material.py . | tee "$LOGS/asset-signing-scan.log"
  grep -q 'passed' "$LOGS/asset-signing-scan.log"
  python3 -m py_compile tools/*.py tools/blender/*.py tests/*.py
)

mark "Run integration Python tests"
python3 -m unittest discover -s tests -v 2>&1 | tee "$LOGS/game-python-tests.log"
python3 -m py_compile tools/asset_lab/*.py tests/*.py

mark "Resolve Android build tools"
SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
test -n "$SDK_ROOT"
BUILD_TOOLS_DIR="$SDK_ROOT/build-tools/$ANDROID_BUILD_TOOLS"
for tool in aapt apksigner zipalign; do test -x "$BUILD_TOOLS_DIR/$tool"; done
test -x "$SDK_ROOT/platform-tools/adb"
export PATH="$BUILD_TOOLS_DIR:$SDK_ROOT/platform-tools:$PATH"
printf '%s\n' "$BUILD_TOOLS_DIR" "$SDK_ROOT/platform-tools" >> "$GITHUB_PATH"

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

mark "Verify installed production tool versions"
"$BLENDER" --version | tee "$REPORTS/BLENDER_VERSION.txt"
grep -q '^Blender 4.3.2' "$REPORTS/BLENDER_VERSION.txt"
"$GODOT" --version | tee "$REPORTS/GODOT_VERSION.txt"
grep -q '^4.3.stable.official.77dcf97d8' "$REPORTS/GODOT_VERSION.txt"
java -version 2>&1 | tee "$REPORTS/JAVA_VERSION.txt"
sdkmanager --version | tee "$REPORTS/ANDROID_SDKMANAGER_VERSION.txt"
adb version | tee "$REPORTS/ADB_VERSION.txt"
aapt version 2>&1 | tee "$REPORTS/AAPT_VERSION.txt"
apksigner version 2>&1 | tee "$REPORTS/APKSIGNER_VERSION.txt"
(zipalign -h 2>&1 || true) | head -20 | tee "$REPORTS/ZIPALIGN_VERSION.txt"

mark "Generate deterministic validation cube twice"
for run in a b; do
  "$BLENDER" --background --factory-startup --python tools/asset_lab/generate_validation_cube.py -- \
    --output-dir "$BUILD/cube-$run" --report "$REPORTS/CUBE_GENERATION_${run^^}.json"
done

mark "Require deterministic cube GLB bytes"
cmp "$BUILD/cube-a/bb_validation_cube_1m.glb" "$BUILD/cube-b/bb_validation_cube_1m.glb"
sha256sum "$BUILD/cube-a/bb_validation_cube_1m.blend" "$BUILD/cube-a/bb_validation_cube_1m.glb" | tee "$REPORTS/CUBE_SHA256SUMS.txt"
stat -c '%n %s' "$BUILD/cube-a/bb_validation_cube_1m.blend" "$BUILD/cube-a/bb_validation_cube_1m.glb" | tee "$REPORTS/CUBE_SIZES.txt"

mark "Install Khronos glTF Validator"
GLTF_VALIDATOR_ROOT="$BUILD/gltf-validator"
mkdir -p "$GLTF_VALIDATOR_ROOT"
npm install --prefix "$GLTF_VALIDATOR_ROOT" --ignore-scripts --no-audit --no-fund "gltf-validator@$GLTF_VALIDATOR_VERSION"
npm list --prefix "$GLTF_VALIDATOR_ROOT" --depth=0 | tee "$REPORTS/GLTF_VALIDATOR_VERSION.txt"
export GLTF_VALIDATOR_ROOT

mark "Run Khronos glTF Validator"
node tools/asset_lab/validate_gltf_khronos.js "$BUILD/cube-a/bb_validation_cube_1m.glb" "$REPORTS/CUBE_KHRONOS_GLTF_VALIDATION.json"

mark "Run independent cube contract validator"
python3 tools/asset_lab/validate_glb_asset.py "$BUILD/cube-a/bb_validation_cube_1m.glb" --expected-name bb_validation_cube_1m --expected-size 1.0 --report "$REPORTS/CUBE_INDEPENDENT_VALIDATION.json"

mark "Run production asset generators"
"$BLENDER" --background --factory-startup --python tools/asset_lab/generate_architecture_families.py -- --output-dir "$BUILD/generated/architecture" --seed 1405 --report "$REPORTS/ARCHITECTURE_GENERATION.json"
"$BLENDER" --background --factory-startup --python tools/asset_lab/generate_commercial_modules.py -- --output-dir "$BUILD/generated/commercial"
python3 - "$BUILD/generated/commercial" "$REPORTS/COMMERCIAL_GENERATION.json" <<'PY'
from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1]); outputs=[{'path':p.as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(root.glob('*.glb'))]
assert len(outputs)==4, outputs
Path(sys.argv[2]).write_text(json.dumps({'asset_records':4,'outputs':outputs},indent=2)+'\n')
PY
while IFS= read -r -d '' glb; do
  report="$REPORTS/generated-$(basename "$glb").json"
  node tools/asset_lab/validate_gltf_khronos.js "$glb" "$report"
done < <(find "$BUILD/generated" -name '*.glb' -type f -print0 | sort -z)

mark "Install generated assets into recovered game source"
cp -a assets/. "$GAME/assets/"
cp scripts/asset_lab_runtime.gd "$GAME/scripts/asset_lab_runtime.gd"
cp scenes/world.tscn "$GAME/scenes/world.tscn"
mkdir -p "$GAME/tests" "$GAME/assets/validation"
cp tests/test_asset_lab_runtime_integration.py "$GAME/tests/test_asset_lab_runtime_integration.py"
cp "$BUILD/cube-a/bb_validation_cube_1m.glb" "$GAME/assets/validation/"
cp -a "$BUILD/generated/architecture/balanced/traditional/." "$GAME/assets/environment/architecture/traditional/"
cp -a "$BUILD/generated/architecture/balanced/souq/." "$GAME/assets/environment/architecture/souq/"
cp -a "$BUILD/generated/architecture/balanced/waterfront/." "$GAME/assets/environment/architecture/waterfront/"

mark "Run clean Godot import"
rm -rf "$GAME/.godot"
"$GODOT" --headless --path "$GAME" --editor --import --quit --verbose 2>&1 | tee "$LOGS/godot-import.log"
! grep -Eiq 'SCRIPT ERROR|Parse Error|ERROR:.*(failed|missing|invalid)' "$LOGS/godot-import.log"

mark "Validate asset integration and wrapper scenes"
python3 tests/test_asset_lab_runtime_integration.py 2>&1 | tee "$LOGS/asset-runtime-integration.log"
grep -q 'node name="AssetLab"' "$GAME/scenes/world.tscn"
grep -q '"VillaDistrict"' "$GAME/scripts/asset_lab_runtime.gd"
compgen -G "$GAME/.godot/imported/bb_validation_cube_1m.glb-*.md5" >/dev/null

mark "Apply verified premium validation overlay"
python3 tools/apply_premium_overlay_resilient.py "$GAME" --report "$REPORTS/PREMIUM_WORLD_OVERLAY_REPORT.json"
python3 tools/apply_premium_validation_corrections.py "$GAME" --report "$REPORTS/RUNTIME_DEFECT_CORRECTIONS.json"

mark "Run gameplay regression suites"
bash tools/asset_lab/run_game_regressions.sh "$GODOT" "$GAME" "$LOGS" "$REPORTS"

mark "Protected-control post-check"
python3 tools/verify_frozen_controls.py "$GAME" --json-out "$REPORTS/FROZEN_CONTROLS_POST.json" --markdown-out "$REPORTS/FROZEN_CONTROLS_POST.md"
cmp "$REPORTS/FROZEN_CONTROLS_PRE.json" "$REPORTS/FROZEN_CONTROLS_POST.json"

mark "Export Android APK"
ANDROID_BUILD_TOOLS="$ANDROID_BUILD_TOOLS" VERSION_CODE="$VERSION_CODE" VERSION_NAME="$VERSION_NAME" \
  bash tools/asset_lab/export_asset_production_android.sh "$GODOT" "$GAME" "$ARTIFACTS/$APK_NAME" "$PACKAGE_NAME" "$REPORTS" "$LOGS"

mark "Validate Android APK"
test -s "$ARTIFACTS/$APK_NAME"
grep -q "package: name='$PACKAGE_NAME' versionCode='$VERSION_CODE' versionName='$VERSION_NAME'" "$REPORTS/APK_BADGING.txt"
test -s "$REPORTS/APK_SIGNING.txt"
