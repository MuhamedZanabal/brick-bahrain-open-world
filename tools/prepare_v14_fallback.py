#!/usr/bin/env python3
"""Prepare the checksum-locked historical v1.4 fallback source for QA.

This script reconstructs the exact v1.4 delta, applies only the parser corrections
already proven by historical Godot 4.3 import, assigns an isolated QA package/version,
forces landscape orientation, configures runtime-only debug signing, and generates a
project-loaded smoke scene so project autoloads are available.

It does not claim or create v15 authority.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import re
import tarfile
from pathlib import Path

DELTA_SHA256 = "7d1f637c83f32824dadf9d5b3a675184507707d3ddc2f557036d7afad1ac45a7"
BASE_COMMIT = "08378d1383eb7aeb1ae91b9eeb8994b79a96f1de"
DELTA_BRANCH_HEAD = "721e8c9df6cb8a4e142c18723a7fc72c27350159"

PARSER_PATCHES: dict[str, list[tuple[str, str, int]]] = {
    "tests/runtime_smoke_test_v14.gd": [
        (
            "var candidate := SaveManager.save_path + suffix",
            "var candidate: String = SaveManager.save_path + str(suffix)",
            2,
        ),
    ],
    "scripts/hero_district_builder.gd": [
        (
            "var outward := side * float(level) * 0.18",
            "var outward: float = float(side) * float(level) * 0.18",
            1,
        ),
        (
            "var label_data := storefront_names[shop_index % storefront_names.size()]",
            "var label_data: Array = storefront_names[shop_index % storefront_names.size()]",
            1,
        ),
        ("var z := z_slots[index]", "var z: float = float(z_slots[index])", 1),
        (
            "var x := side * (24.0 + float(index % 2) * 2.5)",
            "var x: float = float(side) * (24.0 + float(index % 2) * 2.5)",
            1,
        ),
    ],
    "scripts/hud.gd": [
        (
            'var in_vehicle := player.has_method("is_in_vehicle") and bool(player.call("is_in_vehicle"))',
            'var in_vehicle: bool = player.has_method("is_in_vehicle") and bool(player.call("is_in_vehicle"))',
            1,
        ),
    ],
    "scripts/phone_ui.gd": [
        (
            'var location := district.call("get_location_name", position) if district and district.has_method("get_location_name") else "Central Manama"',
            'var location: String = str(district.call("get_location_name", position)) if district and district.has_method("get_location_name") else "Central Manama"',
            1,
        ),
    ],
    "scripts/traffic_manager.gd": [
        (
            "var archetype := ARCHETYPES[index % ARCHETYPES.size()]",
            "var archetype: String = str(ARCHETYPES[index % ARCHETYPES.size()])",
            1,
        ),
    ],
    "scripts/wanted_level.gd": [
        (
            "var police := police_npcs.pop_back()",
            "var police: Node3D = police_npcs.pop_back() as Node3D",
            1,
        ),
    ],
}


def replace_exact(text: str, old: str, new: str, expected: int, label: str) -> str:
    actual = text.count(old)
    if actual != expected:
        raise RuntimeError(f"{label}: expected {expected} occurrence(s), found {actual}")
    return text.replace(old, new)


def reconstruct(root: Path) -> dict[str, object]:
    parts = sorted(root.glob("ci/v14_delta.b64.*"))
    if len(parts) != 17:
        raise RuntimeError(f"expected 17 delta chunks, found {len(parts)}")
    encoded = b"".join(path.read_bytes() for path in parts)
    raw = base64.b64decode(encoded, validate=True)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != DELTA_SHA256:
        raise RuntimeError(f"delta checksum mismatch: expected {DELTA_SHA256}, got {digest}")

    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:xz") as archive:
        members = archive.getmembers()
        for member in members:
            target = (root / member.name).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(f"unsafe archive member: {member.name}")
        archive.extractall(root, filter="data")

    return {
        "delta_parts": len(parts),
        "delta_base64_bytes": len(encoded),
        "delta_bytes": len(raw),
        "delta_sha256": digest,
        "delta_members": len(members),
    }


def apply_parser_fixes(root: Path) -> list[str]:
    changed: list[str] = []
    for filename, replacements in PARSER_PATCHES.items():
        path = root / filename
        text = path.read_text(encoding="utf-8")
        for old, new, expected in replacements:
            text = replace_exact(text, old, new, expected, filename)
        path.write_text(text, encoding="utf-8")
        changed.append(filename)
    return sorted(changed)


def configure_qa(root: Path) -> None:
    project_path = root / "project.godot"
    project = project_path.read_text(encoding="utf-8")
    project, count = re.subn(
        r"(?m)^window/handheld/orientation=.*$",
        "window/handheld/orientation=4",
        project,
    )
    if count != 1:
        raise RuntimeError(f"project orientation replacements={count}")
    project_path.write_text(project, encoding="utf-8")

    preset_path = root / "export_presets.cfg"
    preset = preset_path.read_text(encoding="utf-8")
    replacements = {
        "version/code": "1401",
        "version/name": '"1.4.0.1-fallback-qa"',
        "package/unique_name": '"com.brickbahrain.openworld.fallbackqa"',
        "package/name": '"Brick Bahrain Fallback QA"',
        "keystore/debug": '"res://build/ci/debug.keystore"',
        "keystore/debug_password": '"android"',
        "keystore/debug_user": '"androiddebugkey"',
        "keystore/release": '""',
        "keystore/release_password": '""',
        "keystore/release_user": '""',
    }
    for key, value in replacements.items():
        preset, count = re.subn(rf"(?m)^{re.escape(key)}=.*$", f"{key}={value}", preset)
        if count != 1:
            raise RuntimeError(f"{key}: replacements={count}")
    preset_path.write_text(preset, encoding="utf-8")


def generate_project_loaded_runner(root: Path) -> list[str]:
    source = (root / "tests/runtime_smoke_test_v14.gd").read_text(encoding="utf-8")
    replacements = [
        ("extends SceneTree", "extends Node", 1),
        ("func _initialize() -> void:", "func _ready() -> void:", 1),
        ("await process_frame", "await get_tree().process_frame", 2),
        ("root.add_child(world)", "get_tree().root.add_child(world)", 1),
        ("\tquit(1 if _failed > 0 else 0)", "\tget_tree().quit(1 if _failed > 0 else 0)", 1),
    ]
    for old, new, expected in replacements:
        source = replace_exact(source, old, new, expected, f"runner transform {old!r}")

    build_ci = root / "build/ci"
    build_ci.mkdir(parents=True, exist_ok=True)
    runner_script = build_ci / "runtime_smoke_runner_v14.gd"
    runner_scene = build_ci / "runtime_smoke_runner_v14.tscn"
    runner_script.write_text(source, encoding="utf-8")
    runner_scene.write_text(
        '[gd_scene load_steps=2 format=3]\n\n'
        '[ext_resource type="Script" path="res://build/ci/runtime_smoke_runner_v14.gd" id="1"]\n\n'
        '[node name="RuntimeSmokeRunner" type="Node"]\n'
        'script = ExtResource("1")\n',
        encoding="utf-8",
    )
    return [runner_script.relative_to(root).as_posix(), runner_scene.relative_to(root).as_posix()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--provenance-out", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        raise SystemExit(f"source root is not a directory: {root}")

    reconstruction = reconstruct(root)
    parser_files = apply_parser_fixes(root)
    configure_qa(root)
    runner_files = generate_project_loaded_runner(root)

    provenance = {
        "evidence_class": "VERIFIED",
        "classification": "historical v1.4 landscape fallback QA; not v15 authority",
        "base_commit": BASE_COMMIT,
        "delta_branch": "v14-phone-apk",
        "delta_branch_head": DELTA_BRANCH_HEAD,
        **reconstruction,
        "parser_fix_files": parser_files,
        "generated_runner_files": runner_files,
        "qa_package": "com.brickbahrain.openworld.fallbackqa",
        "qa_version_code": 1401,
        "qa_version_name": "1.4.0.1-fallback-qa",
        "qa_orientation_project_value": 4,
        "authority_warning": "must not replace v15.0.1 authority",
    }
    args.provenance_out.parent.mkdir(parents=True, exist_ok=True)
    args.provenance_out.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(provenance, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
