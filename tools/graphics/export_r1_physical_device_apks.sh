#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:?repository root is required}"
OUTPUT_ROOT="${2:?output root is required}"
RECONSTRUCTION="$OUTPUT_ROOT/reconstruction"
GAME="$RECONSTRUCTION/game"
GL_PROJECT="$OUTPUT_ROOT/gl-project"
MOBILE_PROJECT="$OUTPUT_ROOT/mobile-project"
GL_APK="$OUTPUT_ROOT/bahrain-brick-r1-physical-gl-arm64.apk"
MOBILE_APK="$OUTPUT_ROOT/bahrain-brick-r1-physical-mobile-arm64.apk"
GL_PACKAGE="com.brickbahrain.r1physical.gl"
MOBILE_PACKAGE="com.brickbahrain.r1physical.mobile"
GODOT_RELEASE="4.3-stable"
GODOT_ARCHIVE="Godot_v4.3-stable_linux.x86_64.zip"
TEMPLATE="Godot_v4.3-stable_export_templates.tpz"
ROOT_URL="https://github.com/godotengine/godot-builds/releases/download/$GODOT_RELEASE"
GODOT_DIR="$OUTPUT_ROOT/godot"
XDG_DATA_HOME="$OUTPUT_ROOT/godot-user-data"
TEMPLATE_DIR="$OUTPUT_ROOT/templates"
mkdir -p "$OUTPUT_ROOT" "$GODOT_DIR" "$XDG_DATA_HOME" "$TEMPLATE_DIR"

SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
APKSIGNER="$SDK_ROOT/build-tools/34.0.0/apksigner"
test -x "$APKSIGNER"

rm -rf "$RECONSTRUCTION"
PATCHED_RECONSTRUCTION="$OUTPUT_ROOT/reconstruct.r1.physical.sh"
python3 - "$REPO_ROOT/tools/vertical_slice/reconstruct_manama_souq_composite.sh" "$PATCHED_RECONSTRUCTION" <<'PY'
from pathlib import Path
import sys
source = Path(sys.argv[1])
target = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
old = 'test "${ImageVersion:-}" = "20260714.240.1"'
new = 'test -n "${ImageVersion:-}"'
if text.count(old) != 1:
    raise SystemExit("historical image assertion not found exactly once")
target.write_text(text.replace(old, new), encoding="utf-8")
target.chmod(0o755)
PY
bash "$PATCHED_RECONSTRUCTION" A "$RECONSTRUCTION" "$REPO_ROOT/authority/manama_souq_composite_source.json" "$(git -C "$REPO_ROOT" rev-parse HEAD)"
python3 "$REPO_ROOT/tools/graphics/patch_r1_reconstruction_preflight.py" \
  --manifest "$RECONSTRUCTION/evidence/FINAL_TREE_MANIFEST.json" \
  --game "$GAME" \
  --output "$OUTPUT_ROOT/SOURCE_TREE_EQUIVALENCE.json"

mkdir -p "$GAME/tests/graphics"
cp "$REPO_ROOT/tests/graphics/r1_renderer_runtime_debug.gd" "$GAME/tests/graphics/"
cp "$REPO_ROOT/tests/graphics/r1_renderer_runtime_debug.tscn" "$GAME/tests/graphics/"

curl --fail --location --retry 5 --retry-all-errors "$ROOT_URL/SHA512-SUMS.txt" -o "$TEMPLATE_DIR/SHA512-SUMS.txt"
curl --fail --location --retry 5 --retry-all-errors "$ROOT_URL/$GODOT_ARCHIVE" -o "$GODOT_DIR/$GODOT_ARCHIVE"
curl --fail --location --retry 5 --retry-all-errors "$ROOT_URL/$TEMPLATE" -o "$TEMPLATE_DIR/$TEMPLATE"
for asset in "$GODOT_ARCHIVE" "$TEMPLATE"; do
  file="$GODOT_DIR/$asset"
  [[ "$asset" == "$TEMPLATE" ]] && file="$TEMPLATE_DIR/$asset"
  expected="$(awk -v name="$asset" '$NF == name || $NF == "*" name {print $1; exit}' "$TEMPLATE_DIR/SHA512-SUMS.txt")"
  test -n "$expected"
  printf '%s  %s\n' "$expected" "$file" | sha512sum -c -
done
unzip -q "$GODOT_DIR/$GODOT_ARCHIVE" -d "$GODOT_DIR"
GODOT="$(find "$GODOT_DIR" -maxdepth 1 -type f -name 'Godot*' | head -1)"
test -n "$GODOT"
chmod +x "$GODOT"
"$GODOT" --version | tee "$OUTPUT_ROOT/GODOT_VERSION.txt"
grep -q '^4\.3\.' "$OUTPUT_ROOT/GODOT_VERSION.txt"
TEMPLATE_VERSION="$(sed -E 's/\.official.*$//' "$OUTPUT_ROOT/GODOT_VERSION.txt" | head -1)"
test -n "$TEMPLATE_VERSION"
unzip -q "$TEMPLATE_DIR/$TEMPLATE" -d "$TEMPLATE_DIR/unpacked"
mkdir -p "$XDG_DATA_HOME/godot/export_templates/$TEMPLATE_VERSION"
cp -a "$TEMPLATE_DIR/unpacked/templates/." "$XDG_DATA_HOME/godot/export_templates/$TEMPLATE_VERSION/"

rm -rf "$GAME/.godot" "$GL_PROJECT" "$MOBILE_PROJECT"
timeout --signal=TERM --kill-after=30s 1800s xvfb-run -a -s '-screen 0 1920x1080x24' \
  "$GODOT" --path "$GAME" --editor --import --quit --verbose \
  --rendering-method mobile --rendering-driver vulkan 2>&1 | tee "$OUTPUT_ROOT/import.log"
printf 'complete\n' > "$OUTPUT_ROOT/IMPORT_COMPLETE.txt"
cp -a "$GAME" "$GL_PROJECT"
cp -a "$GAME" "$MOBILE_PROJECT"

python3 - "$GL_PROJECT" gl_compatibility "$GL_PACKAGE" gl_production "$OUTPUT_ROOT/GL_VARIANT_OVERRIDE.json" <<'PY'
from pathlib import Path
import hashlib, json, sys
project_root = Path(sys.argv[1])
renderer, package_name, default_mode = sys.argv[2:5]
report_path = Path(sys.argv[5])
project = project_root / "project.godot"
preset = project_root / "export_presets.cfg"
script = project_root / "tests/graphics/r1_renderer_runtime_debug.gd"
before = {"project": project.read_bytes(), "preset": preset.read_bytes(), "script": script.read_bytes()}
project_text = before["project"].decode()
preset_text = before["preset"].decode()
script_text = before["script"].decode()
def replace_line(text: str, prefix: str, replacement: str) -> str:
    lines = text.splitlines()
    matches = [i for i, line in enumerate(lines) if line.startswith(prefix)]
    if len(matches) != 1:
        raise SystemExit(f"expected one {prefix!r} line, found {len(matches)}")
    lines[matches[0]] = replacement
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")
project_text = replace_line(project_text, "run/main_scene=", 'run/main_scene="res://tests/graphics/r1_renderer_runtime_debug.tscn"')
project_text = replace_line(project_text, "renderer/rendering_method=", f'renderer/rendering_method="{renderer}"')
project_text = replace_line(project_text, "renderer/rendering_method.mobile=", f'renderer/rendering_method.mobile="{renderer}"')
preset_text = replace_line(preset_text, "architectures/armeabi-v7a=", "architectures/armeabi-v7a=false")
preset_text = replace_line(preset_text, "architectures/arm64-v8a=", "architectures/arm64-v8a=true")
preset_text = replace_line(preset_text, "architectures/x86_64=", "architectures/x86_64=false")
preset_text = replace_line(preset_text, "package/unique_name=", f'package/unique_name="{package_name}"')
needle = '\t\treturn "mobile_baseline"'
if script_text.count(needle) != 2:
    raise SystemExit("default-mode returns not found exactly twice")
script_text = script_text.replace(needle, f'\t\treturn "{default_mode}"')
project.write_text(project_text, encoding="utf-8")
preset.write_text(preset_text, encoding="utf-8")
script.write_text(script_text, encoding="utf-8")
def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
report = {
    "schema_version": 1,
    "renderer": renderer,
    "package_name": package_name,
    "default_mode": default_mode,
    "architecture": "arm64-v8a",
    "qa_override_only": True,
    "project_before_sha256": digest(before["project"]),
    "project_after_sha256": digest(project.read_bytes()),
    "preset_before_sha256": digest(before["preset"]),
    "preset_after_sha256": digest(preset.read_bytes()),
    "script_before_sha256": digest(before["script"]),
    "script_after_sha256": digest(script.read_bytes()),
}
report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

python3 - "$MOBILE_PROJECT" mobile "$MOBILE_PACKAGE" mobile_baseline "$OUTPUT_ROOT/MOBILE_VARIANT_OVERRIDE.json" <<'PY'
from pathlib import Path
import hashlib, json, sys
project_root = Path(sys.argv[1])
renderer, package_name, default_mode = sys.argv[2:5]
report_path = Path(sys.argv[5])
project = project_root / "project.godot"
preset = project_root / "export_presets.cfg"
script = project_root / "tests/graphics/r1_renderer_runtime_debug.gd"
before = {"project": project.read_bytes(), "preset": preset.read_bytes(), "script": script.read_bytes()}
project_text = before["project"].decode()
preset_text = before["preset"].decode()
script_text = before["script"].decode()
def replace_line(text: str, prefix: str, replacement: str) -> str:
    lines = text.splitlines()
    matches = [i for i, line in enumerate(lines) if line.startswith(prefix)]
    if len(matches) != 1:
        raise SystemExit(f"expected one {prefix!r} line, found {len(matches)}")
    lines[matches[0]] = replacement
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")
project_text = replace_line(project_text, "run/main_scene=", 'run/main_scene="res://tests/graphics/r1_renderer_runtime_debug.tscn"')
project_text = replace_line(project_text, "renderer/rendering_method=", f'renderer/rendering_method="{renderer}"')
project_text = replace_line(project_text, "renderer/rendering_method.mobile=", f'renderer/rendering_method.mobile="{renderer}"')
preset_text = replace_line(preset_text, "architectures/armeabi-v7a=", "architectures/armeabi-v7a=false")
preset_text = replace_line(preset_text, "architectures/arm64-v8a=", "architectures/arm64-v8a=true")
preset_text = replace_line(preset_text, "architectures/x86_64=", "architectures/x86_64=false")
preset_text = replace_line(preset_text, "package/unique_name=", f'package/unique_name="{package_name}"')
needle = '\t\treturn "mobile_baseline"'
if script_text.count(needle) != 2:
    raise SystemExit("default-mode returns not found exactly twice")
script_text = script_text.replace(needle, f'\t\treturn "{default_mode}"')
project.write_text(project_text, encoding="utf-8")
preset.write_text(preset_text, encoding="utf-8")
script.write_text(script_text, encoding="utf-8")
def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
report = {
    "schema_version": 1,
    "renderer": renderer,
    "package_name": package_name,
    "default_mode": default_mode,
    "architecture": "arm64-v8a",
    "qa_override_only": True,
    "project_before_sha256": digest(before["project"]),
    "project_after_sha256": digest(project.read_bytes()),
    "preset_before_sha256": digest(before["preset"]),
    "preset_after_sha256": digest(preset.read_bytes()),
    "script_before_sha256": digest(before["script"]),
    "script_after_sha256": digest(script.read_bytes()),
}
report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

export XDG_DATA_HOME
export GODOT_ANDROID_KEYSTORE_DEBUG_PATH="$REPO_ROOT/debug.keystore"
export GODOT_ANDROID_KEYSTORE_DEBUG_USER=androiddebugkey
export GODOT_ANDROID_KEYSTORE_DEBUG_PASSWORD=android
timeout --signal=TERM --kill-after=30s 1800s "$GODOT" --headless --path "$GL_PROJECT" --verbose --export-debug Android "$GL_APK" 2>&1 | tee "$OUTPUT_ROOT/export-gl.log"
timeout --signal=TERM --kill-after=30s 1800s "$GODOT" --headless --path "$MOBILE_PROJECT" --verbose --export-debug Android "$MOBILE_APK" 2>&1 | tee "$OUTPUT_ROOT/export-mobile.log"

: > "$OUTPUT_ROOT/apk-signing.txt"
for apk in "$GL_APK" "$MOBILE_APK"; do
  test -s "$apk"
  "$APKSIGNER" verify --verbose --print-certs "$apk" >> "$OUTPUT_ROOT/apk-signing.txt"
done
sha256sum "$GL_APK" "$MOBILE_APK" > "$OUTPUT_ROOT/APK_SHA256SUMS.txt"
python3 - "$OUTPUT_ROOT" "$GL_APK" "$MOBILE_APK" <<'PY'
from pathlib import Path
import hashlib, json, sys
root = Path(sys.argv[1])
gl = Path(sys.argv[2])
mobile = Path(sys.argv[3])
def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
manifest = {
    "schema_version": 1,
    "purpose": "R1 named physical-device renderer qualification handoff",
    "engine": (root / "GODOT_VERSION.txt").read_text().strip(),
    "architecture": "arm64-v8a",
    "renderer_defaults_modified": False,
    "production_fix_authorized": False,
    "apks": [
        {"renderer": "gl_compatibility", "default_mode": "gl_production", "package": "com.brickbahrain.r1physical.gl", "filename": gl.name, "size_bytes": gl.stat().st_size, "sha256": sha(gl)},
        {"renderer": "mobile", "default_mode": "mobile_baseline", "package": "com.brickbahrain.r1physical.mobile", "filename": mobile.name, "size_bytes": mobile.stat().st_size, "sha256": sha(mobile)},
    ],
}
(root / "R1_PHYSICAL_DEVICE_APK_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
PY
