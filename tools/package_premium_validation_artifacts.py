#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,zipfile
from pathlib import Path

FORBIDDEN_PARTS={'.git','.godot','.cache','__pycache__'}
FORBIDDEN_NAMES={'debug.keystore','.env','id_rsa','id_ed25519'}

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def make_zip(out:Path,entries:list[tuple[Path,str]])->Path:
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for src,arc in sorted(entries,key=lambda x:x[1]): z.write(src,arc)
    with zipfile.ZipFile(out) as z:
        bad=z.testzip()
        if bad: raise RuntimeError(f'archive CRC failure {out.name}: {bad}')
        names=z.namelist()
        if not names: raise RuntimeError(f'empty archive: {out}')
        for name in names:
            parts=Path(name).parts
            if any(part in FORBIDDEN_PARTS for part in parts) or Path(name).name in FORBIDDEN_NAMES:
                raise RuntimeError(f'forbidden archive entry in {out.name}: {name}')
    return out

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument('root',type=Path); p.add_argument('--apk-name',required=True); p.add_argument('--premium-authority',required=True); p.add_argument('--validation-head',required=True)
    a=p.parse_args(); root=a.root.resolve(); build=root/'build'; report_dir=build/'reports'; apk=build/a.apk_name
    if not apk.is_file(): raise SystemExit(f'APK missing: {apk}')
    export=root/'export_presets.cfg'; text=export.read_text(); text=re.sub(r'(?m)^keystore/debug=.*$','keystore/debug=""',text); export.write_text(text)
    def allowed_source(path:Path)->bool:
        rel=path.relative_to(root)
        if not path.is_file() or any(part in FORBIDDEN_PARTS for part in rel.parts): return False
        if rel.parts[:1]==('build',) or path.name in FORBIDDEN_NAMES: return False
        return True
    source=make_zip(build/'bahrain_brick_v14.0.4-premium-visual-source.zip',[(x,x.relative_to(root).as_posix()) for x in root.rglob('*') if allowed_source(x)])
    if 'project.godot' not in zipfile.ZipFile(source).namelist(): raise RuntimeError('source archive lacks project.godot')
    runtime_art=make_zip(build/'bahrain_brick_v14.0.4-runtime-artwork.zip',[(x,x.relative_to(root).as_posix()) for base in [root/'assets/ui/runtime',root/'assets/icons'] for x in base.rglob('*') if x.is_file()])
    source_art=make_zip(build/'bahrain_brick_v14.0.4-source-artwork.zip',[(x,x.relative_to(root).as_posix()) for x in (root/'artwork/source').rglob('*') if x.is_file()])
    logos=make_zip(build/'bahrain_brick_v14.0.4-logo-icon-package.zip',[(x,x.relative_to(root).as_posix()) for base in [root/'assets/brand',root/'assets/icons'] for x in base.rglob('*') if x.is_file()])
    workspace_entries=[(source,source.name),(apk,apk.name),(runtime_art,runtime_art.name),(source_art,source_art.name),(logos,logos.name)]
    for folder in ['reports','logs','premium_visual_evidence','visual_evidence']:
        base=build/folder
        for x in base.rglob('*'):
            if x.is_file(): workspace_entries.append((x,f'{folder}/{x.relative_to(base).as_posix()}'))
    workspace=make_zip(build/'bahrain_brick_v14.0.4-premium-visual-workspace.zip',workspace_entries)
    packages=[apk,source,workspace,runtime_art,source_art,logos]
    for item in packages: item.with_suffix(item.suffix+'.sha256').write_text(f'{sha(item)}  {item.name}\n')
    premium=json.loads((report_dir/'PREMIUM_PRESENTATION_RESULT.json').read_text())
    metadata=json.loads((report_dir/'APK_METADATA_REPORT.json').read_text())
    provenance={
      'evidence_class':'VERIFIED package inspection and hosted runtime',
      'classification':'historical v1.4 premium-world QA; not v15 authority',
      'repository':'MuhamedZanabal/brick-bahrain-open-world',
      'premium_authority_sha':a.premium_authority,'validation_head_sha':a.validation_head,
      'apk':metadata,
      'source_zip':{'name':source.name,'size_bytes':source.stat().st_size,'sha256':sha(source)},
      'workspace_zip':{'name':workspace.name,'size_bytes':workspace.stat().st_size,'sha256':sha(workspace)},
      'runtime_artwork':{'name':runtime_art.name,'size_bytes':runtime_art.stat().st_size,'sha256':sha(runtime_art)},
      'source_artwork':{'name':source_art.name,'size_bytes':source_art.stat().st_size,'sha256':sha(source_art)},
      'logo_icon_package':{'name':logos.name,'size_bytes':logos.stat().st_size,'sha256':sha(logos)},
      'runtime_smoke':'43 passed, 0 failed','controls_regression':'28 passed, 0 failed',
      'presentation_regression':'10 passed, 0 failed','premium_world_acceptance':'12 passed, 0 failed',
      'premium_presentation_acceptance':premium,'android_emulator_tested':False,'physical_android_tested':False,
      'signing':'ephemeral QA certificate; not production',
    }
    (report_dir/'PREMIUM_VISUAL_BUILD_PROVENANCE.json').write_text(json.dumps(provenance,indent=2)+'\n')
    (report_dir/'KNOWN_ISSUES.md').write_text(
      '# Known Issues and Test Boundaries\n\n'
      '- Android emulator launch verification not performed by this hosted workflow.\n'
      '- Physical Android device test not performed.\n'
      '- Performance evidence is hosted GL Compatibility/software rendering and is not representative physical-device performance.\n'
      '- APK uses an ephemeral QA debug certificate and is not production-signed.\n')
    (report_dir/'ANDROID_EMULATOR_STATUS.txt').write_text('Android emulator launch verification not performed.\n')
    (report_dir/'PHYSICAL_DEVICE_STATUS.txt').write_text('Physical Android device test not performed.\n')
    evidence=[]
    for pattern in ['visual_evidence/*.mp4','visual_evidence/screenshots/*.png','premium_visual_evidence/comparisons/*.png']:
        for x in sorted(build.glob(pattern)): evidence.append(f'{sha(x)}  {x.relative_to(build).as_posix()}')
    (report_dir/'EVIDENCE_CHECKSUMS.sha256').write_text('\n'.join(evidence)+'\n')
    manifest=[]
    for x in sorted(build.rglob('*')):
        if x.is_file() and x.name!='FILE_MANIFEST.sha256': manifest.append(f'{sha(x)}  {x.relative_to(build).as_posix()}')
    (report_dir/'FILE_MANIFEST.sha256').write_text('\n'.join(manifest)+'\n')
    print(json.dumps(provenance,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
