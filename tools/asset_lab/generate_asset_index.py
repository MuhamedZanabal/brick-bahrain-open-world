#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from validate_manifest_schema import ASSETS_RELATIVE, SCHEMA_RELATIVE, validate_manifest_tree

DEFAULT_OUTPUT = Path("asset_lab/manifests/asset-index.json")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_index(root: Path) -> dict[str, object]:
    root = root.resolve()
    validation = validate_manifest_tree(root, allow_empty=False)
    if not validation["passed"]:
        raise ValueError(f"manifest validation failed: {validation}")
    schema_path = root / SCHEMA_RELATIVE
    assets_dir = root / ASSETS_RELATIVE
    entries: list[dict[str, object]] = []
    for path in sorted(assets_dir.rglob("*.json")) if assets_dir.exists() else []:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        entries.append({
            "asset_id": manifest["asset_id"],
            "display_name": manifest["display_name"],
            "category": manifest["category"],
            "version": manifest["version"],
            "source_path": manifest["source_path"],
            "export_path": manifest["export_path"],
            "legacy_ids": manifest.get("legacy_ids", []),
            "approval_states": {key: value["state"] for key, value in sorted(manifest["approvals"].items())},
            "manifest_path": path.relative_to(root).as_posix(),
            "manifest_sha256": _sha256(path)
        })
    entries.sort(key=lambda item: item["asset_id"])
    return {
        "schema_version": "1.0.0",
        "schema_path": SCHEMA_RELATIVE.as_posix(),
        "schema_sha256": _sha256(schema_path),
        "manifest_count": len(entries),
        "assets": entries
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the Bahrain Brick global asset index from validated production manifests.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        index = generate_index(args.root)
    except ValueError as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, indent=2, sort_keys=True))
        return 1
    output = args.output if args.output.is_absolute() else args.root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(index, indent=2, sort_keys=True) + "\n"
    output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
