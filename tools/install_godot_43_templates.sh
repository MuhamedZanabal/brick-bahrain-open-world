#!/usr/bin/env bash
set -euo pipefail

REPORT_PATH="${1:-recovery/v14/build/reports/GODOT_EXPORT_TEMPLATE_REPORT.json}"
PROJECT_ROOT="${2:-recovery/v14}"
mkdir -p "$(dirname "$REPORT_PATH")" "$PROJECT_ROOT/build/logs"

GODOT_BIN="$(command -v godot || true)"
if [[ -z "$GODOT_BIN" || ! -x "$GODOT_BIN" ]]; then
  echo "godot executable not found on PATH" >&2
  exit 1
fi
GODOT_BIN="$(readlink -f "$GODOT_BIN")"
GODOT_VERSION="$($GODOT_BIN --version | head -n1 | tr -d '\r')"
printf 'Godot executable: %s\n' "$GODOT_BIN"
printf 'Godot version: %s\n' "$GODOT_VERSION"

TEMPLATE_VERSION="$(python3 - "$GODOT_VERSION" <<'PY'
import re,sys
version=sys.argv[1].strip()
match=re.search(r'(?<!\d)(\d+\.\d+\.(?:stable|beta\d*|rc\d*|dev\d*))',version)
if not match:
    raise SystemExit(f'cannot derive export-template directory from Godot version: {version!r}')
print(match.group(1))
PY
)"
if [[ "$TEMPLATE_VERSION" != "4.3.stable" ]]; then
  echo "refusing mismatched templates: Godot requires $TEMPLATE_VERSION, expected 4.3.stable" >&2
  exit 1
fi

DEST_DIR="$HOME/.local/share/godot/export_templates/$TEMPLATE_VERSION"
mkdir -p "$DEST_DIR"
FOUND_SOURCE=""
for candidate in \
  "$DEST_DIR" \
  "/root/.local/share/godot/export_templates/$TEMPLATE_VERSION" \
  "/usr/local/share/godot/export_templates/$TEMPLATE_VERSION" \
  "/usr/share/godot/export_templates/$TEMPLATE_VERSION" \
  "/opt/godot/.local/share/godot/export_templates/$TEMPLATE_VERSION"; do
  if [[ -s "$candidate/android_debug.apk" && -s "$candidate/android_release.apk" ]]; then
    FOUND_SOURCE="$candidate"
    break
  fi
done

DOWNLOAD_URL=""
CHECKSUM_SOURCE=""
VERIFIED_DIGEST=""
ARCHIVE_PATH=""
if [[ -n "$FOUND_SOURCE" ]]; then
  echo "Found matching installed templates at: $FOUND_SOURCE"
  if [[ "$(readlink -f "$FOUND_SOURCE")" != "$(readlink -f "$DEST_DIR")" ]]; then
    cp -a "$FOUND_SOURCE/." "$DEST_DIR/"
  fi
else
  RELEASE_TAG="4.3-stable"
  RELEASE_API="https://api.github.com/repos/godotengine/godot-builds/releases/tags/$RELEASE_TAG"
  ASSET_NAME="Godot_v4.3-stable_export_templates.tpz"
  WORK_DIR="${RUNNER_TEMP:-/tmp}/godot-4.3-export-templates"
  rm -rf "$WORK_DIR"
  mkdir -p "$WORK_DIR"
  RELEASE_JSON="$WORK_DIR/release.json"
  ARCHIVE_PATH="$WORK_DIR/$ASSET_NAME"
  CHECKSUM_PATH="$WORK_DIR/checksums.txt"

  curl -fL --retry 4 --retry-delay 3 --connect-timeout 30 \
    -H 'Accept: application/vnd.github+json' \
    -H 'X-GitHub-Api-Version: 2022-11-28' \
    "$RELEASE_API" -o "$RELEASE_JSON"

  readarray -t RELEASE_INFO < <(python3 - "$RELEASE_JSON" "$RELEASE_TAG" "$ASSET_NAME" <<'PY'
import json,sys
path,expected_tag,asset_name=sys.argv[1:]
data=json.load(open(path,encoding='utf-8'))
if data.get('tag_name') != expected_tag:
    raise SystemExit(f"release tag mismatch: {data.get('tag_name')!r}")
assets={item.get('name'):item for item in data.get('assets',[])}
asset=assets.get(asset_name)
if not asset:
    raise SystemExit(f'official release asset missing: {asset_name}')
url=asset.get('browser_download_url','')
prefix=f'https://github.com/godotengine/godot-builds/releases/download/{expected_tag}/'
if not url.startswith(prefix):
    raise SystemExit(f'unexpected template asset URL: {url}')
checksum=None
for name in ('SHA512-SUMS.txt','SHA256-SUMS.txt'):
    if name in assets:
        checksum=assets[name]
        break
checksum_url=checksum.get('browser_download_url','') if checksum else ''
digest=asset.get('digest') or ''
print(url)
print(checksum_url)
print(digest)
PY
  )
  DOWNLOAD_URL="${RELEASE_INFO[0]}"
  CHECKSUM_URL="${RELEASE_INFO[1]}"
  API_DIGEST="${RELEASE_INFO[2]}"

  curl -fL --retry 4 --retry-delay 3 --connect-timeout 30 "$DOWNLOAD_URL" -o "$ARCHIVE_PATH"
  [[ -s "$ARCHIVE_PATH" ]] || { echo "template archive is empty" >&2; exit 1; }
  [[ "$(stat -c '%s' "$ARCHIVE_PATH")" -gt 1000000 ]] || { echo "template archive is unexpectedly small" >&2; exit 1; }
  python3 - "$ARCHIVE_PATH" <<'PY'
from pathlib import Path
import sys
path=Path(sys.argv[1])
magic=path.read_bytes()[:4]
if magic != b'PK\x03\x04':
    preview=path.read_bytes()[:200].decode('utf-8','replace')
    raise SystemExit(f'official template download is not a ZIP/TPZ archive; first bytes={magic!r}; preview={preview!r}')
PY
  unzip -t "$ARCHIVE_PATH" > "$PROJECT_ROOT/build/logs/godot-template-archive-integrity.txt"

  if [[ -n "$CHECKSUM_URL" ]]; then
    curl -fL --retry 4 --retry-delay 3 --connect-timeout 30 "$CHECKSUM_URL" -o "$CHECKSUM_PATH"
    [[ -s "$CHECKSUM_PATH" ]] || { echo "official checksum file is empty" >&2; exit 1; }
    VERIFIED_DIGEST="$(python3 - "$CHECKSUM_PATH" "$ASSET_NAME" "$ARCHIVE_PATH" <<'PY'
import hashlib,re,sys
checksum_path,name,archive_path=sys.argv[1:]
text=open(checksum_path,encoding='utf-8',errors='strict').read()
match=None
for line in text.splitlines():
    fields=line.strip().split()
    if len(fields)>=2 and fields[-1].lstrip('*')==name:
        match=fields[0].lower(); break
if not match:
    raise SystemExit(f'official checksum entry missing for {name}')
algorithm={64:'sha256',128:'sha512'}.get(len(match))
if not algorithm or not re.fullmatch(r'[0-9a-f]+',match):
    raise SystemExit(f'unsupported official checksum format: {match!r}')
h=hashlib.new(algorithm)
with open(archive_path,'rb') as f:
    for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
actual=h.hexdigest()
if actual != match:
    raise SystemExit(f'official {algorithm} mismatch: expected {match}, got {actual}')
print(f'{algorithm}:{actual}')
PY
    )"
    CHECKSUM_SOURCE="$CHECKSUM_URL"
  elif [[ "$API_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]]; then
    ACTUAL_SHA256="$(sha256sum "$ARCHIVE_PATH" | awk '{print $1}')"
    [[ "sha256:$ACTUAL_SHA256" == "$API_DIGEST" ]] || { echo "GitHub release asset digest mismatch" >&2; exit 1; }
    VERIFIED_DIGEST="$API_DIGEST"
    CHECKSUM_SOURCE="$RELEASE_API asset.digest"
  else
    echo "official release exposes neither checksum asset nor usable asset digest" >&2
    exit 1
  fi

  STAGING="$WORK_DIR/extracted"
  mkdir -p "$STAGING"
  unzip -q "$ARCHIVE_PATH" -d "$STAGING"
  SOURCE_TEMPLATES="$STAGING/templates"
  [[ -d "$SOURCE_TEMPLATES" ]] || { echo "TPZ archive lacks top-level templates directory" >&2; exit 1; }
  [[ -s "$SOURCE_TEMPLATES/android_debug.apk" ]] || { echo "archive android_debug.apk missing/empty" >&2; exit 1; }
  [[ -s "$SOURCE_TEMPLATES/android_release.apk" ]] || { echo "archive android_release.apk missing/empty" >&2; exit 1; }
  rm -rf "$DEST_DIR"
  mkdir -p "$DEST_DIR"
  cp -a "$SOURCE_TEMPLATES/." "$DEST_DIR/"
fi

DEBUG_TEMPLATE="$DEST_DIR/android_debug.apk"
RELEASE_TEMPLATE="$DEST_DIR/android_release.apk"
[[ -s "$DEBUG_TEMPLATE" ]] || { echo "matching Android debug template unavailable: $DEBUG_TEMPLATE" >&2; exit 1; }
[[ -s "$RELEASE_TEMPLATE" ]] || { echo "matching Android release template unavailable: $RELEASE_TEMPLATE" >&2; exit 1; }
unzip -t "$DEBUG_TEMPLATE" > "$PROJECT_ROOT/build/logs/android-debug-template-integrity.txt"
unzip -t "$RELEASE_TEMPLATE" > "$PROJECT_ROOT/build/logs/android-release-template-integrity.txt"
printf 'Resolved debug template: %s (%s bytes)\n' "$DEBUG_TEMPLATE" "$(stat -c '%s' "$DEBUG_TEMPLATE")"
printf 'Resolved release template: %s (%s bytes)\n' "$RELEASE_TEMPLATE" "$(stat -c '%s' "$RELEASE_TEMPLATE")"

python3 - "$REPORT_PATH" "$GODOT_BIN" "$GODOT_VERSION" "$TEMPLATE_VERSION" "$DEST_DIR" "$DEBUG_TEMPLATE" "$RELEASE_TEMPLATE" "$DOWNLOAD_URL" "$CHECKSUM_SOURCE" "$VERIFIED_DIGEST" <<'PY'
import hashlib,json,sys
from pathlib import Path
(report,godot_bin,godot_version,template_version,dest,debug,release,url,checksum_source,verified_digest)=sys.argv[1:]
def item(path):
    p=Path(path); h=hashlib.sha256(p.read_bytes()).hexdigest()
    return {'path':str(p),'size_bytes':p.stat().st_size,'sha256':h}
data={
 'conclusion':'pass',
 'godot_executable':godot_bin,
 'godot_version':godot_version,
 'template_version':template_version,
 'resolved_template_directory':dest,
 'official_download_url':url or None,
 'integrity_source':checksum_source or 'preinstalled matching templates; APK ZIP integrity independently verified',
 'verified_archive_digest':verified_digest or None,
 'android_debug':item(debug),
 'android_release':item(release),
}
Path(report).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print(json.dumps(data,indent=2))
PY
