#!/usr/bin/env bash
set -euo pipefail

readonly ARTIFACT_ID="8295853465"
readonly APK_NAME="bahrain_brick_v14.0.4-premium-visual-qa.apk"
readonly APK_SHA256="7e32e81f005f300fca115e39f2962c9cac3c9835d34ac15d4bece2f86655bf65"
readonly TAG_NAME="v14.0.4-premium-visual-qa"
readonly VALIDATION_SHA="83dd98013e75785c0101fa9501c461fc807cc342"
readonly PREMIUM_SHA="e26ec912db5c10d071a8e120010bdb5a9a136f17"
readonly RELEASE_URL="https://github.com/${GITHUB_REPOSITORY}/releases/tag/${TAG_NAME}"
readonly APK_URL="https://github.com/${GITHUB_REPOSITORY}/releases/download/${TAG_NAME}/${APK_NAME}"

: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${GITHUB_RUN_ID:?GITHUB_RUN_ID is required}"

rm -rf qa-release-work
mkdir -p qa-release-work/artifact qa-release-work/assets qa-release-work/remote
cd qa-release-work

curl --fail-with-body --location --retry 3 \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${GH_TOKEN}" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/artifacts/${ARTIFACT_ID}/zip" \
  --output artifact.zip
unzip -q artifact.zip -d artifact

mapfile -d '' apk_matches < <(find artifact -type f -name "${APK_NAME}" -print0)
if [ "${#apk_matches[@]}" -ne 1 ]; then
  echo "Expected exactly one ${APK_NAME}; found ${#apk_matches[@]}." >&2
  find artifact -maxdepth 5 -type f -print >&2
  exit 1
fi
cp -- "${apk_matches[0]}" "assets/${APK_NAME}"

actual_sha="$(sha256sum "assets/${APK_NAME}" | awk '{print $1}')"
if [ "${actual_sha}" != "${APK_SHA256}" ]; then
  echo "Artifact APK SHA-256 mismatch: expected ${APK_SHA256}, got ${actual_sha}." >&2
  exit 1
fi
printf '%s  %s\n' "${APK_SHA256}" "${APK_NAME}" > assets/APK_SHA256.txt
metadata="$(find artifact -type f -path '*/reports/APK_METADATA_REPORT.json' -print -quit)"
if [ -n "${metadata}" ]; then
  cp "${metadata}" assets/APK_METADATA_REPORT.json
fi

cat > release-notes.md <<'EOF'
# Bahrain Brick v14.0.4 Premium Visual QA

**Classification:** WORLD UPGRADE COMPLETE — PHYSICAL DEVICE TEST PENDING

This is a public **QA pre-release** solely for physical Android testing. It is not a production release and is not production-signed.

## Frozen authority

- Premium authority: `e26ec912db5c10d071a8e120010bdb5a9a136f17`
- Validation head: `83dd98013e75785c0101fa9501c461fc807cc342`
- Successful workflow: `29292680122`
- Successful job: `86959477146`
- APK: `bahrain_brick_v14.0.4-premium-visual-qa.apk`
- APK SHA-256: `7e32e81f005f300fca115e39f2962c9cac3c9835d34ac15d4bece2f86655bf65`

## Mandatory test rule

Verify the downloaded APK SHA-256 before installation. A physical-device result is invalid if the hash differs.

## Release boundaries

- Ephemeral QA certificate
- Debug/QA build
- Physical-device validation pending
- PR #55 remains unmerged
- No production signing authorization
- No production-release authorization
EOF

if gh release view "${TAG_NAME}" --repo "${GITHUB_REPOSITORY}" >/dev/null 2>&1; then
  echo "Release ${TAG_NAME} already exists; verifying without replacing or mutating it."
else
  gh release create "${TAG_NAME}" \
    --repo "${GITHUB_REPOSITORY}" \
    --target "${VALIDATION_SHA}" \
    --title "Bahrain Brick v14.0.4 Premium Visual QA — Physical Test Candidate" \
    --notes-file release-notes.md \
    --prerelease \
    assets/*
fi

gh release view "${TAG_NAME}" --repo "${GITHUB_REPOSITORY}" --json isPrerelease,isDraft,tagName,url,assets > release.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path('release.json').read_text())
assert data['tagName'] == 'v14.0.4-premium-visual-qa', data
assert data['isPrerelease'] is True, data
assert data['isDraft'] is False, data
names = {asset['name'] for asset in data.get('assets', [])}
assert 'bahrain_brick_v14.0.4-premium-visual-qa.apk' in names, names
assert 'APK_SHA256.txt' in names, names
PY

gh release download "${TAG_NAME}" \
  --repo "${GITHUB_REPOSITORY}" \
  --pattern "${APK_NAME}" \
  --pattern "APK_SHA256.txt" \
  --dir remote

remote_sha="$(sha256sum "remote/${APK_NAME}" | awk '{print $1}')"
if [ "${remote_sha}" != "${APK_SHA256}" ]; then
  echo "Published APK SHA-256 mismatch: expected ${APK_SHA256}, got ${remote_sha}." >&2
  exit 1
fi
grep -Fqx "${APK_SHA256}  ${APK_NAME}" remote/APK_SHA256.txt

marker='<!-- bahrain-brick-v14.0.4-qa-release -->'
run_url="https://github.com/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"
cat > comment.md <<EOF
${marker}
## Verified public QA pre-release

- Release: ${RELEASE_URL}
- Direct APK: ${APK_URL}
- APK SHA-256: \`${APK_SHA256}\`
- Tag: \`${TAG_NAME}\`
- Target validation head: \`${VALIDATION_SHA}\`
- Premium authority: \`${PREMIUM_SHA}\`
- Verification workflow: ${run_url}
- Public release asset re-downloaded and SHA-256 verified: **PASS**

This remains a QA physical-test candidate. PR #55 is unmerged; production signing and production publication remain unauthorized.
EOF

comment_id="$(gh api --paginate "/repos/${GITHUB_REPOSITORY}/issues/55/comments" --jq ".[] | select(.body | contains(\"${marker}\")) | .id" | head -n 1)"
jq -n --rawfile body comment.md '{body: $body}' > comment.json
if [ -n "${comment_id}" ]; then
  gh api --method PATCH "/repos/${GITHUB_REPOSITORY}/issues/comments/${comment_id}" --input comment.json >/dev/null
else
  gh api --method POST "/repos/${GITHUB_REPOSITORY}/issues/55/comments" --input comment.json >/dev/null
fi

printf 'RELEASE_URL=%s\nAPK_URL=%s\nAPK_SHA256=%s\n' "${RELEASE_URL}" "${APK_URL}" "${APK_SHA256}"
