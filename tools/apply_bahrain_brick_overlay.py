#!/usr/bin/env python3
"""Apply the Bahrain Brick controls/branding overlay to reconstructed v1.4 source."""
from __future__ import annotations

import argparse
import base64
import io
import json
import re
import shutil
import tarfile
from pathlib import Path


def replace_line(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"(?m)^{re.escape(key)}=.*$")
    text, count = pattern.subn(f"{key}={value}", text)
    if count != 1:
        raise RuntimeError(f"{key}: expected one replacement, found {count}")
    return text


def read_payload() -> bytes:
    parts_dir = Path(__file__).resolve().parent / "overlay_payload_parts"
    parts = sorted(parts_dir.glob("part-*.b64"))
    if len(parts) != 6:
        raise RuntimeError(f"expected 6 overlay payload parts, found {len(parts)}")
    encoded = "".join(part.read_text(encoding="utf-8").strip() for part in parts)
    return base64.b64decode(encoded, validate=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    overlay = root / "build" / "embedded_bahrain_brick_overlay"
    if overlay.exists():
        shutil.rmtree(overlay)
    overlay.mkdir(parents=True, exist_ok=True)
    raw = read_payload()
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        for member in archive.getmembers():
            target = (overlay / member.name).resolve()
            if target != overlay and overlay not in target.parents:
                raise RuntimeError(f"unsafe overlay member: {member.name}")
        archive.extractall(overlay, filter="data")
    changed: list[str] = []
    for source in sorted(path for path in overlay.rglob("*") if path.is_file()):
        relative = source.relative_to(overlay)
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        changed.append(relative.as_posix())

    project_path = root / "project.godot"
    project = project_path.read_text(encoding="utf-8")
    project = replace_line(project, "config/name", '"Bahrain Brick"')
    project = replace_line(
        project,
        "config/description",
        '"A stylized open-world brick adventure inspired by Bahrain."',
    )
    project = replace_line(project, "driver/enable_input", "false")
    project_path.write_text(project, encoding="utf-8")
    changed.append("project.godot")

    preset_path = root / "export_presets.cfg"
    preset = preset_path.read_text(encoding="utf-8")
    replacements = {
        "version/code": "1402",
        "version/name": '"1.4.0.2-controls-qa"',
        "package/unique_name": '"com.bahrainbrick.game.qa"',
        "package/name": '"Bahrain Brick"',
        "permissions/record_audio": "false",
    }
    for key, value in replacements.items():
        preset = replace_line(preset, key, value)
    preset_path.write_text(preset, encoding="utf-8")
    changed.append("export_presets.cfg")

    report = {
        "classification": "historical v1.4 fallback overlay; not v15 authority",
        "game_title": "Bahrain Brick",
        "package": "com.bahrainbrick.game.qa",
        "version_code": 1402,
        "version_name": "1.4.0.2-controls-qa",
        "changed_files": sorted(set(changed)),
        "movement_fix": {
            "joystick": "viewport-level touch-index capture",
            "camera": "dedicated right-side touch drag router",
            "hud_input": "full-screen root ignores unrelated touch",
            "control_modes": "walking and vehicle layers are mutually exclusive",
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
