#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA_RELATIVE = Path("asset_lab/manifests/schema/asset-manifest.schema.json")
ASSETS_RELATIVE = Path("asset_lab/manifests/assets")
VALID_EXAMPLES_RELATIVE = Path("asset_lab/manifests/examples/valid")
INVALID_EXAMPLES_RELATIVE = Path("asset_lab/manifests/examples/invalid")
EXPECTED_LOD_LEVELS = {0, 1, 2}
TEXTURE_ROLES = {"albedo", "normal", "orm", "emissive", "opacity", "mask"}


def _load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _schema_validator(root: Path):
    schema_path = root / SCHEMA_RELATIVE
    if not schema_path.exists():
        return None, None, "SCHEMA_MISSING", "Authoritative manifest schema is missing."
    try:
        schema = _load_json(schema_path)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return None, None, "INVALID_JSON", str(exc)
    try:
        import jsonschema
    except ImportError:
        return schema, None, "VALIDATOR_DEPENDENCY_MISSING", "Install tools/asset_lab/requirements-manifest-validation.txt."
    try:
        validator_cls = jsonschema.validators.validator_for(schema)
        validator_cls.check_schema(schema)
        return schema, validator_cls(schema), None, None
    except Exception as exc:
        return schema, None, "SCHEMA_INVALID", str(exc)


def semantic_failures(manifest: dict[str, Any]) -> list[dict[str, object]]:
    failures: list[dict[str, object]] = []
    category = manifest.get("category")
    family = manifest.get("family")
    variant = manifest.get("variant")
    serial = manifest.get("serial")
    asset_id = manifest.get("asset_id")
    if isinstance(category, str) and isinstance(family, str) and isinstance(variant, str) and isinstance(serial, int) and not isinstance(serial, bool):
        expected = f"bb_{category}_{family}_{variant}_{serial:03d}"
        if asset_id != expected:
            failures.append({"json_path": ["asset_id"], "message": f"must equal derived ID {expected!r}"})

    if isinstance(asset_id, str):
        for field, extension in (("source_path", ".blend"), ("export_path", ".glb")):
            value = manifest.get(field)
            if isinstance(value, str):
                path = Path(value)
                if path.suffix.lower() != extension or path.stem != asset_id:
                    failures.append({"json_path": [field], "message": f"basename must be {asset_id}{extension}"})

        lods = manifest.get("lods")
        if isinstance(lods, list):
            level_sequence = [item.get("level") for item in lods if isinstance(item, dict)]
            levels = set(level_sequence)
            if levels != EXPECTED_LOD_LEVELS or level_sequence != [0, 1, 2]:
                failures.append({"json_path": ["lods"], "message": "must contain LOD levels 0, 1, and 2 exactly once and in order"})
            seen_triangles: list[int] = []
            previous_end: float | None = None
            for index, item in enumerate(lods):
                if not isinstance(item, dict):
                    continue
                level = item.get("level")
                path = item.get("path")
                if isinstance(level, int) and isinstance(path, str):
                    expected_stem = f"{asset_id}_lod{level}"
                    if Path(path).suffix.lower() != ".glb" or Path(path).stem != expected_stem:
                        failures.append({"json_path": ["lods", index, "path"], "message": f"basename must be {expected_stem}.glb"})
                triangles = item.get("triangle_count")
                if isinstance(triangles, int):
                    seen_triangles.append(triangles)
                start = item.get("distance_start_m")
                end = item.get("distance_end_m")
                if level == 0 and start != 0:
                    failures.append({"json_path": ["lods", index, "distance_start_m"], "message": "LOD0 must start at 0 m"})
                if level == 2 and end is not None:
                    failures.append({"json_path": ["lods", index, "distance_end_m"], "message": "LOD2 must have no finite end distance"})
                if isinstance(start, (int, float)) and previous_end is not None and start != previous_end:
                    failures.append({"json_path": ["lods", index, "distance_start_m"], "message": "must equal previous LOD distance_end_m"})
                if isinstance(end, (int, float)):
                    previous_end = float(end)
                elif end is None:
                    previous_end = None
            if seen_triangles and any(a < b for a, b in zip(seen_triangles, seen_triangles[1:])):
                failures.append({"json_path": ["lods"], "message": "triangle counts must not increase at lower-detail LODs"})

        collision = manifest.get("collision")
        if isinstance(collision, dict):
            ctype, path = collision.get("type"), collision.get("path")
            if ctype == "none" and path is not None:
                failures.append({"json_path": ["collision", "path"], "message": "must be null when collision type is none"})
            if ctype != "none":
                expected_stem = f"{asset_id}_col"
                if not isinstance(path, str) or Path(path).suffix.lower() != ".glb" or Path(path).stem != expected_stem:
                    failures.append({"json_path": ["collision", "path"], "message": f"basename must be {expected_stem}.glb"})

        navigation = manifest.get("navigation")
        if isinstance(navigation, dict):
            behavior, path = navigation.get("behavior"), navigation.get("path")
            if behavior == "none" and path is not None:
                failures.append({"json_path": ["navigation", "path"], "message": "must be null when navigation behavior is none"})
            if behavior != "none":
                expected_stem = f"{asset_id}_nav"
                if not isinstance(path, str) or Path(path).suffix.lower() != ".glb" or Path(path).stem != expected_stem:
                    failures.append({"json_path": ["navigation", "path"], "message": f"basename must be {expected_stem}.glb"})

    textures = manifest.get("textures")
    if isinstance(textures, list):
        texture_keys: set[tuple[str, str]] = set()
        for index, texture in enumerate(textures):
            if not isinstance(texture, dict):
                continue
            texture_id = texture.get("texture_id")
            role = texture.get("role")
            path = texture.get("path")
            if isinstance(texture_id, str) and isinstance(role, str):
                key = (texture_id, role)
                if key in texture_keys:
                    failures.append({"json_path": ["textures", index], "message": "duplicate texture_id/role pair"})
                texture_keys.add(key)
                if role in TEXTURE_ROLES and isinstance(path, str):
                    expected_stem = f"{texture_id}_{role}"
                    if Path(path).stem != expected_stem:
                        failures.append({"json_path": ["textures", index, "path"], "message": f"basename must start with {expected_stem}"})

    materials = manifest.get("materials")
    if isinstance(materials, list) and len(materials) != len(set(x for x in materials if isinstance(x, str))):
        failures.append({"json_path": ["materials"], "message": "material IDs must be unique within a manifest"})

    return failures


def validate_manifest_file(root: Path, manifest_path: Path) -> dict[str, object]:
    root = root.resolve()
    path = manifest_path if manifest_path.is_absolute() else root / manifest_path
    _, validator, state, detail = _schema_validator(root)
    if state:
        return {"passed": False, "state": state, "path": path.as_posix(), "failures": [], "detail": detail}
    try:
        manifest = _load_json(path)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return {"passed": False, "state": "INVALID_JSON", "path": path.as_posix(), "failures": [], "detail": str(exc)}
    if not isinstance(manifest, dict):
        return {"passed": False, "state": "MANIFEST_INVALID", "path": path.as_posix(), "failures": [{"json_path": [], "message": "root must be an object"}]}
    failures: list[dict[str, object]] = []
    assert validator is not None
    for error in sorted(validator.iter_errors(manifest), key=lambda e: list(e.absolute_path)):
        failures.append({"json_path": list(error.absolute_path), "message": error.message})
    if not failures:
        failures.extend(semantic_failures(manifest))
    return {"passed": not failures, "state": "VALIDATED" if not failures else "MANIFEST_INVALID", "path": path.relative_to(root).as_posix() if path.is_relative_to(root) else path.as_posix(), "asset_id": manifest.get("asset_id"), "failures": failures}


def validate_manifest_tree(root: Path, *, allow_empty: bool = False) -> dict[str, object]:
    root = root.resolve()
    schema_path = root / SCHEMA_RELATIVE
    assets_dir = root / ASSETS_RELATIVE
    manifests = sorted(assets_dir.rglob("*.json")) if assets_dir.exists() else []
    if not schema_path.exists():
        if not manifests and allow_empty:
            return {"passed": True, "state": "EMPTY_BOOTSTRAP", "schema": SCHEMA_RELATIVE.as_posix(), "manifest_count": 0, "failures": []}
        return {"passed": False, "state": "SCHEMA_MISSING", "schema": SCHEMA_RELATIVE.as_posix(), "manifest_count": len(manifests), "failures": []}
    _, validator, state, detail = _schema_validator(root)
    if state:
        return {"passed": False, "state": state, "schema": SCHEMA_RELATIVE.as_posix(), "manifest_count": len(manifests), "failures": [], "detail": detail}
    assert validator is not None
    failures: list[dict[str, object]] = []
    seen_ids: dict[str, str] = {}
    fatal_state: str | None = None
    for path in manifests:
        result = validate_manifest_file(root, path)
        if not result["passed"]:
            if result.get("state") == "INVALID_JSON":
                fatal_state = "INVALID_JSON"
            failures.append({"path": path.relative_to(root).as_posix(), "state": result.get("state"), "failures": result["failures"], "detail": result.get("detail")})
            continue
        asset_id = result.get("asset_id")
        if isinstance(asset_id, str):
            prior = seen_ids.get(asset_id)
            if prior:
                failures.append({"path": path.relative_to(root).as_posix(), "failures": [{"json_path": ["asset_id"], "message": f"duplicate asset_id also used by {prior}"}]})
            else:
                seen_ids[asset_id] = path.relative_to(root).as_posix()
    return {"passed": not failures, "state": "VALIDATED" if not failures else (fatal_state or "MANIFEST_INVALID"), "schema": SCHEMA_RELATIVE.as_posix(), "manifest_count": len(manifests), "failures": failures}


def validate_examples(root: Path) -> dict[str, object]:
    root = root.resolve()
    valid_paths = sorted((root / VALID_EXAMPLES_RELATIVE).glob("*.json"))
    invalid_paths = sorted((root / INVALID_EXAMPLES_RELATIVE).glob("*.json"))
    valid_results = [validate_manifest_file(root, path) for path in valid_paths]
    invalid_results = [validate_manifest_file(root, path) for path in invalid_paths]
    unexpected_valid_failures = [r for r in valid_results if not r["passed"]]
    unexpected_invalid_passes = [r for r in invalid_results if r["passed"]]
    return {"passed": not unexpected_valid_failures and not unexpected_invalid_passes and bool(valid_results) and bool(invalid_results), "valid_examples": valid_results, "invalid_examples": invalid_results, "unexpected_valid_failures": unexpected_valid_failures, "unexpected_invalid_passes": unexpected_invalid_passes}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Bahrain Brick asset manifests against the authoritative JSON schema and semantic naming contract.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--allow-empty", action="store_true")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--examples", action="store_true")
    args = parser.parse_args()
    report = validate_manifest_file(args.root, args.manifest) if args.manifest else validate_examples(args.root) if args.examples else validate_manifest_tree(args.root, allow_empty=args.allow_empty)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
