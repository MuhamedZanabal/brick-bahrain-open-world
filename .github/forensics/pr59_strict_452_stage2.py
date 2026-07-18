#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, time, zipfile
from pathlib import Path, PurePosixPath
from typing import Any

CORPUS_SHA = "413a0d6516bd3cb2e8b64e2f4f0bf0f33a1b8cc9ae57c7c4202e6d397b213739"
ENGINE_SHA = "87f6e6be292929e363d15ed9052f277b2ba4e95ed994e1e099048097be2dfd03"
ENGINE_VERSION = "4.5.2.stable.official.6ce3de25a"
MODEL_EXTS = {".glb", ".gltf", ".fbx", ".obj"}
PATH_RE = re.compile(r'(?m)^path="res://([^"\r\n]+)"\s*$')
SOURCE_RE = re.compile(r'(?m)^source_file="res://([^"\r\n]+)"\s*$')
MD5_RE = re.compile(r'(?m)^([A-Za-z0-9_./-]+)="([^"]*)"\s*$')
ERROR_RE = re.compile(r"SCRIPT ERROR|Parse Error|Parser Error|Failed to load script|Failed to create an autoload|\bFATAL\b|Fatal signal", re.I)

def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def safe_name(name: str) -> str:
    if name.startswith("/") or "\\" in name or ".." in PurePosixPath(name).parts:
        raise ValueError(f"unsafe archive path: {name}")
    return name.rstrip("/")

def extract_exact(archive: Path, target: Path) -> list[dict[str, Any]]:
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    rows = []
    with zipfile.ZipFile(archive) as z:
        infos = sorted((i for i in z.infolist() if not i.is_dir()), key=lambda i: i.filename)
        names = [safe_name(i.filename) for i in infos]
        if len(names) != len(set(names)):
            raise RuntimeError("duplicate archive paths")
        for info in infos:
            rel = safe_name(info.filename)
            data = z.read(info)
            dst = target / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
            os.chmod(dst, 0o644)
            os.utime(dst, (315532800, 315532800))
            rows.append({"path": rel, "bytes": len(data), "sha256": sha_bytes(data)})
    for directory in sorted((p for p in target.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        os.chmod(directory, 0o755)
        os.utime(directory, (315532800, 315532800))
    return rows

def parse_sidecar(data: bytes) -> dict[str, Any]:
    text = data[:-1].decode("utf-8") if data.endswith(b"\0") else data.decode("utf-8")
    pm, sm = PATH_RE.search(text), SOURCE_RE.search(text)
    return {"path": pm.group(1) if pm else None, "source_file": sm.group(1) if sm else None, "sha256": sha_bytes(data), "bytes": len(data), "terminal_nul": data.endswith(b"\0")}

def strict_sidecars(source_zip: Path, output_zip: Path, output_manifest: Path) -> dict[str, Any]:
    rows = []
    with zipfile.ZipFile(source_zip) as src, zipfile.ZipFile(output_zip, "w", zipfile.ZIP_STORED) as dst:
        infos = sorted((i for i in src.infolist() if not i.is_dir()), key=lambda i: i.filename)
        for info in infos:
            rel = safe_name(info.filename)
            if not rel.endswith(".import"):
                raise RuntimeError(f"non-sidecar in authority: {rel}")
            logical = rel[:-7]
            if PurePosixPath(logical).suffix.lower() not in MODEL_EXTS:
                continue
            data = src.read(info)
            parsed = parse_sidecar(data)
            if parsed["source_file"] != logical:
                raise RuntimeError(f"source identity mismatch: {rel}: {parsed}")
            zi = zipfile.ZipInfo(rel, (1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_STORED
            zi.external_attr = (0o100444 << 16)
            dst.writestr(zi, data)
            rows.append({"path": rel, "logical_source": logical, **parsed})
    if len(rows) != 8:
        raise RuntimeError(f"expected exactly 8 model sidecars, got {len(rows)}")
    result = {"schema_version": 1, "source_authority_zip_sha256": sha_file(source_zip), "strict_sidecar_count": len(rows), "excluded_derived_sidecar_count": 8, "records": rows, "archive": {"path": str(output_zip), "bytes": output_zip.stat().st_size, "sha256": sha_file(output_zip)}, "rule": "Only the eight top-level model source sidecars are preserved; derived embedded-texture files and sidecars must be independently regenerated."}
    write_json(output_manifest, result)
    return result

def overlay(archive: Path, root: Path) -> None:
    with zipfile.ZipFile(archive) as z:
        for info in sorted((i for i in z.infolist() if not i.is_dir()), key=lambda i: i.filename):
            rel = safe_name(info.filename)
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(z.read(info))
            os.chmod(dst, 0o444)
            os.utime(dst, (315532800, 315532800))

def inventory(root: Path, *, original_paths: set[str]) -> dict[str, Any]:
    rows, original, generated, editor = [], [], [], []
    for path in sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.relative_to(root).as_posix()):
        rel = path.relative_to(root).as_posix()
        row = {"path": rel, "bytes": path.stat().st_size, "sha256": sha_file(path)}
        rows.append(row)
        if rel in original_paths:
            original.append(row)
        elif rel.startswith(".godot/editor/"):
            editor.append(row)
        else:
            generated.append(row)
    aggregate = sha_bytes("\n".join(f"{r['path']}\0{r['bytes']}\0{r['sha256']}" for r in generated).encode())
    return {"records": rows, "original_records": original, "generated_export_relevant": generated, "editor_cache_records": editor, "generated_export_relevant_aggregate_sha256": aggregate}

def run_import(engine: Path, root: Path, output: Path, semantic_script: Path, selection: Path, label: str, original_rows: list[dict[str, Any]]) -> dict[str, Any]:
    original_map = {r["path"]: r for r in original_rows}
    before = inventory(root, original_paths=set(original_map))
    env = os.environ.copy()
    xdg = output / f"xdg-{label}"
    if xdg.exists(): shutil.rmtree(xdg)
    xdg.mkdir(parents=True)
    env.update({"TZ": "UTC", "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8", "XDG_DATA_HOME": str(xdg)})
    log = output / f"{label}.godot.log"
    start = time.time()
    with log.open("wb") as f:
        proc = subprocess.run([str(engine), "--headless", "--path", str(root), "--editor", "--import", "--quit", "--verbose"], stdout=f, stderr=subprocess.STDOUT, env=env)
    log_data = log.read_bytes()
    after = inventory(root, original_paths=set(original_map))
    original_after = {r["path"]: r for r in after["original_records"]}
    authority_equal = original_map == original_after
    sem_path = output / f"{label}.MODEL_SEMANTIC_GRAPH.json"
    sem_log = output / f"{label}.semantic.log"
    with sem_log.open("wb") as f:
        sem = subprocess.run([str(engine), "--headless", "--path", str(root), "--script", str(semantic_script.resolve()), "--", str(selection.resolve()), str(sem_path.resolve())], stdout=f, stderr=subprocess.STDOUT, env=env)
    result = {"label": label, "command": [str(engine), "--headless", "--path", str(root), "--editor", "--import", "--quit", "--verbose"], "exit_code": proc.returncode, "elapsed_seconds": round(time.time() - start, 3), "error_pattern_count": len(ERROR_RE.findall(log_data.decode(errors="replace"))), "log_sha256": sha_bytes(log_data), "original_authority_equal_before_after": authority_equal, "before": before, "after": after, "semantic_exit_code": sem.returncode, "semantic_graph": {"path": str(sem_path), "exists": sem_path.is_file(), "bytes": sem_path.stat().st_size if sem_path.is_file() else None, "sha256": sha_file(sem_path) if sem_path.is_file() else None}}
    write_json(output / f"{label}.IMPORT_RESULT.json", result)
    if proc.returncode != 0 or result["error_pattern_count"] or not authority_equal or sem.returncode != 0 or not sem_path.is_file():
        raise RuntimeError(f"{label} import validation failed: {result}")
    return result

def compare(d1: dict[str, Any], d2: dict[str, Any], output: Path, selection: dict[str, Any]) -> dict[str, Any]:
    a = {r["path"]: r for r in d1["after"]["generated_export_relevant"]}
    b = {r["path"]: r for r in d2["after"]["generated_export_relevant"]}
    differences = []
    for path in sorted(set(a) | set(b)):
        if path not in a or path not in b:
            differences.append({"path": path, "category": "PATH_SET", "missing_d1": path not in a, "missing_d2": path not in b})
        elif a[path]["sha256"] != b[path]["sha256"] or a[path]["bytes"] != b[path]["bytes"]:
            category = "OTHER"
            if path.endswith(".import"): category = "SOURCE_ADJACENT_IMPORT"
            elif path == ".godot/uid_cache.bin": category = "UID_CACHE"
            elif path.startswith(".godot/imported/") and path.endswith(".md5"): category = "IMPORTED_MD5"
            elif path.startswith(".godot/imported/"): category = "IMPORTED_BINARY"
            elif not path.startswith(".godot/"): category = "DERIVED_SOURCE_FILE"
            differences.append({"path": path, "category": category, "d1": a[path], "d2": b[path]})
    resource_rows = []
    for item in selection["resources"]:
        logical = item["logical_source"]
        sidecar = logical + ".import"
        s1, s2 = parse_sidecar((Path(d1["root"]) / sidecar).read_bytes()), parse_sidecar((Path(d2["root"]) / sidecar).read_bytes())
        target1, target2 = s1["path"], s2["path"]
        p1, p2 = Path(d1["root"]) / target1, Path(d2["root"]) / target2
        md51, md52 = p1.with_suffix(".md5"), p2.with_suffix(".md5")
        fields1 = dict(MD5_RE.findall(md51.read_text())), fields2 = dict(MD5_RE.findall(md52.read_text()))
        resource_rows.append({"selection_id": item["selection_id"], "logical_source": logical, "source_type": item["source_type"], "matrix_member": item["matrix_member"], "sidecar_equal": s1 == s2, "target_path_equal": target1 == target2, "imported_bytes_d1": p1.stat().st_size, "imported_bytes_d2": p2.stat().st_size, "imported_sha256_d1": sha_file(p1), "imported_sha256_d2": sha_file(p2), "imported_equal": sha_file(p1) == sha_file(p2), "source_md5_d1": fields1.get("source_md5"), "source_md5_d2": fields2.get("source_md5"), "dest_md5_d1": fields1.get("dest_md5"), "dest_md5_d2": fields2.get("dest_md5"), "dest_md5_equal": fields1.get("dest_md5") == fields2.get("dest_md5")})
    sem1, sem2 = json.loads(Path(d1["semantic_graph"]["path"]).read_text()), json.loads(Path(d2["semantic_graph"]["path"]).read_text())
    category_counts: dict[str, int] = {}
    for row in differences: category_counts[row["category"]] = category_counts.get(row["category"], 0) + 1
    stage2_pass = not differences and all(x["imported_equal"] and x["dest_md5_equal"] and x["sidecar_equal"] and x["target_path_equal"] and x["source_md5_d1"] == x["source_md5_d2"] for x in resource_rows) and sem1 == sem2 and d1["original_authority_equal_before_after"] and d2["original_authority_equal_before_after"]
    result = {"schema_version": 1, "engine_version": ENGINE_VERSION, "strict_exact_source_test": True, "stage2_pass": stage2_pass, "classification": "STAGE2_PASS" if stage2_pass else "Q1", "explicit_editor_cache_exclusion": ".godot/editor/** only", "generated_export_relevant_path_set_equal": set(a) == set(b), "generated_export_relevant_difference_count": len(differences), "difference_category_counts": category_counts, "differences": differences, "resource_results": resource_rows, "semantic_equal": sem1 == sem2, "uid_cache_equal": a.get(".godot/uid_cache.bin") == b.get(".godot/uid_cache.bin"), "original_authority_unchanged_d1": d1["original_authority_equal_before_after"], "original_authority_unchanged_d2": d2["original_authority_equal_before_after"], "derived_source_files_d1": [r for r in a.values() if not r["path"].startswith(".godot/") and not r["path"].endswith(".import")], "derived_source_files_d2": [r for r in b.values() if not r["path"].startswith(".godot/") and not r["path"].endswith(".import")]}
    write_json(output / "STRICT_STAGE2_COMPARISON.json", result)
    return result

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--corpus-zip", required=True)
    ap.add_argument("--source-sidecar-zip", required=True)
    ap.add_argument("--semantic-script", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--work-root", required=True)
    args = ap.parse_args()
    engine, corpus_zip, source_sidecar_zip = Path(args.engine), Path(args.corpus_zip), Path(args.source_sidecar_zip)
    output, work = Path(args.output), Path(args.work_root)
    output.mkdir(parents=True, exist_ok=True)
    if sha_file(engine) != ENGINE_SHA: raise RuntimeError("engine SHA mismatch")
    if sha_file(corpus_zip) != CORPUS_SHA: raise RuntimeError("corpus SHA mismatch")
    strict_zip = output / "STRICT_MODEL_SIDECAR_AUTHORITY.zip"
    strict_manifest = output / "STRICT_MODEL_SIDECAR_AUTHORITY.json"
    strict_sidecars(source_sidecar_zip, strict_zip, strict_manifest)
    selection_root = work / "selection"
    original_rows = extract_exact(corpus_zip, selection_root)
    manifest_path = selection_root / "QUALIFICATION_CORPUS_MANIFEST.json"
    selection = json.loads(manifest_path.read_text())
    if len(selection["resources"]) != 8: raise RuntimeError("selection count mismatch")
    roots = {}
    results = {}
    for label in ("d1", "d2"):
        root = work / label
        rows = extract_exact(corpus_zip, root)
        if rows != original_rows: raise RuntimeError("independent corpus materialization mismatch")
        overlay(strict_zip, root)
        result = run_import(engine, root, output, Path(args.semantic_script), manifest_path, label, original_rows)
        result["root"] = str(root)
        roots[label] = root
        results[label] = result
    final = compare(results["d1"], results["d2"], output, selection)
    write_json(output / "STRICT_STAGE2_AUTHORITY.json", {"engine": {"version": ENGINE_VERSION, "sha256": ENGINE_SHA, "bytes": engine.stat().st_size}, "corpus": {"sha256": CORPUS_SHA, "bytes": corpus_zip.stat().st_size, "file_count": len(original_rows)}, "strict_sidecar_authority": json.loads(strict_manifest.read_text()), "no_generated_binary_copied": True, "no_derived_source_file_copied": True, "no_android_export": True, "no_project_migration": True})
    return 0 if final["stage2_pass"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
