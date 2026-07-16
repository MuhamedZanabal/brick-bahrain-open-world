#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,importlib.util,json,shutil,subprocess
from v3_patch_restore import apply_patch_isolated, restore_missing_new_files
from pathlib import Path

MODULE_PATH=Path(__file__).resolve().parent/'apply_bahrain_brick_premium_world_overlay.py'
spec=importlib.util.spec_from_file_location('premium_overlay_base',MODULE_PATH)
base=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(base)

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def ensure_svg_renderer()->None:
    if shutil.which('rsvg-convert'):
        return
    sudo=shutil.which('sudo')
    if not sudo:
        raise RuntimeError('rsvg-convert missing and sudo is unavailable')
    subprocess.run([sudo,'apt-get','update'],check=True)
    subprocess.run([sudo,'apt-get','install','-y','--no-install-recommends','librsvg2-bin'],check=True)
    if not shutil.which('rsvg-convert'):
        raise RuntimeError('librsvg2-bin installed but rsvg-convert is unavailable')

def apply_v3(project:Path,patch:bytes,expected:dict[str,str])->tuple[list[str],list[str]]:
    collisions=[]
    for relative in base._v3_new_file_paths(patch):
        if relative not in expected: raise RuntimeError(f'new file absent from manifest: {relative}')
        target=project/relative
        if target.exists():
            if not target.is_file(): raise RuntimeError(f'new-file collision is not a file: {relative}')
            target.unlink(); collisions.append(relative)
    apply_patch_isolated(project, patch)
    restored=restore_missing_new_files(project,patch,expected,set(base._v3_new_file_paths(patch)))
    for relative,digest in sorted(expected.items()):
        target=project/relative
        if not target.is_file(): raise RuntimeError(f'premium v3 output missing after deterministic restoration: {relative}')
        actual=sha(target)
        if actual!=digest: raise RuntimeError(f'premium v3 output hash mismatch for {relative}: expected {digest}, got {actual}')
    return sorted(expected),restored

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument('project_root',type=Path); p.add_argument('--report',type=Path,required=True)
    a=p.parse_args(); project=a.project_root.resolve(); tools=Path(__file__).resolve().parent
    if not (project/'project.godot').is_file(): raise SystemExit('project.godot missing')
    before={x:sha(project/x) for x in base.FROZEN}
    v2=base.load_v2_payload(tools); changed=base.apply_v2_overlay(project,v2,False)
    patch,manifest=base.load_v3_patch_and_manifest(tools)
    v3_files,restored=apply_v3(project,patch,manifest)
    post=base.apply_post_v3_replacements(project)
    ensure_svg_renderer()
    generated=base.generate_binary_artwork(project)+base.prepare_release_smoke_harness(project)
    changed=sorted(set(changed+v3_files+post+generated))
    after={x:sha(project/x) for x in base.FROZEN}; mismatches=[x for x in base.FROZEN if before[x]!=after[x]]
    if mismatches: raise SystemExit(f'frozen controls modified: {mismatches}')
    report={'evidence_class':'VERIFIED','classification':'premium world and presentation upgrade on historical v1.4 fallback; not v1.5 authority','base_integrated_source_sha256':base.EXPECTED_SOURCE_SHA256,'v2_payload_sha256':base.EXPECTED_V2_PAYLOAD_SHA256,'v3_patch_sha256':base.EXPECTED_V3_PATCH_SHA256,'v3_patch_gzip_sha256':base.EXPECTED_V3_PATCH_GZIP_SHA256,'v3_manifest_sha256':base.EXPECTED_V3_MANIFEST_SHA256,'overlay_files':changed,'v3_patched_files':v3_files,'deterministically_restored_new_files':restored,'post_v3_compatibility_fixes':post,'generated_binary_artwork':generated,'frozen_controls_unchanged':True,'frozen_control_hashes':after}
    a.report.parent.mkdir(parents=True,exist_ok=True); a.report.write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
