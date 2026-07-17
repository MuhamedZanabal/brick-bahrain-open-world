#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

ALLOWED_ORIGINS = {
    "historical source",
    "436-asset authority",
    "PR #59 checkout",
    "premium overlay",
    "validation correction",
    "deterministically generated output",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHA512_RE = re.compile(r"^[0-9a-f]{128}$")
REQUIRED_COMPARE_FILES = (
    "FINAL_TREE_MANIFEST.json",
    "FINAL_TREE_AUTHORITY.json",
    "FROZEN_CONTROLS_PRE.json",
    "FROZEN_CONTROLS_POST.json",
)


class AuthorityError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AuthorityError(f"required JSON file missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AuthorityError(f"invalid JSON file {path}: {exc}") from exc


def normalize_relative_path(raw: str) -> str:
    if not isinstance(raw, str) or not raw or "\x00" in raw or "\\" in raw:
        raise AuthorityError(f"unsafe normalized path: {raw!r}")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise AuthorityError(f"unsafe normalized path: {raw!r}")
    normalized = path.as_posix()
    if normalized != raw:
        raise AuthorityError(f"unsafe normalized path: {raw!r}")
    return normalized


def ensure_plain_file(path: Path, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as exc:
        raise AuthorityError(f"{label} missing: {path}") from exc
    if stat.S_ISLNK(mode):
        raise AuthorityError(f"symbolic link is forbidden for {label}: {path}")
    if not stat.S_ISREG(mode):
        raise AuthorityError(f"{label} is not a regular file: {path}")


def required_nonempty(mapping: dict[str, Any], key: str, prefix: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AuthorityError(f"{prefix}.{key} must be pinned and non-empty")
    return value


def validate_contract(contract_path: Path, repo_root: Path) -> dict[str, Any]:
    contract = load_json(contract_path)
    if not isinstance(contract, dict):
        raise AuthorityError("authority contract must be a JSON object")
    if contract.get("schema_version") != 1:
        raise AuthorityError("authority contract schema_version must equal 1")
    if contract.get("authority_classification") != "deterministically_reconstructable_composite":
        raise AuthorityError("authority_classification must be deterministically_reconstructable_composite")
    for key in ("candidate_branch", "base_authority", "frozen_premium_authority"):
        required_nonempty(contract, key, "contract")
    for key in ("base_authority", "frozen_premium_authority"):
        if not re.fullmatch(r"[0-9a-f]{40}", str(contract[key])):
            raise AuthorityError(f"contract.{key} must be a 40-character commit SHA")

    inputs = contract.get("external_inputs")
    if not isinstance(inputs, list) or not inputs:
        raise AuthorityError("external_inputs must be a non-empty list")
    seen_ids: set[str] = set()
    for index, item in enumerate(inputs):
        if not isinstance(item, dict):
            raise AuthorityError(f"external_inputs[{index}] must be an object")
        input_id = required_nonempty(item, "id", f"external_inputs[{index}]")
        if input_id in seen_ids:
            raise AuthorityError(f"duplicate external input id: {input_id}")
        seen_ids.add(input_id)
        locator = required_nonempty(item, "immutable_locator", f"external_inputs[{index}]")
        if not locator.startswith("https://"):
            raise AuthorityError(f"external input locator must use HTTPS: {locator}")
        digest = required_nonempty(item, "sha256", f"external_inputs[{index}]")
        if not SHA256_RE.fullmatch(digest):
            raise AuthorityError(f"external input sha256 is not pinned: {input_id}")
        size = item.get("bytes")
        if not isinstance(size, int) or size <= 0:
            raise AuthorityError(f"external input byte size is not pinned: {input_id}")
        required_nonempty(item, "provenance_authority", f"external_inputs[{index}]")
        normalize_relative_path(required_nonempty(item, "extraction_destination", f"external_inputs[{index}]"))

    toolchain = contract.get("toolchain")
    if not isinstance(toolchain, dict):
        raise AuthorityError("toolchain must be an object")
    for key in (
        "runner_image",
        "os_release",
        "python",
        "pillow",
        "librsvg2_bin",
        "godot_version",
        "godot_archive_sha512",
    ):
        required_nonempty(toolchain, key, "toolchain")
    if not SHA512_RE.fullmatch(str(toolchain["godot_archive_sha512"])):
        raise AuthorityError("toolchain.godot_archive_sha512 must be a pinned SHA-512")

    scripts = contract.get("reconstruction_scripts")
    if not isinstance(scripts, list) or not scripts:
        raise AuthorityError("reconstruction_scripts must be a non-empty list")
    seen_paths: set[str] = set()
    root = repo_root.resolve()
    for index, record in enumerate(scripts):
        if not isinstance(record, dict):
            raise AuthorityError(f"reconstruction_scripts[{index}] must be an object")
        relative = normalize_relative_path(required_nonempty(record, "path", f"reconstruction_scripts[{index}]"))
        if relative in seen_paths:
            raise AuthorityError(f"duplicate reconstruction script path: {relative}")
        seen_paths.add(relative)
        expected = required_nonempty(record, "sha256", f"reconstruction_scripts[{index}]")
        if not SHA256_RE.fullmatch(expected):
            raise AuthorityError(f"reconstruction script checksum is not pinned: {relative}")
        target = root / relative
        ensure_plain_file(target, "reconstruction script")
        actual = sha256_file(target)
        if actual != expected:
            raise AuthorityError(
                f"reconstruction script checksum mismatch for {relative}: expected {expected}, got {actual}"
            )

    protected = contract.get("protected_files", [])
    if not isinstance(protected, list):
        raise AuthorityError("protected_files must be a list")
    for index, record in enumerate(protected):
        if not isinstance(record, dict):
            raise AuthorityError(f"protected_files[{index}] must be an object")
        normalize_relative_path(required_nonempty(record, "path", f"protected_files[{index}]"))
        digest = required_nonempty(record, "sha256", f"protected_files[{index}]")
        if not SHA256_RE.fullmatch(digest):
            raise AuthorityError(f"protected_files[{index}].sha256 must be pinned")

    expected_final = contract.get("expected_final")
    if not isinstance(expected_final, dict):
        raise AuthorityError("expected_final must be an object")
    for key in ("manifest_sha256", "aggregate_tree_sha256"):
        value = expected_final.get(key)
        if value is not None and (not isinstance(value, str) or not SHA256_RE.fullmatch(value)):
            raise AuthorityError(f"expected_final.{key} must be null or SHA-256")
    for key in ("file_count", "total_bytes"):
        value = expected_final.get(key)
        if value is not None and (not isinstance(value, int) or value < 0):
            raise AuthorityError(f"expected_final.{key} must be null or a non-negative integer")
    return contract


def collect_plain_files(root: Path, excluded: set[str] | None = None) -> dict[str, Path]:
    if not root.is_dir():
        raise AuthorityError(f"directory missing: {root}")
    excluded = excluded or set()
    found: dict[str, Path] = {}
    casefolded: dict[str, str] = {}
    for directory, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        directory_path = Path(directory)
        for dirname in list(dirnames):
            candidate = directory_path / dirname
            if candidate.is_symlink():
                raise AuthorityError(f"symbolic link directory is forbidden: {candidate}")
        for filename in filenames:
            candidate = directory_path / filename
            relative = normalize_relative_path(candidate.relative_to(root).as_posix())
            if relative in excluded:
                continue
            ensure_plain_file(candidate, "source file")
            folded = relative.casefold()
            previous = casefolded.get(folded)
            if previous is not None and previous != relative:
                raise AuthorityError(f"case-colliding paths: {previous!r} and {relative!r}")
            casefolded[folded] = relative
            if relative in found:
                raise AuthorityError(f"duplicate normalized path: {relative}")
            found[relative] = candidate
    return found


def load_origin_ledger(path: Path) -> dict[str, str]:
    data = load_json(path)
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("files"), list):
        raise AuthorityError("origin ledger must contain schema_version=1 and a files list")
    result: dict[str, str] = {}
    casefolded: dict[str, str] = {}
    for record in data["files"]:
        if not isinstance(record, dict):
            raise AuthorityError("origin ledger records must be objects")
        relative = normalize_relative_path(record.get("path"))
        origin = record.get("origin")
        if origin not in ALLOWED_ORIGINS:
            raise AuthorityError(f"invalid origin category for {relative}: {origin!r}")
        if relative in result:
            raise AuthorityError(f"duplicate normalized origin path: {relative}")
        folded = relative.casefold()
        prior = casefolded.get(folded)
        if prior is not None and prior != relative:
            raise AuthorityError(f"case-colliding origin paths: {prior!r} and {relative!r}")
        casefolded[folded] = relative
        result[relative] = origin
    return result


def aggregate_records(records: Iterable[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(record["path"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(record["bytes"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(record["sha256"].encode("ascii"))
        digest.update(b"\0")
        digest.update(record["origin"].encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def command_validate_contract(args: argparse.Namespace) -> dict[str, Any]:
    contract = validate_contract(args.contract, args.repo_root)
    return {
        "passed": True,
        "contract_sha256": sha256_file(args.contract),
        "reconstruction_script_count": len(contract["reconstruction_scripts"]),
    }


def command_verify_input(args: argparse.Namespace) -> dict[str, Any]:
    ensure_plain_file(args.file, f"external input {args.id}")
    actual_bytes = args.file.stat().st_size
    actual_sha256 = sha256_file(args.file)
    if actual_bytes != args.expected_bytes:
        raise AuthorityError(
            f"byte-size mismatch for {args.id}: expected {args.expected_bytes}, got {actual_bytes}"
        )
    if actual_sha256 != args.expected_sha256:
        raise AuthorityError(
            f"checksum mismatch for {args.id}: expected {args.expected_sha256}, got {actual_sha256}"
        )
    report = {
        "id": args.id,
        "path": str(args.file),
        "bytes": actual_bytes,
        "expected_bytes": args.expected_bytes,
        "sha256": actual_sha256,
        "expected_sha256": args.expected_sha256,
        "passed": True,
    }
    write_json(args.output, report)
    return report


def command_manifest(args: argparse.Namespace) -> dict[str, Any]:
    contract = validate_contract(args.contract, args.repo_root)
    actual = collect_plain_files(args.game_root)
    origins = load_origin_ledger(args.origin_ledger)
    actual_paths = set(actual)
    origin_paths = set(origins)
    unexpected = sorted(actual_paths - origin_paths)
    missing = sorted(origin_paths - actual_paths)
    if unexpected:
        raise AuthorityError(f"unexpected files without origin: {unexpected}")
    if missing:
        raise AuthorityError(f"origin records for missing files: {missing}")

    records: list[dict[str, Any]] = []
    for relative in sorted(actual, key=lambda item: item.encode("utf-8")):
        path = actual[relative]
        records.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "origin": origins[relative],
            }
        )
    total_bytes = sum(record["bytes"] for record in records)
    aggregate = aggregate_records(records)
    manifest = {
        "schema_version": 1,
        "candidate_commit": args.candidate_commit,
        "file_count": len(records),
        "total_bytes": total_bytes,
        "aggregate_tree_sha256": aggregate,
        "files": records,
    }
    write_json(args.output, manifest)
    manifest_sha256 = sha256_file(args.output)

    protected_map = {record["path"]: record["sha256"] for record in contract.get("protected_files", [])}
    record_map = {record["path"]: record["sha256"] for record in records}
    protected_mismatches = []
    for relative, expected in sorted(protected_map.items()):
        actual_digest = record_map.get(relative)
        if actual_digest != expected:
            protected_mismatches.append(
                {"path": relative, "expected_sha256": expected, "actual_sha256": actual_digest}
            )
    if protected_mismatches:
        raise AuthorityError(f"frozen protected files changed: {protected_mismatches}")

    report = {
        "schema_version": 1,
        "candidate_commit": args.candidate_commit,
        "base_authority": contract["base_authority"],
        "frozen_premium_authority": contract["frozen_premium_authority"],
        "external_inputs": [
            {
                "id": item["id"],
                "immutable_locator": item["immutable_locator"],
                "sha256": item["sha256"],
                "bytes": item["bytes"],
                "provenance_authority": item["provenance_authority"],
                "extraction_destination": item["extraction_destination"],
            }
            for item in contract["external_inputs"]
        ],
        "reconstruction_scripts": contract["reconstruction_scripts"],
        "manifest_sha256": manifest_sha256,
        "file_count": len(records),
        "total_bytes": total_bytes,
        "aggregate_tree_sha256": aggregate,
        "protected_file_count": len(protected_map),
        "protected_files_unchanged": True,
    }
    expected = contract["expected_final"]
    comparisons = {
        "manifest_sha256": manifest_sha256,
        "aggregate_tree_sha256": aggregate,
        "file_count": len(records),
        "total_bytes": total_bytes,
    }
    for key, actual_value in comparisons.items():
        expected_value = expected.get(key)
        if expected_value is not None and expected_value != actual_value:
            raise AuthorityError(
                f"final assembled authority mismatch for {key}: expected {expected_value}, got {actual_value}"
            )
    write_json(args.report, report)
    return report


def command_archive(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.manifest)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list):
        raise AuthorityError("invalid final-tree manifest")
    actual = collect_plain_files(args.game_root)
    records = manifest["files"]
    expected_paths = [record.get("path") for record in records]
    if len(expected_paths) != len(set(expected_paths)):
        raise AuthorityError("duplicate normalized path in final-tree manifest")
    if set(actual) != set(expected_paths):
        raise AuthorityError("game tree no longer matches final-tree manifest paths")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        args.output,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for record in records:
            relative = normalize_relative_path(record["path"])
            path = actual[relative]
            if path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
                raise AuthorityError(f"game file changed after manifest generation: {relative}")
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.flag_bits |= 0x800
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    report = {
        "passed": True,
        "manifest_sha256": sha256_file(args.manifest),
        "file_count": len(records),
        "archive_bytes": args.output.stat().st_size,
        "archive_sha256": sha256_file(args.output),
    }
    write_json(args.report, report)
    return report


def command_inventory(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    output = args.output.resolve()
    try:
        relative_output = normalize_relative_path(output.relative_to(root).as_posix())
        excluded = {relative_output}
    except ValueError:
        relative_output = ""
        excluded = set()
    files = collect_plain_files(root, excluded=excluded)
    records = [
        {
            "path": relative,
            "bytes": files[relative].stat().st_size,
            "sha256": sha256_file(files[relative]),
            "retention": "retained",
        }
        for relative in sorted(files, key=lambda item: item.encode("utf-8"))
    ]
    report = {
        "schema_version": 1,
        "file_count": len(records),
        "total_bytes": sum(record["bytes"] for record in records),
        "files": records,
        "intentionally_excluded": [relative_output] if excluded else [],
    }
    write_json(args.output, report)
    return report


def command_verify_inventory(args: argparse.Namespace) -> dict[str, Any]:
    inventory = load_json(args.inventory)
    root = args.root.resolve()
    inventory_path = args.inventory.resolve()
    excluded: set[str] = set()
    try:
        excluded.add(normalize_relative_path(inventory_path.relative_to(root).as_posix()))
    except ValueError:
        pass
    actual = collect_plain_files(root, excluded=excluded)
    records = inventory.get("files") if isinstance(inventory, dict) else None
    if not isinstance(records, list):
        raise AuthorityError("evidence inventory mismatch: files list missing")
    expected: dict[str, tuple[int, str]] = {}
    for record in records:
        relative = normalize_relative_path(record.get("path"))
        if relative in expected:
            raise AuthorityError(f"evidence inventory mismatch: duplicate path {relative}")
        expected[relative] = (record.get("bytes"), record.get("sha256"))
    actual_values = {
        relative: (path.stat().st_size, sha256_file(path)) for relative, path in actual.items()
    }
    if expected != actual_values:
        missing = sorted(set(expected) - set(actual_values))
        unexpected = sorted(set(actual_values) - set(expected))
        changed = sorted(
            path for path in set(expected) & set(actual_values) if expected[path] != actual_values[path]
        )
        raise AuthorityError(
            f"evidence inventory mismatch: missing={missing}, unexpected={unexpected}, changed={changed}"
        )
    return {
        "passed": True,
        "file_count": len(actual_values),
        "total_bytes": sum(value[0] for value in actual_values.values()),
        "inventory_sha256": sha256_file(args.inventory),
    }


def command_compare(args: argparse.Namespace) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    compared: list[dict[str, Any]] = []
    for relative in REQUIRED_COMPARE_FILES:
        path_a = args.run_a / relative
        path_b = args.run_b / relative
        ensure_plain_file(path_a, f"run A evidence {relative}")
        ensure_plain_file(path_b, f"run B evidence {relative}")
        digest_a = sha256_file(path_a)
        digest_b = sha256_file(path_b)
        compared.append({"path": relative, "run_a_sha256": digest_a, "run_b_sha256": digest_b})
        if digest_a != digest_b or path_a.read_bytes() != path_b.read_bytes():
            mismatches.append({"path": relative, "run_a_sha256": digest_a, "run_b_sha256": digest_b})
    authority_a = load_json(args.run_a / "FINAL_TREE_AUTHORITY.json")
    authority_b = load_json(args.run_b / "FINAL_TREE_AUTHORITY.json")
    for key in ("manifest_sha256", "file_count", "total_bytes", "aggregate_tree_sha256"):
        if authority_a.get(key) != authority_b.get(key):
            mismatches.append(
                {"field": key, "run_a": authority_a.get(key), "run_b": authority_b.get(key)}
            )
    if mismatches:
        raise AuthorityError(f"reconstruction mismatch: {mismatches}")
    report = {
        "schema_version": 1,
        "passed": True,
        "run_a": str(args.run_a),
        "run_b": str(args.run_b),
        "manifest_sha256": authority_a.get("manifest_sha256"),
        "file_count": authority_a.get("file_count"),
        "total_bytes": authority_a.get("total_bytes"),
        "aggregate_tree_sha256": authority_a.get("aggregate_tree_sha256"),
        "byte_identical_files": compared,
    }
    write_json(args.output, report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bahrain Brick composite source authority tooling")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate-contract")
    validate.add_argument("--contract", type=Path, required=True)
    validate.add_argument("--repo-root", type=Path, required=True)
    validate.set_defaults(handler=command_validate_contract)

    verify = sub.add_parser("verify-input")
    verify.add_argument("--file", type=Path, required=True)
    verify.add_argument("--expected-sha256", required=True)
    verify.add_argument("--expected-bytes", type=int, required=True)
    verify.add_argument("--id", required=True)
    verify.add_argument("--output", type=Path, required=True)
    verify.set_defaults(handler=command_verify_input)

    manifest = sub.add_parser("manifest")
    manifest.add_argument("--contract", type=Path, required=True)
    manifest.add_argument("--repo-root", type=Path, required=True)
    manifest.add_argument("--game-root", type=Path, required=True)
    manifest.add_argument("--origin-ledger", type=Path, required=True)
    manifest.add_argument("--candidate-commit", required=True)
    manifest.add_argument("--output", type=Path, required=True)
    manifest.add_argument("--report", type=Path, required=True)
    manifest.set_defaults(handler=command_manifest)

    archive = sub.add_parser("archive")
    archive.add_argument("--game-root", type=Path, required=True)
    archive.add_argument("--manifest", type=Path, required=True)
    archive.add_argument("--output", type=Path, required=True)
    archive.add_argument("--report", type=Path, required=True)
    archive.set_defaults(handler=command_archive)

    inventory = sub.add_parser("inventory")
    inventory.add_argument("--root", type=Path, required=True)
    inventory.add_argument("--output", type=Path, required=True)
    inventory.set_defaults(handler=command_inventory)

    verify_inventory = sub.add_parser("verify-inventory")
    verify_inventory.add_argument("--root", type=Path, required=True)
    verify_inventory.add_argument("--inventory", type=Path, required=True)
    verify_inventory.set_defaults(handler=command_verify_inventory)

    compare = sub.add_parser("compare")
    compare.add_argument("--run-a", type=Path, required=True)
    compare.add_argument("--run-b", type=Path, required=True)
    compare.add_argument("--output", type=Path, required=True)
    compare.set_defaults(handler=command_compare)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = args.handler(args)
    except AuthorityError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
