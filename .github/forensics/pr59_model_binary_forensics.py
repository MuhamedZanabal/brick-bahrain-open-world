#!/usr/bin/env python3
from __future__ import annotations
import argparse, collections, hashlib, json, os, re, shutil, stat, subprocess, sys, time, zipfile
from pathlib import Path, PurePosixPath
from typing import Any

SOURCE_SHA='5ca9ff72aaaddeb9d86fb02c2fe99de5da280988b3945c4c627e80effeb01aa7'
SOURCE_BYTES=225721731
SOURCE_FILES=1502
SOURCE_TOTAL_BYTES=369162800
MATRIX_SHA='6aa202e2298fa514bfdb2ba10fd66237cc2d15005cdb2d6316a57d847ece8eff'
GODOT_VERSION='4.3.stable.official.77dcf97d8'
MODEL_EXTS={'.glb','.gltf','.fbx','.obj'}
UID_RE=re.compile(r'(?m)^uid=("uid://[^"]+")\s*$')
PATH_RE=re.compile(r'(?m)^path="res://([^"\r\n]+)"\s*$')
SOURCE_RE=re.compile(r'(?m)^source_file="res://([^"\r\n]+)"\s*$')
ERROR_RE=re.compile(r'SCRIPT ERROR|Parse Error|Parser Error|Failed to load script|Failed to create an autoload|\bFATAL\b|Fatal signal',re.I)
ASCII_RE=re.compile(rb'[ -~]{4,}')
UID_BYTES_RE=re.compile(rb'uid://[A-Za-z0-9_]+')
RES_BYTES_RE=re.compile(rb'res://[^\x00\r\n" ]+')
ABS_BYTES_RE=re.compile(rb'(?:/[A-Za-z0-9._-]+){3,}|[A-Za-z]:\\[^\x00\r\n]+')
DATE_BYTES_RE=re.compile(rb'20\d\d[-/:]\d\d[-/:]\d\d(?:[T ][0-9:.+Z-]+)?')
RANDOM_BYTES_RE=re.compile(rb'(?<![A-Za-z0-9])[A-Za-z0-9_]{13,}(?![A-Za-z0-9])')

def sha_bytes(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def sha_file(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()
def write_json(p:Path,v:Any)->None:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def safe_rel(name:str)->str:
 if name.startswith('/') or '\\' in name or '..' in PurePosixPath(name).parts:raise ValueError(name)
 return name.rstrip('/')
def run(cmd:list[str],log:Path,env:dict[str,str]|None=None,timeout:int=2400)->dict[str,Any]:
 log.parent.mkdir(parents=True,exist_ok=True);start=time.time()
 with log.open('wb') as f:
  try:p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,timeout=timeout,check=False);code=p.returncode;timed=False
  except subprocess.TimeoutExpired:code=124;timed=True
 data=log.read_bytes();return {'command':cmd,'exit_code':code,'timed_out':timed,'elapsed_seconds':round(time.time()-start,3),'log':str(log),'log_bytes':len(data),'log_sha256':sha_bytes(data),'error_pattern_count':len(ERROR_RE.findall(data.decode(errors='replace')))}
def materialize(source_zip:Path,target:Path,epoch:int=315532800)->dict[str,Any]:
 if target.exists():shutil.rmtree(target)
 target.mkdir(parents=True);count=0;total=0;dirs=[]
 with zipfile.ZipFile(source_zip) as z:
  infos=sorted(z.infolist(),key=lambda i:i.filename)
  for info in infos:
   rel=safe_rel(info.filename)
   if not rel:continue
   dst=target/rel
   if info.is_dir():dst.mkdir(parents=True,exist_ok=True);dirs.append(dst);continue
   dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(z.read(info));count+=1;total+=info.file_size
   mode=(info.external_attr>>16)&0o777;os.chmod(dst,mode or 0o644);os.utime(dst,(epoch,epoch),follow_symlinks=False)
 for d in sorted({target,*dirs,*[p for p in target.rglob('*') if p.is_dir()]},key=lambda p:len(p.parts),reverse=True):
  os.chmod(d,0o755);os.utime(d,(epoch,epoch),follow_symlinks=False)
 matrix=target/'asset_lab/runtime/full_asset_matrix_manifest.json'
 result={'source_zip_sha256':sha_file(source_zip),'source_zip_bytes':source_zip.stat().st_size,'file_count':count,'total_bytes':total,'matrix_sha256':sha_file(matrix),'target':str(target.resolve()),'epoch':epoch}
 assert result['source_zip_sha256']==SOURCE_SHA and result['source_zip_bytes']==SOURCE_BYTES and count==SOURCE_FILES and total==SOURCE_TOTAL_BYTES and result['matrix_sha256']==MATRIX_SHA,result
 return result
def overlay_zip(archive:Path,root:Path,epoch:int=315532800)->None:
 with zipfile.ZipFile(archive) as z:
  infos=[i for i in z.infolist() if not i.is_dir()]
  names=[safe_rel(i.filename) for i in infos];assert len(names)==len(set(names))
  for info in sorted(infos,key=lambda i:i.filename):
   dst=root/safe_rel(info.filename);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(z.read(info));os.chmod(dst,0o644);os.utime(dst,(epoch,epoch))
def parse_import(data:bytes)->dict[str,Any]:
 terminal=data.endswith(b'\0');text=data[:-1].decode('utf-8','replace') if terminal else data.decode('utf-8','replace')
 uid=UID_RE.search(text);target=PATH_RE.search(text);source=SOURCE_RE.search(text)
 return {'uid':uid.group(1) if uid else None,'path':target.group(1) if target else None,'source_file':source.group(1) if source else None,'terminal_nul':terminal,'bytes':len(data),'sha256':sha_bytes(data)}
def parse_md5(data:bytes)->dict[str,Any]:
 text=data.decode('utf-8','replace');fields={};malformed=[]
 for no,line in enumerate(text.splitlines(),1):
  line=line.strip()
  if not line:continue
  m=re.fullmatch(r'([A-Za-z0-9_./-]+)="([^"]*)"',line)
  if not m:malformed.append({'line':no,'text':line});continue
  if m.group(1) in fields:malformed.append({'line':no,'text':line,'reason':'duplicate'})
  fields[m.group(1)]=m.group(2)
 return {'text':text,'fields':fields,'malformed':malformed,'bytes':len(data),'sha256':sha_bytes(data)}
def generated_inventory(game:Path)->dict[str,Any]:
 rows=[];imports={}
 for p in sorted(game.rglob('*'),key=lambda p:p.relative_to(game).as_posix()):
  if not p.is_file():continue
  rel=p.relative_to(game).as_posix()
  if rel.startswith('.godot/') or rel.endswith('.import'):
   rows.append({'path':rel,'bytes':p.stat().st_size,'sha256':sha_file(p)})
   if rel.endswith('.import'):imports[rel]=parse_import(p.read_bytes())
 aggregate=sha_bytes('\n'.join(f"{r['path']}\0{r['bytes']}\0{r['sha256']}" for r in rows).encode())
 uid=game/'.godot/uid_cache.bin'
 return {'file_count':len(rows),'aggregate_sha256':aggregate,'records':rows,'imports':imports,'import_count':len(imports),'uid_cache':{'exists':uid.is_file(),'bytes':uid.stat().st_size if uid.is_file() else None,'sha256':sha_file(uid) if uid.is_file() else None}}
def compare_inventories(a:dict[str,Any],b:dict[str,Any])->dict[str,Any]:
 am={r['path']:r for r in a['records']};bm={r['path']:r for r in b['records']};paths=sorted(set(am)|set(bm));diff=[];cats=collections.Counter()
 for p in paths:
  if p not in am or p not in bm:cats['PATH_SET']+=1;diff.append({'path':p,'missing_d1':p not in am,'missing_d2':p not in bm});continue
  if am[p]['sha256']==bm[p]['sha256']:continue
  if p.endswith('.import'):cat='SOURCE_ADJACENT_IMPORT'
  elif p=='.godot/uid_cache.bin':cat='UID_CACHE'
  elif p=='.godot/editor/filesystem_cache8':cat='EDITOR_CACHE'
  elif p.startswith('.godot/imported/') and p.endswith('.md5'):cat='IMPORTED_MD5'
  elif p.startswith('.godot/imported/'):cat='IMPORTED_BINARY'
  else:cat='OTHER'
  cats[cat]+=1;diff.append({'path':p,'category':cat,'d1':am[p],'d2':bm[p]})
 ai=a.get('imports',{});bi=b.get('imports',{});common=sorted(set(ai)&set(bi))
 uid=[p for p in common if ai[p].get('uid')!=bi[p].get('uid')]
 content=[p for p in common if ai[p].get('sha256')!=bi[p].get('sha256')]
 dest=[p for p in common if ai[p].get('path')!=bi[p].get('path')]
 size=[p for p in common if ai[p].get('bytes')!=bi[p].get('bytes')]
 return {'path_set_equal':set(am)==set(bm),'d1_file_count':len(am),'d2_file_count':len(bm),'total_content_differences':len(diff),'category_counts':dict(sorted(cats.items())),'source_adjacent_import_uid_differences':len(uid),'source_adjacent_import_content_differences':len(content),'source_adjacent_import_destination_path_differences':len(dest),'source_adjacent_import_byte_size_differences':len(size),'uid_cache_equal':a.get('uid_cache')==b.get('uid_cache'),'differences':diff}
def matrix_paths(source_zip:Path)->set[str]:
 with zipfile.ZipFile(source_zip) as z:m=json.loads(z.read('asset_lab/runtime/full_asset_matrix_manifest.json'))
 result=set()
 for a in m['assets']:
  for paths in a['paths'].values():result.update(x.removeprefix('res://') for x in paths)
 result.update(x['path'].removeprefix('res://') for x in m['commercial']);assert len(result)==436
 return result
def source_info(z:zipfile.ZipFile,path:str)->dict[str,Any]:
 data=z.read(path);return {'bytes':len(data),'sha256':sha_bytes(data)}
def resolve_deps(z:zipfile.ZipFile,logical:str)->list[str]:
 names=set(i.filename for i in z.infolist() if not i.is_dir());data=z.read(logical);base=PurePosixPath(logical).parent;ext=PurePosixPath(logical).suffix.lower();deps=set()
 def add(uri:str):
  if not uri or uri.startswith(('data:','http:','https:')):return
  p=(base/PurePosixPath(uri)).as_posix()
  if p in names:deps.add(p)
 if ext=='.gltf':
  obj=json.loads(data.decode('utf-8'))
  for r in obj.get('buffers',[]):add(r.get('uri',''))
  for r in obj.get('images',[]):add(r.get('uri',''))
 elif ext=='.obj':
  text=data.decode('utf-8','replace')
  for line in text.splitlines():
   if line.lower().startswith('mtllib '):add(line.split(None,1)[1].strip())
  for mtl in list(deps):
   try:t=z.read(mtl).decode('utf-8','replace')
   except KeyError:continue
   for line in t.splitlines():
    if re.match(r'(?i)^(map_|bump\b|disp\b|decal\b)',line.strip()):
     parts=line.split();
     if parts:add(parts[-1])
 elif ext=='.fbx':
  basenames={m.decode('utf-8','ignore') for m in re.findall(rb'[A-Za-z0-9_ .-]+\.(?:png|jpe?g|tga|bmp|webp)',data,re.I)}
  for n in names:
   if PurePosixPath(n).name in basenames and (PurePosixPath(n).parent==base or str(PurePosixPath(n).parent).startswith(str(base.parent))):deps.add(n)
 return sorted(deps)
def choose_quantile(rows:list[dict[str,Any]],q:float)->dict[str,Any]:
 rows=sorted(rows,key=lambda r:(r['source_bytes'],r['logical_source']));assert rows;return dict(rows[round((len(rows)-1)*q)])
def retained_cmd(a:argparse.Namespace)->int:
 out=Path(a.output);out.mkdir(parents=True,exist_ok=True);d1=json.loads(Path(a.d1).read_text());d2=json.loads(Path(a.d2).read_text());source_zip=Path(a.source_zip);seed=json.loads(Path(a.seed_manifest).read_text())
 assert sha_file(source_zip)==SOURCE_SHA and seed['sidecar_count']==1455
 cmp=compare_inventories(d1['generated'],d2['generated']);cmp.update({'authority':{'d1_artifact':8425001064,'d2_artifact':8424999903,'seed_artifact':8424941278},'retained_binary_bytes_available':False,'retained_md5_contents_available':False,'note':'Original compact D1/D2 artifacts retained hashes and sizes, not generated binary or .md5 bytes; later phases perform bounded exact diagnostic reimports.'})
 write_json(out/'SEEDED_IMPORT_COMPARISON.json',cmp);(out/'SEEDED_IMPORT_DIFFERING_PATHS.txt').write_text('\n'.join(x['path'] for x in cmp['differences'])+'\n');write_json(out/'SEEDED_IMPORT_CATEGORY_SUMMARY.json',{'total':cmp['total_content_differences'],'categories':cmp['category_counts'],'path_set_equal':cmp['path_set_equal'],'uid_differences':cmp['source_adjacent_import_uid_differences'],'uid_cache_equal':cmp['uid_cache_equal']})
 imports=d1['generated']['imports'];records={r['path']:r for r in d1['generated']['records']};records2={r['path']:r for r in d2['generated']['records']};mset=matrix_paths(source_zip);models=[]
 with zipfile.ZipFile(source_zip) as z:
  for sidecar,meta in imports.items():
   logical=sidecar[:-7];ext=PurePosixPath(logical).suffix.lower()
   if ext not in MODEL_EXTS:continue
   target=meta['path'];rec=records[target];rec2=records2[target];si=source_info(z,logical)
   models.append({'logical_source':logical,'sidecar_path':sidecar,'target_path':target,'md5_path':str(PurePosixPath(target).with_suffix('.md5')),'importer':'wavefront_obj' if ext=='.obj' else 'scene','source_type':ext[1:].upper(),'source_bytes':si['bytes'],'source_sha256':si['sha256'],'d1_imported_bytes':rec['bytes'],'d1_imported_sha256':rec['sha256'],'d2_imported_bytes':rec2['bytes'],'d2_imported_sha256':rec2['sha256'],'matrix_member':logical in mset,'dependencies':resolve_deps(z,logical)})
 assert len(models)==800 and collections.Counter(x['source_type'] for x in models)=={'GLB':578,'GLTF':203,'FBX':18,'OBJ':1}
 glbm=[x for x in models if x['source_type']=='GLB' and x['matrix_member']];glbn=[x for x in models if x['source_type']=='GLB' and not x['matrix_member']];gltf=[x for x in models if x['source_type']=='GLTF'];fbx=[x for x in models if x['source_type']=='FBX'];obj=[x for x in models if x['source_type']=='OBJ']
 char=lambda p:any(k in p.lower() for k in ('character','soldier','female','male','npc','person','human','body','cowboy','casual'))
 env=lambda p:any(k in p.lower() for k in ('environment','architecture','brick','building','road','street','tree','rock','floor','wall','door','window','column'))
 chosen=[('glb_matrix_small',choose_quantile(glbm,.25)),('glb_matrix_medium',choose_quantile(glbm,.50)),('glb_matrix_large',choose_quantile(glbm,.75)),('glb_non_matrix',choose_quantile(glbn,.50)),('gltf_character',choose_quantile([x for x in gltf if char(x['logical_source'])],.50)),('gltf_environment',choose_quantile([x for x in gltf if env(x['logical_source'])],.50)),('fbx_character',choose_quantile([x for x in fbx if char(x['logical_source'])] or fbx,.50)),('obj_single',obj[0])]
 selected=[]
 for sid,row in chosen:row=dict(row);row['selection_id']=sid;row['selection_rule']={'glb_matrix_small':'25th percentile matrix GLB source size','glb_matrix_medium':'50th percentile matrix GLB source size','glb_matrix_large':'75th percentile matrix GLB source size','glb_non_matrix':'median non-matrix GLB source size','gltf_character':'median character-keyword GLTF source size','gltf_environment':'median environment-keyword GLTF source size','fbx_character':'median character-keyword FBX source size','obj_single':'only OBJ import'}[sid];selected.append(row)
 write_json(out/'REPRESENTATIVE_SELECTION.json',{'schema_version':1,'model_population':{'total':800,'GLB':578,'GLTF':203,'FBX':18,'OBJ':1,'matrix':436},'resources':selected})
 return 0
def verify_seed(seed_zip:Path,manifest:dict[str,Any])->None:
 assert sha_file(seed_zip)==manifest['archive_sha256'];records={r['path']:r for r in manifest['records']}
 with zipfile.ZipFile(seed_zip) as z:
  names=[i.filename for i in z.infolist() if not i.is_dir()];assert len(names)==len(set(names))==1455 and set(names)==set(records)
  for n in names:assert sha_bytes(z.read(n))==records[n]['sha256']
def import_env(xdg:Path)->dict[str,str]:
 if xdg.exists():shutil.rmtree(xdg)
 xdg.mkdir(parents=True);env=os.environ.copy();env.update({'TZ':'UTC','LC_ALL':'C.UTF-8','LANG':'C.UTF-8','XDG_DATA_HOME':str(xdg)});return env
def collect_model_md5(game:Path)->dict[str,Any]:
 result={}
 for sidecar in sorted(game.rglob('*.import')):
  rel=sidecar.relative_to(game).as_posix();logical=rel[:-7]
  if PurePosixPath(logical).suffix.lower() not in MODEL_EXTS:continue
  meta=parse_import(sidecar.read_bytes());target=meta['path'];md5=str(PurePosixPath(target).with_suffix('.md5'));mp=game/md5
  assert target and (game/target).is_file() and mp.is_file(),(rel,target,md5)
  result[md5]={'logical_source':logical,'sidecar_path':rel,'target_path':target,'record':parse_md5(mp.read_bytes()),'imported_sha256':sha_file(game/target),'imported_bytes':(game/target).stat().st_size}
 assert len(result)==800,len(result);return result
def copy_selected(game:Path,selection:dict[str,Any],out:Path)->dict[str,Any]:
 rows=[]
 for r in selection['resources']:
  sid=r['selection_id'];dest=out/'selected'/sid;dest.mkdir(parents=True,exist_ok=True)
  files={'source':r['logical_source'],'sidecar':r['sidecar_path'],'imported':r['target_path'],'md5':r['md5_path']}
  retained={}
  for role,rel in files.items():
   src=game/rel;assert src.is_file(),(role,rel);suffix={'source':PurePosixPath(rel).suffix,'sidecar':'.import','imported':PurePosixPath(rel).suffix,'md5':'.md5'}[role];dst=dest/(role+suffix);shutil.copy2(src,dst);retained[role]={'relative_path':dst.relative_to(out).as_posix(),'original_path':rel,'bytes':dst.stat().st_size,'sha256':sha_file(dst)}
  rows.append({'selection_id':sid,'logical_source':r['logical_source'],'source_type':r['source_type'],'matrix_member':r['matrix_member'],'retained':retained})
 return {'resources':rows}
def snapshot_cache(game:Path,dest:Path)->dict[str,Any]:
 if dest.exists():dest.unlink()
 with zipfile.ZipFile(dest,'w',zipfile.ZIP_STORED) as z:
  for p in sorted(game.rglob('*'),key=lambda p:p.relative_to(game).as_posix()):
   if p.is_file():
    rel=p.relative_to(game).as_posix()
    if rel.startswith('.godot/') or rel.endswith('.import'):
     zi=zipfile.ZipInfo(rel,(1980,1,1,0,0,0));zi.compress_type=zipfile.ZIP_STORED;zi.external_attr=(0o100444)<<16;z.writestr(zi,p.read_bytes())
 os.chmod(dest,0o444);return {'bytes':dest.stat().st_size,'sha256':sha_file(dest)}
def corrected_e(source_zip:Path,godot:Path,seed_zip:Path,game:Path,out:Path,work:Path)->dict[str,Any]:
 snap=work/'verified_cache_snapshot.zip';snap.parent.mkdir(parents=True,exist_ok=True);authority=snapshot_cache(game,snap);runs=[]
 for label in ('E1','E2'):
  g=work/f'pack-{label.lower()}'/'game';materialize(source_zip,g);overlay_zip(seed_zip,g);overlay_zip(snap,g)
  before=generated_inventory(g);pck=(out/f'{label}_shared_cache.pck').resolve();pck.parent.mkdir(parents=True,exist_ok=True);env=import_env(work/f'xdg-{label.lower()}')
  rr=run([str(godot),'--headless','--path',str(g),'--export-pack','Android',str(pck),'--verbose'],out/f'{label}_shared_cache_export.log',env,2400);after=generated_inventory(g)
  pack={'exists':pck.is_file(),'bytes':pck.stat().st_size if pck.is_file() else None,'sha256':sha_file(pck) if pck.is_file() else None};runs.append({'label':label,'run':rr,'pack':pack,'input_cache_aggregate':before['aggregate_sha256'],'post_cache_aggregate':after['aggregate_sha256'],'cache_unchanged':before['aggregate_sha256']==after['aggregate_sha256']})
 for p in out.glob('*_shared_cache.pck'):p.unlink()
 return {'original_failure':'relative output path build/suite/... was resolved relative to project root and parent did not exist; Godot reached Save PCK then failed to open output','correction':'absolute pre-created output path; same existing Android preset used only with --export-pack, no Android SDK tooling invoked','cache_snapshot':authority,'runs':runs,'both_exist':all(x['pack']['exists'] for x in runs),'sha_equal':runs[0]['pack']['sha256']==runs[1]['pack']['sha256'] if all(x['pack']['exists'] for x in runs) else None}
def seeded_run_cmd(a:argparse.Namespace)->int:
 source_zip=Path(a.source_zip);godot=Path(a.godot);seed_zip=Path(a.seed_zip);seed_manifest=json.loads(Path(a.seed_manifest).read_text());selection=json.loads(Path(a.selection).read_text()) if a.selection else {'resources':[]};out=Path(a.output);work=Path(a.work_root);game=work/'game';out.mkdir(parents=True,exist_ok=True);verify_seed(seed_zip,seed_manifest);mat=materialize(source_zip,game);overlay_zip(seed_zip,game)
 preseed=None
 if a.preseed_cache:
  pc=Path(a.preseed_cache);(game/'.godot').mkdir(parents=True,exist_ok=True);shutil.copy2(pc,game/'.godot/uid_cache.bin');preseed={'bytes':pc.stat().st_size,'sha256':sha_file(pc)}
 env=import_env(work/'xdg');old=os.umask(0o022)
 try:rr=run([str(godot),'--headless','--path',str(game),'--editor','--import','--quit','--verbose'],out/f'{a.label}.godot.log',env,2400)
 finally:os.umask(old)
 inv=generated_inventory(game);assert rr['exit_code']==0 and rr['error_pattern_count']==0 and inv['uid_cache']['exists'],rr
 md5=collect_model_md5(game);write_json(out/'MODEL_MD5_RECORDS.json',md5);selected=copy_selected(game,selection,out) if selection['resources'] else {'resources':[]};write_json(out/'SELECTED_RETAINED_FILES.json',selected)
 uid=game/'.godot/uid_cache.bin';shutil.copy2(uid,out/'uid_cache.bin')
 result={'label':a.label,'materialization':mat,'run':rr,'preseed_cache':preseed,'generated':inv,'model_md5_count':len(md5),'selected_count':len(selected['resources']),'uid_cache':{'bytes':uid.stat().st_size,'sha256':sha_file(uid)}};write_json(out/'SEEDED_DIAGNOSTIC_RESULT.json',result)
 if a.semantic_script and selection['resources']:
  sem=run([str(godot),'--headless','--path',str(game),'--script',str(Path(a.semantic_script).resolve()),'--',str(Path(a.selection).resolve()),str((out/'MODEL_SEMANTIC_GRAPH.json').resolve())],out/'semantic_dump.log',env,1200);write_json(out/'SEMANTIC_RUN.json',sem);assert sem['exit_code']==0 and (out/'MODEL_SEMANTIC_GRAPH.json').is_file(),sem
 if a.corrected_e:write_json(out/'CORRECTED_EXPERIMENT_E.json',corrected_e(source_zip,godot,seed_zip,game,out,work/'corrected-e'))
 return 0
def diff_ranges(a:bytes,b:bytes)->dict[str,Any]:
 n=max(len(a),len(b));pos=[]
 for i in range(n):
  av=a[i] if i<len(a) else None;bv=b[i] if i<len(b) else None
  if av!=bv:pos.append(i)
 ranges=[]
 if pos:
  s=prev=pos[0]
  for x in pos[1:]:
   if x!=prev+1:ranges.append((s,prev));s=x
   prev=x
  ranges.append((s,prev))
 return {'first':pos[0] if pos else None,'final':pos[-1] if pos else None,'positions':len(pos),'range_count':len(ranges),'longest_range':max((e-s+1 for s,e in ranges),default=0),'ranges':ranges}
def strings(data:bytes)->set[str]:return {x.decode('utf-8','replace') for x in ASCII_RE.findall(data)}
def hex_windows(a:bytes,b:bytes,ranges:list[tuple[int,int]],limit:int=20)->list[dict[str,Any]]:
 out=[]
 for s,e in ranges[:limit]:
  lo=max(0,s-32);hi=min(max(len(a),len(b)),e+33);out.append({'start':s,'end':e,'window_start':lo,'window_end':hi,'d1_hex':a[lo:min(hi,len(a))].hex(),'d2_hex':b[lo:min(hi,len(b))].hex()})
 return out
def semantic_sections(obj:dict[str,Any])->dict[str,str]:return obj.get('section_sha256',{})
def compare_pairs_cmd(a:argparse.Namespace)->int:
 d1=Path(a.d1);d2=Path(a.d2);out=Path(a.output);out.mkdir(parents=True,exist_ok=True);m1=json.loads((d1/'MODEL_MD5_RECORDS.json').read_text());m2=json.loads((d2/'MODEL_MD5_RECORDS.json').read_text());assert set(m1)==set(m2) and len(m1)==800
 rows=[];fc=collections.Counter();source_alarm=[]
 for p in sorted(m1):
  x=m1[p];y=m2[p];fields=sorted(set(x['record']['fields'])|set(y['record']['fields']));diff={k:{'d1':x['record']['fields'].get(k),'d2':y['record']['fields'].get(k)} for k in fields if x['record']['fields'].get(k)!=y['record']['fields'].get(k)}
  for k in diff:fc[k]+=1
  if any(k in diff for k in ('source_md5','source_hash','source_checksum')):source_alarm.append(p)
  rows.append({'md5_path':p,'logical_source':x['logical_source'],'target_path':x['target_path'],'differing_fields':diff,'d1_sha256':x['record']['sha256'],'d2_sha256':y['record']['sha256']})
 write_json(out/'IMPORTED_MD5_FIELD_COMPARISON.json',{'records':rows});write_json(out/'IMPORTED_MD5_SUMMARY.json',{'record_count':800,'differing_record_count':sum(bool(x['differing_fields']) for x in rows),'differing_field_counts':dict(sorted(fc.items())),'source_hash_alarm_count':len(source_alarm),'source_hash_alarm_paths':source_alarm});assert not source_alarm
 sel1=json.loads((d1/'SELECTED_RETAINED_FILES.json').read_text());sel2=json.loads((d2/'SELECTED_RETAINED_FILES.json').read_text());r1={x['selection_id']:x for x in sel1['resources']};r2={x['selection_id']:x for x in sel2['resources']};assert set(r1)==set(r2) and len(r1)==8
 raw=[];strdiff=[];windows=[]
 for sid in sorted(r1):
  p1=d1/r1[sid]['retained']['imported']['relative_path'];p2=d2/r2[sid]['retained']['imported']['relative_path'];b1=p1.read_bytes();b2=p2.read_bytes();dr=diff_ranges(b1,b2);s1=strings(b1);s2=strings(b2)
  raw.append({'selection_id':sid,'logical_source':r1[sid]['logical_source'],'source_type':r1[sid]['source_type'],'matrix_member':r1[sid]['matrix_member'],'d1_sha256':sha_bytes(b1),'d2_sha256':sha_bytes(b2),'d1_bytes':len(b1),'d2_bytes':len(b2),'first_differing_offset':dr['first'],'final_differing_offset':dr['final'],'differing_byte_positions':dr['positions'],'differing_contiguous_ranges':dr['range_count'],'longest_differing_range':dr['longest_range'],'absolute_paths_d1':sorted(x.decode(errors='replace') for x in ABS_BYTES_RE.findall(b1))[:100],'absolute_paths_d2':sorted(x.decode(errors='replace') for x in ABS_BYTES_RE.findall(b2))[:100],'uid_strings_d1':sorted(x.decode() for x in UID_BYTES_RE.findall(b1)),'uid_strings_d2':sorted(x.decode() for x in UID_BYTES_RE.findall(b2)),'source_paths_d1':sorted(x.decode(errors='replace') for x in RES_BYTES_RE.findall(b1))[:200],'source_paths_d2':sorted(x.decode(errors='replace') for x in RES_BYTES_RE.findall(b2))[:200],'timestamps_d1':sorted(x.decode(errors='replace') for x in DATE_BYTES_RE.findall(b1))[:100],'timestamps_d2':sorted(x.decode(errors='replace') for x in DATE_BYTES_RE.findall(b2))[:100],'random_identifiers_d1':sorted(x.decode(errors='replace') for x in RANDOM_BYTES_RE.findall(b1))[:200],'random_identifiers_d2':sorted(x.decode(errors='replace') for x in RANDOM_BYTES_RE.findall(b2))[:200]})
  strdiff.append({'selection_id':sid,'unique_d1':sorted(s1-s2)[:500],'unique_d2':sorted(s2-s1)[:500],'unique_d1_count':len(s1-s2),'unique_d2_count':len(s2-s1)});windows.append({'selection_id':sid,'windows':hex_windows(b1,b2,dr['ranges'])})
 write_json(out/'MODEL_BINARY_RAW_DIFFS.json',{'resources':raw});write_json(out/'MODEL_BINARY_STRING_DIFFS.json',{'resources':strdiff});write_json(out/'MODEL_BINARY_HEX_WINDOWS.json',{'resources':windows})
 s1=json.loads((d1/'MODEL_SEMANTIC_GRAPH.json').read_text());s2=json.loads((d2/'MODEL_SEMANTIC_GRAPH.json').read_text());g1={x['selection_id']:x for x in s1['resources']};g2={x['selection_id']:x for x in s2['resources']};sem=[];cc=collections.Counter()
 for sid in sorted(g1):
  x=g1[sid];y=g2[sid];sx=semantic_sections(x);sy=semantic_sections(y);section={k:{'equal':sx.get(k)==sy.get(k),'d1':sx.get(k),'d2':sy.get(k)} for k in sorted(set(sx)|set(sy))};different=[k for k,v in section.items() if not v['equal']]
  failed=x.get('failures',[])+y.get('failures',[])
  if failed:cat='G'
  elif not different:cat='B'
  elif set(different)<= {'identifiers'}:cat='A'
  elif 'floats' in different and len(different)==1:cat='C'
  elif 'order' in different and len(different)==1:cat='D'
  else:cat='E' if any(k in different for k in ('geometry','materials','animations','skeletons','nodes')) else 'F'
  cc[cat]+=1;sem.append({'selection_id':sid,'logical_source':x['logical_source'],'source_type':x['source_type'],'classification':cat,'section_comparison':section,'differing_sections':different,'failures':failed,'skipped_properties_d1':x.get('skipped_properties',[]),'skipped_properties_d2':y.get('skipped_properties',[])})
 write_json(out/'D1_MODEL_SEMANTIC_GRAPH.json',s1);write_json(out/'D2_MODEL_SEMANTIC_GRAPH.json',s2);write_json(out/'MODEL_SEMANTIC_COMPARISON.json',{'classification_counts':dict(sorted(cc.items())),'resources':sem,'geometry_diff_count':sum('geometry' in x['differing_sections'] for x in sem),'materials_diff_count':sum('materials' in x['differing_sections'] for x in sem),'animations_diff_count':sum('animations' in x['differing_sections'] for x in sem),'skeletons_diff_count':sum('skeletons' in x['differing_sections'] for x in sem),'nodes_diff_count':sum('nodes' in x['differing_sections'] for x in sem),'identifier_only_count':sum(x['classification']=='A' for x in sem),'serialization_only_count':sum(x['classification']=='B' for x in sem)})
 return 0
def inventory_only_result(path:Path)->dict[str,Any]:return json.loads((path/'SEEDED_DIAGNOSTIC_RESULT.json').read_text())['generated']
def preseed_compare_cmd(a:argparse.Namespace)->int:
 d1=inventory_only_result(Path(a.d1));d2=inventory_only_result(Path(a.d2));cmp=compare_inventories(d1,d2);write_json(Path(a.output),cmp);return 0
def make_minimal(source_zip:Path,seed_zip:Path,r:dict[str,Any],root:Path)->dict[str,Any]:
 if root.exists():shutil.rmtree(root)
 root.mkdir(parents=True);(root/'project.godot').write_text('config_version=5\n[application]\nconfig/name="PR59MinimalImport"\n')
 with zipfile.ZipFile(source_zip) as z,zipfile.ZipFile(seed_zip) as sz:
  names=set(i.filename for i in z.infolist() if not i.is_dir());snames=set(i.filename for i in sz.infolist() if not i.is_dir());needed=[r['logical_source'],*r.get('dependencies',[])]
  for rel in needed:
   dst=root/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(z.read(rel));os.utime(dst,(315532800,315532800))
   side=rel+'.import'
   if side in snames:data=sz.read(side)
   elif side in names:data=z.read(side)
   else:data=None
   if data is not None:s=root/side;s.parent.mkdir(parents=True,exist_ok=True);s.write_bytes(data);os.utime(s,(315532800,315532800))
  side=r['sidecar_path'];data=sz.read(side) if side in snames else z.read(side);s=root/side;s.parent.mkdir(parents=True,exist_ok=True);s.write_bytes(data);os.utime(s,(315532800,315532800))
 return {'files':sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file())}
def minimal_cmd(a:argparse.Namespace)->int:
 source_zip=Path(a.source_zip);seed_zip=Path(a.seed_zip);godot=Path(a.godot);sel=json.loads(Path(a.selection).read_text());out=Path(a.output);work=Path(a.work_root);out.mkdir(parents=True,exist_ok=True);wanted={'GLB':'glb_matrix_medium','GLTF':'gltf_character','FBX':'fbx_character','OBJ':'obj_single'};results=[]
 byid={r['selection_id']:r for r in sel['resources']}
 for fmt,sid in wanted.items():
  row=byid[sid];runs=[]
  for n in (1,2):
   game=work/f'{fmt.lower()}-canonical/game';manifest=make_minimal(source_zip,seed_zip,row,game);env=import_env(work/f'{fmt.lower()}-xdg');rr=run([str(godot),'--headless','--path',str(game),'--editor','--import','--quit','--verbose'],out/f'{fmt}_{n}.log',env,1200);target=game/row['target_path'];md5=game/row['md5_path'];runs.append({'run':rr,'target_exists':target.is_file(),'target_bytes':target.stat().st_size if target.is_file() else None,'target_sha256':sha_file(target) if target.is_file() else None,'md5':parse_md5(md5.read_bytes()) if md5.is_file() else None,'project_files':manifest['files']});assert rr['exit_code']==0 and target.is_file() and md5.is_file(),runs[-1]
  results.append({'format':fmt,'selection_id':sid,'logical_source':row['logical_source'],'dependencies':row.get('dependencies',[]),'run1':runs[0],'run2':runs[1],'binary_equal':runs[0]['target_sha256']==runs[1]['target_sha256'],'md5_equal':runs[0]['md5']['sha256']==runs[1]['md5']['sha256']})
 write_json(out/'MINIMAL_MODEL_IMPORT_RESULTS.json',{'results':results});return 0
def source_audit_cmd(a:argparse.Namespace)->int:
 root=Path(a.source_root);out=Path(a.output);files=[];candidates=[]
 specs=[('core/io/resource.cpp','Resource::generate_scene_unique_id','generate_scene_unique_id'),('core/io/resource_format_binary.cpp','ResourceFormatSaverBinaryInstance::save','generate_scene_unique_id'),('editor/import/3d/resource_importer_scene.cpp','ResourceImporterScene','ResourceSaver::save'),('editor/import/resource_importer_obj.cpp','ResourceImporterOBJ','ResourceSaver::save'),('modules/gltf/gltf_document.cpp','GLTFDocument','HashMap'),('scene/resources/packed_scene.cpp','PackedScene','scene_unique')]
 for rel,func,needle in specs:
  p=root/rel
  if not p.is_file():continue
  lines=p.read_text(errors='replace').splitlines();hits=[i for i,x in enumerate(lines,1) if needle in x]
  for h in hits[:20]:
   lo=max(1,h-8);hi=min(len(lines),h+14);snippet='\n'.join(f'{i}:{lines[i-1]}' for i in range(lo,hi+1));files.append({'file':rel,'function_hint':func,'line_start':lo,'line_end':hi,'matched_line':h,'needle':needle,'snippet':snippet,'blob_sha256':sha_file(p)})
 for item in files:
  if item['file']=='core/io/resource.cpp' and item['needle']=='generate_scene_unique_id':candidates.append({'classification':'RANDOM_SCENE_UNIQUE_ID_GENERATION','source_file':item['file'],'function':'Resource::generate_scene_unique_id','line_range':[103,130],'why':'Hashes wall-clock date, microsecond ticks, and Math::rand() to generate a five-character local resource ID.','evidence':'Same input import creates different local IDs.'})
  if item['file']=='core/io/resource_format_binary.cpp' and item['needle']=='generate_scene_unique_id':candidates.append({'classification':'BINARY_SAVER_ASSIGNMENT_TO_BUILT_IN_SUBRESOURCES','source_file':item['file'],'function':'ResourceFormatSaverBinaryInstance::save','line_range':[2460,2490],'why':'Every built-in resource lacking scene_unique_id receives ClassName_ + random generate_scene_unique_id() before local:// serialization.','evidence':'Model imports contain many built-in meshes/materials/skins/animations; single-resource texture imports do not.'})
 write_json(out/'GODOT_4_3_IMPORT_SOURCE_TRACE.json',{'godot_commit':'77dcf97d8','files':files});write_json(out/'GODOT_4_3_NONDETERMINISM_CANDIDATES.json',{'candidates':candidates});return 0
def aggregate_cmd(a:argparse.Namespace)->int:
 out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
 def j(p,n):return json.loads((Path(p)/n).read_text())
 retained=j(a.retained,'SEEDED_IMPORT_COMPARISON.json');md5=j(a.pairs,'IMPORTED_MD5_SUMMARY.json');sem=j(a.pairs,'MODEL_SEMANTIC_COMPARISON.json');pre=json.loads(Path(a.preseed).read_text());mini=j(a.minimal,'MINIMAL_MODEL_IMPORT_RESULTS.json');e=j(a.d1,'CORRECTED_EXPERIMENT_E.json');audit=j(a.audit,'GODOT_4_3_NONDETERMINISM_CANDIDATES.json')
 pre_model=pre['category_counts'].get('IMPORTED_BINARY',0);minimal_differ=sum(not x['binary_equal'] for x in mini['results']);source_candidate=any(x['classification']=='BINARY_SAVER_ASSIGNMENT_TO_BUILT_IN_SUBRESOURCES' for x in audit['candidates'])
 if sem['geometry_diff_count']==sem['materials_diff_count']==sem['animations_diff_count']==sem['skeletons_diff_count']==sem['nodes_diff_count']==0 and sem['identifier_only_count']+sem['serialization_only_count']==8 and pre_model==800 and minimal_differ==4 and source_candidate:
  classification=['IMPORTED_SUBRESOURCE_UID_NONDETERMINISM','PACKED_SCENE_LOCAL_ID_NONDETERMINISM']
 else:classification=['EVIDENCE_INSUFFICIENT']
 viable=[{'option':1,'name':'Official supported deterministic importer mechanism','status':'not found in Godot 4.3 source examined','risk':'none available to authorize'},{'option':2,'name':'Pinned imported-resource authority','status':'technically viable architecture change','risk':'abandons independent clean-import proof; large cache integrity and invalidation burden'},{'option':3,'name':'Pinned custom Godot 4.3 build','status':'technically viable after patching deterministic local ID assignment','risk':'engine fork security, licensing attribution, maintenance, template/editor parity, broad regression burden'},{'option':4,'name':'Engine upgrade','status':'requires separate migration and exact-fix validation','risk':'project/import/runtime regressions and source-format migration'},{'option':5,'name':'Retain Class C','status':'safe current disposition','risk':'Gate 4 remains failed'}]
 final={'classification':classification,'evidence':{'retained_differences':retained['category_counts'],'md5_differing_fields':md5['differing_field_counts'],'semantic':sem,'uid_cache_preseed':pre['category_counts'],'minimal_formats_differing':minimal_differ,'corrected_experiment_e':{'both_exist':e['both_exist'],'sha_equal':e['sha_equal']},'source_candidates':audit['candidates']},'viable_options':viable,'recommended_option':{'option':5,'reason':'No PR correction is safe under the fixed Godot 4.3 authority. Preserve Gate 5 and keep Gate 4 Class C until a separately approved engine-upgrade or custom-engine program proves deterministic imports.'},'correction_safe_to_authorize':False,'gate4':'FAIL','gate5':'PASS retained original APKs only','android_runtime_tested':False,'pr_modified':False}
 write_json(out/'FINAL_MODEL_IMPORT_FORENSICS.json',final);prov={'accepted_pr_head':'5b4e2466ef84f3984f3bf336b31925d4d2e97a7f','source_manifest_sha256':'ba937afa335170ccaa726297fc23712a44e3295689a86640e1c1dbe6165701ab','source_tree_sha256':'e0cfa6604569c13e1d75b2439d6936b7e2423ad5ba3715f033200335e864bc4e','godot_version':GODOT_VERSION,'classification':classification,'no_android_export':True,'no_apk_mutation':True,'no_pr_correction':True,'evidence_sha256':{}}
 for root in [Path(a.retained),Path(a.pairs),Path(a.d1),Path(a.d2),Path(a.preseed).parent,Path(a.minimal),Path(a.audit)]:
  for p in sorted(root.rglob('*.json')):prov['evidence_sha256'][f'{root.name}/{p.relative_to(root).as_posix()}']=sha_file(p)
 write_json(out/'FINAL_FORENSIC_PROVENANCE.json',prov);(out/'FINAL_FORENSIC_PROVENANCE_SHA256.txt').write_text(sha_file(out/'FINAL_FORENSIC_PROVENANCE.json')+'\n');return 0
def main()->int:
 p=argparse.ArgumentParser();s=p.add_subparsers(dest='cmd',required=True)
 q=s.add_parser('retained');q.add_argument('--d1',required=True);q.add_argument('--d2',required=True);q.add_argument('--source-zip',required=True);q.add_argument('--seed-manifest',required=True);q.add_argument('--output',required=True);q.set_defaults(fn=retained_cmd)
 q=s.add_parser('seeded-run')
 for n in ('source-zip','godot','seed-zip','seed-manifest','output','work-root','label'):q.add_argument('--'+n,required=True)
 q.add_argument('--selection');q.add_argument('--semantic-script');q.add_argument('--preseed-cache');q.add_argument('--corrected-e',action='store_true');q.set_defaults(fn=seeded_run_cmd)
 q=s.add_parser('compare-pairs');q.add_argument('--d1',required=True);q.add_argument('--d2',required=True);q.add_argument('--output',required=True);q.set_defaults(fn=compare_pairs_cmd)
 q=s.add_parser('preseed-compare');q.add_argument('--d1',required=True);q.add_argument('--d2',required=True);q.add_argument('--output',required=True);q.set_defaults(fn=preseed_compare_cmd)
 q=s.add_parser('minimal');q.add_argument('--source-zip',required=True);q.add_argument('--seed-zip',required=True);q.add_argument('--godot',required=True);q.add_argument('--selection',required=True);q.add_argument('--output',required=True);q.add_argument('--work-root',required=True);q.set_defaults(fn=minimal_cmd)
 q=s.add_parser('source-audit');q.add_argument('--source-root',required=True);q.add_argument('--output',required=True);q.set_defaults(fn=source_audit_cmd)
 q=s.add_parser('aggregate')
 for n in ('retained','pairs','d1','d2','preseed','minimal','audit','output'):q.add_argument('--'+n,required=True)
 q.set_defaults(fn=aggregate_cmd)
 a=p.parse_args();return a.fn(a)
if __name__=='__main__':raise SystemExit(main())
