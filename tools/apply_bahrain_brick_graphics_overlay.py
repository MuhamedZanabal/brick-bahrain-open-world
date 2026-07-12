#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, shutil
from pathlib import Path

TEXT_EXTENSIONS={'.gd','.tscn','.godot','.cfg','.py','.md','.json','.txt','.sh','.yml','.yaml'}
FORBIDDEN=('brick bahrain','legends are brick','v1.3.0 prototype','lego loading')
VARIANTS={
    'assets/ui/runtime/splash_mansoory.svg':('#071827','#123e51','#37d1e8',True),
    'assets/ui/runtime/main_menu_background.svg':('#0a3150','#d67431','#f2bf49',False),
    'assets/ui/runtime/loading_background.svg':('#163c55','#e08a41','#ffc95a',False),
    'assets/ui/runtime/character_select_background.svg':('#14314c','#8b4e2d','#7dd7e9',False),
    'assets/ui/runtime/pause_background.svg':('#07111c','#173349','#e6ad39',True),
}

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def replace_function(text:str,name:str,replacement:str)->str:
    pattern=rf'(?ms)^func {re.escape(name)}\b.*?(?=^func |\Z)'
    updated,count=re.subn(pattern,replacement.rstrip()+'\n\n',text,count=1)
    if count!=1: raise RuntimeError(f'function patch failed: {name}, matches={count}')
    return updated

def main()->int:
    parser=argparse.ArgumentParser(description='Apply native Bahrain Brick presentation overlay without changing frozen controls.')
    parser.add_argument('root',type=Path)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args(); root=args.root.resolve(); repo=Path(__file__).resolve().parent.parent
    overlay=repo/'presentation_overlay'; manifest=json.loads((repo/'tools/bahrain_brick_graphics_manifest.json').read_text())
    if not (root/'project.godot').is_file(): raise RuntimeError('not a Godot project')

    # The controls baseline smoke deliberately writes a dedicated test save. Remove only
    # that test artifact from every possible Godot user-data root before the second smoke.
    user_data_roots={
        Path.home()/'.local/share/godot/app_userdata',
        Path('/root/.local/share/godot/app_userdata'),
        Path('/github/home/.local/share/godot/app_userdata'),
    }
    for user_data_root in user_data_roots:
        if user_data_root.exists():
            for test_save in user_data_root.rglob('savegame.v14.smoke.json'):
                test_save.unlink()

    base_relative='assets/ui/runtime/splash_zanabal.svg'
    base_source=overlay/base_relative
    if not base_source.is_file(): raise RuntimeError(f'missing overlay file: {base_relative}')
    base_text=base_source.read_text(encoding='utf-8')
    generated={base_relative:base_text}
    for relative,(sky_a,sky_b,accent,night_orb) in VARIANTS.items():
        text=base_text.replace('#08111f',sky_a).replace('#422511',sky_b).replace('#d6a33b',accent)
        if night_orb:
            text=text.replace('cx="220" cy="160" r="130" fill="#ffd66b" opacity=".18"','cx="1020" cy="150" r="150" fill="#55d8ff" opacity=".12"')
        generated[relative]=text

    verified={}
    runtime_assets=set(manifest['runtime_assets'])
    for relative,expected in manifest['overlay_files'].items():
        destination=root/relative; destination.parent.mkdir(parents=True,exist_ok=True)
        if relative in generated:
            destination.write_text(generated[relative],encoding='utf-8')
        else:
            source=overlay/relative
            if not source.is_file(): raise RuntimeError(f'missing overlay file: {relative}')
            shutil.copy2(source,destination)
        actual={'bytes':destination.stat().st_size,'sha256':sha(destination)}
        if relative in runtime_assets and actual!=expected:
            raise RuntimeError(f'runtime asset identity mismatch: {relative}: {actual} != {expected}')
        verified[relative]=actual

    for relative in manifest['deleted_files']:
        path=root/relative
        if path.exists(): path.unlink()

    project=root/'project.godot'; text=project.read_text(encoding='utf-8')
    text=re.sub(r'(?m)^config/name=.*$', 'config/name="Bahrain Brick"', text)
    text=re.sub(r'(?m)^run/main_scene=.*$', 'run/main_scene="res://scenes/splash_screen.tscn"', text)
    text=re.sub(r'(?m)^boot_splash/image=.*\n?', '', text)
    if 'boot_splash/show_image=' in text:
        text=re.sub(r'(?m)^boot_splash/show_image=.*$', 'boot_splash/show_image=false', text)
    else:
        marker='boot_splash/bg_color=Color(0.05, 0.05, 0.08, 1)'
        if marker in text: text=text.replace(marker,'boot_splash/bg_color=Color(0.03, 0.05, 0.09, 1)\nboot_splash/show_image=false')
        else: text=text.replace('[application]','[application]\nboot_splash/show_image=false',1)
    project.write_text(text,encoding='utf-8')

    export=root/'export_presets.cfg'; text=export.read_text(encoding='utf-8')
    replacements={
        r'(?m)^export_path=.*$':'export_path="build/bahrain_brick_v14.0.3-graphics-qa.apk"',
        r'(?m)^version/code=.*$':'version/code=1403',
        r'(?m)^version/name=.*$':'version/name="1.4.0.3-graphics-qa"',
        r'(?m)^package/unique_name=.*$':'package/unique_name="com.bahrainbrick.game.qa"',
        r'(?m)^package/name=.*$':'package/name="Bahrain Brick"',
        r'(?m)^permissions/record_audio=.*$':'permissions/record_audio=false',
    }
    for pattern,replacement in replacements.items():
        text,count=re.subn(pattern,replacement,text)
        if count!=1: raise RuntimeError(f'export metadata patch failed: {pattern}, matches={count}')
    export.write_text(text,encoding='utf-8')

    hud=root/'scripts/hud.gd'; text=hud.read_text(encoding='utf-8')
    text=replace_function(text,'_on_pause_pressed','''func _on_pause_pressed() -> void:
\tif get_tree().paused:
\t\treturn
\tvar packed := load("res://scenes/pause_menu.tscn") as PackedScene
\tif packed:
\t\tvar pause_menu := packed.instantiate()
\t\tadd_child(pause_menu)''')
    hud.write_text(text,encoding='utf-8')

    cleanup=[(r'(?i)brick bahrain','Bahrain Brick'),(r'(?i)legends are brick','Bahrain Brick'),(r'(?i)v1\.3\.0 prototype',''),(r'(?i)lego loading','Loading')]
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS: continue
        relative=path.relative_to(root)
        if any(part in {'.git','.godot','build'} for part in relative.parts): continue
        content=path.read_text(encoding='utf-8',errors='replace'); updated=content
        for pattern,replacement in cleanup: updated=re.sub(pattern,replacement,updated)
        if updated!=content: path.write_text(updated,encoding='utf-8')

    hits=[]
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS: continue
        relative=path.relative_to(root)
        if any(part in {'.git','.godot','build'} for part in relative.parts): continue
        lower=path.read_text(encoding='utf-8',errors='replace').lower()
        for term in FORBIDDEN:
            if term in lower: hits.append(f'{relative.as_posix()}: {term}')
    if hits: raise RuntimeError('forbidden branding remains:\n'+'\n'.join(hits))

    report={'evidence_class':'VERIFIED','classification':'presentation overlay on frozen v1.4 controls baseline; not v15 authority','frozen_controls_commit':manifest['baseline_controls_commit'],'game_title':'Bahrain Brick','startup_sequence':['Zanabal Gaming','Mansoory Games','Bahrain Brick main menu'],'overlay_files':verified,'runtime_assets':{key:verified[key] for key in manifest['runtime_assets']},'deleted_obsolete_files':manifest['deleted_files'],'forbidden_text_hits':[]}
    args.report.parent.mkdir(parents=True,exist_ok=True); args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8'); print(json.dumps(report,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
