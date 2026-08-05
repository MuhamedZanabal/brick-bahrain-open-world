#!/usr/bin/env bash
set -Eeuo pipefail
exec "$(dirname "$0")/apk-gameplay-probe.sh" "$@"
