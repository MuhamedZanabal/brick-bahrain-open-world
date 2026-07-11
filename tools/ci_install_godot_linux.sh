#!/usr/bin/env bash
set -euo pipefail

GODOT_VERSION="${GODOT_VERSION:-4.3}"
INSTALL_ROOT="${GODOT_INSTALL_ROOT:-$HOME/.local/share/godot-ci}"
BIN_DIR="$INSTALL_ROOT/bin"
TEMPLATE_DIR="$HOME/.local/share/godot/export_templates/${GODOT_VERSION}.stable"
CACHE_DIR="${RUNNER_TEMP:-/tmp}/godot-${GODOT_VERSION}"
EDITOR_ZIP="$CACHE_DIR/godot-linux.zip"
TEMPLATE_TPZ="$CACHE_DIR/export-templates.tpz"
EDITOR_URL="https://downloads.godotengine.org/?flavor=stable&platform=linux.64&slug=linux.x86_64.zip&version=${GODOT_VERSION}"
TEMPLATE_URL="https://downloads.godotengine.org/?flavor=stable&platform=templates&slug=export_templates.tpz&version=${GODOT_VERSION}"

mkdir -p "$BIN_DIR" "$TEMPLATE_DIR" "$HOME/.local/bin" "$CACHE_DIR"

curl --fail --location --retry 8 --retry-all-errors --connect-timeout 30 "$EDITOR_URL" --output "$EDITOR_ZIP"
unzip -t "$EDITOR_ZIP" >/dev/null
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
unzip -t "$TEMPLATE_TPZ" >/dev/null
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
  test -s "$TEMPLATE_DIR/$required" || { echo "Missing export template: $TEMPLATE_DIR/$required" >&2; exit 1; }
done
