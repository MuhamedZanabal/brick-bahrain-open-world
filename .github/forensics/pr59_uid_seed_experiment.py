#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, shutil, zipfile
from pathlib import Path
from typing import Any
BASE_PATH=Path(__file__).with_name('pr59_import_experiments.py')
spec=importlib.util.spec_from_file_location('expbase',BASE_PATH);base=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(base)
def write_json(p:Path,v:Any)->None:base.write_json(p,v)
def sha(p:Path)->str:return base.sha256_file(p)
def source_manifest(source_zip:Path)->dict[str,Any]:
 rows=[]
 with zipfile.ZipFile(source_zip) as z:
  for info in sorted((x for x in z.infolist() if not x.is_dir()),key=lambda x:x.filename):
   data=z.read(info);rows.append({'path':info.filename,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 return {'source_zip_sha256':sha(source_zip),'file_count':len(rows),'total_bytes':sum(r['bytes'] for r in rows),'files':rows}
def verify_source(root:Path,manifest:dict[str,Any])->dict[str,Any]:
 failures=[]
 for r in manifest['files']:
  p=root/r['path']
  if not p.is_file():failures.append({'path':r['path'],'reason':'missing'});continue
  actual={'bytes':p.stat().st_size,'sha256':sha(p)}
  if actual['bytes']!=r['bytes'] or actual['sha256']!=r['sha256']:failures.append({'path':r['path'],'reason':'content_mismatch','expected_bytes':r['bytes'],'actual_bytes':actual['bytes'],'expected_sha256':r['sha256'],'actual_sha256':actual['sha256']})
 return {'passed':not failures,'expected':manifest['file_count'],'failures':failures}
def verify_seed(seed_zip:Path,manifest:dict[str,Any],check_archive:bool=True)->dict[str,Any]:
 failures=[]
 if check_archive and sha(seed_zip)!=manifest['archive_sha256']:failures.append({'reason':'archive_sha256'})
 records={r['path']:r for r in manifest['records']}
 with zipfile.ZipFile(seed_zip) as z:
  infos=[i for i in z.infolist() if not i.is_dir()];names=[i.filename for i in infos]
  if len(names)!=len(set(names)):failures.append({'reason':'duplicate_paths'})
  if any(not n.endswith('.import') or n.startswith('.godot/') or n.startswith('/') or '..' in Path(n).parts or '\\' in n for n in names):failures.append({'reason':'forbidden_path'})
  if set(names)!=set(records):failures.append({'reason':'path_set'})
  for n in names:
   data=z.read(n);r=records.get(n)
   if not r or len(data)!=r['bytes'] or hashlib.sha256(data).hexdigest()!=r['sha256']:failures.append({'reason':'content','path':n})
 return {'passed':not failures,'sidecar_count':len(records),'failures':failures}
def generate(args:argparse.Namespace)->int:
 src=Path(args.source_zip);godot=Path(args.godot);out=Path(args.output);work=Path(args.work_root);out.mkdir(parents=True,exist_ok=True)
 sm=source_manifest(src);write_json(out/'SOURCE_CONTENT_MANIFEST.json',sm)
 base.run_import('seed_generation',src,godot,work/'game',315532800,out,work/'xdg')
 source_paths={r['path'] for r in sm['files']};seed=[]
 for p in sorted((work/'game').rglob('*.import')):
  rel=p.relative_to(work/'game').as_posix()
  if rel in source_paths:continue
  data=p.read_bytes();logical=rel[:-7];source=work/'game'/logical;meta=base.import_metadata(p)
  if not source.is_file() or not meta['uid']:raise RuntimeError({'path':rel,'source_exists':source.is_file(),'metadata':meta})
  seed.append({'path':rel,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'uid':meta['uid'],'logical_source':logical,'source_bytes':source.stat().st_size,'source_sha256':sha(source)})
 if len(seed)!=1455:raise RuntimeError(f'expected 1455 new sidecars, found {len(seed)}')
 seed_zip=out/'GODOT_IMPORT_UID_SIDECARS_V1.zip'
 with zipfile.ZipFile(seed_zip,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for r in seed:
   data=(work/'game'/r['path']).read_bytes();zi=zipfile.ZipInfo(r['path'],(1980,1,1,0,0,0));zi.compress_type=zipfile.ZIP_DEFLATED;zi.external_attr=(0o100644)<<16;z.writestr(zi,data)
 manifest={'schema_version':1,'authority':'Godot 4.3 source-controlled import sidecars','sidecar_count':len(seed),'archive_sha256':sha(seed_zip),'archive_bytes':seed_zip.stat().st_size,'records':seed}
 write_json(out/'GODOT_IMPORT_UID_SIDECARS_V1.json',manifest);assert verify_seed(seed_zip,manifest)['passed'];return 0
def overlay(seed_zip:Path,game:Path)->None:
 with zipfile.ZipFile(seed_zip) as z:
  for info in sorted(z.infolist(),key=lambda x:x.filename):
   p=game/info.filename;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(info));os.chmod(p,0o644);os.utime(p,(315532800,315532800))
def verify_seed_in_tree(game:Path,manifest:dict[str,Any])->dict[str,Any]:
 failures=[]
 for r in manifest['records']:
  p=game/r['path']
  if not p.is_file():failures.append({'path':r['path'],'reason':'missing'})
  elif p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:failures.append({'path':r['path'],'reason':'changed'})
 return {'passed':not failures,'failures':failures}
def run_seeded(args:argparse.Namespace)->int:
 src=Path(args.source_zip);godot=Path(args.godot);seed=Path(args.seed_zip);seed_manifest=json.loads(Path(args.seed_manifest).read_text());sm=json.loads(Path(args.source_manifest).read_text());out=Path(args.output);work=Path(args.work_root);game=work/'game';out.mkdir(parents=True,exist_ok=True)
 sv=verify_seed(seed,seed_manifest);write_json(out/'SEED_ARCHIVE_VERIFICATION.json',sv);assert sv['passed'],sv
 base.materialize(src,game,315532800);source_check=verify_source(game,sm);write_json(out/'SOURCE_VERIFICATION.json',source_check);assert source_check['passed'],source_check
 overlay(seed,game);before_seed=verify_seed_in_tree(game,seed_manifest);assert before_seed['passed']
 before=base.metadata_manifest(game);xdg=work/'xdg';shutil.rmtree(xdg,ignore_errors=True);xdg.mkdir(parents=True)
 env=os.environ.copy();env.update({'TZ':'UTC','LC_ALL':'C.UTF-8','LANG':'C.UTF-8','XDG_DATA_HOME':str(xdg)});old=os.umask(0o022)
 try:run=base.run_cmd([str(godot),'--headless','--path',str(game),'--editor','--import','--quit','--verbose'],out/f'{args.label}.godot.log',env,1800)
 finally:os.umask(old)
 generated=base.generated_inventory(game);after_seed=verify_seed_in_tree(game,seed_manifest)
 result={'label':args.label,'source_metadata_before_import':before,'source_verification':source_check,'seed_verification_before_import':before_seed,'seed_verification_after_import':after_seed,'run':run,'generated':generated}
 write_json(out/'SEEDED_IMPORT_RESULT.json',result)
 if run['exit_code'] or run['error_pattern_count'] or not after_seed['passed']:raise RuntimeError(result)
 return 0
def negative(args:argparse.Namespace)->int:
 src=Path(args.source_zip);seed=Path(args.seed_zip);seed_manifest=json.loads(Path(args.seed_manifest).read_text());sm=json.loads(Path(args.source_manifest).read_text());work=Path(args.work_root);out=Path(args.output);out.mkdir(parents=True,exist_ok=True);results={}
 game=work/'mutation';base.materialize(src,game,315532800);p=game/sm['files'][0]['path'];data=p.read_bytes();p.write_bytes(bytes([data[0]^1])+data[1:]);results['one_byte_source_mutation_rejected']=not verify_source(game,sm)['passed']
 game=work/'missing';base.materialize(src,game,315532800);(game/sm['files'][0]['path']).unlink();results['missing_source_rejected']=not verify_source(game,sm)['passed']
 game=work/'matrix';base.materialize(src,game,315532800);matrix_rec=next(r for r in sm['files'] if r['path'].lower().endswith('.glb'));mp=game/matrix_rec['path'];d=mp.read_bytes();mp.write_bytes(bytes([d[0]^1])+d[1:]);results['changed_matrix_resource_rejected']=not verify_source(game,sm)['passed']
 bad=out/'mutated_seed.zip';shutil.copy2(seed,bad)
 with zipfile.ZipFile(bad,'a') as z:
  r=seed_manifest['records'][0];z.writestr(r['path'],b'changed importer setting')
 results['changed_importer_metadata_rejected']=not verify_seed(bad,seed_manifest,check_archive=False)['passed']
 with zipfile.ZipFile(seed) as z:names=[i.filename for i in z.infolist() if not i.is_dir()]
 results['no_generated_resource_copied']=all(n.endswith('.import') and not n.startswith('.godot/') for n in names)
 results['all_negative_controls_passed']=all(results.values());write_json(out/'NEGATIVE_TESTS.json',results);return 0 if results['all_negative_controls_passed'] else 1
def compare_cmd(args:argparse.Namespace)->int:
 a=json.loads((Path(args.a)/'SEEDED_IMPORT_RESULT.json').read_text());b=json.loads((Path(args.b)/'SEEDED_IMPORT_RESULT.json').read_text());result=base.compare(a,b);result['correction_candidate_authorized']=result['content_difference_count']==0 and result['uid_difference_count']==0 and result['path_set_equal'];Path(args.output).mkdir(parents=True,exist_ok=True);write_json(Path(args.output)/'SEEDED_IMPORT_COMPARISON.json',result);return 0 if result['correction_candidate_authorized'] else 1
def main()->int:
 p=argparse.ArgumentParser();s=p.add_subparsers(dest='cmd',required=True)
 q=s.add_parser('generate');q.add_argument('--source-zip',required=True);q.add_argument('--godot',required=True);q.add_argument('--work-root',required=True);q.add_argument('--output',required=True);q.set_defaults(fn=generate)
 q=s.add_parser('run')
 for n in ('source-zip','godot','seed-zip','seed-manifest','source-manifest','work-root','output','label'):q.add_argument('--'+n,required=True)
 q.set_defaults(fn=run_seeded)
 q=s.add_parser('negative')
 for n in ('source-zip','seed-zip','seed-manifest','source-manifest','work-root','output'):q.add_argument('--'+n,required=True)
 q.set_defaults(fn=negative)
 q=s.add_parser('compare');q.add_argument('--a',required=True);q.add_argument('--b',required=True);q.add_argument('--output',required=True);q.set_defaults(fn=compare_cmd)
 a=p.parse_args();return a.fn(a)
if __name__=='__main__':raise SystemExit(main())