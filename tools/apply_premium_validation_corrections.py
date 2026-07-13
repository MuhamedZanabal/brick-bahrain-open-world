#!/usr/bin/env python3
"""Assemble checksum-pinned corrections, apply teardown fixes, and preserve source diagnostics."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
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


def _load_module(name: str, filename: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load validation correction module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_post = _load_module(
    "post_lifecycle_teardown_guards",
    "apply_post_lifecycle_teardown_guards.py",
)
_evidence = _load_module(
    "visual_evidence_shutdown_fix",
    "apply_visual_evidence_shutdown_fix.py",
)

TRANSFORM_TOKENS = ("global_position", "global_transform", "get_global_transform")
TEARDOWN_TOKENS = (
    "_exit_tree",
    "NOTIFICATION_EXIT_TREE",
    "tree_exiting",
    "tree_exited",
    "child_exiting_tree",
    "queue_free",
    "free()",
    "get_tree().quit",
)


def _normalize_final_guard_for_checksum_pinned_base(root: Path) -> str:
    """Restore only the base block's unprotected line before its idempotence check."""
    world_path = root / _post.WORLD_PATH
    if not world_path.is_file():
        return "not_present"
    text = world_path.read_text(encoding="utf-8")
    safe_count = text.count(_post.SAFE_PARENT_LINE)
    unsafe_count = text.count(_post.UNSAFE_PARENT_LINE)
    if safe_count == 1 and unsafe_count == 0:
        text = text.replace(_post.SAFE_PARENT_LINE, _post.UNSAFE_PARENT_LINE, 1)
        world_path.write_text(text, encoding="utf-8")
        return "normalized"
    if safe_count == 0:
        return "not_required"
    raise RuntimeError(
        "final lifecycle guard normalization mismatch: "
        f"safe_count={safe_count}, unsafe_count={unsafe_count}"
    )


def _function_for_line(lines: list[str], line_index: int) -> str:
    for index in range(line_index, -1, -1):
        match = re.match(r"^func\s+([A-Za-z0-9_]+)\b", lines[index])
        if match:
            return match.group(1)
    return "<top-level>"


def collect_transform_access_inventory(root: Path) -> dict:
    entries: list[dict] = []
    source_snapshots: dict[str, str] = {}
    teardown_sources: dict[str, str] = {}
    for base_name in ("scripts", "tests"):
        base = root / base_name
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.gd")):
            if any(part in {".godot", "build"} for part in path.relative_to(root).parts):
                continue
            relative = path.relative_to(root).as_posix()
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            lines = text.splitlines()
            matched = False
            for line_index, line in enumerate(lines):
                tokens = [token for token in TRANSFORM_TOKENS if token in line]
                if not tokens:
                    continue
                matched = True
                start = max(0, line_index - 4)
                end = min(len(lines), line_index + 5)
                entries.append(
                    {
                        "path": relative,
                        "function": _function_for_line(lines, line_index),
                        "line": line_index + 1,
                        "tokens": tokens,
                        "text": line.strip(),
                        "context_start_line": start + 1,
                        "context": [
                            {"line": idx + 1, "text": lines[idx]}
                            for idx in range(start, end)
                        ],
                    }
                )
            if matched:
                source_snapshots[relative] = text
            if any(token in text for token in TEARDOWN_TOKENS):
                teardown_sources[relative] = text
    return {
        "entry_count": len(entries),
        "file_count": len(source_snapshots),
        "entries": entries,
        "source_snapshots": source_snapshots,
        "teardown_source_snapshots": teardown_sources,
    }


def apply(root: Path) -> dict:
    root = root.resolve()
    normalization_state = _normalize_final_guard_for_checksum_pinned_base(root)
    report = _base_apply(root)
    full_project_contract = (root / "scenes/world.tscn").is_file()
    post_report = _post.apply(
        root,
        require_npc_scans=full_project_contract,
    )
    evidence_report = _evidence.apply(
        root,
        require_evidence=full_project_contract,
    )

    world_path = root / _post.WORLD_PATH
    lifecycle_test_path = root / _post.LIFECYCLE_TEST_PATH
    npc_path = root / _post.NPC_PATH
    world_sha = hashlib.sha256(world_path.read_bytes()).hexdigest()
    lifecycle_test_sha = hashlib.sha256(lifecycle_test_path.read_bytes()).hexdigest()
    npc_sha = hashlib.sha256(npc_path.read_bytes()).hexdigest()

    world_result = next(
        item for item in report["corrections"] if item["path"] == _post.WORLD_PATH
    )
    world_result["after_sha256"] = world_sha

    npc_result = next(
        item for item in report["corrections"] if item["path"] == _post.NPC_PATH
    )
    npc_result["after_sha256"] = npc_sha
    npc_result["states"].extend(post_report["changes"][2]["states"])
    npc_result["reasons"].extend(post_report["changes"][2]["reasons"])

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
    report["visual_evidence_shutdown_fix"] = evidence_report
    report["post_lifecycle_base_normalization"] = normalization_state
    report["full_project_contract"] = full_project_contract
    report.setdefault("diagnostic_sources", {})[_post.WORLD_PATH] = world_path.read_text(
        encoding="utf-8"
    )
    report["diagnostic_sources"][_post.LIFECYCLE_TEST_PATH] = lifecycle_test_path.read_text(
        encoding="utf-8"
    )
    report["diagnostic_sources"][_post.NPC_PATH] = npc_path.read_text(encoding="utf-8")

    evidence_path = root / _evidence.EVIDENCE_PATH
    if evidence_path.is_file():
        report["diagnostic_sources"][_evidence.EVIDENCE_PATH] = evidence_path.read_text(
            encoding="utf-8"
        )
    report["transform_access_inventory"] = collect_transform_access_inventory(root)
    return report


def compact_stdout_summary(report: dict) -> dict:
    """Return a scanner-safe summary; complete source diagnostics stay in the JSON report."""
    corrections = []
    for item in report.get("corrections", []):
        corrections.append(
            {
                "path": item.get("path"),
                "states": item.get("states", []),
                "before_sha256": item.get("before_sha256"),
                "after_sha256": item.get("after_sha256"),
            }
        )

    generated_resources = []
    for item in report.get("generated_validation_resources", []):
        generated_resources.append(
            {
                "path": item.get("path"),
                "state": item.get("state"),
                "post_correction_state": item.get("post_correction_state"),
                "sha256": item.get("sha256"),
                "size_bytes": item.get("size_bytes"),
            }
        )

    evidence = report.get("visual_evidence_shutdown_fix", {})
    inventory = report.get("transform_access_inventory", {})
    post = report.get("post_lifecycle_teardown_guard", {})
    return {
        "conclusion": report.get("conclusion"),
        "protected_world_exit_actual_sha256": report.get(
            "protected_world_exit_actual_sha256"
        ),
        "protected_world_exit_unchanged": report.get(
            "protected_world_exit_unchanged"
        ),
        "post_lifecycle_base_normalization": report.get(
            "post_lifecycle_base_normalization"
        ),
        "full_project_contract": report.get("full_project_contract"),
        "corrections": corrections,
        "generated_validation_resources": generated_resources,
        "post_lifecycle_teardown_guard": {
            "conclusion": post.get("conclusion"),
            "protected_world_exit_unchanged": post.get(
                "protected_world_exit_unchanged"
            ),
            "change_paths": [item.get("path") for item in post.get("changes", [])],
        },
        "visual_evidence_shutdown_fix": {
            "conclusion": evidence.get("conclusion"),
            "path": evidence.get("path"),
            "state": evidence.get("state"),
            "required": evidence.get("required"),
            "before_sha256": evidence.get("before_sha256"),
            "after_sha256": evidence.get("after_sha256"),
            "size_bytes": evidence.get("size_bytes"),
        },
        "transform_access_inventory": {
            "entry_count": inventory.get("entry_count", 0),
            "file_count": inventory.get("file_count", 0),
            "teardown_source_file_count": len(
                inventory.get("teardown_source_snapshots", {})
            ),
        },
    }


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
    print(json.dumps(compact_stdout_summary(report), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
