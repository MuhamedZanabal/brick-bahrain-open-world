#!/usr/bin/env python3
"""Materialize the emulator validator with exact wall-clock traversal/soak gates.

This is fail-closed for the reviewed legacy source shape and pass-through for an
already-compliant validator. Unrecognized source drift prevents execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

OLD_STATE = """TRAVERSAL_PASS=false
SOAK_PASS=false
MEMORY_PASS=false
SCREENSHOT_WIDTH=0
"""
NEW_STATE = """TRAVERSAL_PASS=false
SOAK_PASS=false
MEMORY_PASS=false
ACTUAL_TRAVERSAL_SECONDS=0
ACTUAL_SOAK_SECONDS=0
SCREENSHOT_WIDTH=0
"""

OLD_ENV = '  TRAVERSAL_SECONDS="$TRAVERSAL_SECONDS" SOAK_SECONDS="$SOAK_SECONDS" \\\n'
NEW_ENV = '  TRAVERSAL_SECONDS="$TRAVERSAL_SECONDS" SOAK_SECONDS="$SOAK_SECONDS" ACTUAL_TRAVERSAL_SECONDS="$ACTUAL_TRAVERSAL_SECONDS" ACTUAL_SOAK_SECONDS="$ACTUAL_SOAK_SECONDS" \\\n'

OLD_JSON = """    'ten_minute_traversal': {'seconds': int(os.environ['TRAVERSAL_SECONDS']), 'passed': boolean('TRAVERSAL_PASS')},
    'thirty_minute_soak': {'seconds': int(os.environ['SOAK_SECONDS']), 'passed': boolean('SOAK_PASS')},
"""
NEW_JSON = """    'ten_minute_traversal': {'required_seconds': int(os.environ['TRAVERSAL_SECONDS']), 'actual_seconds': int(os.environ['ACTUAL_TRAVERSAL_SECONDS']), 'passed': boolean('TRAVERSAL_PASS')},
    'thirty_minute_soak': {'required_seconds': int(os.environ['SOAK_SECONDS']), 'actual_seconds': int(os.environ['ACTUAL_SOAK_SECONDS']), 'passed': boolean('SOAK_PASS')},
"""

OLD_RSS = '''  total_rss="$(awk '/TOTAL RSS:/{print $3; exit} /^ TOTAL[[:space:]]/{print $3; exit}' "$raw")"\n'''
NEW_RSS = '''  total_rss="$(awk '/TOTAL RSS:/{for(i=1;i<=NF;i++) if($i=="RSS:"){print $(i+1); exit}} /^ TOTAL[[:space:]]/{print $3; exit}' "$raw")"\n'''

OLD_RUNTIME = r'''printf 'timestamp_utc,label,pid,total_pss_kb,total_rss_kb\n' > "$METRICS"
sample_memory "START"
traversal_iterations=$((TRAVERSAL_SECONDS / 10))
{
  printf 'started_utc=%s\n' "$(date -u +%FT%TZ)"
  printf 'duration_seconds=%s\n' "$TRAVERSAL_SECONDS"
  printf 'iterations=%s\n' "$traversal_iterations"
} > "$TRAVERSAL_REPORT"
for iteration in $(seq 1 "$traversal_iterations"); do
  exercise_runtime_input
  sleep 8
  [[ -n "$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')" ]] || failed "application process exited during the 10-minute active traversal at iteration $iteration"
  if [[ "$iteration" -eq $((traversal_iterations / 2)) ]]; then
    sample_memory "TRAVERSAL_MID"
    capture_screenshot "$TRAVERSAL_MID_SCREENSHOT"
  fi
  sleep 1
done
TRAVERSAL_PASS=true
printf 'completed_utc=%s\nresult=PASS\n' "$(date -u +%FT%TZ)" >> "$TRAVERSAL_REPORT"

soak_iterations=$((SOAK_SECONDS / 15))
{
  printf 'started_utc=%s\n' "$(date -u +%FT%TZ)"
  printf 'duration_seconds=%s\n' "$SOAK_SECONDS"
  printf 'iterations=%s\n' "$soak_iterations"
} > "$SOAK_REPORT"
for iteration in $(seq 1 "$soak_iterations"); do
  exercise_runtime_input
  sleep 14
  [[ -n "$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')" ]] || failed "application process exited during the 30-minute soak at iteration $iteration"
  if [[ "$iteration" -eq $((soak_iterations / 2)) ]]; then
    sample_memory "SOAK_MID"
  fi
done
sample_memory "END"
SOAK_PASS=true
printf 'completed_utc=%s\nresult=PASS\n' "$(date -u +%FT%TZ)" >> "$SOAK_REPORT"
'''

NEW_RUNTIME = r'''printf 'timestamp_utc,label,pid,total_pss_kb,total_rss_kb\n' > "$METRICS"
sample_memory "START"
TRAVERSAL_STARTED_EPOCH="$(date +%s)"
TRAVERSAL_DEADLINE=$((TRAVERSAL_STARTED_EPOCH + TRAVERSAL_SECONDS))
TRAVERSAL_MIDPOINT=$((TRAVERSAL_STARTED_EPOCH + TRAVERSAL_SECONDS / 2))
TRAVERSAL_MID_CAPTURED=false
TRAVERSAL_ITERATIONS=0
{
  printf 'started_utc=%s\n' "$(date -u +%FT%TZ)"
  printf 'required_duration_seconds=%s\n' "$TRAVERSAL_SECONDS"
  printf 'deadline_epoch=%s\n' "$TRAVERSAL_DEADLINE"
} > "$TRAVERSAL_REPORT"
while (( $(date +%s) < TRAVERSAL_DEADLINE )); do
  TRAVERSAL_ITERATIONS=$((TRAVERSAL_ITERATIONS + 1))
  exercise_runtime_input
  sleep 8
  [[ -n "$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')" ]] || failed "application process exited during the 10-minute active traversal at iteration $TRAVERSAL_ITERATIONS"
  NOW_EPOCH="$(date +%s)"
  if [[ "$TRAVERSAL_MID_CAPTURED" == false ]] && (( NOW_EPOCH >= TRAVERSAL_MIDPOINT )); then
    sample_memory "TRAVERSAL_MID"
    capture_screenshot "$TRAVERSAL_MID_SCREENSHOT"
    TRAVERSAL_MID_CAPTURED=true
  fi
done
ACTUAL_TRAVERSAL_SECONDS=$(( $(date +%s) - TRAVERSAL_STARTED_EPOCH ))
(( ACTUAL_TRAVERSAL_SECONDS >= TRAVERSAL_SECONDS )) || failed "active traversal ended before the required 600 seconds"
[[ "$TRAVERSAL_MID_CAPTURED" == true ]] || failed "traversal midpoint evidence was not captured"
TRAVERSAL_PASS=true
printf 'completed_utc=%s\nactual_duration_seconds=%s\niterations=%s\nresult=PASS\n' "$(date -u +%FT%TZ)" "$ACTUAL_TRAVERSAL_SECONDS" "$TRAVERSAL_ITERATIONS" >> "$TRAVERSAL_REPORT"

SOAK_STARTED_EPOCH="$(date +%s)"
SOAK_DEADLINE=$((SOAK_STARTED_EPOCH + SOAK_SECONDS))
SOAK_MIDPOINT=$((SOAK_STARTED_EPOCH + SOAK_SECONDS / 2))
SOAK_MID_CAPTURED=false
SOAK_ITERATIONS=0
{
  printf 'started_utc=%s\n' "$(date -u +%FT%TZ)"
  printf 'required_duration_seconds=%s\n' "$SOAK_SECONDS"
  printf 'deadline_epoch=%s\n' "$SOAK_DEADLINE"
} > "$SOAK_REPORT"
while (( $(date +%s) < SOAK_DEADLINE )); do
  SOAK_ITERATIONS=$((SOAK_ITERATIONS + 1))
  exercise_runtime_input
  sleep 14
  [[ -n "$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')" ]] || failed "application process exited during the 30-minute soak at iteration $SOAK_ITERATIONS"
  NOW_EPOCH="$(date +%s)"
  if [[ "$SOAK_MID_CAPTURED" == false ]] && (( NOW_EPOCH >= SOAK_MIDPOINT )); then
    sample_memory "SOAK_MID"
    SOAK_MID_CAPTURED=true
  fi
done
ACTUAL_SOAK_SECONDS=$(( $(date +%s) - SOAK_STARTED_EPOCH ))
(( ACTUAL_SOAK_SECONDS >= SOAK_SECONDS )) || failed "soak ended before the required 1800 seconds"
[[ "$SOAK_MID_CAPTURED" == true ]] || failed "soak midpoint memory evidence was not captured"
sample_memory "END"
SOAK_PASS=true
printf 'completed_utc=%s\nactual_duration_seconds=%s\niterations=%s\nresult=PASS\n' "$(date -u +%FT%TZ)" "$ACTUAL_SOAK_SECONDS" "$SOAK_ITERATIONS" >> "$SOAK_REPORT"
'''

REQUIRED_TOKENS = (
    'TRAVERSAL_DEADLINE',
    'SOAK_DEADLINE',
    'ACTUAL_TRAVERSAL_SECONDS',
    'ACTUAL_SOAK_SECONDS',
)
COMPLIANT_TOKENS = REQUIRED_TOKENS + (
    'wait_for_world_ready_after',
    'ANDROID_EMULATOR_GFXINFO.txt',
    'ANDROID_EMULATOR_FOCUS.txt',
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def replace_exact(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one reviewed source block, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()

    source_bytes = args.source.read_bytes()
    text = source_bytes.decode('utf-8')
    already_compliant = all(token in text for token in COMPLIANT_TOKENS)
    patches_applied = 0
    if not already_compliant:
        for label, old, new in (
            ('state', OLD_STATE, NEW_STATE),
            ('report environment', OLD_ENV, NEW_ENV),
            ('report JSON', OLD_JSON, NEW_JSON),
            ('RSS parser', OLD_RSS, NEW_RSS),
            ('runtime duration block', OLD_RUNTIME, NEW_RUNTIME),
        ):
            text = replace_exact(text, old, new, label)
        patches_applied = 5

    if not all(token in text for token in REQUIRED_TOKENS):
        raise SystemExit('effective validator is missing wall-clock tokens')
    output_bytes = text.encode('utf-8')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(output_bytes)
    os.chmod(args.output, 0o755)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({
        'source_path': args.source.as_posix(),
        'source_sha256': digest(source_bytes),
        'output_path': args.output.as_posix(),
        'output_sha256': digest(output_bytes),
        'patches_applied': patches_applied,
        'source_already_compliant': already_compliant,
        'traversal_required_seconds': 600,
        'soak_required_seconds': 1800,
        'wall_clock_enforced': True,
    }, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
