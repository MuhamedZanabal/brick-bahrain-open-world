#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_ID="${1:?Actions artifact ID is required}"
RELEASE_TAG="${2:?existing release tag is required}"
EXPECTED_SHA256="${3:?expected SHA-256 is required}"
EXPECTED_BYTES="${4:?expected byte size is required}"
ASSET_NAME="${5:?release asset name is required}"
REPORT_PATH="${6:?report path is required}"

: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${GH_TOKEN:?GH_TOKEN is required}"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
SOURCE="$WORK/$ASSET_NAME"
DOWNLOADED="$WORK/downloaded/$ASSET_NAME"
mkdir -p "$(dirname "$DOWNLOADED")" "$(dirname "$REPORT_PATH")"

verify_exact() {
  local path="$1"
  local label="$2"
  test -f "$path" || { echo "$label missing: $path" >&2; exit 1; }
  local actual_bytes actual_sha256
  actual_bytes="$(stat -c '%s' "$path")"
  actual_sha256="$(sha256sum "$path" | awk '{print $1}')"
  test "$actual_bytes" = "$EXPECTED_BYTES" || {
    echo "$label byte-size mismatch: expected=$EXPECTED_BYTES actual=$actual_bytes" >&2
    exit 1
  }
  test "$actual_sha256" = "$EXPECTED_SHA256" || {
    echo "$label checksum mismatch: expected=$EXPECTED_SHA256 actual=$actual_sha256" >&2
    exit 1
  }
}

gh release view "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" >/dev/null

if gh release download "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --pattern "$ASSET_NAME" --dir "$(dirname "$DOWNLOADED")"; then
  verify_exact "$DOWNLOADED" "existing release authority"
  promotion_state="already_present_exact"
else
  rm -f "$DOWNLOADED"
  gh api "repos/${GITHUB_REPOSITORY}/actions/artifacts/${ARTIFACT_ID}/zip" > "$SOURCE"
  verify_exact "$SOURCE" "Actions artifact authority"
  gh release upload "$RELEASE_TAG" "$SOURCE" --repo "$GITHUB_REPOSITORY"
  gh release download "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --pattern "$ASSET_NAME" --dir "$(dirname "$DOWNLOADED")"
  verify_exact "$DOWNLOADED" "promoted release authority"
  promotion_state="uploaded_exact"
fi

python3 - "$REPORT_PATH" "$ARTIFACT_ID" "$RELEASE_TAG" "$ASSET_NAME" "$EXPECTED_BYTES" "$EXPECTED_SHA256" "$promotion_state" <<'PY'
from pathlib import Path
import json,sys
report,artifact_id,tag,name,size,digest,state=sys.argv[1:]
repository=__import__('os').environ['GITHUB_REPOSITORY']
value={
    'schema_version':1,
    'passed':True,
    'promotion_state':state,
    'originating_actions_artifact_id':int(artifact_id),
    'release_tag':tag,
    'release_asset_name':name,
    'immutable_locator':f'https://github.com/{repository}/releases/download/{tag}/{name}',
    'bytes':int(size),
    'sha256':digest,
    'provenance_commit':'ba31e620bdcbc2e8def98e2b888362620c26c4db',
    'extraction_destination':'build/manama-souq-source/source',
}
Path(report).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(value,indent=2,sort_keys=True))
PY
