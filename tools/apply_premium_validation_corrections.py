#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

CORRECTIONS = {
    'scripts/npc_pedestrian.gd': [(
        (
            '\t\t_anim_player = _model.get_meta("anim_player", null)',
            '\t\t_anim_player = _model.get_meta("anim_player")',
        ),
        '\t\t_anim_player = _model.get_meta("anim_player") if _model.has_meta("anim_player") else null',
        'avoid get_meta runtime errors when imported NPC models have no AnimationPlayer metadata',
    )],
    'scripts/save_manager.gd': [((
        '\tif player:\n\t\tsave_data["player"]["position"] = {',
    ),
        '\tif player and player.is_inside_tree():\n\t\tsave_data["player"]["position"] = {',
        'avoid global-transform access after the player has left the SceneTree during teardown save',
    )],
    'scripts/world.gd': [((
        '\ttitle.text = "BRICK BAHRAIN"',
    ),
        '\ttitle.text = "Bahrain Brick"',
        'remove obsolete reversed product title from the in-world loading overlay',
    )],
}
RUNTIME_TEXT_ROOTS = ('scripts', 'scenes', 'assets', 'artwork')
RUNTIME_TEXT_FILES = ('project.godot', 'export_presets.cfg')
STALE_TITLES = ('Brick Bahrain', 'BRICK BAHRAIN')
NPC_SCENE_RELATIVE = 'scenes/npc_pedestrian.tscn'
NPC_SCENE_CONTENT = '''[gd_scene load_steps=2 format=3]\n\n[ext_resource type="Script" path="res://scripts/npc_pedestrian.gd" id="1_npc"]\n\n[node name="NPCPedestrian" type="CharacterBody3D"]\nscript = ExtResource("1_npc")\n'''


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


def replace_variant(text: str, old_variants: tuple[str, ...], new: str, label: str) -> tuple[str, str]:
    old_counts = {old: text.count(old) for old in old_variants}
    total_old = sum(old_counts.values())
    new_count = text.count(new)
    if total_old == 1 and new_count == 0:
        selected = next(old for old, count in old_counts.items() if count == 1)
        return text.replace(selected, new), 'applied'
    if total_old == 0 and new_count == 1:
        return text, 'already_satisfied'
    raise RuntimeError(
        f'correction state mismatch for {label}: '
        f'old_counts={old_counts}, new_count={new_count}'
    )


def ensure_npc_scene(root: Path) -> dict:
    path = root / NPC_SCENE_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if not path.is_file():
            raise RuntimeError(f'NPC scene path is not a file: {NPC_SCENE_RELATIVE}')
        text = path.read_text(encoding='utf-8')
        if 'res://scripts/npc_pedestrian.gd' not in text or 'type="CharacterBody3D"' not in text:
            raise RuntimeError(f'existing NPC scene is incompatible: {NPC_SCENE_RELATIVE}')
        state = 'already_satisfied'
    else:
        path.write_text(NPC_SCENE_CONTENT, encoding='utf-8')
        state = 'generated'
    return {
        'path': NPC_SCENE_RELATIVE,
        'state': state,
        'sha256': sha(path.read_bytes()),
        'reason': 'satisfy the recovered NPCManager preload with the real NPCPedestrian script',
    }


def apply(root: Path) -> dict:
    results=[]
    for relative, replacements in CORRECTIONS.items():
        path=root/relative
        if not path.is_file():
            raise RuntimeError(f'correction target missing: {relative}')
        before=path.read_bytes(); text=before.decode('utf-8')
        reasons=[]; states=[]
        for old_variants,new,reason in replacements:
            text,state=replace_variant(text,old_variants,new,relative)
            states.append(state); reasons.append(reason)
        path.write_text(text,encoding='utf-8')
        after=path.read_bytes()
        results.append({'path':relative,'before_sha256':sha(before),'after_sha256':sha(after),'states':states,'reasons':reasons})
    generated_resources=[ensure_npc_scene(root)]
    export=root/'export_presets.cfg'
    text=export.read_text(encoding='utf-8')
    text,n1=re.subn(r'(?m)^version/code=.*$', 'version/code=1404', text)
    text,n2=re.subn(r'(?m)^version/name=.*$', 'version/name="1.4.0.4-premium-visual-qa"', text)
    if (n1,n2)!=(1,1):
        raise RuntimeError(f'export version replacement failure: {(n1,n2)}')
    export.write_text(text,encoding='utf-8')
    stale=[]; scanned=[]
    for path in runtime_text_paths(root):
        relative=path.relative_to(root).as_posix(); scanned.append(relative)
        try: body=path.read_text(encoding='utf-8')
        except (UnicodeDecodeError,OSError): continue
        for token in STALE_TITLES:
            if token in body: stale.append({'path':relative,'token':token})
    if stale:
        raise RuntimeError(f'obsolete runtime title occurrences remain: {stale}')
    return {
        'conclusion':'pass',
        'corrections':results,
        'generated_runtime_resources':generated_resources,
        'runtime_text_files_scanned':sorted(set(scanned)),
        'obsolete_runtime_title_occurrences':stale,
    }


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument('root',type=Path); p.add_argument('--report',type=Path,required=True)
    a=p.parse_args()
    try:
        report=apply(a.root.resolve())
    except Exception as error:
        a.report.parent.mkdir(parents=True,exist_ok=True)
        a.report.write_text(json.dumps({'conclusion':'fail','error_type':type(error).__name__,'error':str(error)},indent=2)+'\n',encoding='utf-8')
        raise
    a.report.parent.mkdir(parents=True,exist_ok=True); a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2)); return 0

if __name__=='__main__': raise SystemExit(main())
