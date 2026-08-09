#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from check_repository_binaries import scan_repository
from validate_manifest_schema import validate_manifest_tree


def run_checks(root: Path) -> dict[str, object]:
    binary = scan_repository(root)
    manifests = validate_manifest_tree(root, allow_empty=True)
    return {
        "passed": bool(binary["passed"] and manifests["passed"]),
        "binary_policy": binary,
        "manifest_schema": manifests,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Bahrain Brick Phase 2 repository architecture checks.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = run_checks(args.root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
