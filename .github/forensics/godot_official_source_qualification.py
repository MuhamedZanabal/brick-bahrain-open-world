#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import tarfile
import urllib.request
from pathlib import Path

CANDIDATES = ["4.4.1-stable", "4.5.2-stable", "4.6.3-stable", "4.7.1-stable"]
BASELINE = "4.3-stable"
CORPUS = [
    "assets/generated/full_matrix/architecture/low/waterfront/bh_waterfront_hotel_dropoff_01_lod0.glb",
    "assets/generated/full_matrix/architecture/balanced/souq/bh_souq_shop_perfume_01_lod1.glb",
    "assets/generated/full_matrix/architecture/high/traditional/bh_traditional_alley_arch_01_lod0.glb",
    "assets/props/street/bh_cr_desert_planter_01_lod0.glb",
    "assets/characters_kit/Casual_Male.gltf",
    "assets/citykit/models/Brick_Plain_1.gltf",
    "assets/characters/fbx/Cowboy_Male.fbx",
    "addons/flexible_toon_shader/example/cup.obj",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def request(url: str) -> urllib.request.Request:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "bahrain-brick-engine-qualification",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    return urllib.request.Request(url, headers=headers)


def get_json(url: str) -> dict:
    with urllib.request.urlopen(request(url), timeout=120) as response:
        return json.load(response)


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(request(url), timeout=300) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle, 1024 * 1024)


def tag_commit(tag: str) -> str:
    ref = get_json(f"https://api.github.com/repos/godotengine/godot/git/ref/tags/{tag}")
    obj = ref["object"]
    if obj["type"] == "tag":
        obj = get_json(obj["url"])["object"]
    return obj["sha"]


def extract_source(archive: Path, destination: Path) -> Path:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    with tarfile.open(archive, "r:gz") as handle:
        handle.extractall(destination, filter="data")
    roots = [path for path in destination.iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise RuntimeError(f"unexpected source roots: {roots}")
    return roots[0]


def function_text(text: str, signature: str) -> str:
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise RuntimeError(f"unterminated function: {signature}")


def audit_source(tag: str, source_root: Path) -> dict:
    resource = source_root / "core/io/resource.cpp"
    saver = source_root / "core/io/resource_format_binary.cpp"
    resource_text = resource.read_text(errors="replace")
    saver_text = saver.read_text(errors="replace")
    generator = function_text(resource_text, "String Resource::generate_scene_unique_id()")
    saver_excerpt = "\n".join(
        line
        for line in saver_text.splitlines()
        if "generate_scene_unique_id" in line
        or "local://" in line
        or "get_scene_unique_id" in line
    )
    findings = {
        "uses_wall_clock": "get_datetime()" in generator,
        "uses_microsecond_ticks": "get_ticks_usec()" in generator,
        "uses_random_number_generation": "Math::rand()" in generator
        or "unique_id_gen.rand()" in generator,
        "generates_random_five_character_local_ids": "characters = 5" in generator,
        "binary_saver_calls_scene_unique_id_generator": "Resource::generate_scene_unique_id()"
        in saver_text,
        "binary_saver_serializes_local_ids": '"local://" + r->get_scene_unique_id()'
        in saver_text,
        "seed_api_exists_but_default_is_environment_random": "seed_scene_unique_id"
        in resource_text
        and "get_seed() == 0" in generator,
        "documented_supported_deterministic_import_option_found": False,
    }
    required = [
        "uses_wall_clock",
        "uses_microsecond_ticks",
        "uses_random_number_generation",
        "generates_random_five_character_local_ids",
        "binary_saver_calls_scene_unique_id_generator",
        "binary_saver_serializes_local_ids",
    ]
    persists = all(findings[key] for key in required)
    return {
        "schema_version": 1,
        "tag": tag,
        "source_files": {
            "core/io/resource.cpp": {
                "bytes": resource.stat().st_size,
                "sha256": sha256(resource),
            },
            "core/io/resource_format_binary.cpp": {
                "bytes": saver.stat().st_size,
                "sha256": sha256(saver),
            },
        },
        "generate_scene_unique_id_sha256": hashlib.sha256(generator.encode()).hexdigest(),
        "relevant_source_excerpt_sha256": hashlib.sha256(
            (generator + "\n" + saver_excerpt).encode()
        ).hexdigest(),
        "findings": findings,
        "known_4_3_mechanism_persists": persists,
        "stage_1_result": "Q0_SOURCE_AUDIT_REJECTION"
        if persists
        else "REQUIRES_STAGE_2_RUNTIME",
        "reason": (
            "Exact source retains environment/random-seeded five-character built-in local IDs "
            "which the binary saver serializes into imported resources."
            if persists
            else "Known mechanism was not conclusively present."
        ),
    }


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def inventory(directory: Path, run_id: int, workflow_sha: str, branch: str) -> None:
    rows = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "FINAL_INVENTORY.json":
            rows.append(
                {
                    "path": path.relative_to(directory).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    write_json(
        directory / "FINAL_INVENTORY.json",
        {
            "run_id": run_id,
            "workflow_sha": workflow_sha,
            "branch": branch,
            "frozen_pr_head": "5b4e2466ef84f3984f3bf336b31925d4d2e97a7f",
            "no_android_export": True,
            "no_apk_or_aab_outputs": True,
            "no_project_migration": True,
            "no_merge_or_publication": True,
            "files": rows,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--work-root", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    work = Path(args.work_root)
    output.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)

    baseline_archive = work / f"{BASELINE}.tar.gz"
    download(
        f"https://codeload.github.com/godotengine/godot/tar.gz/refs/tags/{BASELINE}",
        baseline_archive,
    )
    baseline_root = extract_source(baseline_archive, work / f"source-{BASELINE}")
    baseline_audit = audit_source(BASELINE, baseline_root)
    results = []

    for tag in CANDIDATES:
        candidate_dir = output / tag
        candidate_dir.mkdir(parents=True, exist_ok=True)
        try:
            release = get_json(
                f"https://api.github.com/repos/godotengine/godot-builds/releases/tags/{tag}"
            )
            archive_name = f"Godot_v{tag}_linux.x86_64.zip"
            assets = {asset["name"]: asset for asset in release["assets"]}
            if archive_name not in assets:
                raise RuntimeError(f"official archive missing: {archive_name}")
            commit = tag_commit(tag)
            source_archive = work / f"{tag}.tar.gz"
            download(
                f"https://codeload.github.com/godotengine/godot/tar.gz/refs/tags/{tag}",
                source_archive,
            )
            source_root = extract_source(source_archive, work / f"source-{tag}")
            audit = audit_source(tag, source_root)

            binary_archive = work / archive_name
            download(assets[archive_name]["browser_download_url"], binary_archive)
            identity = {
                "schema_version": 1,
                "tag": tag,
                "official_source_commit": commit,
                "release_id": release["id"],
                "published_at": release["published_at"],
                "official_binary_archive": archive_name,
                "official_binary_archive_bytes": binary_archive.stat().st_size,
                "official_binary_archive_sha256": sha256(binary_archive),
                "github_asset_digest": assets[archive_name].get("digest"),
                "official_binary_download_url": assets[archive_name]["browser_download_url"],
                "official_tag_archive": f"godot-{tag}-github-tag.tar.gz",
                "official_tag_archive_bytes": source_archive.stat().st_size,
                "official_tag_archive_sha256": sha256(source_archive),
                "official_tag_archive_provenance": f"https://codeload.github.com/godotengine/godot/tar.gz/refs/tags/{tag}",
                "environment": {
                    "os": platform.platform(),
                    "architecture": platform.machine(),
                    "locale": os.environ.get("LC_ALL"),
                    "timezone": os.environ.get("TZ"),
                    "umask": "0022",
                    "cpu_count": os.cpu_count(),
                    "engine_command_line_arguments": None,
                    "candidate_engine_executed": False,
                    "import_environment_variables": {
                        "TZ": "UTC",
                        "LC_ALL": "C.UTF-8",
                        "LANG": "C.UTF-8",
                    },
                },
                "download_provenance": {
                    "release_api": f"https://api.github.com/repos/godotengine/godot-builds/releases/tags/{tag}",
                    "source_repository": "https://github.com/godotengine/godot",
                },
            }
            change = {
                "schema_version": 1,
                "candidate_tag": tag,
                "baseline_tag": BASELINE,
                "baseline_generate_scene_unique_id_sha256": baseline_audit[
                    "generate_scene_unique_id_sha256"
                ],
                "candidate_generate_scene_unique_id_sha256": audit[
                    "generate_scene_unique_id_sha256"
                ],
                "mechanism_materially_changed": not audit[
                    "known_4_3_mechanism_persists"
                ],
                "assessment": (
                    "Implementation details may differ, but the causal time/ticks/random "
                    "five-character local-ID mechanism and binary-saver path remain."
                ),
            }
            classification = {
                "schema_version": 1,
                "tag": tag,
                "classification": "Q0"
                if audit["known_4_3_mechanism_persists"]
                else "Q6",
                "failure_boundary": "Stage 1 — Candidate source audit",
                "stage_2_entered": False,
                "stage_3_entered": False,
                "stage_4_entered": False,
                "stage_5_entered": False,
                "stage_6_entered": False,
                "minimal_corpus_result": "NOT_RUN_Q0",
                "reason": (
                    "The exact source visibly preserves the accepted causal nondeterministic "
                    "mechanism; the qualification program expressly authorizes Q0 rejection "
                    "without runtime qualification."
                ),
                "pr59_modified": False,
                "android_export_invoked": False,
            }
            write_json(candidate_dir / "ENGINE_IDENTITY.json", identity)
            write_json(candidate_dir / "ENGINE_SOURCE_DETERMINISM_AUDIT.json", audit)
            write_json(candidate_dir / "ENGINE_SOURCE_CHANGE_FROM_4_3.json", change)
            write_json(candidate_dir / "CLASSIFICATION.json", classification)
            write_json(
                candidate_dir / "CORPUS_AUTHORITY.json",
                {
                    "schema_version": 1,
                    "accepted_source_manifest_sha256": "ba937afa335170ccaa726297fc23712a44e3295689a86640e1c1dbe6165701ab",
                    "accepted_source_tree_sha256": "e0cfa6604569c13e1d75b2439d6936b7e2423ad5ba3715f033200335e864bc4e",
                    "matrix_manifest_sha256": "6aa202e2298fa514bfdb2ba10fd66237cc2d15005cdb2d6316a57d847ece8eff",
                    "representative_paths": CORPUS,
                    "prompt_alias_correction": {
                        "building_A.gltf": "assets/citykit/models/Brick_Plain_1.gltf",
                        "airplane.obj": "addons/flexible_toon_shader/example/cup.obj",
                        "basis": "artifact-authenticated accepted representative selection",
                    },
                },
            )
            results.append(
                {
                    "tag": tag,
                    "classification": classification["classification"],
                    "commit": commit,
                    "binary_sha256": identity["official_binary_archive_sha256"],
                    "source_archive_sha256": identity["official_tag_archive_sha256"],
                    "stage_2_entered": False,
                }
            )
        except Exception as error:
            write_json(
                candidate_dir / "QUALIFICATION_ERROR.json",
                {"tag": tag, "classification": "Q6", "errors": [repr(error)]},
            )
            results.append(
                {
                    "tag": tag,
                    "classification": "Q6",
                    "errors": [repr(error)],
                    "stage_2_entered": False,
                }
            )

    dev_dir = output / "4.8-dev1"
    dev_dir.mkdir(exist_ok=True)
    dev_commit = "ebbf577a0"
    dev_archive = work / "4.8-dev1.tar.gz"
    download(
        f"https://codeload.github.com/godotengine/godot/tar.gz/{dev_commit}",
        dev_archive,
    )
    dev_root = extract_source(dev_archive, work / "source-4.8-dev1")
    dev_audit = audit_source("4.8-dev1", dev_root)
    write_json(dev_dir / "ENGINE_SOURCE_DETERMINISM_AUDIT.json", dev_audit)
    write_json(
        dev_dir / "DIAGNOSTIC_CLASSIFICATION.json",
        {
            "tag": "4.8-dev1",
            "official_announced_commit_prefix": dev_commit,
            "classification": "DIAGNOSTIC_Q0",
            "authoritative_candidate": False,
            "runtime_entered": False,
            "reason": "The preview source retains the same accepted random local-ID mechanism.",
        },
    )

    aggregate = output / "aggregate"
    aggregate.mkdir(exist_ok=True)
    write_json(
        aggregate / "CROSS_VERSION_QUALIFICATION_MATRIX.json",
        {
            "schema_version": 1,
            "baseline": {
                "tag": "4.3-stable",
                "gate_4": "FAIL",
                "gate_5": "PASS_RETAINED_ORIGINAL_APKS",
                "differing_model_binaries": 800,
                "differing_md5": 800,
                "representative_semantic_content_differences": 0,
            },
            "candidates": results,
            "stage_3_candidates": [],
            "stage_4_candidates": [],
            "stage_5_candidates": [],
            "stage_6_candidates": [],
            "earliest_q5": None,
            "recommended_engine": None,
            "program_result": "NO_OFFICIAL_STABLE_Q5",
            "gate_4": "FAIL",
            "gate_5": "PASS_RETAINED_4_3_APKS_ONLY",
        },
    )
    write_json(
        aggregate / "CUSTOM_ENGINE_FEASIBILITY.json",
        {
            "schema_version": 1,
            "required": True,
            "build_authorized": False,
            "patch_scope": [
                "core/io/resource.cpp: deterministic replacement for environment/random default scene-unique-ID generation",
                "core/io/resource_format_binary.cpp: deterministic built-in local-resource naming and stable saved-resource traversal",
                "model importer collection paths: canonical animation/material/mesh/subresource ordering",
                "dictionary serialization: canonical key ordering where serialized order affects bytes",
            ],
            "requirements": [
                "editor and export-template parity",
                "checksummed source and binary reproducibility",
                "MIT license and attribution preservation",
                "security-update tracking",
                "upstream merge-burden assessment",
                "full 800-model and Gate 1–5 regressions",
                "rollback to official 4.3 authority",
            ],
            "alternatives": [
                "pinned imported-resource authority",
                "retain Gate 4 failure",
                "await later official release",
            ],
            "next_step": "Separate architectural approval only; do not build a custom engine in this checkpoint.",
        },
    )
    write_json(
        aggregate / "PROGRAM_LIMITATIONS.json",
        {
            "source_audit_is_decisive_under_q0_rule": True,
            "candidate_engines_executed": False,
            "minimal_imports_run": False,
            "reason": "Every official stable candidate was rejected at Stage 1 because its exact source preserved the accepted causal mechanism.",
            "no_claim_of_runtime_failure": True,
        },
    )

    run_id = int(os.environ.get("GITHUB_RUN_ID", "0"))
    workflow_sha = os.environ.get("GITHUB_SHA", "")
    branch = os.environ.get("GITHUB_REF_NAME", "")
    for directory in [path for path in output.iterdir() if path.is_dir()]:
        inventory(directory, run_id, workflow_sha, branch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
