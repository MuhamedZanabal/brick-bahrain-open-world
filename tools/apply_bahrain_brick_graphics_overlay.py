#!/usr/bin/env python3
"""Apply the presentation-only Bahrain Brick graphics overlay to the frozen controls source."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import tarfile
import tempfile
from pathlib import Path

TEXT_EXTENSIONS = {'.gd', '.tscn', '.godot', '.cfg', '.py', '.md', '.json', '.txt', '.sh'}
FORBIDDEN_TEXT = ('brick bahrain', 'legends are brick', 'lego loading', 'v1.3.0 prototype')


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def safe_extract(archive_path: Path, target: Path) -> None:
    with tarfile.open(archive_path, 'r:xz') as archive:
        for member in archive.getmembers():
            destination = (target / member.name).resolve()
            if destination != target and target not in destination.parents:
                raise RuntimeError(f'unsafe archive member: {member.name}')
        archive.extractall(target, filter='data')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    tools = Path(__file__).resolve().parent
    parts_dir = tools / 'graphics_overlay_parts'
    manifest_path = tools / 'bahrain_brick_graphics_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))

    if not root.joinpath('project.godot').is_file():
        raise RuntimeError(f'not a Godot project: {root}')
    if not parts_dir.is_dir():
        raise RuntimeError('graphics overlay payload is incomplete')

    encoded_parts = sorted(parts_dir.glob('part-*.b64'))
    if len(encoded_parts) != int(manifest['overlay_base64_parts']):
        raise RuntimeError(
            f"overlay part count mismatch: expected {manifest['overlay_base64_parts']}, "
            f'found {len(encoded_parts)}'
        )
    encoded = b''.join(path.read_bytes() for path in encoded_parts)
    raw = base64.b64decode(encoded, validate=True)
    actual_archive_sha = hashlib.sha256(raw).hexdigest()
    if actual_archive_sha != manifest['overlay_archive_sha256']:
        raise RuntimeError(
            f"overlay archive hash mismatch: expected {manifest['overlay_archive_sha256']}, "
            f'got {actual_archive_sha}'
        )
    with tempfile.NamedTemporaryFile(suffix='.tar.xz') as temporary:
        temporary.write(raw)
        temporary.flush()
        safe_extract(Path(temporary.name), root)

    for relative in manifest['deleted_files']:
        path = root / relative
        if path.exists():
            path.unlink()

    verified_files: dict[str, dict[str, object]] = {}
    for relative, expected in manifest['overlay_files'].items():
        path = root / relative
        if not path.is_file():
            raise RuntimeError(f'missing runtime asset after extraction: {relative}')
        actual_sha = sha256(path)
        actual_bytes = path.stat().st_size
        if actual_sha != expected['sha256'] or actual_bytes != expected['bytes']:
            raise RuntimeError(f'runtime asset identity mismatch: {relative}')
        verified_files[relative] = {'bytes': actual_bytes, 'sha256': actual_sha}

    forbidden_hits: list[str] = []
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        if any(part in {'.git', '.godot', 'build'} for part in path.relative_to(root).parts):
            continue
        text = path.read_text(encoding='utf-8', errors='replace').lower()
        for term in FORBIDDEN_TEXT:
            if term in text:
                forbidden_hits.append(f'{path.relative_to(root).as_posix()}: {term}')
    if forbidden_hits:
        raise RuntimeError('obsolete or protected text remains:\n' + '\n'.join(forbidden_hits))

    report = {
        'evidence_class': 'VERIFIED',
        'classification': 'presentation overlay on frozen v1.4 controls baseline; not v15 authority',
        'frozen_controls_commit': manifest['baseline_controls_commit'],
        'game_title': 'Bahrain Brick',
        'startup_sequence': ['Zanabal Gaming', 'Mansoory Games', 'Bahrain Brick main menu'],
        'overlay_files': verified_files,
        'runtime_assets': {key: verified_files[key] for key in manifest['runtime_assets']},
        'deleted_obsolete_files': manifest['deleted_files'],
        'forbidden_text_hits': [],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
