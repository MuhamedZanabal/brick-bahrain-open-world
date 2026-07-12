#!/usr/bin/env python3
"""Verify Bahrain Bricks v15 authority artifacts without modifying a repository.

Exit codes:
  0: all requested checks passed
  2: verification failed
  3: invocation/environment error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


class VerificationError(RuntimeError):
    pass


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: Iterable[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(f"Cannot read manifest {path}: {exc}") from exc
    if not isinstance(manifest.get("artifacts"), dict):
        raise VerificationError("Manifest must contain an artifacts object")
    return manifest


def identify_artifact(path: Path, manifest: dict[str, Any], kind: str | None) -> tuple[str, dict[str, Any]]:
    artifacts = manifest["artifacts"]
    if path.name in artifacts:
        return path.name, artifacts[path.name]
    if kind:
        matches = [(name, spec) for name, spec in artifacts.items() if spec.get("kind") == kind]
        if len(matches) == 1:
            return matches[0]
        raise VerificationError(
            f"Artifact filename {path.name!r} is not in the manifest and kind {kind!r} "
            f"matches {len(matches)} entries"
        )
    raise VerificationError(
        f"Artifact filename {path.name!r} is not listed in the manifest; use the canonical filename"
    )


def verify_common(path: Path, name: str, spec: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    if not path.is_file():
        return [Check("file_present", False, f"File not found: {path}")]
    checks.append(Check("file_present", True, str(path.resolve())))

    actual_size = path.stat().st_size
    expected_size = spec.get("size")
    if expected_size is not None:
        checks.append(
            Check(
                "size",
                actual_size == int(expected_size),
                f"actual={actual_size} expected={expected_size}",
            )
        )
    else:
        checks.append(Check("size", True, f"actual={actual_size}; no expected size recorded"))

    actual_hash = sha256_file(path)
    expected_hash = str(spec.get("sha256", "")).lower()
    checks.append(
        Check(
            "sha256",
            bool(expected_hash) and actual_hash == expected_hash,
            f"actual={actual_hash} expected={expected_hash or '<missing>'}",
        )
    )
    checks.append(Check("manifest_identity", path.name == name, f"canonical={name} supplied={path.name}"))
    return checks


def verify_zip(path: Path, kind: str) -> list[Check]:
    checks: list[Check] = []
    try:
        with zipfile.ZipFile(path) as archive:
            bad_member = archive.testzip()
            names = archive.namelist()
            checks.append(Check("zip_integrity", bad_member is None, f"bad_member={bad_member}"))
            if kind == "source_zip":
                project_files = [name for name in names if name.rstrip("/").endswith("project.godot")]
                checks.append(
                    Check(
                        "godot_project_present",
                        len(project_files) == 1,
                        f"matches={project_files[:5]} count={len(project_files)}",
                    )
                )
            elif kind == "apk":
                required = {"AndroidManifest.xml", "classes.dex"}
                missing = sorted(required.difference(names))
                checks.append(Check("apk_core_entries", not missing, f"missing={missing}"))
    except (OSError, zipfile.BadZipFile) as exc:
        checks.append(Check("zip_integrity", False, str(exc)))
    return checks


def verify_bundle(path: Path, manifest: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    if shutil.which("git") is None:
        return [Check("git_available", False, "git executable not found")]
    checks.append(Check("git_available", True, shutil.which("git") or "git"))

    with tempfile.TemporaryDirectory(prefix="bb-bundle-verify-") as verify_dir:
        verify_repo = Path(verify_dir) / "verify.git"
        init = run(["git", "init", "--bare", str(verify_repo)])
        checks.append(Check("bundle_verify_repo", init.returncode == 0, init.stdout.strip()))
        if init.returncode != 0:
            return checks
        bundle_verify = run(["git", "bundle", "verify", str(path.resolve())], cwd=verify_repo)
    checks.append(Check("bundle_verify", bundle_verify.returncode == 0, bundle_verify.stdout.strip()))
    if bundle_verify.returncode != 0:
        return checks

    authority = manifest.get("authority", {})
    expected_branch = str(authority.get("branch", ""))
    expected_commit = str(authority.get("commit", ""))
    expected_tree = str(authority.get("tree", ""))

    heads = run(["git", "bundle", "list-heads", str(path)])
    checks.append(Check("bundle_list_heads", heads.returncode == 0, heads.stdout.strip()))
    if expected_branch:
        expected_ref = f"refs/heads/{expected_branch}"
        branch_line = next((line for line in heads.stdout.splitlines() if line.endswith(expected_ref)), None)
        checks.append(Check("authority_branch_in_bundle", branch_line is not None, branch_line or expected_ref))

    with tempfile.TemporaryDirectory(prefix="bb-authority-") as temp_dir:
        clone_path = Path(temp_dir) / "repo"
        clone = run(["git", "clone", "--no-checkout", str(path), str(clone_path)])
        checks.append(Check("bundle_clone", clone.returncode == 0, clone.stdout.strip()))
        if clone.returncode != 0:
            return checks

        if expected_branch:
            checkout = run(["git", "checkout", expected_branch], cwd=clone_path)
            if checkout.returncode != 0 and expected_commit:
                checkout = run(["git", "checkout", "--detach", expected_commit], cwd=clone_path)
            checks.append(Check("authority_checkout", checkout.returncode == 0, checkout.stdout.strip()))
            if checkout.returncode != 0:
                return checks

        head = run(["git", "rev-parse", "HEAD"], cwd=clone_path)
        actual_commit = head.stdout.strip()
        checks.append(
            Check(
                "authority_commit",
                head.returncode == 0 and bool(expected_commit) and actual_commit == expected_commit,
                f"actual={actual_commit} expected={expected_commit}",
            )
        )

        tree = run(["git", "rev-parse", "HEAD^{tree}"], cwd=clone_path)
        actual_tree = tree.stdout.strip()
        checks.append(
            Check(
                "authority_tree",
                tree.returncode == 0 and bool(expected_tree) and actual_tree == expected_tree,
                f"actual={actual_tree} expected={expected_tree}",
            )
        )

        status = run(["git", "status", "--porcelain"], cwd=clone_path)
        checks.append(
            Check(
                "clean_worktree",
                status.returncode == 0 and status.stdout.strip() == "",
                status.stdout.strip() or "clean",
            )
        )

        project_files = list(clone_path.rglob("project.godot"))
        checks.append(
            Check(
                "godot_project_present",
                len(project_files) == 1,
                f"matches={[str(p.relative_to(clone_path)) for p in project_files[:5]]} count={len(project_files)}",
            )
        )
    return checks


def verify_artifact(path: Path, manifest: dict[str, Any], kind: str | None = None) -> dict[str, Any]:
    canonical_name, spec = identify_artifact(path, manifest, kind)
    artifact_kind = str(spec.get("kind", "generic"))
    checks = verify_common(path, canonical_name, spec)

    # Do not parse a file further when identity checks already failed; this avoids treating
    # an arbitrary ZIP or bundle as trusted project content.
    common_passed = all(check.passed for check in checks if check.name in {"file_present", "size", "sha256"})
    if common_passed:
        if artifact_kind in {"source_zip", "apk"}:
            checks.extend(verify_zip(path, artifact_kind))
        elif artifact_kind == "git_bundle":
            checks.extend(verify_bundle(path, manifest))

    return {
        "artifact": str(path),
        "canonical_name": canonical_name,
        "kind": artifact_kind,
        "passed": all(check.passed for check in checks),
        "checks": [asdict(check) for check in checks],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", nargs="+", type=Path, help="Artifact files to verify")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).with_name("v15_authority_manifest.json"),
        help="Verification manifest JSON",
    )
    parser.add_argument(
        "--kind",
        choices=("git_bundle", "source_zip", "apk"),
        help="Use only when testing a custom manifest with a non-canonical filename",
    )
    parser.add_argument("--json-output", type=Path, help="Write complete machine-readable results")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        results = [verify_artifact(path, manifest, args.kind) for path in args.artifacts]
    except VerificationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

    payload = {
        "schema_version": 1,
        "passed": all(result["passed"] for result in results),
        "manifest": str(args.manifest),
        "results": results,
    }
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    for result in results:
        state = "PASS" if result["passed"] else "FAIL"
        print(f"[{state}] {result['canonical_name']} ({result['kind']})")
        for check in result["checks"]:
            marker = "PASS" if check["passed"] else "FAIL"
            print(f"  [{marker}] {check['name']}: {check['detail']}")

    return 0 if payload["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
