#!/usr/bin/env bash
set -euo pipefail
GODOT_VERSION="${GODOT_VERSION:-4.3}"
GODOT_RELEASE="${GODOT_RELEASE:-4.3-stable}"
INSTALL_ROOT="${GODOT_INSTALL_ROOT:-$HOME/.local/share/godot-ci}"
BIN_DIR="$INSTALL_ROOT/bin"
TEMPLATE_DIR="$HOME/.local/share/godot/export_templates/${GODOT_VERSION}.stable"
mkdir -p "$BIN_DIR" "$TEMPLATE_DIR" "$HOME/.local/bin"
EDITOR_ZIP="${RUNNER_TEMP:-/tmp}/Godot_v${GODOT_RELEASE}_linux.x86_64.zip"
TEMPLATE_TPZ="${RUNNER_TEMP:-/tmp}/Godot_v${GODOT_RELEASE}_export_templates.tpz"
curl --fail --location --retry 5 --retry-delay 2 "https://github.com/godotengine/godot/releases/download/${GODOT_RELEASE}/Godot_v${GODOT_RELEASE}_linux.x86_64.zip" --output "$EDITOR_ZIP"
unzip -o -q "$EDITOR_ZIP" -d "$BIN_DIR"
GODOT_SOURCE="$(find "$BIN_DIR" -maxdepth 1 -type f -name 'Godot_v*_linux.x86_64' -print -quit)"
[[ -n "$GODOT_SOURCE" ]]
chmod +x "$GODOT_SOURCE"
ln -sf "$GODOT_SOURCE" "$HOME/.local/bin/godot"
curl --fail --location --retry 5 --retry-delay 2 "https://github.com/godotengine/godot/releases/download/${GODOT_RELEASE}/Godot_v${GODOT_RELEASE}_export_templates.tpz" --output "$TEMPLATE_TPZ"
TMP_TEMPLATES="$(mktemp -d)"
unzip -o -q "$TEMPLATE_TPZ" -d "$TMP_TEMPLATES"
cp -a "$TMP_TEMPLATES/templates/." "$TEMPLATE_DIR/"
rm -rf "$TMP_TEMPLATES"
export PATH="$HOME/.local/bin:$PATH"
godot --version
[[ -f "$TEMPLATE_DIR/android_debug.apk" ]]
[[ -f "$TEMPLATE_DIR/android_release.apk" ]]
