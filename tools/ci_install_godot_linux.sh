#!/usr/bin/env bash
set -euo pipefail

mkdir -p build/ci_logs
exec > >(tee build/ci_logs/godot-toolchain-install.log) 2>&1
set -x

GODOT_VERSION="${GODOT_VERSION:-4.3}"
GODOT_RELEASE="${GODOT_RELEASE:-${GODOT_VERSION}-stable}"
INSTALL_ROOT="${GODOT_INSTALL_ROOT:-$HOME/.local/share/godot-ci}"
BIN_DIR="$INSTALL_ROOT/bin"
TEMPLATE_DIR="$HOME/.local/share/godot/export_templates/${GODOT_VERSION}.stable"
CACHE_DIR="${RUNNER_TEMP:-/tmp}/godot-${GODOT_VERSION}"
EDITOR_ZIP="$CACHE_DIR/Godot_v${GODOT_RELEASE}_linux.x86_64.zip"
TEMPLATE_TPZ="$CACHE_DIR/Godot_v${GODOT_RELEASE}_export_templates.tpz"
EDITOR_URL="https://github.com/godotengine/godot-builds/releases/download/${GODOT_RELEASE}/Godot_v${GODOT_RELEASE}_linux.x86_64.zip"
TEMPLATE_URL="https://github.com/godotengine/godot-builds/releases/download/${GODOT_RELEASE}/Godot_v${GODOT_RELEASE}_export_templates.tpz"

mkdir -p "$BIN_DIR" "$TEMPLATE_DIR" "$HOME/.local/bin" "$CACHE_DIR"

curl --fail --location --retry 8 --retry-all-errors --connect-timeout 30 "$EDITOR_URL" --output "$EDITOR_ZIP"
ls -lh "$EDITOR_ZIP"
unzip -t "$EDITOR_ZIP"
unzip -o -q "$EDITOR_ZIP" -d "$BIN_DIR"
GODOT_SOURCE="$(find "$BIN_DIR" -maxdepth 1 -type f -name 'Godot_v*_linux.x86_64' -print -quit)"
if [[ -z "$GODOT_SOURCE" ]]; then
  echo "Godot executable not found after extracting $EDITOR_ZIP" >&2
  find "$BIN_DIR" -maxdepth 2 -type f -print >&2
  exit 1
fi
chmod +x "$GODOT_SOURCE"
ln -sfn "$GODOT_SOURCE" "$HOME/.local/bin/godot"

curl --fail --location --retry 8 --retry-all-errors --connect-timeout 30 "$TEMPLATE_URL" --output "$TEMPLATE_TPZ"
ls -lh "$TEMPLATE_TPZ"
unzip -t "$TEMPLATE_TPZ"
TMP_TEMPLATES="$(mktemp -d)"
trap 'rm -rf "$TMP_TEMPLATES"' EXIT
unzip -o -q "$TEMPLATE_TPZ" -d "$TMP_TEMPLATES"
if [[ ! -d "$TMP_TEMPLATES/templates" ]]; then
  echo "Godot template archive did not contain templates/" >&2
  find "$TMP_TEMPLATES" -maxdepth 3 -type f -print >&2
  exit 1
fi
cp -a "$TMP_TEMPLATES/templates/." "$TEMPLATE_DIR/"

export PATH="$HOME/.local/bin:$PATH"
godot --version
for required in android_debug.apk android_release.apk; do
  test -s "$TEMPLATE_DIR/$required" || { echo "Missing export template: $TEMPLATE_DIR/$required" >&2; find "$TEMPLATE_DIR" -maxdepth 1 -type f -printf '%f\n' >&2; exit 1; }
done
