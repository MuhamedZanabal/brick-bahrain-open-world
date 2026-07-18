#!/usr/bin/env python3
from __future__ import annotations
import argparse, collections, hashlib, json, os, re, shutil, stat, subprocess, time, zipfile
from pathlib import Path, PurePosixPath
from typing import Any

EXPECTED_SOURCE_FILES=1502
EXPECTED_SOURCE_BYTES=369162800
EXPECTED_MATRIX_SHA='6aa202e2298fa514bfdb2ba10fd66237cc2d15005cdb2d6316a57d847ece8eff'
UID_RE=re.compile(r'(?m)^uid=("uid://[^"]+")\s*$')
PATH_RE=re.compile(r'(?m)^path="res://([^"\r\n]+)"\s*$')
ERROR_RE=re.compile(r'SCRIPT ERROR|Parse Error|Parser Error|Failed to load script|Failed to create an autoload|\bFATAL\b|Fatal signal',re.I)

def sha256_file(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
 return h.hexdigest()

def write_json(p:Path,v:Any)->None:
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')

def safe_rel(name:str)->str:
 if name.startswith('/') or '\\' in name or '..' in PurePosixPath(name).parts: raise ValueError(name)
 return name.rstrip('/')

def materialize(source_zip:Path,target:Path,epoch:int)->dict[str,Any]:
 if target.exists(): shutil.rmtree(target)
 target.mkdir(parents=True)
 files=0;total=0;dirs=[]
 with zipfile.ZipFile(source_zip) as z:
  infos=sorted(z.infolist(),key=lambda i:i.filename)
  for info in infos:
   rel=safe_rel(info.filename)
   if not rel: continue
   dst=target/rel
   if info.is_dir(): dst.mkdir(parents=True,exist_ok=True);dirs.append(dst);continue
   dst.parent.mkdir(parents=True,exist_ok=True)
   dst.write_bytes(z.read(info));files+=1;total+=info.file_size
   mode=(info.external_attr>>16)&0o777
   os.chmod(dst,mode or 0o644);os.utime(dst,(epoch,epoch),follow_symlinks=False)
 for d in sorted({target,*dirs,*[p for p in target.rglob('*') if p.is_dir()]},key=lambda p:len(p.parts),reverse=True):
  os.chmod(d,0o755);os.utime(d,(epoch,epoch),follow_symlinks=False)
 matrix=target/'asset_lab/runtime/full_asset_matrix_manifest.json'
 result={'source_zip':str(source_zip),'source_zip_sha256':sha256_file(source_zip),'target':str(target.resolve()),'epoch':epoch,'file_count':files,'total_bytes':total,'matrix_sha256':sha256_file(matrix) if matrix.is_file() else None}
 if files!=EXPECTED_SOURCE_FILES or total!=EXPECTED_SOURCE_BYTES or result['matrix_sha256']!=EXPECTED_MATRIX_SHA: raise RuntimeError(result)
 return result

def metadata_manifest(root:Path)->dict[str,Any]:
 rows=[]
 for p in sorted(root.rglob('*'),key=lambda p:p.relative_to(root).as_posix()):
  rel=p.relative_to(root).as_posix();st=p.lstat()
  rows.append({'path':rel,'type':'dir' if p.is_dir() else 'file','bytes':st.st_size if p.is_file() else 0,'sha256':sha256_file(p) if p.is_file() else None,'mtime_ns':st.st_mtime_ns,'atime_ns':st.st_atime_ns,'mode':stat.S_IMODE(st.st_mode),'uid':st.st_uid,'gid':st.st_gid,'symlink':p.is_symlink()})
 return {'root':str(root.resolve()),'records':rows,'file_count':sum(1 for r in rows if r['type']=='file'),'total_file_bytes':sum(r['bytes'] for r in rows if r['type']=='file')}

def import_metadata(p:Path)->dict[str,Any]:
 data=p.read_bytes();terminal=data.endswith(b'\0')
 if terminal:data=data[:-1]
 text=data.decode('utf-8',errors='replace');uid=UID_RE.search(text);target=PATH_RE.search(text)
 return {'uid':uid.group(1) if uid else None,'path':target.group(1) if target else None,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'terminal_nul':terminal}

def generated_inventory(game:Path)->dict[str,Any]:
 rows=[];imports={}
 for p in sorted(game.rglob('*'),key=lambda p:p.relative_to(game).as_posix()):
  if not p.is_file():continue
  rel=p.relative_to(game).as_posix()
  if rel.startswith('.godot/') or rel.endswith('.import'):
   row={'path':rel,'bytes':p.stat().st_size,'sha256':sha256_file(p)};rows.append(row)
   if rel.endswith('.import'):imports[rel]=import_metadata(p)
 aggregate=hashlib.sha256('\n'.join(f"{r['path']}\0{r['bytes']}\0{r['sha256']}" for r in rows).encode()).hexdigest()
 uidp=game/'.godot/uid_cache.bin'
 return {'root':str(game.resolve()),'file_count':len(rows),'aggregate_sha256':aggregate,'records':rows,'import_count':len(imports),'imports':imports,'uid_cache':{'exists':uidp.is_file(),'bytes':uidp.stat().st_size if uidp.is_file() else None,'sha256':sha256_file(uidp) if uidp.is_file() else None}}

def current_umask()->int:
 old=os.umask(0);os.umask(old);return old

def selected_env()->dict[str,Any]:
 keys=['TZ','LC_ALL','LANG','HOME','XDG_DATA_HOME','RUNNER_OS','RUNNER_ARCH','ImageOS','ImageVersion','GITHUB_JOB','GITHUB_RUN_ID']
 return {k:os.environ.get(k) for k in keys}|{'cpu_count':os.cpu_count(),'cwd':os.getcwd(),'umask':oct(current_umask())}

def run_cmd(cmd:list[str],log:Path,env:dict[str,str],timeout:int=1200)->dict[str,Any]:
 log.parent.mkdir(parents=True,exist_ok=True);start=time.time()
 with log.open('wb') as f:p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,timeout=timeout,check=False)
 data=log.read_bytes();return {'command':cmd,'exit_code':p.returncode,'elapsed_seconds':round(time.time()-start,3),'log':str(log),'log_bytes':len(data),'log_sha256':hashlib.sha256(data).hexdigest(),'error_pattern_count':len(ERROR_RE.findall(data.decode(errors='replace')))}

def run_import(label:str,source_zip:Path,godot:Path,game:Path,epoch:int,out:Path,xdg:Path)->dict[str,Any]:
 mat=materialize(source_zip,game,epoch);before=metadata_manifest(game)
 if xdg.exists():shutil.rmtree(xdg)
 xdg.mkdir(parents=True);env=os.environ.copy();env.update({'TZ':'UTC','LC_ALL':'C.UTF-8','LANG':'C.UTF-8','XDG_DATA_HOME':str(xdg)})
 old=os.umask(0o022)
 try:run=run_cmd([str(godot),'--headless','--path',str(game),'--editor','--import','--quit','--verbose'],out/f'{label}.godot.log',env,1800)
 finally:os.umask(old)
 inv=generated_inventory(game);result={'label':label,'materialization':mat,'source_metadata_before_import':before,'environment':selected_env()|{'effective_env':{k:env.get(k) for k in ('TZ','LC_ALL','LANG','XDG_DATA_HOME')}},'run':run,'generated':inv}
 write_json(out/f'{label}.json',result)
 if run['exit_code']!=0 or run['error_pattern_count']!=0 or not inv['uid_cache']['exists']:raise RuntimeError(result)
 return result

def compare(a:dict[str,Any],b:dict[str,Any])->dict[str,Any]:
 am={r['path']:r for r in a['generated']['records']};bm={r['path']:r for r in b['generated']['records']};paths=sorted(set(am)|set(bm));diff=[];cats=collections.Counter()
 for p in paths:
  if p not in am or p not in bm:diff.append({'path':p,'missing_a':p not in am,'missing_b':p not in bm});cats['PATH_SET']+=1
  elif am[p]['sha256']!=bm[p]['sha256']:
   cat='IMPORT_METADATA' if p.endswith('.import') else ('GODOT_IMPORTED' if p.startswith('.godot/imported/') else ('GODOT_EXPORTED' if p.startswith('.godot/exported/') else ('UID_CACHE' if p=='.godot/uid_cache.bin' else 'OTHER')))
   cats[cat]+=1;diff.append({'path':p,'category':cat,'a':am[p],'b':bm[p]})
 ai=a['generated']['imports'];bi=b['generated']['imports'];uid_diffs=[p for p in sorted(set(ai)&set(bi)) if ai[p]['uid']!=bi[p]['uid']]
 return {'a':a['label'],'b':b['label'],'path_set_equal':set(am)==set(bm),'generated_file_count_a':len(am),'generated_file_count_b':len(bm),'content_difference_count':len(diff),'category_counts':dict(sorted(cats.items())),'uid_difference_count':len(uid_diffs),'first_25_uid_differences':uid_diffs[:25],'uid_cache_equal':a['generated']['uid_cache']==b['generated']['uid_cache'],'aggregate_equal':a['generated']['aggregate_sha256']==b['generated']['aggregate_sha256'],'differences':diff}

def snapshot_import(game:Path,dest:Path)->None:
 if dest.exists():dest.unlink()
 with zipfile.ZipFile(dest,'w',zipfile.ZIP_STORED) as z:
  for p in sorted(game.rglob('*'),key=lambda p:p.relative_to(game).as_posix()):
   if p.is_file():
    rel=p.relative_to(game).as_posix()
    if rel.startswith('.godot/') or rel.endswith('.import'):z.write(p,rel)

def overlay_snapshot(snapshot:Path,game:Path)->None:
 with zipfile.ZipFile(snapshot) as z:
  for info in sorted(z.infolist(),key=lambda i:i.filename):
   rel=safe_rel(info.filename);dst=game/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(z.read(info))

def run_export_pack(label:str,source_zip:Path,godot:Path,snapshot:Path,game:Path,out:Path,xdg:Path)->dict[str,Any]:
 materialize(source_zip,game,315532800);overlay_snapshot(snapshot,game);before=generated_inventory(game)
 if xdg.exists():shutil.rmtree(xdg)
 xdg.mkdir(parents=True);env=os.environ.copy();env.update({'TZ':'UTC','LC_ALL':'C.UTF-8','LANG':'C.UTF-8','XDG_DATA_HOME':str(xdg)})
 pck=out/f'{label}.pck';run=run_cmd([str(godot),'--headless','--path',str(game),'--export-pack','Android',str(pck),'--verbose'],out/f'{label}.export.log',env,1800);after=generated_inventory(game)
 result={'label':label,'run':run,'input_cache':before,'post_export_cache':after,'input_cache_aggregate_unchanged':before['aggregate_sha256']==after['aggregate_sha256'],'pack':{'exists':pck.is_file(),'bytes':pck.stat().st_size if pck.is_file() else None,'sha256':sha256_file(pck) if pck.is_file() else None}}
 write_json(out/f'{label}.json',result);return result

def suite(args:argparse.Namespace)->int:
 out=Path(args.output);out.mkdir(parents=True,exist_ok=True);src=Path(args.source_zip);godot=Path(args.godot);base=Path(args.work_root)
 write_json(out/'GODOT_AUTHORITY.json',{'version':subprocess.check_output([str(godot),'--version'],text=True).strip(),'binary_sha256':sha256_file(godot),'help_sha256':hashlib.sha256(subprocess.check_output([str(godot),'--help'])).hexdigest()})
 a1=run_import('A1_same_path',src,godot,base/'canonical/game',315532800,out,base/'xdg');snap=base/'verified_import_snapshot.zip';snapshot_import(base/'canonical/game',snap)
 a2=run_import('A2_same_path',src,godot,base/'canonical/game',315532800,out,base/'xdg');write_json(out/'EXPERIMENT_A.json',compare(a1,a2))
 b1=run_import('B1_path_a',src,godot,base/'path-a/game',315532800,out,base/'xdg');b2=run_import('B2_path_b',src,godot,base/'path-b/game',315532800,out,base/'xdg');write_json(out/'EXPERIMENT_B.json',compare(b1,b2))
 c1=run_import('C1_epoch_1980',src,godot,base/'timestamp/game',315532800,out,base/'xdg');c2=run_import('C2_epoch_2000',src,godot,base/'timestamp/game',946684800,out,base/'xdg');write_json(out/'EXPERIMENT_C.json',compare(c1,c2))
 e1=run_export_pack('E1_shared_cache_export',src,godot,snap,base/'export-e1/game',out,base/'xdg-e1');e2=run_export_pack('E2_shared_cache_export',src,godot,snap,base/'export-e2/game',out,base/'xdg-e2')
 write_json(out/'EXPERIMENT_E.json',{'e1':e1,'e2':e2,'pack_both_exist':e1['pack']['exists'] and e2['pack']['exists'],'pack_sha_equal':e1['pack']['sha256']==e2['pack']['sha256'] if e1['pack']['exists'] and e2['pack']['exists'] else None})
 for p in out.glob('*.pck'):p.unlink()
 return 0

def single(args:argparse.Namespace)->int:
 out=Path(args.output);out.mkdir(parents=True,exist_ok=True);r=run_import(args.label,Path(args.source_zip),Path(args.godot),Path(args.work_root)/'canonical/game',315532800,out,Path(args.work_root)/'xdg');write_json(out/'EXPERIMENT_D_SINGLE.json',r);return 0

def aggregate(args:argparse.Namespace)->int:
 out=Path(args.output);out.mkdir(parents=True,exist_ok=True);suite_root=Path(args.suite);d1=json.loads((Path(args.d1)/'EXPERIMENT_D_SINGLE.json').read_text());d2=json.loads((Path(args.d2)/'EXPERIMENT_D_SINGLE.json').read_text());dc=compare(d1,d2);write_json(out/'EXPERIMENT_D.json',dc)
 a=json.loads((suite_root/'EXPERIMENT_A.json').read_text());b=json.loads((suite_root/'EXPERIMENT_B.json').read_text());c=json.loads((suite_root/'EXPERIMENT_C.json').read_text());e=json.loads((suite_root/'EXPERIMENT_E.json').read_text());random_proven=a['uid_difference_count']>0 and a['content_difference_count']>0
 write_json(out/'ROOT_CAUSE_CLASSIFICATION.json',{'classification':'RESOURCE_UID_GENERATION_NONDETERMINISM' if random_proven else 'EVIDENCE_INSUFFICIENT','causality':{'same_path_same_metadata_sequential_uid_differences':a['uid_difference_count'],'same_path_same_metadata_content_differences':a['content_difference_count'],'absolute_path_experiment_uid_differences':b['uid_difference_count'],'timestamp_experiment_uid_differences':c['uid_difference_count'],'separate_runner_uid_differences':dc['uid_difference_count'],'shared_cache_export_pack_sha_equal':e['pack_sha_equal']},'correction_authorized':False,'reason':'Intrinsic random UID generation is proven, but no supported deterministic correction has yet been validated by a controlled preservation experiment.'});return 0

def main()->int:
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True)
 q=sub.add_parser('suite');q.add_argument('--source-zip',required=True);q.add_argument('--godot',required=True);q.add_argument('--work-root',required=True);q.add_argument('--output',required=True);q.set_defaults(fn=suite)
 q=sub.add_parser('single');q.add_argument('--source-zip',required=True);q.add_argument('--godot',required=True);q.add_argument('--work-root',required=True);q.add_argument('--output',required=True);q.add_argument('--label',required=True);q.set_defaults(fn=single)
 q=sub.add_parser('aggregate');q.add_argument('--suite',required=True);q.add_argument('--d1',required=True);q.add_argument('--d2',required=True);q.add_argument('--output',required=True);q.set_defaults(fn=aggregate)
 a=p.parse_args();return a.fn(a)
if __name__=='__main__':raise SystemExit(main())