#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, time, zipfile
from pathlib import Path, PurePosixPath
from typing import Any

SOURCE_SHA = "5ca9ff72aaaddeb9d86fb02c2fe99de5da280988b3945c4c627e80effeb01aa7"
SOURCE_BYTES = 225721731
SOURCE_FILES = 1502
SOURCE_TOTAL_BYTES = 369162800
ENGINE_VERSION = "4.5.2.stable.official.6ce3de25a"
MODEL_EXTS = {".glb", ".gltf", ".fbx", ".obj"}
PATH_RE = re.compile(r'(?m)^path="res://([^"\r\n]+)"\s*$')
SOURCE_RE = re.compile(r'(?m)^source_file="res://([^"\r\n]+)"\s*$')
IMPORTER_RE = re.compile(r'(?m)^importer="([^"]+)"\s*$')
MD5_RE = re.compile(r'(?m)^([A-Za-z0-9_./-]+)="([^"]*)"\s*$')
ERROR_RE = re.compile(r"SCRIPT ERROR|Parse Error|Parser Error|Failed to load script|Failed to create an autoload|\bFATAL\b|Fatal signal", re.I)

def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def sha_bytes(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
def safe_name(name: str) -> str:
    if name.startswith("/") or "\\" in name or ".." in PurePosixPath(name).parts: raise ValueError(name)
    return name.rstrip("/")

def materialize(archive: Path, target: Path) -> list[dict[str, Any]]:
    if sha_file(archive) != SOURCE_SHA or archive.stat().st_size != SOURCE_BYTES: raise RuntimeError("source archive authority mismatch")
    if target.exists(): shutil.rmtree(target)
    target.mkdir(parents=True); rows = []
    with zipfile.ZipFile(archive) as z:
        infos = sorted((i for i in z.infolist() if not i.is_dir()), key=lambda i: i.filename)
        names = [safe_name(i.filename) for i in infos]
        if len(names) != len(set(names)) or len(names) != SOURCE_FILES: raise RuntimeError("source path authority mismatch")
        for info in infos:
            rel = safe_name(info.filename); data = z.read(info); dst = target / rel
            dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(data); os.chmod(dst, 0o644); os.utime(dst, (315532800, 315532800))
            rows.append({"path": rel, "bytes": len(data), "sha256": sha_bytes(data)})
    if sum(x["bytes"] for x in rows) != SOURCE_TOTAL_BYTES: raise RuntimeError("source byte authority mismatch")
    return rows

def import_env(xdg: Path) -> dict[str, str]:
    shutil.rmtree(xdg, ignore_errors=True); xdg.mkdir(parents=True)
    env = os.environ.copy(); env.update({"TZ": "UTC", "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8", "XDG_DATA_HOME": str(xdg)}); return env

def run_import(engine: Path, root: Path, output: Path, label: str) -> dict[str, Any]:
    env = import_env(output / "xdg"); log = output / f"{label}.godot.log"; start = time.time()
    with log.open("wb") as f:
        proc = subprocess.run([str(engine), "--headless", "--path", str(root), "--editor", "--import", "--quit", "--verbose"], stdout=f, stderr=subprocess.STDOUT, env=env)
    data = log.read_bytes()
    result = {"label": label, "command": [str(engine), "--headless", "--path", str(root), "--editor", "--import", "--quit", "--verbose"], "exit_code": proc.returncode, "elapsed_seconds": round(time.time()-start,3), "error_pattern_count": len(ERROR_RE.findall(data.decode(errors="replace"))), "log_sha256": sha_bytes(data), "log_bytes": len(data)}
    write_json(output / f"{label}.RUN.json", result)
    if proc.returncode or result["error_pattern_count"]: raise RuntimeError(f"Godot import failed: {result}")
    return result

def parse_sidecar(path: Path) -> dict[str, Any]:
    data = path.read_bytes(); text = data[:-1].decode("utf-8") if data.endswith(b"\0") else data.decode("utf-8")
    pm, sm, im = PATH_RE.search(text), SOURCE_RE.search(text), IMPORTER_RE.search(text)
    return {"target_path": pm.group(1) if pm else None, "source_file": sm.group(1) if sm else None, "importer": im.group(1) if im else None, "bytes": len(data), "sha256": sha_bytes(data), "terminal_nul": data.endswith(b"\0")}

def model_sources(root: Path) -> list[str]:
    rows = [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.suffix.lower() in MODEL_EXTS]
    rows.sort()
    if len(rows) != 800: raise RuntimeError(f"expected exactly 800 model sources, got {len(rows)}")
    counts = {ext[1:].upper(): sum(PurePosixPath(p).suffix.lower() == ext for p in rows) for ext in sorted(MODEL_EXTS)}
    if counts != {"FBX":18,"GLB":578,"GLTF":203,"OBJ":1}: raise RuntimeError(f"model type counts mismatch: {counts}")
    return rows

def seed(args: argparse.Namespace) -> int:
    engine, source, out, work = Path(args.engine), Path(args.source_zip), Path(args.output), Path(args.work_root)
    out.mkdir(parents=True, exist_ok=True); root = work / "game"; accepted = materialize(source, root); models = model_sources(root)
    run = run_import(engine, root, out, "SEED")
    records = []
    authority_zip = out / "GODOT_4_5_2_FULL_MODEL_SIDECARS.zip"
    with zipfile.ZipFile(authority_zip, "w", zipfile.ZIP_STORED) as z:
        for logical in models:
            sidecar_rel = logical + ".import"; sidecar = root / sidecar_rel
            if not sidecar.is_file(): raise RuntimeError(f"missing generated model sidecar: {sidecar_rel}")
            meta = parse_sidecar(sidecar)
            if meta["source_file"] != logical: raise RuntimeError(f"sidecar source mismatch: {sidecar_rel}")
            if not meta["target_path"] or not (root / meta["target_path"]).is_file(): raise RuntimeError(f"missing seed target: {logical}")
            data = sidecar.read_bytes(); zi = zipfile.ZipInfo(sidecar_rel,(1980,1,1,0,0,0)); zi.compress_type=zipfile.ZIP_STORED; zi.external_attr=(0o100444<<16); z.writestr(zi,data)
            source_path = root / logical
            records.append({"logical_source":logical,"source_bytes":source_path.stat().st_size,"source_sha256":sha_file(source_path),"sidecar_path":sidecar_rel,**meta})
    if len(records) != 800: raise RuntimeError("seed record count mismatch")
    result = {"schema_version":1,"engine_version":ENGINE_VERSION,"engine_executable_sha256":sha_file(engine),"source_archive":{"bytes":source.stat().st_size,"sha256":sha_file(source),"accepted_file_count":len(accepted)},"model_count":len(records),"type_counts":{"GLB":578,"GLTF":203,"FBX":18,"OBJ":1},"records":records,"authority_zip":{"bytes":authority_zip.stat().st_size,"sha256":sha_file(authority_zip)},"run":run,"only_model_sidecars_preserved":True,"derived_source_files_preserved":False,"generated_imported_binaries_preserved":False,"no_android_export":True}
    write_json(out/"FULL_MODEL_SIDECAR_AUTHORITY.json",result); return 0

def overlay_authority(archive: Path, root: Path) -> set[str]:
    paths=set()
    with zipfile.ZipFile(archive) as z:
        infos=sorted((i for i in z.infolist() if not i.is_dir()),key=lambda i:i.filename); names=[safe_name(i.filename) for i in infos]
        if len(names)!=len(set(names)) or len(names)!=800: raise RuntimeError("sidecar authority path mismatch")
        for info in infos:
            rel=safe_name(info.filename); dst=root/rel; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(z.read(info)); os.chmod(dst,0o444);os.utime(dst,(315532800,315532800));paths.add(rel)
    return paths

def run_full(args: argparse.Namespace) -> int:
    engine,source,authority,out,work=Path(args.engine),Path(args.source_zip),Path(args.sidecar_zip),Path(args.output),Path(args.work_root)
    out.mkdir(parents=True,exist_ok=True);root=work/"game";accepted=materialize(source,root);accepted_map={x["path"]:x for x in accepted};models=model_sources(root);overlay_paths=overlay_authority(authority,root)
    run=run_import(engine,root,out,args.label)
    accepted_failures=[]
    for rel,row in accepted_map.items():
        if rel in overlay_paths: continue
        p=root/rel
        if not p.is_file(): accepted_failures.append({"path":rel,"reason":"missing"})
        elif p.stat().st_size!=row["bytes"] or sha_file(p)!=row["sha256"]: accepted_failures.append({"path":rel,"reason":"content_changed","before":row,"after":{"bytes":p.stat().st_size,"sha256":sha_file(p)}})
    sidecar_failures=[];records=[]
    with zipfile.ZipFile(authority) as z:
        authority_hash={i.filename:sha_bytes(z.read(i)) for i in z.infolist() if not i.is_dir()}
    for logical in models:
        sidecar_rel=logical+".import";sidecar=root/sidecar_rel;meta=parse_sidecar(sidecar)
        if meta["sha256"]!=authority_hash.get(sidecar_rel): sidecar_failures.append({"path":sidecar_rel,"reason":"authority_changed"})
        if meta["source_file"]!=logical: sidecar_failures.append({"path":sidecar_rel,"reason":"source_identity"})
        target=meta["target_path"]; imported=root/target if target else None; md5=imported.with_suffix(".md5") if imported else None
        missing=not target or not imported.is_file() or not md5.is_file()
        if missing:
            records.append({"logical_source":logical,"source_sha256":sha_file(root/logical),"source_bytes":(root/logical).stat().st_size,"sidecar_path":sidecar_rel,"sidecar_sha256":meta["sha256"],"importer":meta["importer"],"target_path":target,"missing":True});continue
        fields=dict(MD5_RE.findall(md5.read_text()))
        records.append({"logical_source":logical,"source_sha256":sha_file(root/logical),"source_bytes":(root/logical).stat().st_size,"sidecar_path":sidecar_rel,"sidecar_sha256":meta["sha256"],"importer":meta["importer"],"target_path":target,"imported_bytes":imported.stat().st_size,"imported_sha256":sha_file(imported),"md5_path":md5.relative_to(root).as_posix(),"md5_bytes":md5.stat().st_size,"md5_sha256":sha_file(md5),"source_md5":fields.get("source_md5"),"dest_md5":fields.get("dest_md5"),"missing":False,"semantic_status":"PENDING_COMPARISON"})
    result={"schema_version":1,"label":args.label,"engine_version":ENGINE_VERSION,"engine_executable_sha256":sha_file(engine),"source_archive_sha256":sha_file(source),"sidecar_authority_sha256":sha_file(authority),"run":run,"expected_model_count":800,"imported_model_count":sum(not x["missing"] for x in records),"missing_model_count":sum(x["missing"] for x in records),"accepted_source_failures":accepted_failures,"sidecar_authority_failures":sidecar_failures,"records":records,"no_shared_cache":True,"no_generated_binary_copied":True,"no_android_export":True}
    write_json(out/f"FULL_MODEL_CORPUS_{args.label}.json",result)
    if accepted_failures or sidecar_failures or result["missing_model_count"]: raise RuntimeError("full corpus import authority failure")
    return 0

def compare(args: argparse.Namespace) -> int:
    d1=json.loads(Path(args.d1).read_text());d2=json.loads(Path(args.d2).read_text());out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    a={x["logical_source"]:x for x in d1["records"]};b={x["logical_source"]:x for x in d2["records"]};paths=sorted(set(a)|set(b));rows=[];binary_diff=md5_diff=source_alarm=missing=0
    for logical in paths:
        x=a.get(logical);y=b.get(logical)
        if not x or not y:
            missing+=1;rows.append({"logical_source":logical,"status":"MISSING_PATH"});continue
        source_equal=x["source_sha256"]==y["source_sha256"] and x.get("source_md5")==y.get("source_md5")
        if not source_equal: source_alarm+=1
        binary_equal=x.get("imported_sha256")==y.get("imported_sha256") and x.get("imported_bytes")==y.get("imported_bytes")
        md5_equal=x.get("dest_md5")==y.get("dest_md5") and x.get("md5_sha256")==y.get("md5_sha256")
        if not binary_equal: binary_diff+=1
        if not md5_equal: md5_diff+=1
        rows.append({"logical_source":logical,"importer":x.get("importer"),"source_sha256":x["source_sha256"],"source_md5_d1":x.get("source_md5"),"source_md5_d2":y.get("source_md5"),"sidecar_sha256":x["sidecar_sha256"],"imported_path_d1":x.get("target_path"),"imported_path_d2":y.get("target_path"),"imported_bytes_d1":x.get("imported_bytes"),"imported_bytes_d2":y.get("imported_bytes"),"imported_sha256_d1":x.get("imported_sha256"),"imported_sha256_d2":y.get("imported_sha256"),"destination_md5_d1":x.get("dest_md5"),"destination_md5_d2":y.get("dest_md5"),"binary_equal":binary_equal,"destination_md5_equal":md5_equal,"source_hash_equal":source_equal,"semantic_comparison_status":"BYTE_IDENTICAL_IMPLIES_IDENTICAL_SERIALIZED_RESOURCE" if binary_equal else "NOT_ASSUMED_DIFFERENT_BINARY"})
    stage4_pass=len(paths)==800 and len(a)==len(b)==800 and binary_diff==0 and md5_diff==0 and source_alarm==0 and missing==0 and d1["missing_model_count"]==d2["missing_model_count"]==0 and not d1["accepted_source_failures"] and not d2["accepted_source_failures"] and not d1["sidecar_authority_failures"] and not d2["sidecar_authority_failures"]
    result={"schema_version":1,"engine_version":ENGINE_VERSION,"stage4_pass":stage4_pass,"classification":"STAGE4_PASS" if stage4_pass else "Q3","expected_model_resources":800,"imported_model_resources_d1":len(a),"imported_model_resources_d2":len(b),"identical_path_sets":set(a)==set(b),"differing_imported_binaries":binary_diff,"differing_destination_md5_records":md5_diff,"source_hash_alarms":source_alarm,"missing_resources":missing+d1["missing_model_count"]+d2["missing_model_count"],"importer_failures":d1["run"]["error_pattern_count"]+d2["run"]["error_pattern_count"],"records":rows,"no_sample_extrapolation":True,"no_android_export":True}
    write_json(out/"FULL_MODEL_CORPUS_COMPARISON.json",result);return 0 if stage4_pass else 2

def main()->int:
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest="cmd",required=True)
    p=sub.add_parser("seed");p.add_argument("--engine",required=True);p.add_argument("--source-zip",required=True);p.add_argument("--output",required=True);p.add_argument("--work-root",required=True)
    p=sub.add_parser("run");p.add_argument("--engine",required=True);p.add_argument("--source-zip",required=True);p.add_argument("--sidecar-zip",required=True);p.add_argument("--label",required=True);p.add_argument("--output",required=True);p.add_argument("--work-root",required=True)
    p=sub.add_parser("compare");p.add_argument("--d1",required=True);p.add_argument("--d2",required=True);p.add_argument("--output",required=True)
    args=ap.parse_args();return {"seed":seed,"run":run_full,"compare":compare}[args.cmd](args)
if __name__=="__main__":raise SystemExit(main())
