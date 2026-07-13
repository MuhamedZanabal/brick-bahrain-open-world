#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import gzip
import io
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

EXPECTED_SOURCE_SHA256 = "5c4d8ac4497eda7752058424062a74a97c1f6f5e0c9a1ff393abac2a2c7c828a"
EXPECTED_V2_PAYLOAD_SHA256 = "6f5f13df926a7813f7b6d9720147f592b7870d8bf078c11e7797f541b1f29351"
EXPECTED_V3_PATCH_SHA256 = "37197fcb47242638207e050e25ce77b761d223344f2c64ddec4edfcacd5f5640"
EXPECTED_V3_MANIFEST_SHA256 = "f7ce0c40ca9399c383b1986efc94add5feb7db32f7c895f79212879a3a9e9c05"
FROZEN = [
    "scripts/virtual_joystick.gd",
    "scripts/touch_input.gd",
    "scripts/player_controller.gd",
    "scripts/hud.gd",
    "tests/mobile_input_pipeline_test.gd",
    "scenes/mobile_input_pipeline_test.tscn",
    "tests/mobile_input_visual_evidence.gd",
    "scenes/mobile_input_visual_evidence.tscn",
]
V2_PAYLOAD_CHUNKS = [
    "part01.b64", "part02.b64", "part03.b64", "part04.b64", "part05_07.b64",
    "part08.b64", "part09.b64", "part10.b64", "part11_13.b64",
]
V3_PATCH_B64_CHUNKS = ["patch_gzip_b64_00.txt"] + [f"patch_gzip_b64_{i:02d}.txt" for i in range(7, 42)]
EXPECTED_V3_PATCH_GZIP_SHA256 = "1a4fa681fb2e03c395f4d9455711a1c5c2a0e48d2fa64079804d5645323edc85"
POST_EXTRACT_REPLACEMENTS = {
    "scripts/hero_district_builder.gd": [
        (
            '\t\tvar material := _materials["curb_red"] if index % 2 == 0 else _materials["curb_white"]',
            '\t\tvar material: Material = _materials["curb_red"] if index % 2 == 0 else _materials["curb_white"]',
        ),
    ],
}
EVIDENCE_ONLY = {
    "tests/premium_world_visual_evidence.gd",
    "scenes/premium_world_visual_evidence.tscn",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_v2_payload(tools: Path) -> bytes:
    payload_dir = tools / "premium_payload_v2"
    chunks = [payload_dir / name for name in V2_PAYLOAD_CHUNKS]
    missing = [path.name for path in chunks if not path.is_file()]
    if missing:
        raise SystemExit(f"premium v2 payload chunks missing: {missing}")
    encoded = "".join(chunk.read_text(encoding="utf-8").strip() for chunk in chunks)
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise SystemExit(f"premium v2 payload base64 validation failed: {exc}") from exc
    digest = sha256_bytes(decoded)
    if digest != EXPECTED_V2_PAYLOAD_SHA256:
        raise SystemExit(
            "premium v2 payload SHA-256 mismatch: "
            f"expected {EXPECTED_V2_PAYLOAD_SHA256}, got {digest}"
        )
    return decoded


def load_v3_patch_and_manifest(tools: Path) -> tuple[bytes, dict[str, str]]:
    patch_dir = tools / "premium_visual_upgrade_v3"
    chunks = [patch_dir / name for name in V3_PATCH_B64_CHUNKS]
    missing = [path.name for path in chunks if not path.is_file()]
    if missing:
        raise SystemExit(f"premium v3 patch chunks missing: {missing}")
    encoded = "".join(path.read_text(encoding="utf-8").strip() for path in chunks)
    try:
        compressed = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise SystemExit(f"premium v3 patch base64 validation failed: {exc}") from exc
    compressed_digest = sha256_bytes(compressed)
    if compressed_digest != EXPECTED_V3_PATCH_GZIP_SHA256:
        raise SystemExit(
            "premium v3 patch gzip SHA-256 mismatch: "
            f"expected {EXPECTED_V3_PATCH_GZIP_SHA256}, got {compressed_digest}"
        )
    try:
        patch = gzip.decompress(compressed)
    except OSError as exc:
        raise SystemExit(f"premium v3 patch gzip validation failed: {exc}") from exc
    patch_digest = sha256_bytes(patch)
    if patch_digest != EXPECTED_V3_PATCH_SHA256:
        raise SystemExit(
            "premium v3 patch SHA-256 mismatch: "
            f"expected {EXPECTED_V3_PATCH_SHA256}, got {patch_digest}"
        )
    manifest_path = patch_dir / "premium_visual_upgrade_v3_manifest.json"
    if not manifest_path.is_file():
        raise SystemExit("premium v3 manifest missing")
    manifest_digest = sha256_file(manifest_path)
    if manifest_digest != EXPECTED_V3_MANIFEST_SHA256:
        raise SystemExit(
            "premium v3 manifest SHA-256 mismatch: "
            f"expected {EXPECTED_V3_MANIFEST_SHA256}, got {manifest_digest}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("files")
    if not isinstance(files, dict) or manifest.get("file_count") != len(files):
        raise SystemExit("premium v3 manifest structure invalid")
    return patch, files


def apply_v2_overlay(project: Path, payload: bytes, evidence_only: bool) -> list[str]:
    changed: list[str] = []
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
        bad_entry = archive.testzip()
    except zipfile.BadZipFile as exc:
        raise SystemExit(f"premium v2 ZIP validation failed: {exc}") from exc
    if bad_entry:
        raise SystemExit(f"premium v2 ZIP CRC failed: {bad_entry}")
    with archive:
        for relative in sorted(archive.namelist()):
            if relative.endswith("/"):
                continue
            if evidence_only and relative not in EVIDENCE_ONLY:
                continue
            target = project / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(relative))
            changed.append(relative)
    if not evidence_only:
        for relative, replacements in POST_EXTRACT_REPLACEMENTS.items():
            target = project / relative
            text = target.read_text(encoding="utf-8")
            for old, new in replacements:
                count = text.count(old)
                if count != 1:
                    raise SystemExit(
                        f"post-extract replacement count mismatch for {relative}: {count}"
                    )
                text = text.replace(old, new)
            target.write_text(text, encoding="utf-8")
    return changed


def _v3_new_file_paths(patch: bytes) -> list[str]:
    try:
        text = patch.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SystemExit(f"premium v3 patch UTF-8 validation failed: {exc}") from exc
    current: str | None = None
    new_files: list[str] = []
    for line in text.splitlines():
        if line.startswith("diff --git a/") and " b/" in line:
            current = line.split(" b/", 1)[0][len("diff --git a/"):]
        elif line.startswith("new file mode "):
            if not current:
                raise SystemExit("premium v3 patch new-file header missing path")
            new_files.append(current)
    return new_files


def apply_v3_patch(project: Path, patch: bytes, expected_files: dict[str, str]) -> list[str]:
    collisions: list[str] = []
    for relative in _v3_new_file_paths(patch):
        if relative not in expected_files:
            raise SystemExit(f"premium v3 new file absent from manifest: {relative}")
        target = project / relative
        if target.exists():
            if not target.is_file():
                raise SystemExit(f"premium v3 new-file collision is not a file: {relative}")
            target.unlink()
            collisions.append(relative)
    if collisions:
        print(json.dumps({"replaced_v2_runtime_assets": collisions}, indent=2))

    with tempfile.NamedTemporaryFile(prefix="bahrain-brick-v3-", suffix=".patch") as handle:
        handle.write(patch)
        handle.flush()
        subprocess.run(
            ["git", "apply", "--check", "--unsafe-paths", handle.name],
            cwd=project,
            check=True,
        )
        subprocess.run(
            ["git", "apply", "--unsafe-paths", "--whitespace=nowarn", handle.name],
            cwd=project,
            check=True,
        )
    for relative, expected_digest in sorted(expected_files.items()):
        target = project / relative
        if not target.is_file():
            raise SystemExit(f"premium v3 output missing: {relative}")
        actual_digest = sha256_file(target)
        if actual_digest != expected_digest:
            raise SystemExit(
                f"premium v3 output hash mismatch for {relative}: "
                f"expected {expected_digest}, got {actual_digest}"
            )
    return sorted(expected_files)


def _replace_expected(
    text: str, old: str, new: str, label: str, expected_count: int = 1
) -> str:
    count = text.count(old)
    if count != expected_count:
        raise SystemExit(
            f"{label} replacement mismatch: expected {expected_count}, found {count}"
        )
    return text.replace(old, new)


def prepare_release_smoke_harness(project: Path) -> list[str]:
    source = project / "tests/runtime_smoke_test_v14.gd"
    if not source.is_file():
        raise SystemExit(f"release smoke source missing: {source}")
    text = source.read_text(encoding="utf-8")
    text = _replace_expected(text, "extends SceneTree", "extends Node", "smoke base type")
    text = _replace_expected(
        text, "func _initialize() -> void:", "func _ready() -> void:", "smoke entry point"
    )
    text = _replace_expected(
        text,
        "\t\tawait process_frame",
        "\t\tawait get_tree().process_frame",
        "smoke frame wait",
        expected_count=2,
    )
    text = _replace_expected(
        text, "\troot.add_child(world)", "\tget_tree().root.add_child(world)", "smoke world parent"
    )
    text = _replace_expected(
        text,
        "\tquit(1 if _failed > 0 else 0)",
        "\tget_tree().quit(1 if _failed > 0 else 0)",
        "smoke exit",
    )
    harness_dir = project / "build/ci"
    harness_dir.mkdir(parents=True, exist_ok=True)
    script_path = harness_dir / "runtime_smoke_runner_v14.gd"
    scene_path = harness_dir / "runtime_smoke_runner_v14.tscn"
    script_path.write_text(text, encoding="utf-8")
    scene_path.write_text(
        '[gd_scene load_steps=2 format=3]\n\n'
        '[ext_resource type="Script" path="res://build/ci/runtime_smoke_runner_v14.gd" id="1_smoke"]\n\n'
        '[node name="RuntimeSmokeRunnerV14" type="Node"]\n'
        'script = ExtResource("1_smoke")\n',
        encoding="utf-8",
    )
    return [
        script_path.relative_to(project).as_posix(),
        scene_path.relative_to(project).as_posix(),
    ]


def _ensure_svg_renderer() -> str:
    renderer = shutil.which("rsvg-convert")
    if renderer:
        return renderer
    if os.geteuid() != 0:
        raise SystemExit("rsvg-convert missing and runner lacks permission to install librsvg2-bin")
    subprocess.run(["apt-get", "update"], check=True)
    subprocess.run(
        ["apt-get", "install", "-y", "--no-install-recommends", "librsvg2-bin"],
        check=True,
    )
    renderer = shutil.which("rsvg-convert")
    if not renderer:
        raise SystemExit("librsvg2-bin installation completed but rsvg-convert is still unavailable")
    return renderer


def render_svg(source: Path, target: Path, width: int, height: int | None = None) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [_ensure_svg_renderer(), "-w", str(width)]
    if height is not None:
        command += ["-h", str(height)]
    command += ["-o", str(target), str(source)]
    subprocess.run(command, check=True)
    if not target.is_file() or target.stat().st_size == 0:
        raise SystemExit(f"failed to render {target}")


def generate_binary_artwork(project: Path) -> list[str]:
    generated: list[str] = []
    emblem = project / "assets/brand/bahrain_brick_emblem.svg"
    targets = [
        (project / "assets/brand/bahrain_brick_app_icon_1024.png", 1024, 1024),
        (project / "assets/icons/icon_main_192.png", 192, 192),
        (project / "assets/icons/icon_adaptive_fg_432.png", 432, 432),
    ]
    for target, width, height in targets:
        render_svg(emblem, target, width, height)
        generated.append(target.relative_to(project).as_posix())

    from PIL import Image

    background = project / "assets/icons/icon_adaptive_bg_432.png"
    background.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (432, 432), (10, 20, 34)).save(background, optimize=True)
    generated.append(background.relative_to(project).as_posix())

    high_res = project / "artwork/source/high_resolution_png"
    for source in sorted((project / "artwork/source").glob("*_master.svg")):
        target = high_res / f"{source.stem}.png"
        render_svg(source, target, 3840, 2160)
        generated.append(target.relative_to(project).as_posix())

    logo_out = project / "artwork/source/logo_package_png"
    for source in sorted((project / "assets/brand").glob("*.svg")):
        target = logo_out / f"{source.stem}_2048.png"
        render_svg(source, target, 2048)
        generated.append(target.relative_to(project).as_posix())
    return generated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--evidence-only", action="store_true")
    args = parser.parse_args()

    project = args.project_root.resolve()
    if not (project / "project.godot").is_file():
        raise SystemExit("project.godot missing")
    tools = Path(__file__).resolve().parent
    before = {relative: sha256_file(project / relative) for relative in FROZEN}

    v2_payload = load_v2_payload(tools)
    changed = apply_v2_overlay(project, v2_payload, args.evidence_only)
    v3_files: list[str] = []
    generated: list[str] = []
    if not args.evidence_only:
        v3_patch, v3_manifest = load_v3_patch_and_manifest(tools)
        v3_files = apply_v3_patch(project, v3_patch, v3_manifest)
        generated = generate_binary_artwork(project)
        generated += prepare_release_smoke_harness(project)
        changed = sorted(set(changed + v3_files + generated))

    after = {relative: sha256_file(project / relative) for relative in FROZEN}
    mismatches = [relative for relative in FROZEN if before[relative] != after[relative]]
    if mismatches:
        raise SystemExit(f"frozen controls modified: {mismatches}")

    report = {
        "evidence_class": "VERIFIED",
        "classification": (
            "premium world and presentation upgrade on historical v1.4 fallback; "
            "not v1.5 authority"
        ),
        "base_integrated_source_sha256": EXPECTED_SOURCE_SHA256,
        "v2_payload_sha256": EXPECTED_V2_PAYLOAD_SHA256,
        "v3_patch_sha256": EXPECTED_V3_PATCH_SHA256 if not args.evidence_only else None,
        "v3_patch_gzip_sha256": EXPECTED_V3_PATCH_GZIP_SHA256 if not args.evidence_only else None,
        "v3_manifest_sha256": EXPECTED_V3_MANIFEST_SHA256 if not args.evidence_only else None,
        "evidence_only": args.evidence_only,
        "overlay_files": changed,
        "v3_patched_files": v3_files,
        "generated_binary_artwork": generated,
        "frozen_controls_unchanged": True,
        "frozen_control_hashes": after,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
