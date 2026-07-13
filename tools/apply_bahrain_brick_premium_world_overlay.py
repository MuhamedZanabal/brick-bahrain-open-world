#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import zipfile
from pathlib import Path

EXPECTED_SOURCE_SHA256 = "5c4d8ac4497eda7752058424062a74a97c1f6f5e0c9a1ff393abac2a2c7c828a"
EXPECTED_PAYLOAD_SHA256 = "6f5f13df926a7813f7b6d9720147f592b7870d8bf078c11e7797f541b1f29351"
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
PAYLOAD_CHUNKS = [
    "part01.b64",
    "part02.b64",
    "part03.b64",
    "part04.b64",
    "part05_07.b64",
    "part08.b64",
    "part09.b64",
    "part10.b64",
    "part11_13.b64",
]
EVIDENCE_ONLY = {
    "tests/premium_world_visual_evidence.gd",
    "scenes/premium_world_visual_evidence.tscn",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_payload() -> bytes:
    payload_dir = Path(__file__).resolve().parent / "premium_payload_v2"
    chunks = [payload_dir / name for name in PAYLOAD_CHUNKS]
    missing = [path.name for path in chunks if not path.is_file()]
    if missing:
        raise SystemExit(f"premium payload chunks missing: {missing}")
    encoded = "".join(chunk.read_text(encoding="utf-8").strip() for chunk in chunks)
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise SystemExit(f"premium payload base64 validation failed: {exc}") from exc
    digest = sha256_bytes(decoded)
    if digest != EXPECTED_PAYLOAD_SHA256:
        raise SystemExit(
            f"premium payload SHA-256 mismatch: expected {EXPECTED_PAYLOAD_SHA256}, got {digest}"
        )
    return decoded


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--evidence-only", action="store_true")
    args = parser.parse_args()

    project = args.project_root.resolve()
    if not (project / "project.godot").is_file():
        raise SystemExit("project.godot missing")

    before = {relative: sha256_file(project / relative) for relative in FROZEN}
    changed: list[str] = []
    payload_bytes = load_payload()

    try:
        archive = zipfile.ZipFile(io.BytesIO(payload_bytes))
        bad_entry = archive.testzip()
    except zipfile.BadZipFile as exc:
        raise SystemExit(f"premium payload ZIP validation failed: {exc}") from exc
    if bad_entry:
        raise SystemExit(f"premium payload ZIP CRC failed: {bad_entry}")

    with archive:
        for relative in sorted(archive.namelist()):
            if args.evidence_only and relative not in EVIDENCE_ONLY:
                continue
            target = project / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(relative))
            changed.append(relative)

    after = {relative: sha256_file(project / relative) for relative in FROZEN}
    mismatches = [relative for relative in FROZEN if before[relative] != after[relative]]
    if mismatches:
        raise SystemExit(f"frozen controls modified: {mismatches}")

    report = {
        "evidence_class": "VERIFIED",
        "classification": "premium world overlay on historical v1.4 fallback; not v15 authority",
        "base_integrated_source_sha256": EXPECTED_SOURCE_SHA256,
        "payload_sha256": EXPECTED_PAYLOAD_SHA256,
        "payload_chunks": PAYLOAD_CHUNKS,
        "evidence_only": args.evidence_only,
        "overlay_files": changed,
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
