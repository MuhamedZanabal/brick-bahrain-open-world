#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

GODOT_ORIENTATION_NAMES = {
    0: "landscape",
    1: "portrait",
    2: "reverseLandscape",
    3: "reversePortrait",
    4: "sensorLandscape",
    5: "sensorPortrait",
    6: "sensor",
}
PACKAGE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cfg_value(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(key)}=(.+)$", text)
    if not match:
        return None
    raw = match.group(1).strip()
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    return raw


def cfg_bool(text: str, key: str) -> bool | None:
    raw = cfg_value(text, key)
    if raw is None:
        return None
    if raw == "true":
        return True
    if raw == "false":
        return False
    raise ValueError(f"invalid boolean for {key}: {raw}")


def cfg_int(text: str, key: str) -> int | None:
    raw = cfg_value(text, key)
    if raw is None or raw == "":
        return None
    return int(raw)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def inspect(preset_path: Path, project_path: Path) -> dict[str, Any]:
    preset_text = preset_path.read_text(encoding="utf-8")
    project_text = project_path.read_text(encoding="utf-8")
    orientation_value = cfg_int(project_text, "window/handheld/orientation")
    if orientation_value is None:
        orientation_value = cfg_int(project_text, "orientation")
    renderer = cfg_value(project_text, "renderer/rendering_method.mobile") or cfg_value(
        project_text, "renderer/rendering_method"
    )
    architectures = {
        name: cfg_bool(preset_text, f"architectures/{name}")
        for name in ("armeabi-v7a", "arm64-v8a", "x86_64", "x86")
    }
    debug_keystore = cfg_value(preset_text, "keystore/debug")
    report: dict[str, Any] = {
        "preset_file": str(preset_path.resolve()),
        "preset_sha256": sha256_file(preset_path),
        "project_file": str(project_path.resolve()),
        "project_sha256": sha256_file(project_path),
        "preset_name": cfg_value(preset_text, "name"),
        "platform": cfg_value(preset_text, "platform"),
        "runnable": cfg_bool(preset_text, "runnable"),
        "export_filter": cfg_value(preset_text, "export_filter"),
        "export_path": cfg_value(preset_text, "export_path"),
        "package_id": cfg_value(preset_text, "package/unique_name"),
        "application_label": cfg_value(preset_text, "package/name"),
        "package_signed": cfg_bool(preset_text, "package/signed"),
        "version_name": cfg_value(preset_text, "version/name"),
        "version_code": cfg_int(preset_text, "version/code"),
        "min_sdk": cfg_value(preset_text, "gradle_build/min_sdk"),
        "target_sdk": cfg_value(preset_text, "gradle_build/target_sdk"),
        "sdk_resolution": "resolved from exported APK when preset leaves SDK fields unset",
        "architectures": architectures,
        "renderer": renderer,
        "orientation_value": orientation_value,
        "orientation": GODOT_ORIENTATION_NAMES.get(
            orientation_value, f"unknown:{orientation_value}" if orientation_value is not None else None
        ),
        "debuggable_export": True,
        "permissions": {
            "internet": cfg_bool(preset_text, "permissions/internet"),
            "access_network_state": cfg_bool(preset_text, "permissions/access_network_state"),
            "record_audio": cfg_bool(preset_text, "permissions/record_audio"),
            "custom_permissions": cfg_value(preset_text, "permissions/custom_permissions"),
        },
        "expansion_file_enabled": cfg_bool(preset_text, "apk_expansion/enable"),
        "use_gradle_build": cfg_bool(preset_text, "gradle_build/use_gradle_build"),
        "signing": {
            "debug_keystore": debug_keystore,
            "debug_alias": cfg_value(preset_text, "keystore/debug_user"),
            "release_keystore": cfg_value(preset_text, "keystore/release"),
            "authority": (
                "external QA/debug environment override" if not debug_keystore else "preset debug keystore path"
            ),
            "passwords_redacted": True,
        },
        "texture_compression": {
            "etc2_astc_import_enabled": cfg_value(
                project_text, "textures/vram_compression/import_etc2_astc"
            )
        },
    }
    failures: list[dict[str, Any]] = []
    required_equals = {
        "preset_name": "Android",
        "platform": "Android",
        "runnable": True,
        "package_signed": True,
        "use_gradle_build": False,
    }
    for field, expected in required_equals.items():
        if report[field] != expected:
            failures.append({"field": field, "expected": expected, "actual": report[field]})
    package_id = report["package_id"]
    if not isinstance(package_id, str) or not PACKAGE_RE.fullmatch(package_id):
        failures.append({"field": "package_id", "reason": "invalid or missing reverse-DNS package ID"})
    if not report["application_label"]:
        failures.append({"field": "application_label", "reason": "missing application label"})
    if not report["version_name"]:
        failures.append({"field": "version_name", "reason": "missing version name"})
    if not isinstance(report["version_code"], int) or report["version_code"] <= 0:
        failures.append({"field": "version_code", "reason": "version code must be positive"})
    if not any(enabled is True for enabled in architectures.values()):
        failures.append({"field": "architectures", "reason": "no architecture selected"})
    if report["orientation"] not in {"landscape", "reverseLandscape", "sensorLandscape"}:
        failures.append(
            {
                "field": "orientation",
                "reason": "accepted Android project is not landscape-constrained",
                "actual": report["orientation"],
            }
        )
    if not report["signing"]["debug_alias"]:
        failures.append({"field": "signing.debug_alias", "reason": "debug signing alias missing"})
    report["valid"] = not failures
    report["failures"] = failures
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect the accepted Manama Souq Android export preset")
    parser.add_argument("--preset", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = inspect(args.preset, args.project)
    write_json(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
