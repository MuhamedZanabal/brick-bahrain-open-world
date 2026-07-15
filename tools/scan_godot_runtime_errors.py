#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

DUMMY_MESH_ERROR = 'ERROR: Parameter "m" is null.'
DUMMY_MESH_STACK = 'at: mesh_get_surface_count (servers/rendering/dummy/storage/mesh_storage.h:120)'
CRITICAL_RE = re.compile(
    r'(SCRIPT ERROR:|ERROR:|\bCRASH(?:ED)?\b|Assertion failed|assertion failed|'
    r'Invalid call|Invalid get index|Invalid set index|Stack trace|stack trace|'
    r'Failed to load|Failed to create an autoload|Parse Error|Parser Error|'
    r'Shader compilation failed|RenderingDevice.*(?:error|failed))',
    re.IGNORECASE,
)


def scan(log_dir: Path) -> dict:
    files = sorted(p for p in log_dir.rglob('*.log') if p.is_file())
    events: list[dict] = []
    categories: Counter[str] = Counter()
    allowlisted = 0
    unresolved = 0
    for path in files:
        lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
        for index, line in enumerate(lines):
            stripped = line.strip()
            if not CRITICAL_RE.search(stripped):
                continue
            next_line = lines[index + 1].strip() if index + 1 < len(lines) else ''
            category = 'unresolved_critical_error'
            disposition = 'unresolved'
            justification = 'No narrow allowlist matched this critical signature.'
            if stripped == DUMMY_MESH_ERROR and next_line == DUMMY_MESH_STACK:
                category = 'dummy_renderer_null_mesh_surface_query'
                disposition = 'allowlisted'
                justification = (
                    'Exact Godot 4.3 dummy-renderer signature from '
                    'servers/rendering/dummy/storage/mesh_storage.h:120. '
                    'It occurs only in headless Dummy rendering after project assertions pass; '
                    'GL Compatibility evidence runs do not use this renderer. The match requires '
                    'both the exact error and exact engine stack line, so project errors are not masked.'
                )
                allowlisted += 1
            else:
                unresolved += 1
            categories[category] += 1
            events.append({
                'file': path.relative_to(log_dir).as_posix(),
                'line': index + 1,
                'message': stripped,
                'next_line': next_line,
                'category': category,
                'disposition': disposition,
                'justification': justification,
            })
    return {
        'log_directory': str(log_dir),
        'files_scanned': [p.relative_to(log_dir).as_posix() for p in files],
        'raw_error_count': len(events),
        'categorized_count': sum(categories.values()),
        'categories': dict(sorted(categories.items())),
        'allowlisted_count': allowlisted,
        'unresolved_count': unresolved,
        'conclusion': 'pass' if unresolved == 0 else 'fail',
        'allowlist': [{
            'signature': DUMMY_MESH_ERROR,
            'required_following_line': DUMMY_MESH_STACK,
            'classification': 'dummy-renderer limitation',
        }],
        'events': events,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('log_dir', type=Path)
    parser.add_argument('--json-out', type=Path, required=True)
    parser.add_argument('--markdown-out', type=Path, required=True)
    args = parser.parse_args()
    if not args.log_dir.is_dir():
        raise SystemExit(f'log directory missing: {args.log_dir}')
    report = scan(args.log_dir)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    rows = [
        '# Godot Critical Runtime Error Scan', '',
        f"- Raw error count: {report['raw_error_count']}",
        f"- Categorized count: {report['categorized_count']}",
        f"- Allowlisted count: {report['allowlisted_count']}",
        f"- Unresolved count: {report['unresolved_count']}",
        f"- Conclusion: **{report['conclusion'].upper()}**", '',
        '## Categories', '',
    ]
    rows += [f'- `{name}`: {count}' for name, count in report['categories'].items()]
    rows += ['', '## Allowlist justification', '',
             '- Only the exact `Parameter "m" is null` message immediately followed by the '
             'Godot 4.3 dummy mesh-storage stack line is permitted. All other errors fail the gate.', '']
    args.markdown_out.write_text('\n'.join(rows), encoding='utf-8')
    print(json.dumps({k: report[k] for k in (
        'raw_error_count','categorized_count','categories','allowlisted_count','unresolved_count','conclusion'
    )}, indent=2))
    return 0 if report['unresolved_count'] == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
