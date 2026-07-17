#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

ASSET_PREFIX = "assets/"
MAX_METADATA_BYTES = 1024 * 1024
REMAP_PATH_RE = re.compile(r'(?m)^path="res://([^"\r\n]+)"\s*$')
SECTION_RE = re.compile(r"^\[([^\]\r\n]+)\]$")
ASSIGNMENT_RE = re.compile(r"^([A-Za-z0-9_./-]+)\s*=\s*(.*)$")
COMPILED_ALIASES = {
    ".scn": ".tscn",
    ".res": ".tres",
    ".gdc": ".gd",
}


class MetadataError(ValueError):
    pass


class UnsafePathError(ValueError):
    pass


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def strict_relative_path(value: str, *, allow_res_prefix: bool = False) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise UnsafePathError(f"unsafe path: {value!r}")
    raw = value
    if allow_res_prefix and raw.startswith("res://"):
        raw = raw[len("res://") :]
    elif "://" in raw:
        raise UnsafePathError(f"unsupported path scheme: {value!r}")
    if not raw or raw.startswith("/"):
        raise UnsafePathError(f"absolute or empty path: {value!r}")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise UnsafePathError(f"unsafe path: {value!r}")
    normalized = path.as_posix()
    if normalized != raw:
        raise UnsafePathError(f"non-canonical path: {value!r}")
    return normalized


def source_exists(source_root: Path | None, relative: str) -> bool:
    if source_root is None:
        return True
    try:
        safe = strict_relative_path(relative)
    except UnsafePathError:
        return False
    return (source_root / safe).is_file()


def normalize_target(value: str) -> str:
    return strict_relative_path(value, allow_res_prefix=True)


def parse_string_value(raw: str) -> str:
    try:
        value = ast.literal_eval(raw)
    except (SyntaxError, ValueError) as exc:
        raise MetadataError(f"invalid quoted string: {raw!r}") from exc
    if not isinstance(value, str):
        raise MetadataError(f"expected string, found {type(value).__name__}")
    return value


def parse_string_list(raw: str) -> list[str]:
    expression = raw.strip()
    if expression.startswith("PackedStringArray(") and expression.endswith(")"):
        expression = "[" + expression[len("PackedStringArray(") : -1] + "]"
    try:
        value = ast.literal_eval(expression)
    except (SyntaxError, ValueError) as exc:
        raise MetadataError(f"invalid string list: {raw!r}") from exc
    if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) for item in value):
        raise MetadataError("dest_files must be a string list")
    return list(value)


def parse_glb_import_metadata(text: str) -> dict[str, Any]:
    section: str | None = None
    values: dict[tuple[str, str], Any] = {}
    relevant = {("remap", "path"), ("deps", "source_file"), ("deps", "dest_files")}
    seen_sections: set[str] = set()
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        section_match = SECTION_RE.fullmatch(line)
        if section_match:
            section = section_match.group(1)
            seen_sections.add(section)
            continue
        if section is None:
            raise MetadataError(f"assignment outside section at line {line_number}")
        assignment = ASSIGNMENT_RE.fullmatch(line)
        if assignment is None:
            if section in {"remap", "deps"}:
                raise MetadataError(f"malformed assignment at line {line_number}")
            continue
        key, encoded = assignment.groups()
        identity = (section, key)
        if identity not in relevant:
            continue
        if identity in values:
            raise MetadataError(f"duplicate {section}.{key}")
        if identity == ("deps", "dest_files"):
            values[identity] = parse_string_list(encoded)
        else:
            values[identity] = parse_string_value(encoded)
    if "remap" not in seen_sections or "deps" not in seen_sections:
        raise MetadataError("required [remap] and [deps] sections are missing")
    return {
        "path": values.get(("remap", "path")),
        "source_file": values.get(("deps", "source_file")),
        "dest_files": values.get(("deps", "dest_files"), []),
    }


def inventory_apk(apk: Path, source_root: Path | None) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    raw_paths: set[str] = set()
    remap_payloads: dict[str, str] = {}
    glb_import_payloads: dict[str, str] = {}
    unsafe_apk_paths: list[str] = []
    case_collisions: list[list[str]] = []

    with zipfile.ZipFile(apk) as archive:
        file_infos = [info for info in archive.infolist() if not info.is_dir()]
        counts = Counter(info.filename for info in file_infos)
        duplicate_apk_paths = sorted(path for path, count in counts.items() if count > 1)
        casefolded: dict[str, str] = {}
        for info in file_infos:
            if not info.filename.startswith(ASSET_PREFIX):
                continue
            encoded_relative = info.filename[len(ASSET_PREFIX) :]
            try:
                relative = strict_relative_path(encoded_relative)
            except UnsafePathError:
                unsafe_apk_paths.append(info.filename)
                continue
            prior = casefolded.get(relative.casefold())
            if prior is not None and prior != relative:
                pair = sorted([prior, relative])
                if pair not in case_collisions:
                    case_collisions.append(pair)
            else:
                casefolded[relative.casefold()] = relative
            raw_paths.add(relative)
            entries.append(
                {
                    "apk_path": info.filename,
                    "path": relative,
                    "compressed_bytes": info.compress_size,
                    "uncompressed_bytes": info.file_size,
                    "crc32": f"{info.CRC:08x}",
                    "compression": info.compress_type,
                }
            )
            if info.file_size > MAX_METADATA_BYTES:
                continue
            if relative.endswith(".remap"):
                remap_payloads[relative] = archive.read(info).decode("utf-8", errors="replace")
            elif relative.endswith(".glb.import"):
                glb_import_payloads[relative] = archive.read(info).decode("utf-8", errors="replace")

    logical_paths = set(raw_paths)
    aliases: list[dict[str, Any]] = []
    remap_failures: list[dict[str, Any]] = []
    glb_import_rejections: list[dict[str, Any]] = []
    archive_safe = not duplicate_apk_paths and not unsafe_apk_paths and not case_collisions

    if archive_safe:
        for actual in sorted(raw_paths):
            suffix = PurePosixPath(actual).suffix.lower()
            logical_suffix = COMPILED_ALIASES.get(suffix)
            if logical_suffix:
                logical = str(PurePosixPath(actual).with_suffix(logical_suffix))
                if source_exists(source_root, logical):
                    logical_paths.add(logical)
                    aliases.append(
                        {
                            "logical_path": logical,
                            "packaged_path": actual,
                            "reason": f"Godot compiled {logical_suffix} resource",
                            "target_verified": True,
                        }
                    )

        for remap_path, text in sorted(remap_payloads.items()):
            logical = remap_path[: -len(".remap")]
            match = REMAP_PATH_RE.search(text)
            try:
                target = normalize_target(match.group(1)) if match else None
            except UnsafePathError:
                target = None
            target_verified = bool(target and target in raw_paths)
            source_verified = source_exists(source_root, logical)
            if target_verified and source_verified:
                logical_paths.add(logical)
                aliases.append(
                    {
                        "logical_path": logical,
                        "packaged_path": remap_path,
                        "remap_target": target,
                        "reason": "Godot imported-resource remap",
                        "source_verified": source_verified,
                        "target_verified": target_verified,
                    }
                )
            else:
                remap_failures.append(
                    {
                        "remap_path": remap_path,
                        "logical_path": logical,
                        "remap_target": target,
                        "source_verified": source_verified,
                        "target_verified": target_verified,
                    }
                )

        for sidecar_path, text in sorted(glb_import_payloads.items()):
            logical = sidecar_path[: -len(".import")]
            failures: list[str] = []
            source_file: str | None = None
            declared_targets: list[str] = []
            verified_targets: list[str] = []
            source_verified = False
            metadata: dict[str, Any] | None = None

            if not logical.endswith(".glb"):
                failures.append("invalid_logical_extension")
            try:
                logical = strict_relative_path(logical)
            except UnsafePathError:
                failures.append("unsafe_sidecar_logical_path")

            try:
                metadata = parse_glb_import_metadata(text)
            except MetadataError:
                failures.append("malformed_sidecar")

            if source_root is None:
                failures.append("source_root_required")
            elif not failures or failures == ["malformed_sidecar"]:
                source_verified = source_exists(source_root, logical)
                if not source_verified:
                    failures.append("missing_source_file")

            path_target: str | None = None
            dest_targets: list[str] = []
            if metadata is not None:
                explicit_source = metadata.get("source_file")
                if explicit_source is not None:
                    try:
                        source_file = normalize_target(explicit_source)
                    except UnsafePathError:
                        failures.append("unsafe_source_file")
                    else:
                        if source_file != logical:
                            failures.append("source_file_mismatch")
                else:
                    source_file = logical

                encoded_path = metadata.get("path")
                if encoded_path is not None:
                    try:
                        path_target = normalize_target(encoded_path)
                    except UnsafePathError:
                        failures.append("unsafe_import_target")
                for encoded_target in metadata.get("dest_files", []):
                    try:
                        dest_targets.append(normalize_target(encoded_target))
                    except UnsafePathError:
                        failures.append("unsafe_import_target")

                if path_target is not None and dest_targets and path_target not in dest_targets:
                    failures.append("conflicting_import_targets")
                candidates = ([path_target] if path_target is not None else []) + dest_targets
                declared_targets = sorted(set(candidates))
                if not declared_targets:
                    failures.append("missing_declared_import_target")
                for target in declared_targets:
                    if not target.startswith(".godot/imported/"):
                        failures.append("target_outside_godot_imported")
                        continue
                    if target not in raw_paths:
                        failures.append("missing_import_target")
                    else:
                        verified_targets.append(target)
                if declared_targets and not any(target.endswith(".scn") for target in declared_targets):
                    failures.append("missing_packed_scene_target")

            failures = sorted(set(failures))
            record = {
                "logical_path": logical if isinstance(logical, str) else None,
                "sidecar_path": sidecar_path,
                "source_file": source_file,
                "declared_import_targets": declared_targets,
                "verified_import_targets": sorted(verified_targets),
                "source_verified": source_verified,
                "targets_verified": bool(declared_targets) and len(verified_targets) == len(declared_targets),
                "reason": "Godot GLB import sidecar with verified imported PackedScene target",
                "validation_failures": failures,
            }
            if failures:
                glb_import_rejections.append(record)
                continue
            primary_target = path_target or declared_targets[0]
            alias = dict(record)
            alias.update(
                {
                    "packaged_path": sidecar_path,
                    "remap_target": primary_target,
                    "target_verified": True,
                }
            )
            logical_paths.add(logical)
            aliases.append(alias)
    else:
        rejected_sidecars: set[str] = set()
        for path in unsafe_apk_paths:
            if path.startswith(ASSET_PREFIX) and path.endswith(".glb.import"):
                sidecar_path = path[len(ASSET_PREFIX) :]
                rejected_sidecars.add(sidecar_path)
                glb_import_rejections.append(
                    {
                        "logical_path": None,
                        "sidecar_path": sidecar_path,
                        "source_file": None,
                        "declared_import_targets": [],
                        "verified_import_targets": [],
                        "source_verified": False,
                        "targets_verified": False,
                        "reason": "Godot GLB import sidecar rejected before parsing",
                        "validation_failures": ["unsafe_apk_path"],
                    }
                )
        for sidecar_path in sorted(glb_import_payloads):
            if sidecar_path in rejected_sidecars:
                continue
            full_path = ASSET_PREFIX + sidecar_path
            validation_failures: list[str] = []
            if full_path in duplicate_apk_paths:
                validation_failures.append("duplicate_apk_path")
            if any(sidecar_path in collision for collision in case_collisions):
                validation_failures.append("case_collision")
            if not validation_failures:
                validation_failures.append("archive_integrity_failure")
            glb_import_rejections.append(
                {
                    "logical_path": sidecar_path[: -len(".import")],
                    "sidecar_path": sidecar_path,
                    "source_file": None,
                    "declared_import_targets": [],
                    "verified_import_targets": [],
                    "source_verified": False,
                    "targets_verified": False,
                    "reason": "Godot GLB import sidecar rejected before parsing",
                    "validation_failures": validation_failures,
                }
            )

    glb_aliases = [item for item in aliases if str(item.get("logical_path", "")).endswith(".glb") and "sidecar_path" in item]
    failures_present = bool(remap_failures or glb_import_rejections or duplicate_apk_paths or unsafe_apk_paths or case_collisions)
    value = {
        "passed": bool(entries) and not failures_present,
        "packaging": "godot-4.3-default-android-apk-assets",
        "pck_required": False,
        "apk": str(apk.resolve()),
        "apk_asset_prefix": ASSET_PREFIX,
        "raw_asset_count": len(raw_paths),
        "logical_file_count": len(logical_paths),
        "files": sorted(logical_paths),
        "raw_files": sorted(raw_paths),
        "entries": sorted(entries, key=lambda item: item["path"]),
        "logical_aliases": sorted(aliases, key=lambda item: (item["logical_path"], item["packaged_path"])),
        "duplicate_apk_paths": duplicate_apk_paths,
        "unsafe_apk_paths": sorted(set(unsafe_apk_paths)),
        "case_collisions": sorted(case_collisions),
        "remap_count": len(remap_payloads),
        "remap_targets_verified": not remap_failures and not glb_import_rejections,
        "remap_failures": remap_failures,
        "glb_import_sidecar_count": len(glb_import_payloads),
        "validated_glb_alias_count": len(glb_aliases),
        "rejected_glb_sidecar_count": len(glb_import_rejections),
        "glb_import_rejections": glb_import_rejections,
        "source_root": str(source_root.resolve()) if source_root else None,
        "source_authority": "Godot 4.3 Android save_apk_file stores exported res:// paths beneath APK assets/",
        "compatibility_note": "The optional compatibility output preserves the existing inspector input schema; it is not evidence of a PCK payload.",
    }
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--compat-output")
    parser.add_argument("--source-root")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    apk = Path(args.apk)
    if not apk.is_file() or apk.stat().st_size == 0:
        raise SystemExit(f"APK missing or empty: {apk}")
    source_root = Path(args.source_root) if args.source_root else None
    if source_root is not None and not source_root.is_dir():
        raise SystemExit(f"source root missing: {source_root}")
    value = inventory_apk(apk, source_root)
    write_json(Path(args.output), value)
    if args.compat_output:
        write_json(Path(args.compat_output), value)
    return 0 if value["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
