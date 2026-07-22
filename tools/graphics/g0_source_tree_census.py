#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

TEXT_EXTENSIONS = {
    ".cfg", ".gd", ".gdshader", ".godot", ".html", ".ini", ".json", ".md",
    ".py", ".shader", ".sh", ".svg", ".toml", ".tscn", ".tres", ".txt",
    ".xml", ".yaml", ".yml",
}
TEXTURE_EXTENSIONS = {".bmp", ".dds", ".exr", ".hdr", ".jpeg", ".jpg", ".ktx", ".png", ".svg", ".tga", ".webp"}
FONT_EXTENSIONS = {".otf", ".ttf", ".woff", ".woff2"}
SCRIPT_EXTENSIONS = {".cs", ".gd", ".py", ".sh"}
SCENE_EXTENSIONS = {".scn", ".tscn"}
RESOURCE_EXTENSIONS = {".res", ".tres"}
SHADER_EXTENSIONS = {".gdshader", ".shader"}
AUTHORIZED_G0_PREFIXES = (
    ".ai/",
    ".github/workflows/bahrain-brick-graphics-g0.yml",
    "authority/bahrain_brick_graphics_upgrade_v1.json",
    "docs/graphics/",
    "reports/graphics/g0/",
    "tests/graphics/",
    "tools/graphics/",
)
RES_REFERENCE = re.compile(rb"res://[A-Za-z0-9_@+./\-]+")
EXIT_TREE_FUNCTION = re.compile(rb"(?m)^\s*func\s+_exit_tree\s*\(")


def run_git(repo: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed with {result.returncode}: "
            f"{result.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return result.stdout


def resolve_commit(repo: Path, ref: str) -> str:
    return run_git(repo, "rev-parse", f"{ref}^{{commit}}").decode().strip()


def commit_exists(repo: Path, ref: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{ref}^{{commit}}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def list_tree(repo: Path, commit: str) -> list[dict[str, Any]]:
    raw = run_git(repo, "ls-tree", "-r", "-l", "-z", commit)
    entries: list[dict[str, Any]] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, object_type, blob_sha, raw_size = metadata.decode("ascii").split()
        if object_type != "blob":
            continue
        path = raw_path.decode("utf-8", errors="surrogateescape")
        entries.append(
            {
                "path": path,
                "mode": mode,
                "git_type": object_type,
                "blob_sha": blob_sha,
                "bytes": int(raw_size),
            }
        )
    return sorted(entries, key=lambda item: item["path"].encode("utf-8", errors="surrogateescape"))


def blob_bytes(repo: Path, blob_sha: str) -> bytes:
    return run_git(repo, "cat-file", "blob", blob_sha)


def is_probably_text(path: str, data: bytes) -> bool:
    if Path(path).suffix.lower() in TEXT_EXTENSIONS:
        return True
    if b"\0" in data[:4096]:
        return False
    try:
        data[:4096].decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def classify_file(path: str, data: bytes) -> list[str]:
    lower = path.lower()
    suffix = Path(lower).suffix
    categories: set[str] = {"project_file"}
    if suffix in SCENE_EXTENSIONS:
        categories.add("scene")
    if suffix in SCRIPT_EXTENSIONS:
        categories.add("script")
    if suffix in RESOURCE_EXTENSIONS:
        categories.add("resource")
    if suffix in SHADER_EXTENSIONS:
        categories.add("shader")
    if suffix in TEXTURE_EXTENSIONS:
        categories.add("texture")
    if suffix in FONT_EXTENSIONS:
        categories.add("font")
    if lower.endswith(".import"):
        categories.add("source_controlled_import")
    if lower.startswith(".godot/"):
        categories.add("godot_dependency")
    if path == "export_presets.cfg":
        categories.update({"android_export_preset", "configuration"})
    if path == "project.godot":
        categories.update({"godot_project", "configuration"})
    if "material" in lower or b"Material" in data[:65536]:
        categories.add("material")
    if "environment" in lower or b"Environment" in data[:65536]:
        categories.add("environment_resource")
    path_ui = any(part in {"ui", "hud", "menu", "menus"} for part in Path(lower).parts)
    if suffix in SCENE_EXTENSIONS and (path_ui or b'type="Control"' in data or b'type="CanvasLayer"' in data):
        categories.add("ui_scene")
    if suffix in SCRIPT_EXTENSIONS and (path_ui or b"extends Control" in data[:4096] or b"extends CanvasLayer" in data[:4096]):
        categories.add("ui_script")
    return sorted(categories)


def parse_project_settings(data: bytes) -> tuple[dict[str, str], dict[str, str]]:
    text = data.decode("utf-8", errors="replace")
    section = ""
    autoloads: dict[str, str] = {}
    renderer: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"')
        if section == "autoload":
            autoloads[key] = value.removeprefix("*")
        elif section == "rendering":
            renderer[key] = value
    return autoloads, renderer


def build_census(repo: Path, ref: str) -> dict[str, Any]:
    commit = resolve_commit(repo, ref)
    entries = list_tree(repo, commit)
    category_paths: dict[str, list[str]] = defaultdict(list)
    references: dict[str, set[str]] = defaultdict(set)
    files: list[dict[str, Any]] = []
    autoloads: dict[str, str] = {}
    renderer_settings: dict[str, str] = {}
    tracked_paths = {entry["path"] for entry in entries}
    aggregate = hashlib.sha256()

    for entry in entries:
        data = blob_bytes(repo, entry["blob_sha"])
        actual_size = len(data)
        if actual_size != entry["bytes"]:
            raise AssertionError(f"git size mismatch for {entry['path']}: {entry['bytes']} != {actual_size}")
        sha256 = hashlib.sha256(data).hexdigest()
        categories = classify_file(entry["path"], data)
        for category in categories:
            category_paths[category].append(entry["path"])
        if entry["path"] == "project.godot":
            autoloads, renderer_settings = parse_project_settings(data)
        if is_probably_text(entry["path"], data):
            for raw_reference in RES_REFERENCE.findall(data):
                reference = raw_reference.decode("utf-8", errors="replace").rstrip(".,;:)]}\"'")
                references[reference].add(entry["path"])
        aggregate.update(entry["path"].encode("utf-8", errors="surrogateescape"))
        aggregate.update(b"\0")
        aggregate.update(sha256.encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(str(actual_size).encode("ascii"))
        aggregate.update(b"\n")
        files.append({**entry, "sha256": sha256, "categories": categories})

    imported_references = []
    for reference in sorted(references):
        logical_path = reference.removeprefix("res://")
        imported_references.append(
            {
                "reference": reference,
                "logical_path": logical_path,
                "exists_in_tree": logical_path in tracked_paths,
                "referrers": sorted(references[reference]),
            }
        )

    return {
        "schema_version": 1,
        "commit": commit,
        "tree_sha": run_git(repo, "rev-parse", f"{commit}^{{tree}}").decode().strip(),
        "file_count": len(files),
        "aggregate_bytes": sum(item["bytes"] for item in files),
        "aggregate_sha256": aggregate.hexdigest(),
        "files": files,
        "category_counts": {key: len(value) for key, value in sorted(category_paths.items())},
        "category_paths": {key: sorted(value) for key, value in sorted(category_paths.items())},
        "autoloads": dict(sorted(autoloads.items())),
        "renderer_settings": dict(sorted(renderer_settings.items())),
        "imported_resource_references": imported_references,
        "source_controlled_import_count": len(category_paths.get("source_controlled_import", [])),
        "godot_dependency_count": len(category_paths.get("godot_dependency", [])),
        "godot_dependencies_evidence_available": bool(category_paths.get("godot_dependency")),
    }


def is_authorized_g0_path(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in AUTHORIZED_G0_PREFIXES)


def compare_censuses(frozen: dict[str, Any], graphics: dict[str, Any]) -> dict[str, Any]:
    frozen_files = {item["path"]: item for item in frozen["files"]}
    graphics_files = {item["path"]: item for item in graphics["files"]}
    added = sorted(set(graphics_files) - set(frozen_files))
    removed = sorted(set(frozen_files) - set(graphics_files))
    modified = sorted(
        path
        for path in set(frozen_files) & set(graphics_files)
        if (frozen_files[path]["sha256"], frozen_files[path]["mode"])
        != (graphics_files[path]["sha256"], graphics_files[path]["mode"])
    )
    unauthorized_added = [path for path in added if not is_authorized_g0_path(path)]
    unauthorized_modified = [path for path in modified if not is_authorized_g0_path(path)]
    unauthorized_removed = [path for path in removed if not is_authorized_g0_path(path)]
    return {
        "schema_version": 1,
        "frozen_commit": frozen["commit"],
        "graphics_commit": graphics["commit"],
        "frozen_file_count": frozen["file_count"],
        "graphics_file_count": graphics["file_count"],
        "frozen_aggregate_bytes": frozen["aggregate_bytes"],
        "graphics_aggregate_bytes": graphics["aggregate_bytes"],
        "added_paths": added,
        "removed_paths": removed,
        "modified_paths": modified,
        "added_details": [graphics_files[path] for path in added],
        "removed_details": [frozen_files[path] for path in removed],
        "modified_details": [
            {"path": path, "frozen": frozen_files[path], "graphics": graphics_files[path]}
            for path in modified
        ],
        "authorized_prefixes": list(AUTHORIZED_G0_PREFIXES),
        "unauthorized_added_paths": unauthorized_added,
        "unauthorized_removed_paths": unauthorized_removed,
        "unauthorized_modified_paths": unauthorized_modified,
        "differences_authorized": not (unauthorized_added or unauthorized_removed or unauthorized_modified),
        "existing_frozen_paths_unchanged": not removed and not modified,
    }


def inspect_world_at_commit(repo: Path, commit: str) -> dict[str, Any]:
    path = "scripts/world.gd"
    result = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{commit}:{path}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        return {"commit": commit, "path": path, "exists": False}
    blob_sha = run_git(repo, "rev-parse", f"{commit}:{path}").decode().strip()
    data = blob_bytes(repo, blob_sha)
    return {
        "commit": commit,
        "path": path,
        "exists": True,
        "blob_sha": blob_sha,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "exit_tree_token_exists": b"_exit_tree" in data,
        "exit_tree_function_exists": bool(EXIT_TREE_FUNCTION.search(data)),
    }


def find_design_references(repo: Path, commit: str) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    for entry in list_tree(repo, commit):
        if Path(entry["path"]).suffix.lower() not in TEXT_EXTENSIONS:
            continue
        data = blob_bytes(repo, entry["blob_sha"])
        if b"_exit_tree" not in data and b"world.gd" not in data:
            continue
        text = data.decode("utf-8", errors="replace")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if "_exit_tree" in line or "world.gd::_exit_tree" in line:
                references.append({"path": entry["path"], "line": line_number, "text": line.strip()})
    return references


def adjudicate_world_gd(repo: Path, frozen_ref: str, authority_commits: Iterable[dict[str, str] | str]) -> dict[str, Any]:
    frozen_commit = resolve_commit(repo, frozen_ref)
    frozen = inspect_world_at_commit(repo, frozen_commit)
    known_authorities: list[dict[str, Any]] = []
    for item in authority_commits:
        if isinstance(item, str):
            authority_id, ref = item, item
        else:
            authority_id, ref = item.get("id", item.get("commit", "unknown")), item["commit"]
        if not commit_exists(repo, ref):
            known_authorities.append({"id": authority_id, "commit": ref, "commit_available": False})
            continue
        commit = resolve_commit(repo, ref)
        known_authorities.append({"id": authority_id, "commit_available": True, **inspect_world_at_commit(repo, commit)})
    symbol_authorities = [
        item for item in known_authorities
        if item.get("exists") and item.get("exit_tree_function_exists")
    ]
    if frozen.get("exit_tree_function_exists"):
        source_classification = "EXACT_FROZEN_GIT_TREE"
        symbol_claim = "PRESENT_IN_EXACT_FROZEN_FILE"
    elif symbol_authorities:
        source_classification = "OTHER_KNOWN_GIT_AUTHORITY"
        symbol_claim = "NOT_PRESENT_IN_EXACT_FROZEN_FILE"
    else:
        source_classification = "UNRESOLVED_RECONSTRUCTED_OR_HISTORICAL_SOURCE_REFERENCE"
        symbol_claim = "NOT_PRESENT_IN_EXACT_FROZEN_FILE"
    return {
        "schema_version": 1,
        "frozen_tree": frozen,
        "design_references": find_design_references(repo, frozen_commit),
        "known_authorities": known_authorities,
        "authorities_containing_exit_tree_function": symbol_authorities,
        "symbol_source_classification": source_classification,
        "symbol_claim": symbol_claim,
        "design_source_inconsistency": bool(frozen.get("exists") and not frozen.get("exit_tree_function_exists")),
        "resulting_protection_rule": "BYTE_PROTECT_EXACT_FROZEN_WORLD_GD" if frozen.get("exists") else "PROTECT_PATH_IF_MATERIALIZED",
        "protection_sha256": frozen.get("sha256"),
        "protection_blob_sha": frozen.get("blob_sha"),
        "rule_explanation": (
            "Protect scripts/world.gd byte-for-byte at the exact frozen PR #59 Git object. "
            "Do not claim _exit_tree exists unless later evidence identifies a separate authoritative source."
        ),
    }


def known_authorities_from_contract(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    keys = (
        "base_authority",
        "frozen_premium_authority",
        "frozen_controls_authority",
        "authority_correction_starting_head",
    )
    return [{"id": key, "commit": payload[key]} for key in keys if payload.get(key)]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate exact Git-object G0 source censuses and world.gd adjudication.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--frozen", required=True)
    parser.add_argument("--graphics", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--composite-authority", type=Path)
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    output = args.output_root.resolve()
    frozen = build_census(repo, args.frozen)
    graphics = build_census(repo, args.graphics)
    comparison = compare_censuses(frozen, graphics)
    world = adjudicate_world_gd(repo, args.frozen, known_authorities_from_contract(args.composite_authority))

    write_json(output / "frozen_source_tree_census.json", frozen)
    write_json(output / "graphics_branch_source_tree_census.json", graphics)
    write_json(output / "source_tree_comparison.json", comparison)
    write_json(output / "world_gd_adjudication.json", world)

    if not comparison["differences_authorized"] or not comparison["existing_frozen_paths_unchanged"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
