#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

SCHEMA_RELATIVE = Path("asset_lab/manifests/schema/asset-manifest.schema.json")
ASSETS_RELATIVE = Path("asset_lab/manifests/assets")


def _load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_manifest_tree(root: Path, *, allow_empty: bool = False) -> dict[str, object]:
    root = root.resolve()
    schema_path = root / SCHEMA_RELATIVE
    assets_dir = root / ASSETS_RELATIVE
    manifests = sorted(assets_dir.rglob("*.json")) if assets_dir.exists() else []

    if not schema_path.exists():
        if not manifests and allow_empty:
            return {
                "passed": True,
                "state": "EMPTY_BOOTSTRAP",
                "schema": SCHEMA_RELATIVE.as_posix(),
                "manifest_count": 0,
                "detail": "Phase 2 bootstrap: no schema or manifests exist yet; Phase 3 must add both before manifests are accepted.",
            }
        return {
            "passed": False,
            "state": "SCHEMA_MISSING",
            "schema": SCHEMA_RELATIVE.as_posix(),
            "manifest_count": len(manifests),
            "detail": "Manifest files may not exist without the authoritative schema.",
        }

    try:
        schema = _load_json(schema_path)
        loaded_manifests = [(path, _load_json(path)) for path in manifests]
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return {
            "passed": False,
            "state": "INVALID_JSON",
            "schema": SCHEMA_RELATIVE.as_posix(),
            "manifest_count": len(manifests),
            "detail": str(exc),
        }

    try:
        import jsonschema  # type: ignore
    except ImportError:
        if manifests:
            return {
                "passed": False,
                "state": "VALIDATOR_DEPENDENCY_MISSING",
                "schema": SCHEMA_RELATIVE.as_posix(),
                "manifest_count": len(manifests),
                "detail": "Install the pinned jsonschema dependency before accepting manifests.",
            }
        return {
            "passed": True,
            "state": "SCHEMA_JSON_ONLY",
            "schema": SCHEMA_RELATIVE.as_posix(),
            "manifest_count": 0,
            "detail": "Schema JSON parses; no manifests exist. Phase 3 must pin jsonschema before semantic manifest validation.",
        }

    try:
        validator_cls = jsonschema.validators.validator_for(schema)
        validator_cls.check_schema(schema)
        validator = validator_cls(schema)
        failures: list[dict[str, object]] = []
        for path, manifest in loaded_manifests:
            for error in sorted(validator.iter_errors(manifest), key=lambda e: list(e.absolute_path)):
                failures.append({
                    "path": path.relative_to(root).as_posix(),
                    "json_path": list(error.absolute_path),
                    "message": error.message,
                })
    except Exception as exc:
        return {
            "passed": False,
            "state": "SCHEMA_INVALID",
            "schema": SCHEMA_RELATIVE.as_posix(),
            "manifest_count": len(manifests),
            "detail": str(exc),
        }

    return {
        "passed": not failures,
        "state": "VALIDATED" if not failures else "MANIFEST_INVALID",
        "schema": SCHEMA_RELATIVE.as_posix(),
        "manifest_count": len(manifests),
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Bahrain Brick asset manifests against the authoritative JSON schema.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--allow-empty", action="store_true", help="Allow the Phase 2 state where neither schema nor manifests exist yet.")
    args = parser.parse_args()
    report = validate_manifest_tree(args.root, allow_empty=args.allow_empty)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
