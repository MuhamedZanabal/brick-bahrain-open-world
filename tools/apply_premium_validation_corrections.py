#!/usr/bin/env python3
"""Assemble the checksum-pinned v18 correction set, then apply final teardown guards."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

EXPECTED_SOURCE_SHA256 = "ff164b38033828bb42133cdafae092271132920c83c189908b0b03ca9c10cb89"
PARTS = tuple(
    Path(__file__).with_name("premium_validation_v18_parts") / f"part_{index:02d}.pyfrag"
    for index in range(6)
)
missing = [path.as_posix() for path in PARTS if not path.is_file()]
if missing:
    raise RuntimeError(f"premium validation correction fragments missing: {missing}")
source = b"".join(path.read_bytes() for path in PARTS)
actual = hashlib.sha256(source).hexdigest()
if actual != EXPECTED_SOURCE_SHA256:
    raise RuntimeError(
        "premium validation correction source SHA-256 mismatch: "
        f"expected={EXPECTED_SOURCE_SHA256}, actual={actual}"
    )

_assembled: dict[str, object] = {
    "__name__": "premium_validation_v18_assembled",
    "__file__": str(PARTS[0]),
}
exec(compile(source.decode("utf-8"), str(PARTS[0]), "exec"), _assembled)
for _name, _value in _assembled.items():
    if not _name.startswith("__"):
        globals()[_name] = _value
_base_apply = _assembled["apply"]

_POST_MODULE = Path(__file__).with_name("apply_post_lifecycle_teardown_guards.py")
_post_spec = importlib.util.spec_from_file_location("post_lifecycle_teardown_guards", _POST_MODULE)
if _post_spec is None or _post_spec.loader is None:
    raise RuntimeError(f"unable to load post-lifecycle guard module: {_POST_MODULE}")
_post = importlib.util.module_from_spec(_post_spec)
_post_spec.loader.exec_module(_post)


def apply(root: Path) -> dict:
    root = root.resolve()
    report = _base_apply(root)
    post_report = _post.apply(root)

    world_path = root / _post.WORLD_PATH
    lifecycle_test_path = root / _post.LIFECYCLE_TEST_PATH
    world_sha = hashlib.sha256(world_path.read_bytes()).hexdigest()
    lifecycle_test_sha = hashlib.sha256(lifecycle_test_path.read_bytes()).hexdigest()

    world_result = next(
        item for item in report["corrections"] if item["path"] == _post.WORLD_PATH
    )
    world_result["after_sha256"] = world_sha
    world_result["states"].append(post_report["changes"][0]["state"])
    world_result["reasons"].append(post_report["changes"][0]["reason"])

    lifecycle_resource = next(
        item
        for item in report["generated_validation_resources"]
        if item["path"] == _post.LIFECYCLE_TEST_PATH
    )
    lifecycle_resource["sha256"] = lifecycle_test_sha
    lifecycle_resource["size_bytes"] = lifecycle_test_path.stat().st_size
    lifecycle_resource["post_correction_state"] = post_report["changes"][1]["state"]
    lifecycle_resource["reason"] += "; " + post_report["changes"][1]["reason"]

    report["protected_world_exit_actual_sha256"] = post_report[
        "protected_world_exit_actual_sha256"
    ]
    report["protected_world_exit_unchanged"] = post_report[
        "protected_world_exit_unchanged"
    ]
    report["post_lifecycle_teardown_guard"] = post_report
    report.setdefault("diagnostic_sources", {})[_post.WORLD_PATH] = world_path.read_text(
        encoding="utf-8"
    )
    report["diagnostic_sources"][_post.LIFECYCLE_TEST_PATH] = lifecycle_test_path.read_text(
        encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = apply(args.root)
    except Exception as error:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(
                {
                    "conclusion": "fail",
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        raise
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
