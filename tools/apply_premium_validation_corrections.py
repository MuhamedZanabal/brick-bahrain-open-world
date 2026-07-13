#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

CORRECTIONS = {
    'scripts/world.gd': [
        ((
            '\t\ttitle.text = "BRICK BAHRAIN"',
            '\ttitle.text = "BRICK BAHRAIN"',
        ),
            '\ttitle.text = "Bahrain Brick"',
            'remove obsolete reversed product title from the in-world loading overlay',
        ),
        ((
            '\t\tif player and player is Node3D:\n\t\t\tSaveManager.set_position((player as Node3D).global_position)',
        ),
            '\t\tif player and player is Node3D and player.is_inside_tree():\n\t\t\tSaveManager.set_position((player as Node3D).global_position)',
            'avoid reading player global_position after the player has left the SceneTree during world teardown',
        ),
    ],
}
RUNTIME_TEXT_ROOTS = ('scripts', 'scenes', 'assets', 'artwork')
RUNTIME_TEXT_FILES = ('project.godot', 'export_presets.cfg')
STALE_TITLES = ('Brick Bahrain', 'BRICK BAHRAIN')
NPC_SCENE_RELATIVE = 'scenes/npc_pedestrian.tscn'
NPC_SCENE_CONTENT = '''[gd_scene load_steps=2 format=3]\n\n[ext_resource type="Script" path="res://scripts/npc_pedestrian.gd" id="1_npc"]\n\n[node name="NPCPedestrian" type="CharacterBody3D"]\nscript = ExtResource("1_npc")\n'''
DIAGNOSTIC_SOURCE_PATHS = (
    'scripts/save_manager.gd', 'scripts/world.gd', 'scripts/npc_manager.gd',
    'scripts/npc_pedestrian.gd', 'scenes/npc_pedestrian.tscn',
    'tests/premium_presentation_acceptance_test.gd',
    'scenes/premium_presentation_acceptance_test.tscn',
)
NPC_UNSAFE_PATTERN = re.compile(
    r'(?m)^(?P<indent>[ \t]*)(?P<variable>_animation_player|_anim_player)\s*=\s*'
    r'_model\.get_meta\(\s*&?["\']anim_player["\']'
    r'(?:\s*,\s*null)?\s*\)(?:\s+as\s+AnimationPlayer)?\s*$'
)
NPC_SAFE_PATTERN = re.compile(
    r'(?m)^[ \t]*(?:_animation_player|_anim_player)\s*=.*_model\.get_meta\(.*anim_player.*\)'
    r'.*_model\.has_meta\(\s*&?["\']anim_player["\']\s*\).*else\s+null\s*$'
)
NPC_SAFE_TEMPLATE = (
    '{indent}{variable} = (_model.get_meta("anim_player") as AnimationPlayer) '
    'if _model.has_meta("anim_player") else null'
)
SAVE_CONDITION_PATTERN = re.compile(r'^(?P<indent>[ \t]*)if\s+(?P<condition>.+):\s*$')
SAVE_TREE_GUARD_PATTERN = re.compile(r'\bplayer\.is_inside_tree\s*\(\s*\)')
PLAYER_GLOBAL_POSITION_PATTERN = re.compile(r'\bplayer\.global_position\b')


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def indentation_width(line: str) -> int:
    leading = line[:len(line) - len(line.lstrip(' \t'))]
    return len(leading.expandtabs(4))


def runtime_text_paths(root: Path):
    for relative in RUNTIME_TEXT_FILES:
        path = root / relative
        if path.is_file():
            yield path
    for folder in RUNTIME_TEXT_ROOTS:
        base = root / folder
        if not base.is_dir():
            continue
        for path in base.rglob('*'):
            if path.is_file() and not any(part in {'.godot', 'build'} for part in path.relative_to(root).parts):
                yield path


def exact_pattern(value: str) -> re.Pattern[str]:
    return re.compile(r'(?m)^' + re.escape(value) + r'$')


def replace_variant(text: str, old_variants: tuple[str, ...], new: str, label: str) -> tuple[str, str]:
    old_patterns = {old: exact_pattern(old) for old in old_variants}
    old_counts = {old: len(pattern.findall(text)) for old, pattern in old_patterns.items()}
    total_old = sum(old_counts.values())
    new_pattern = exact_pattern(new)
    new_count = len(new_pattern.findall(text))
    if total_old == 1 and new_count == 0:
        selected = next(old for old, count in old_counts.items() if count == 1)
        return old_patterns[selected].sub(lambda _m: new, text, count=1), 'applied'
    if total_old == 0 and new_count == 1:
        return text, 'already_satisfied'
    raise RuntimeError(f'correction state mismatch for {label}: old_counts={old_counts}, new_count={new_count}')


def correct_npc_anim_player(text: str) -> tuple[str, str]:
    unsafe = list(NPC_UNSAFE_PATTERN.finditer(text))
    safe = list(NPC_SAFE_PATTERN.finditer(text))
    if len(unsafe) == 1 and len(safe) == 0:
        match = unsafe[0]
        replacement = NPC_SAFE_TEMPLATE.format(indent=match.group('indent'), variable=match.group('variable'))
        return NPC_UNSAFE_PATTERN.sub(lambda _m: replacement, text, count=1), 'applied'
    if len(unsafe) == 0 and len(safe) == 1:
        return text, 'already_satisfied'
    candidates = [line.strip() for line in text.splitlines() if 'anim_player' in line or ('get_meta' in line and '_model' in line)]
    raise RuntimeError(f'NPC anim_player correction state mismatch: unsafe_count={len(unsafe)}, safe_count={len(safe)}, candidates={candidates}')


def correct_save_position_guard(text: str) -> tuple[str, str]:
    lines = text.splitlines(keepends=True)
    access_indices = [i for i, line in enumerate(lines) if PLAYER_GLOBAL_POSITION_PATTERN.search(line)]
    if not access_indices:
        candidates = [line.strip() for line in lines if 'position' in line and ('player' in line or 'save_data' in line)]
        raise RuntimeError(f'player global-position access missing: candidates={candidates}')
    guard_indices: list[int] = []
    contexts: list[list[str]] = []
    for access_index in access_indices:
        access_width = indentation_width(lines[access_index])
        guard_index = None
        for index in range(access_index - 1, -1, -1):
            raw = lines[index].rstrip('\r\n')
            stripped = raw.strip()
            if not stripped or stripped.startswith('#'):
                continue
            width = indentation_width(raw)
            match = SAVE_CONDITION_PATTERN.fullmatch(raw)
            if match and width < access_width and re.search(r'\bplayer\b', match.group('condition')):
                guard_index = index
                break
            if width < access_width and stripped.startswith('func '):
                break
        if guard_index is None:
            contexts.append([line.rstrip('\r\n') for line in lines[max(0, access_index - 4):min(len(lines), access_index + 3)]])
        else:
            guard_indices.append(guard_index)
    if contexts:
        raise RuntimeError(f'player global-position access has no enclosing player guard: contexts={contexts}')
    unique_guards = sorted(set(guard_indices))
    if len(unique_guards) != 1:
        guard_lines = [lines[i].rstrip('\r\n') for i in unique_guards]
        access_lines = [lines[i].strip() for i in access_indices]
        raise RuntimeError(f'player global-position accesses do not share one guard: guards={guard_lines}, accesses={access_lines}')
    guard_index = unique_guards[0]
    raw_guard = lines[guard_index].rstrip('\r\n')
    match = SAVE_CONDITION_PATTERN.fullmatch(raw_guard)
    if match is None:
        raise RuntimeError(f'invalid player guard syntax: {raw_guard}')
    condition = match.group('condition').strip()
    if SAVE_TREE_GUARD_PATTERN.search(condition):
        return text, 'already_satisfied'
    newline = '\r\n' if lines[guard_index].endswith('\r\n') else '\n' if lines[guard_index].endswith('\n') else ''
    lines[guard_index] = f'{match.group("indent")}if {condition} and player.is_inside_tree():' + newline
    return ''.join(lines), 'applied'


def ensure_npc_scene(root: Path) -> dict:
    path = root / NPC_SCENE_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if not path.is_file():
            raise RuntimeError(f'NPC scene path is not a file: {NPC_SCENE_RELATIVE}')
        text = path.read_text(encoding='utf-8')
        if text == NPC_SCENE_CONTENT:
            state = 'already_satisfied'
        elif 'res://scripts/npc_pedestrian.gd' in text and 'type="CharacterBody3D"' in text:
            path.write_text(NPC_SCENE_CONTENT, encoding='utf-8'); state = 'replaced'
        else:
            raise RuntimeError(f'existing NPC scene is incompatible: {NPC_SCENE_RELATIVE}')
    else:
        path.write_text(NPC_SCENE_CONTENT, encoding='utf-8'); state = 'generated'
    if path.read_text(encoding='utf-8') != NPC_SCENE_CONTENT:
        raise RuntimeError(f'canonical NPC scene verification failed: {NPC_SCENE_RELATIVE}')
    return {'path': NPC_SCENE_RELATIVE, 'state': state, 'sha256': sha(path.read_bytes()), 'reason': 'provide one deterministic project-loadable NPCPedestrian scene for NPCManager preload'}


def collect_diagnostic_sources(root: Path) -> dict[str, str]:
    sources: dict[str, str] = {}
    for relative in DIAGNOSTIC_SOURCE_PATHS:
        path = root / relative
        if not path.is_file():
            continue
        try:
            sources[relative] = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            sources[relative] = f'<non-UTF-8 file sha256={sha(path.read_bytes())}>'
    return sources


def apply(root: Path) -> dict:
    results = []
    npc_path = root / 'scripts/npc_pedestrian.gd'
    if not npc_path.is_file():
        raise RuntimeError('correction target missing: scripts/npc_pedestrian.gd')
    before = npc_path.read_bytes(); text = before.decode('utf-8')
    text, state = correct_npc_anim_player(text); npc_path.write_text(text, encoding='utf-8'); after = npc_path.read_bytes()
    results.append({'path':'scripts/npc_pedestrian.gd','before_sha256':sha(before),'after_sha256':sha(after),'states':[state],'reasons':['avoid get_meta runtime errors when imported NPC models have no AnimationPlayer metadata']})

    save_path = root / 'scripts/save_manager.gd'
    if not save_path.is_file():
        raise RuntimeError('correction target missing: scripts/save_manager.gd')
    before = save_path.read_bytes(); text = before.decode('utf-8')
    text, state = correct_save_position_guard(text); save_path.write_text(text, encoding='utf-8'); after = save_path.read_bytes()
    results.append({'path':'scripts/save_manager.gd','before_sha256':sha(before),'after_sha256':sha(after),'states':[state],'reasons':['avoid global-transform access after the player has left the SceneTree during teardown save']})

    for relative, replacements in CORRECTIONS.items():
        path = root / relative
        if not path.is_file():
            raise RuntimeError(f'correction target missing: {relative}')
        before = path.read_bytes(); text = before.decode('utf-8'); reasons=[]; states=[]
        for old_variants, new, reason in replacements:
            text, state = replace_variant(text, old_variants, new, relative)
            states.append(state); reasons.append(reason)
        path.write_text(text, encoding='utf-8'); after = path.read_bytes()
        results.append({'path':relative,'before_sha256':sha(before),'after_sha256':sha(after),'states':states,'reasons':reasons})

    generated_resources = [ensure_npc_scene(root)]
    export = root / 'export_presets.cfg'
    text = export.read_text(encoding='utf-8')
    text, n1 = re.subn(r'(?m)^version/code=.*$', 'version/code=1404', text)
    text, n2 = re.subn(r'(?m)^version/name=.*$', 'version/name="1.4.0.4-premium-visual-qa"', text)
    if (n1, n2) != (1, 1):
        raise RuntimeError(f'export version replacement failure: {(n1,n2)}')
    export.write_text(text, encoding='utf-8')

    stale=[]; scanned=[]
    for path in runtime_text_paths(root):
        relative=path.relative_to(root).as_posix(); scanned.append(relative)
        try: body=path.read_text(encoding='utf-8')
        except (UnicodeDecodeError,OSError): continue
        for token in STALE_TITLES:
            if token in body: stale.append({'path':relative,'token':token})
    if stale:
        raise RuntimeError(f'obsolete runtime title occurrences remain: {stale}')
    return {'conclusion':'pass','corrections':results,'generated_runtime_resources':generated_resources,'runtime_text_files_scanned':sorted(set(scanned)),'obsolete_runtime_title_occurrences':stale,'diagnostic_sources':collect_diagnostic_sources(root)}


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument('root',type=Path); p.add_argument('--report',type=Path,required=True)
    a=p.parse_args()
    try:
        report=apply(a.root.resolve())
    except Exception as error:
        a.report.parent.mkdir(parents=True,exist_ok=True)
        a.report.write_text(json.dumps({'conclusion':'fail','error_type':type(error).__name__,'error':str(error)},indent=2)+'\n',encoding='utf-8')
        raise
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2)); return 0


if __name__=='__main__': raise SystemExit(main())
