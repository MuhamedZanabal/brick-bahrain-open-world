#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

OLD_BLOCK = '''write_mode_file() {
  local package="$1" mode="$2"
  "$ADB" shell run-as "$package" sh -c "mkdir -p files && printf '%s' '$mode' > files/r1_mode.txt"
}
'''

NEW_BLOCK = '''write_mode_file() {
  local package="$1" mode="$2"
  local local_mode_file="$OUTPUT_ROOT/r1-mode-${package//./_}.txt"
  printf '%s' "$mode" > "$local_mode_file"
  "$ADB" push "$local_mode_file" /data/local/tmp/r1_mode.txt >/dev/null
  "$ADB" shell run-as "$package" cp /data/local/tmp/r1_mode.txt files/r1_mode.txt
  "$ADB" shell rm -f /data/local/tmp/r1_mode.txt
  "$ADB" exec-out run-as "$package" cat files/r1_mode.txt > "$local_mode_file.verified"
  cmp -s "$local_mode_file" "$local_mode_file.verified"
}
'''


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def patch_runner(runner: Path, report: Path) -> dict[str, object]:
    before = runner.read_bytes()
    text = before.decode()
    if OLD_BLOCK in text:
        if text.count(OLD_BLOCK) != 1:
            raise ValueError("fragile mode-file writer found more than once")
        text = text.replace(OLD_BLOCK, NEW_BLOCK)
        status = "patched"
    elif NEW_BLOCK in text:
        status = "already_patched"
    else:
        raise ValueError("mode-file writer is neither the accepted old nor corrected form")
    after = text.encode()
    if b'run-as "$package" sh -c "mkdir -p files' in after:
        raise ValueError("fragile nested run-as shell mode writer remains")
    for marker in (
        b'/data/local/tmp/r1_mode.txt',
        b'run-as "$package" cp /data/local/tmp/r1_mode.txt files/r1_mode.txt',
        b'cmp -s "$local_mode_file" "$local_mode_file.verified"',
    ):
        if marker not in after:
            raise ValueError(f"corrected mode-transfer marker missing: {marker!r}")
    if after != before:
        runner.write_bytes(after)
        runner.chmod(0o755)
    result = {
        "schema_version": 1,
        "status": status,
        "runner": runner.as_posix(),
        "before_sha256": sha256(before),
        "after_sha256": sha256(after),
        "changed": before != after,
        "mode_file_transfer": "ADB_PUSH_THEN_RUN_AS_CP_WITH_ROUND_TRIP_COMPARE",
        "production_source_modified": False,
        "renderer_defaults_modified": False,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(patch_runner(args.runner, args.report), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
