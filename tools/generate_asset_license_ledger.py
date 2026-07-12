#!/usr/bin/env python3
"""Generate an evidence-first asset and third-party license ledger.

The tool never marks ownership or redistribution rights as verified merely because a
file exists. Verification requires adjacent license evidence with a recognized text
signature; all other rows remain review-required or blocked.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

SKIP_DIRS = {
    ".git", ".godot", ".gradle", ".idea", ".mono", "__pycache__", "build",
    "dist", "node_modules",
}

THIRD_PARTY_ROOTS = ("addons", "plugins", "third_party", "third-party", "vendor")
PROJECT_ASSET_ROOTS = ("assets", "audio", "art", "models", "textures", "fonts")

ASSET_EXTENSIONS = {
    ".blend", ".dae", ".exr", ".fbx", ".flac", ".glb", ".gltf", ".hdr",
    ".jpeg", ".jpg", ".mp3", ".obj", ".ogg", ".otf", ".png", ".svg",
    ".tga", ".ttf", ".wav", ".webp",
}

THIRD_PARTY_CODE_EXTENSIONS = {
    ".cfg", ".gd", ".gdshader", ".glsl", ".h", ".hpp", ".java", ".json",
    ".md", ".py", ".shader", ".tscn", ".tres", ".txt", ".xml", ".yaml", ".yml",
}

LICENSE_NAMES = {
    "license", "license.md", "license.txt", "copying", "copying.md", "copying.txt",
    "notice", "notice.md", "notice.txt",
}

FIELDS = [
    "path", "asset_name", "component", "creator_source", "source_url", "license",
    "license_text_path", "attribution_required", "commercial_use", "modification_allowed",
    "redistribution_allowed", "proof", "status", "replacement_required",
]


@dataclass(frozen=True)
class LedgerRow:
    path: str
    asset_name: str
    component: str
    creator_source: str
    source_url: str
    license: str
    license_text_path: str
    attribution_required: str
    commercial_use: str
    modification_allowed: str
    redistribution_allowed: str
    proof: str
    status: str
    replacement_required: str


def iter_files(root: Path) -> Iterator[Path]:
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        current_path = Path(current)
        for name in sorted(files):
            yield current_path / name


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def path_root(relative_path: Path) -> str:
    return relative_path.parts[0].lower() if relative_path.parts else ""


def is_candidate(relative_path: Path) -> bool:
    root_name = path_root(relative_path)
    suffix = relative_path.suffix.lower()
    if root_name in THIRD_PARTY_ROOTS:
        return suffix in ASSET_EXTENSIONS or suffix in THIRD_PARTY_CODE_EXTENSIONS or relative_path.name.lower() in LICENSE_NAMES
    if root_name in PROJECT_ASSET_ROOTS:
        return suffix in ASSET_EXTENSIONS
    return False


def component_for(relative_path: Path) -> str:
    if len(relative_path.parts) >= 2 and path_root(relative_path) in THIRD_PARTY_ROOTS:
        return "/".join(relative_path.parts[:2])
    return relative_path.parts[0] if relative_path.parts else "."


def find_license_file(path: Path, root: Path, component: str) -> Path | None:
    component_dir = root / component
    current = path.parent
    while True:
        try:
            for child in current.iterdir():
                if child.is_file() and child.name.lower() in LICENSE_NAMES:
                    return child
        except OSError:
            pass
        if current == component_dir or current == root or root not in current.parents:
            break
        current = current.parent
    return None


def recognize_license(text: str) -> tuple[str, dict[str, str]]:
    lowered = text.lower()
    if "permission is hereby granted, free of charge" in lowered and "the software is provided \"as is\"" in lowered:
        return "MIT", {
            "attribution_required": "yes",
            "commercial_use": "yes",
            "modification_allowed": "yes",
            "redistribution_allowed": "yes",
        }
    if "apache license" in lowered and "version 2.0" in lowered:
        return "Apache-2.0", {
            "attribution_required": "yes",
            "commercial_use": "yes",
            "modification_allowed": "yes",
            "redistribution_allowed": "yes",
        }
    if "cc0 1.0 universal" in lowered or "creative commons zero" in lowered:
        return "CC0-1.0", {
            "attribution_required": "no",
            "commercial_use": "yes",
            "modification_allowed": "yes",
            "redistribution_allowed": "yes",
        }
    if "gnu general public license" in lowered:
        return "GPL-UNSPECIFIED", {
            "attribution_required": "yes",
            "commercial_use": "review",
            "modification_allowed": "review",
            "redistribution_allowed": "review",
        }
    return "UNKNOWN", {
        "attribution_required": "review",
        "commercial_use": "review",
        "modification_allowed": "review",
        "redistribution_allowed": "review",
    }


def row_for(path: Path, root: Path) -> LedgerRow:
    relative_path = path.relative_to(root)
    relative_text = relative_path.as_posix()
    component = component_for(relative_path)
    third_party = path_root(relative_path) in THIRD_PARTY_ROOTS
    license_file = find_license_file(path, root, component) if third_party else None

    license_name = "UNKNOWN"
    rights = {
        "attribution_required": "review",
        "commercial_use": "review",
        "modification_allowed": "review",
        "redistribution_allowed": "review",
    }
    license_path = ""
    proof = ""
    status = "PROJECT_PROVENANCE_REQUIRED"
    replacement_required = "review"

    if third_party:
        if license_file:
            license_path = rel(license_file, root)
            proof = license_path
            text = license_file.read_text(encoding="utf-8", errors="replace")[:200_000]
            license_name, rights = recognize_license(text)
            if license_name == "UNKNOWN":
                status = "REVIEW_REQUIRED"
                replacement_required = "review"
            else:
                status = "VERIFIED_EVIDENCE"
                replacement_required = "no"
        else:
            status = "BLOCKED"
            replacement_required = "yes"

    return LedgerRow(
        path=relative_text,
        asset_name=path.name,
        component=component,
        creator_source="",
        source_url="",
        license=license_name,
        license_text_path=license_path,
        attribution_required=rights["attribution_required"],
        commercial_use=rights["commercial_use"],
        modification_allowed=rights["modification_allowed"],
        redistribution_allowed=rights["redistribution_allowed"],
        proof=proof,
        status=status,
        replacement_required=replacement_required,
    )


def generate_ledger(root: Path) -> list[LedgerRow]:
    root = root.resolve()
    rows = [row_for(path, root) for path in iter_files(root) if is_candidate(path.relative_to(root))]
    rows.sort(key=lambda row: row.path)
    if len({row.path for row in rows}) != len(rows):
        raise RuntimeError("duplicate ledger paths generated")
    return rows


def write_csv(rows: list[LedgerRow], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_notices(rows: list[LedgerRow], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    components: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.status == "VERIFIED_EVIDENCE":
            components.setdefault(row.component, {
                "license": row.license,
                "license_text_path": row.license_text_path,
                "source_url": row.source_url,
                "creator_source": row.creator_source,
            })
    lines = [
        "# Third-Party Notices",
        "",
        "Generated from source-tree evidence. Blank creator/source fields require manual completion.",
        "",
    ]
    if not components:
        lines.append("No third-party component has verified license evidence yet.")
    for component, data in sorted(components.items()):
        lines.extend([
            f"## {component}",
            "",
            f"- License: `{data['license']}`",
            f"- License evidence: `{data['license_text_path']}`",
            f"- Creator/source: {data['creator_source'] or 'REQUIRED'}",
            f"- Source URL: {data['source_url'] or 'REQUIRED'}",
            "",
        ])
    destination.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def summary(rows: list[LedgerRow]) -> dict[str, object]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    return {
        "schema_version": 1,
        "rows": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "blocked_paths": [row.path for row in rows if row.status == "BLOCKED"],
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--csv-out", type=Path, required=True)
    parser.add_argument("--notices-out", type=Path, required=True)
    parser.add_argument("--summary-out", type=Path)
    parser.add_argument("--fail-on-blocked", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if not args.root.is_dir():
        print(f"error: source root is not a directory: {args.root}", file=sys.stderr)
        return 3
    rows = generate_ledger(args.root)
    write_csv(rows, args.csv_out)
    write_notices(rows, args.notices_out)
    report = summary(rows)
    if args.summary_out:
        args.summary_out.parent.mkdir(parents=True, exist_ok=True)
        args.summary_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 2 if args.fail_on_blocked and report["status_counts"].get("BLOCKED", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
