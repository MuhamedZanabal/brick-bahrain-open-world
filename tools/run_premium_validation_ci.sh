#!/usr/bin/env bash
set -euo pipefail
EXPECTED_SOURCE_SHA256="7be73dd8041a03f70699e446004128d3e53c131f0dc4cdc0cc05b8264c3538eb"
PART_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/premium_validation_v18_run_parts"
TMP="$(mktemp -t bahrain-brick-premium-validation-v18.XXXXXX.sh)"
trap 'rm -f "$TMP"' EXIT
for index in 00 01 02 03; do
  part="$PART_DIR/part_${index}.shfrag"
  test -s "$part" || { echo "validation runner fragment missing: $part" >&2; exit 1; }
  cat "$part" >> "$TMP"
done
ACTUAL_SOURCE_SHA256="$(sha256sum "$TMP" | awk '{print $1}')"
if [[ "$ACTUAL_SOURCE_SHA256" != "$EXPECTED_SOURCE_SHA256" ]]; then
  echo "validation runner SHA-256 mismatch: expected=$EXPECTED_SOURCE_SHA256 actual=$ACTUAL_SOURCE_SHA256" >&2
  exit 1
fi
bash -n "$TMP"
bash "$TMP" "$@"
