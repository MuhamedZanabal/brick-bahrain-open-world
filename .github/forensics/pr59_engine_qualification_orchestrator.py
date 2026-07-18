#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, platform, re, shutil, subprocess, sys, tarfile, urllib.request, zipfile
from pathlib import Path
from typing import Any

ROOT = Path(os.environ["GITHUB_WORKSPACE"])
TOKEN = os.environ["GH_TOKEN"]
RUN_ID = int(os.environ["GITHUB_RUN_ID"])
HARNESS = Path("/tmp/pr59_engine_qualification.py")
CORPUS_DIR = ROOT / "build/corpus"
CANDIDATES = ROOT / "build/candidates"
AGGREGATE = ROOT / "build/aggregate"
DOWNLOADS = ROOT / "build/downloads"
SOURCES = ROOT / "build/sources"
WORK = ROOT / "build/work"
SEMANTIC = ROOT / "qualification/.github/forensics/pr59_model_semantic_dump.gd"
FROZEN_PR_HEAD = "5b4e2466ef84f3984f3bf336b31925d4d2e97a7f"
STABLES = ["4.4.1-stable", "4.5.2-stable", "4.6.3-stable", "4.7.1-stable"]
OPTIONAL_DEV = "4.8-dev1"

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def run(cmd: list[str], *, env: dict[str, str] | None = None, check: bool = True, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, cwd=cwd)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed {result.returncode}: {cmd}\n{result.stdout[-8000:]}")
    return result

def api_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json", "User-Agent": "bahrain-brick-engine-qualification-v5"})
    with urllib.request.urlopen(req) as response:
        return json.load(response)

def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    run(["curl", "-fL", "--retry", "4", "--retry-all-errors", url, "-o", str(destination)])

def exact_asset(release: dict[str, Any], name: str) -> dict[str, Any]:
    rows = [a for a in release.get("assets", []) if a.get("name") == name]
    if len(rows) != 1:
        raise RuntimeError(f"expected exactly one official asset {name}, found {len(rows)}")
    return rows[0]

def checksum_authority(release: dict[str, Any], asset: dict[str, Any]) -> dict[str, Any]:
    digest = asset.get("digest") or ""
    if digest.startswith("sha256:"):
        return {"mode": "release_api_digest", "sha256": digest[7:], "asset": None}
    for name in [asset["name"] + ".sha256", asset["name"] + ".sha256sum"]:
        rows = [a for a in release.get("assets", []) if a.get("name") == name]
        if len(rows) == 1:
            return {"mode": "companion_sha256_asset", "sha256": None, "asset": rows[0]}
        if len(rows) > 1:
            raise RuntimeError(f"duplicate checksum assets for {name}")
    manifest_names = {"SHA256SUMS", "SHA256SUMS.txt", "sha256sums.txt", "SHA256-SUMS.txt"}
    rows = [a for a in release.get("assets", []) if a.get("name") in manifest_names]
    if len(rows) == 1:
        return {"mode": "release_sha256_manifest", "sha256": None, "asset": rows[0]}
    raise RuntimeError(f"no official SHA-256 authority for {asset['name']}")

def resolve_checksum(target: dict[str, Any], authority: dict[str, Any], directory: Path) -> tuple[str, dict[str, Any]]:
    if authority["sha256"]:
        return authority["sha256"], {"mode": authority["mode"], "asset_name": None, "asset_id": None, "asset_bytes": None, "asset_sha256": None}
    check_asset = authority["asset"]
    check_path = directory / check_asset["name"]
    download(check_asset["browser_download_url"], check_path)
    text = check_path.read_text("utf-8", errors="replace")
    if authority["mode"] == "companion_sha256_asset":
        matches = {x.lower() for x in re.findall(r"(?i)\b[0-9a-f]{64}\b", text)}
    else:
        matches = set()
        for line in text.splitlines():
            if target["name"] in line:
                found = re.search(r"(?i)\b[0-9a-f]{64}\b", line)
                if found:
                    matches.add(found.group(0).lower())
    if len(matches) != 1:
        raise RuntimeError(f"expected one exact official SHA-256 for {target['name']}, found {sorted(matches)}")
    return next(iter(matches)), {"mode": authority["mode"], "asset_name": check_asset["name"], "asset_id": check_asset["id"], "asset_bytes": check_asset["size"], "asset_sha256": sha256_file(check_path)}

def prepare_corpus() -> Path:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    source_zip = next((p for p in (ROOT / "build/input").rglob("MANAMA_SOUQ_COMPOSITE_SOURCE.zip")), None)
    selection = next((p for p in (ROOT / "build/forensic").rglob("REPRESENTATIVE_SELECTION.json")), None)
    if not source_zip or not selection:
        raise RuntimeError("accepted source or representative selection artifact missing")
    run([sys.executable, str(HARNESS), "prepare-corpus", "--source-zip", str(source_zip), "--selection", str(selection), "--output", str(CORPUS_DIR)])
    corpus = CORPUS_DIR / "BAHRAIN_BRICK_ENGINE_QUALIFICATION_CORPUS.zip"
    if not corpus.is_file():
        raise RuntimeError("qualification corpus was not generated")
    return corpus

def source_tag_commit(tag: str) -> str:
    result = run(["git", "ls-remote", "https://github.com/godotengine/godot.git", f"refs/tags/{tag}^{{}}"], check=False)
    lines = result.stdout.strip().splitlines()
    if not lines:
        result = run(["git", "ls-remote", "https://github.com/godotengine/godot.git", f"refs/tags/{tag}"])
        lines = result.stdout.strip().splitlines()
    if len(lines) != 1:
        raise RuntimeError(f"could not resolve exact source tag commit for {tag}: {lines}")
    return lines[0].split()[0]

def qualify(tag: str, corpus: Path) -> dict[str, Any]:
    out, dl, src, work = CANDIDATES / tag, DOWNLOADS / tag, SOURCES / tag, WORK / tag
    for path in (out, dl, src, work):
        path.mkdir(parents=True, exist_ok=True)
    try:
        release = api_json(f"https://api.github.com/repos/godotengine/godot-builds/releases/tags/{tag}")
        binary_name, source_name = f"Godot_v{tag}_linux.x86_64.zip", f"godot-{tag}.tar.xz"
        binary_asset, source_asset = exact_asset(release, binary_name), exact_asset(release, source_name)
        binary_auth, source_auth = checksum_authority(release, binary_asset), checksum_authority(release, source_asset)
        binary_path, source_path = dl / binary_name, dl / source_name
        download(binary_asset["browser_download_url"], binary_path)
        download(source_asset["browser_download_url"], source_path)
        binary_sha, binary_auth_record = resolve_checksum(binary_asset, binary_auth, dl)
        source_sha, source_auth_record = resolve_checksum(source_asset, source_auth, dl)
        if sha256_file(binary_path) != binary_sha:
            raise RuntimeError(f"binary checksum mismatch for {tag}")
        if sha256_file(source_path) != source_sha:
            raise RuntimeError(f"source checksum mismatch for {tag}")
        engine_dir = dl / "engine"
        with zipfile.ZipFile(binary_path) as archive:
            archive.extractall(engine_dir)
        engine_files = [p for p in engine_dir.rglob("Godot*") if p.is_file() and not p.name.endswith(".txt")]
        if len(engine_files) != 1:
            raise RuntimeError(f"expected one engine executable for {tag}, found {[p.name for p in engine_files]}")
        engine = engine_files[0]
        engine.chmod(0o755)
        with tarfile.open(source_path, "r:xz") as archive:
            archive.extractall(src, filter="data")
        source_roots = [p for p in src.iterdir() if p.is_dir()]
        if len(source_roots) != 1:
            raise RuntimeError(f"expected one source root for {tag}")
        source_root = source_roots[0]
        version_output = run([str(engine), "--version"]).stdout.strip().splitlines()[0]
        identity = {"tag": tag, "release_id": release["id"], "release_url": release["html_url"], "published_at": release["published_at"], "prerelease": bool(release["prerelease"]), "draft": bool(release["draft"]), "binary_archive_filename": binary_name, "binary_archive_sha256": binary_sha, "binary_asset_id": binary_asset["id"], "binary_asset_bytes": binary_asset["size"], "binary_checksum_authority": binary_auth_record, "source_archive_filename": source_name, "source_archive_sha256": source_sha, "source_asset_id": source_asset["id"], "source_asset_bytes": source_asset["size"], "source_checksum_authority": source_auth_record, "source_tag_commit": source_tag_commit(tag), "runtime_version_output": version_output, "operating_system": platform.platform(), "architecture": platform.machine(), "locale": "C.UTF-8", "timezone": "UTC", "umask": "0022", "cpu_count": os.cpu_count(), "command_line_arguments": ["--headless", "--path", "<disposable-project>", "--editor", "--import", "--quit", "--verbose"], "import_environment": {"TZ": "UTC", "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8", "umask": "0022"}, "download_provenance": "official godotengine/godot-builds release API assets; SHA-256 verified through release API digest or exact official checksum asset"}
        write_json(out / "ENGINE_IDENTITY.json", identity)
        result = run([sys.executable, str(HARNESS), "stage2", "--engine", str(engine), "--identity", str(out / "ENGINE_IDENTITY.json"), "--source-root", str(source_root), "--corpus-zip", str(corpus), "--semantic-script", str(SEMANTIC), "--output", str(out), "--work-root", str(work)], check=False, env={**os.environ, "TZ": "UTC", "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8"})
        (out / "QUALIFICATION_COMMAND.log").write_text(result.stdout)
        if result.returncode != 0:
            write_json(out / "ENGINE_CLASSIFICATION.json", {"engine_identity": {"tag": tag}, "classification": "Q6", "stage2_pass": False, "reason": f"qualification harness exited {result.returncode}"})
        return json.loads((out / "ENGINE_CLASSIFICATION.json").read_text())
    except Exception as exc:
        write_json(out / "ENGINE_CLASSIFICATION.json", {"engine_identity": {"tag": tag}, "classification": "Q6", "stage2_pass": False, "reason": f"{type(exc).__name__}: {exc}"})
        write_json(out / "QUALIFICATION_EXCEPTION.json", {"type": type(exc).__name__, "message": str(exc)})
        return json.loads((out / "ENGINE_CLASSIFICATION.json").read_text())
    finally:
        shutil.rmtree(dl, ignore_errors=True)
        shutil.rmtree(src, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)

def main() -> int:
    for path in (CANDIDATES, AGGREGATE, DOWNLOADS, SOURCES, WORK):
        path.mkdir(parents=True, exist_ok=True)
    corpus = prepare_corpus()
    stable_pass = False
    for tag in STABLES:
        result = qualify(tag, corpus)
        stable_pass = stable_pass or bool(result.get("stage2_pass"))
    if not stable_pass:
        qualify(OPTIONAL_DEV, corpus)
    else:
        write_json(CANDIDATES / OPTIONAL_DEV / "UNAVAILABLE_CANDIDATE.json", {"requested_version": OPTIONAL_DEV, "status": "not_entered", "checked_at_utc": None, "evidence": "At least one stable candidate passed Stage 2 and must complete Stages 3-6 before the optional development-build rule can be evaluated.", "classification": "Q6", "reason": "Optional development diagnostic not entered."})
    run([sys.executable, str(HARNESS), "aggregate", "--candidate-root", str(CANDIDATES), "--output", str(AGGREGATE)])
    shutil.copy2(CORPUS_DIR / "CORPUS_AUTHORITY_RESOLUTION.json", AGGREGATE)
    shutil.copy2(CORPUS_DIR / "QUALIFICATION_CORPUS_ARCHIVE.json", AGGREGATE)
    rows = []
    for path in sorted(p for p in AGGREGATE.rglob("*") if p.is_file() and p.name != "FINAL_AGGREGATE_INVENTORY.json"):
        rows.append({"path": path.relative_to(AGGREGATE).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    write_json(AGGREGATE / "FINAL_AGGREGATE_INVENTORY.json", {"workflow_run_id": RUN_ID, "frozen_pr_head": FROZEN_PR_HEAD, "files": rows, "no_android_export": True, "no_project_migration": True})
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
