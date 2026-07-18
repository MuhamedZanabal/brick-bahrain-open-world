#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, time, zipfile
from pathlib import Path, PurePosixPath
from typing import Any

CORPUS_SHA = "413a0d6516bd3cb2e8b64e2f4f0bf0f33a1b8cc9ae57c7c4202e6d397b213739"
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
        raise ValueError(name)
    return name.rstrip("/")

def extract(archive: Path, target: Path) -> list[dict[str, Any]]:
    if target.exists(): shutil.rmtree(target)
    target.mkdir(parents=True)
    rows = []
    with zipfile.ZipFile(archive) as z:
        infos = sorted((i for i in z.infolist() if not i.is_dir()), key=lambda i: i.filename)
        names = [safe_name(i.filename) for i in infos]
        if len(names) != len(set(names)): raise RuntimeError("duplicate paths")
        for info in infos:
            rel = safe_name(info.filename); data = z.read(info); dst = target / rel
            dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(data); os.chmod(dst, 0o644); os.utime(dst, (315532800, 315532800))
            rows.append({"path": rel, "bytes": len(data), "sha256": sha_bytes(data)})
    return rows

def overlay(archive: Path, root: Path) -> None:
    with zipfile.ZipFile(archive) as z:
        infos = sorted((i for i in z.infolist() if not i.is_dir()), key=lambda i: i.filename)
        names = [safe_name(i.filename) for i in infos]
        if len(names) != len(set(names)): raise RuntimeError("duplicate sidecar paths")
        if len(names) != 8: raise RuntimeError(f"expected 8 strict sidecars, got {len(names)}")
        for info in infos:
            rel = safe_name(info.filename); dst = root / rel; dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(z.read(info)); os.chmod(dst, 0o444); os.utime(dst, (315532800, 315532800))

def parse_sidecar(path: Path) -> dict[str, Any]:
    data = path.read_bytes(); text = data[:-1].decode() if data.endswith(b"\0") else data.decode()
    pm, sm = PATH_RE.search(text), SOURCE_RE.search(text)
    return {"path": pm.group(1) if pm else None, "source_file": sm.group(1) if sm else None, "bytes": len(data), "sha256": sha_bytes(data)}

def generated_inventory(root: Path, original_paths: set[str]) -> dict[str, Any]:
    rows, editor = [], []
    for path in sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.relative_to(root).as_posix()):
        rel = path.relative_to(root).as_posix()
        if rel in original_paths: continue
        row = {"path": rel, "bytes": path.stat().st_size, "sha256": sha_file(path)}
        if rel.startswith(".godot/editor/"): editor.append(row)
        else: rows.append(row)
    aggregate = sha_bytes("\n".join(f"{r['path']}\0{r['bytes']}\0{r['sha256']}" for r in rows).encode())
    return {"records": rows, "editor_cache_records": editor, "aggregate_sha256": aggregate, "path_count": len(rows)}

def run_one(engine: Path, corpus: Path, sidecars: Path, label: str, root: Path, output: Path) -> dict[str, Any]:
    if sha_file(corpus) != CORPUS_SHA: raise RuntimeError("corpus SHA mismatch")
    original = extract(corpus, root); original_map = {x["path"]: x for x in original}; overlay(sidecars, root)
    env = os.environ.copy(); xdg = output / "xdg"; shutil.rmtree(xdg, ignore_errors=True); xdg.mkdir(parents=True)
    env.update({"TZ": "UTC", "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8", "XDG_DATA_HOME": str(xdg)})
    log = output / "godot.log"; start = time.time()
    with log.open("wb") as f:
        proc = subprocess.run([str(engine), "--headless", "--path", str(root), "--editor", "--import", "--quit", "--verbose"], stdout=f, stderr=subprocess.STDOUT, env=env)
    log_data = log.read_bytes()
    original_after = []
    for rel in sorted(original_map):
        path = root / rel
        if not path.is_file(): raise RuntimeError(f"original source missing after import: {rel}")
        original_after.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha_file(path)})
    authority_equal = original == original_after
    generated = generated_inventory(root, set(original_map))
    model_rows = []
    for sidecar in sorted(root.rglob("*.import")):
        rel = sidecar.relative_to(root).as_posix(); logical = rel[:-7]
        if PurePosixPath(logical).suffix.lower() not in MODEL_EXTS: continue
        meta = parse_sidecar(sidecar)
        if meta["source_file"] != logical: raise RuntimeError(f"source identity mismatch {rel}")
        target = meta["path"]
        if not target: raise RuntimeError(f"missing target {rel}")
        imported = root / target; md5 = imported.with_suffix(".md5")
        if not imported.is_file() or not md5.is_file(): raise RuntimeError(f"missing imported output for {logical}")
        fields = dict(MD5_RE.findall(md5.read_text()))
        model_rows.append({"logical_source": logical, "sidecar_path": rel, "sidecar_sha256": meta["sha256"], "target_path": target, "imported_bytes": imported.stat().st_size, "imported_sha256": sha_file(imported), "md5_path": md5.relative_to(root).as_posix(), "md5_sha256": sha_file(md5), "source_md5": fields.get("source_md5"), "dest_md5": fields.get("dest_md5")})
    if len(model_rows) != 8: raise RuntimeError(f"expected 8 model outputs, got {len(model_rows)}")
    result = {"schema_version": 1, "label": label, "engine_version": ENGINE_VERSION, "engine_executable_sha256": sha_file(engine), "corpus_sha256": CORPUS_SHA, "strict_sidecar_authority_sha256": sha_file(sidecars), "canonical_root": str(root.resolve()), "environment": {"TZ": "UTC", "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8", "umask": "0022", "cpu_count": os.cpu_count()}, "command": [str(engine), "--headless", "--path", str(root), "--editor", "--import", "--quit", "--verbose"], "exit_code": proc.returncode, "elapsed_seconds": round(time.time() - start, 3), "error_pattern_count": len(ERROR_RE.findall(log_data.decode(errors="replace"))), "log_sha256": sha_bytes(log_data), "original_authority_unchanged": authority_equal, "generated": generated, "model_count": len(model_rows), "models": model_rows, "uid_cache": next((x for x in generated["records"] if x["path"] == ".godot/uid_cache.bin"), None), "no_shared_cache": True, "no_generated_binary_copied": True, "no_android_export": True}
    write_json(output / "IMPORT_MANIFEST.json", result)
    if proc.returncode or result["error_pattern_count"] or not authority_equal: raise RuntimeError(f"import failed: {result}")
    return result

def same_runner(args: argparse.Namespace) -> int:
    out = Path(args.output); out.mkdir(parents=True, exist_ok=True); engine, corpus, sidecars = Path(args.engine), Path(args.corpus_zip), Path(args.sidecar_zip)
    runs = []
    canonical = Path(args.work_root) / "canonical/game"
    for label in ("A1", "A2", "A3"):
        run_out = out / label; run_out.mkdir(parents=True, exist_ok=True); runs.append(run_one(engine, corpus, sidecars, label, canonical, run_out))
    for label in ("B1", "B2"):
        run_out = out / label; run_out.mkdir(parents=True, exist_ok=True); root = Path(args.work_root) / f"different-{label.lower()}/game"; runs.append(run_one(engine, corpus, sidecars, label, root, run_out))
    write_json(out / "SAME_RUNNER_SUMMARY.json", {"runs": [{"label": x["label"], "aggregate_sha256": x["generated"]["aggregate_sha256"], "path_count": x["generated"]["path_count"], "uid_cache": x["uid_cache"]} for x in runs]})
    return 0

def one(args: argparse.Namespace) -> int:
    out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    run_one(Path(args.engine), Path(args.corpus_zip), Path(args.sidecar_zip), args.label, Path(args.work_root) / "game", out)
    return 0

def compare(args: argparse.Namespace) -> int:
    root = Path(args.input_root); out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    manifests = [json.loads(p.read_text()) for p in sorted(root.rglob("IMPORT_MANIFEST.json"))]
    by_label = {x["label"]: x for x in manifests}; expected = {"A1", "A2", "A3", "B1", "B2", "C1", "C2", "D1", "D2"}
    if set(by_label) != expected: raise RuntimeError(f"manifest labels mismatch: {sorted(by_label)}")
    base = {x["path"]: x for x in by_label["A1"]["generated"]["records"]}
    comparisons = []
    for label in sorted(expected):
        current = {x["path"]: x for x in by_label[label]["generated"]["records"]}; differences = []
        for path in sorted(set(base) | set(current)):
            if path not in base or path not in current:
                differences.append({"path": path, "category": "PATH_SET", "missing_baseline": path not in base, "missing_candidate": path not in current})
            elif base[path]["sha256"] != current[path]["sha256"] or base[path]["bytes"] != current[path]["bytes"]:
                category = "OTHER"
                if path.startswith(".godot/imported/") and path.endswith(".md5"): category = "IMPORTED_MD5"
                elif path.startswith(".godot/imported/"): category = "IMPORTED_BINARY"
                elif path.endswith(".import"): category = "SOURCE_ADJACENT_IMPORT"
                elif path == ".godot/uid_cache.bin": category = "UID_CACHE"
                differences.append({"path": path, "category": category, "baseline": base[path], "candidate": current[path]})
        comparisons.append({"label": label, "difference_count": len(differences), "differences": differences, "aggregate_equal": by_label[label]["generated"]["aggregate_sha256"] == by_label["A1"]["generated"]["aggregate_sha256"], "original_authority_unchanged": by_label[label]["original_authority_unchanged"], "model_count": by_label[label]["model_count"]})
    pass_all = all(x["difference_count"] == 0 and x["aggregate_equal"] and x["original_authority_unchanged"] and x["model_count"] == 8 for x in comparisons)
    same = [x for x in comparisons if x["label"].startswith(("A", "B"))]
    cross = [x for x in comparisons if x["label"].startswith(("C", "D"))]
    write_json(out / "ENGINE_REPEATABILITY_MATRIX.json", {"engine_version": ENGINE_VERSION, "stage3_pass": pass_all, "same_runner_and_path": [x for x in same if x["label"].startswith("A")], "different_absolute_paths": [x for x in same if x["label"].startswith("B")], "all_comparisons": comparisons})
    write_json(out / "ENGINE_CROSS_RUNNER_COMPARISON.json", {"engine_version": ENGINE_VERSION, "stage3_pass": pass_all, "separate_runner": [x for x in cross if x["label"].startswith("C")], "parallel_runner": [x for x in cross if x["label"].startswith("D")], "zero_imported_binary_differences": all(not any(d["category"] == "IMPORTED_BINARY" for d in x["differences"]) for x in comparisons), "zero_imported_md5_differences": all(not any(d["category"] == "IMPORTED_MD5" for d in x["differences"]) for x in comparisons)})
    write_json(out / "STAGE3_CLASSIFICATION.json", {"classification": "STAGE3_PASS" if pass_all else "Q2", "stage3_pass": pass_all, "run_count": len(manifests), "baseline_generated_aggregate_sha256": by_label["A1"]["generated"]["aggregate_sha256"], "no_shared_cache": True, "no_android_export": True})
    return 0 if pass_all else 2

def main() -> int:
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("same-runner", "one"):
        p = sub.add_parser(name); p.add_argument("--engine", required=True); p.add_argument("--corpus-zip", required=True); p.add_argument("--sidecar-zip", required=True); p.add_argument("--work-root", required=True); p.add_argument("--output", required=True)
        if name == "one": p.add_argument("--label", required=True)
    p = sub.add_parser("compare"); p.add_argument("--input-root", required=True); p.add_argument("--output", required=True)
    args = ap.parse_args()
    return {"same-runner": same_runner, "one": one, "compare": compare}[args.cmd](args)

if __name__ == "__main__": raise SystemExit(main())
