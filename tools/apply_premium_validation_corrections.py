#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

CORRECTIONS = {
    'scripts/npc_pedestrian.gd': [(
        '\t\t_anim_player = _model.get_meta("anim_player", null)',
        '\t\t_anim_player = _model.get_meta("anim_player") if _model.has_meta("anim_player") else null',
        'avoid get_meta runtime errors when imported NPC models have no AnimationPlayer metadata',
    )],
    'scripts/save_manager.gd': [(
        '\tif player:\n\t\tsave_data["player"]["position"] = {',
        '\tif player and player.is_inside_tree():\n\t\tsave_data["player"]["position"] = {',
        'avoid global-transform access after the player has left the SceneTree during teardown save',
    )],
    'scripts/world.gd': [(
        '\ttitle.text = "BRICK BAHRAIN"',
        '\ttitle.text = "Bahrain Brick"',
        'remove obsolete reversed product title from the in-world loading overlay',
    )],
}
RUNTIME_TEXT_ROOTS = ('scripts', 'scenes', 'assets', 'artwork')
RUNTIME_TEXT_FILES = ('project.godot', 'export_presets.cfg')
STALE_TITLES = ('Brick Bahrain', 'BRICK BAHRAIN')


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


def apply(root: Path) -> dict:
    results=[]
    for relative, replacements in CORRECTIONS.items():
        path=root/relative
        if not path.is_file():
            raise RuntimeError(f'correction target missing: {relative}')
        before=path.read_bytes(); text=before.decode('utf-8')
        reasons=[]; states=[]
        for old,new,reason in replacements:
            old_count=text.count(old); new_count=text.count(new)
            if old_count == 1 and new_count == 0:
                text=text.replace(old,new); states.append('applied')
            elif old_count == 0 and new_count == 1:
                states.append('already_satisfied')
            else:
                raise RuntimeError(
                    f'correction state mismatch for {relative}: '
                    f'old_count={old_count}, new_count={new_count}'
                )
            reasons.append(reason)
        path.write_text(text,encoding='utf-8')
        after=path.read_bytes()
        results.append({'path':relative,'before_sha256':sha(before),'after_sha256':sha(after),'states':states,'reasons':reasons})
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
    return {'conclusion':'pass','corrections':results,'runtime_text_files_scanned':sorted(set(scanned)),'obsolete_runtime_title_occurrences':stale}


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument('root',type=Path); p.add_argument('--report',type=Path,required=True)
    a=p.parse_args()
    try:
        report=apply(a.root.resolve())
    except Exception as error:
        a.report.parent.mkdir(parents=True,exist_ok=True)
        a.report.write_text(json.dumps({'conclusion':'fail','error':str(error)},indent=2)+'\n',encoding='utf-8')
        raise
    a.report.parent.mkdir(parents=True,exist_ok=True); a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2)); return 0

if __name__=='__main__': raise SystemExit(main())
