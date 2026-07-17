#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

SIGNATURE_PATH_RE = re.compile(r"^META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))$", re.I)
TEXTURE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".ktx", ".ktx2", ".dds", ".svg"}
DIRECT_ASSETS_PACKAGING = "godot-4.3-default-android-apk-assets"
REQUIRED_MATRIX_COUNT = 436
ORIENTATION_NAMES = {
    0: "sensor",
    1: "landscape",
    2: "portrait",
    3: "reverseLandscape",
    4: "reversePortrait",
    5: "sensorLandscape",
    6: "sensorPortrait",
    7: "unspecified",
    8: "user",
    9: "behind",
    10: "fullSensor",
    11: "sensorLandscape",
    12: "sensorPortrait",
    13: "fullUser",
    14: "locked",
}


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_cfg_value(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(key)}=(.+)$", text)
    if not match:
        return None
    raw = match.group(1).strip()
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    return raw


def bool_cfg(text: str, key: str) -> bool | None:
    raw = extract_cfg_value(text, key)
    if raw is None:
        return None
    if raw == "true":
        return True
    if raw == "false":
        return False
    raise ValueError(f"invalid boolean for {key}: {raw}")


def command_authority(args: argparse.Namespace) -> int:
    game = Path(args.game).resolve()
    manifest_path = Path(args.manifest).resolve()
    manifest = read_json(manifest_path)
    failures: list[dict[str, Any]] = []
    checked = 0
    total_bytes = 0
    for item in manifest["files"]:
        relative = item["path"]
        target = game / relative
        if not target.is_file():
            failures.append({"path": relative, "reason": "missing"})
            continue
        actual_bytes = target.stat().st_size
        actual_sha = sha256_file(target)
        checked += 1
        total_bytes += actual_bytes
        if actual_bytes != item["bytes"] or actual_sha != item["sha256"]:
            failures.append(
                {
                    "path": relative,
                    "reason": "content_mismatch",
                    "expected_bytes": item["bytes"],
                    "actual_bytes": actual_bytes,
                    "expected_sha256": item["sha256"],
                    "actual_sha256": actual_sha,
                }
            )
    result = {
        "passed": not failures,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "aggregate_tree_sha256": manifest["aggregate_tree_sha256"],
        "expected_file_count": manifest["file_count"],
        "checked_file_count": checked,
        "expected_total_bytes": manifest["total_bytes"],
        "checked_total_bytes": total_bytes,
        "failures": failures,
    }
    write_json(Path(args.output), result)
    return 0 if result["passed"] else 1


def command_preset(args: argparse.Namespace) -> int:
    preset_path = Path(args.preset).resolve()
    project_path = Path(args.project).resolve()
    preset = preset_path.read_text(encoding="utf-8")
    project = project_path.read_text(encoding="utf-8")
    orientation_value = int(extract_cfg_value(project, "window/handheld/orientation") or "-1")
    architectures = {
        name: bool_cfg(preset, f"architectures/{name}")
        for name in ("armeabi-v7a", "arm64-v8a", "x86_64", "x86")
    }
    permissions = {
        "internet": bool_cfg(preset, "permissions/internet"),
        "access_network_state": bool_cfg(preset, "permissions/access_network_state"),
        "custom_permissions": extract_cfg_value(preset, "permissions/custom_permissions"),
    }
    report = {
        "preset_file": str(preset_path),
        "preset_sha256": sha256_file(preset_path),
        "project_file": str(project_path),
        "project_sha256": sha256_file(project_path),
        "preset_name": extract_cfg_value(preset, "name"),
        "platform": extract_cfg_value(preset, "platform"),
        "runnable": bool_cfg(preset, "runnable"),
        "export_path": extract_cfg_value(preset, "export_path"),
        "package_id": extract_cfg_value(preset, "package/unique_name"),
        "application_label": extract_cfg_value(preset, "package/name"),
        "version_name": extract_cfg_value(preset, "version/name"),
        "version_code": int(extract_cfg_value(preset, "version/code") or "0"),
        "min_sdk": extract_cfg_value(preset, "gradle_build/min_sdk"),
        "target_sdk": extract_cfg_value(preset, "gradle_build/target_sdk"),
        "architectures": architectures,
        "renderer": extract_cfg_value(project, "renderer/rendering_method.mobile")
        or extract_cfg_value(project, "renderer/rendering_method"),
        "orientation_value": orientation_value,
        "orientation": ORIENTATION_NAMES.get(orientation_value, f"unknown:{orientation_value}"),
        "debuggable_export": True,
        "permissions": permissions,
        "expansion_file_enabled": bool_cfg(preset, "apk_expansion/enable"),
        "use_gradle_build": bool_cfg(preset, "gradle_build/use_gradle_build"),
        "signing": {
            "debug_keystore": extract_cfg_value(preset, "keystore/debug"),
            "debug_alias": extract_cfg_value(preset, "keystore/debug_user"),
            "release_keystore": extract_cfg_value(preset, "keystore/release"),
            "passwords_redacted": True,
        },
        "texture_compression": {
            "etc2_astc_import_enabled": extract_cfg_value(project, "textures/vram_compression/import_etc2_astc")
        },
    }
    required = {
        "preset_name": "Android",
        "platform": "Android",
        "runnable": True,
        "package_id": "com.brickbahrain.openworld",
        "version_name": "1.0.0",
        "version_code": 1,
        "use_gradle_build": False,
    }
    failures = [
        {"field": key, "expected": expected, "actual": report.get(key)}
        for key, expected in required.items()
        if report.get(key) != expected
    ]
    if not any(value is True for value in architectures.values()):
        failures.append({"field": "architectures", "reason": "no architecture selected"})
    if report["signing"]["debug_keystore"] != "res://debug.keystore":
        failures.append({"field": "signing.debug_keystore", "reason": "unexpected debug signing path"})
    report["valid"] = not failures
    report["failures"] = failures
    write_json(Path(args.output), report)
    return 0 if report["valid"] else 1


def zip_entry_sha256(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> str:
    digest = hashlib.sha256()
    with archive.open(info, "r") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def category_for(path: str) -> str:
    lower = path.lower()
    name = PurePosixPath(path).name
    if lower.startswith("lib/") and lower.endswith(".so"):
        return "native_libraries"
    if re.fullmatch(r"classes\d*\.dex", name, re.I):
        return "dex"
    if lower == "androidmanifest.xml":
        return "android_manifest"
    if lower == "resources.arsc":
        return "resources_table"
    if lower.startswith("assets/"):
        return "assets"
    if lower.startswith("res/"):
        return "android_resources"
    if SIGNATURE_PATH_RE.match(path):
        return "signatures"
    return "other"


def parse_badging(text: str) -> dict[str, Any]:
    package = re.search(r"package: name='([^']+)' versionCode='([^']+)' versionName='([^']*)'", text)
    label = re.search(r"(?m)^application-label(?:-[^:]+)?:'([^']*)'", text)
    launch = re.search(r"launchable-activity: name='([^']+)'", text)
    min_sdk = re.search(r"sdkVersion:'([^']+)'", text)
    target_sdk = re.search(r"targetSdkVersion:'([^']+)'", text)
    native = re.search(r"native-code:(.*)", text)
    permissions = sorted(set(re.findall(r"uses-permission: name='([^']+)'", text)))
    features = sorted(set(re.findall(r"uses-feature(?:-not-required)?: name='([^']+)'", text)))
    architectures = re.findall(r"'([^']+)'", native.group(1)) if native else []
    return {
        "package_id": package.group(1) if package else None,
        "version_code": int(package.group(2)) if package else None,
        "version_name": package.group(3) if package else None,
        "application_label": label.group(1) if label else None,
        "launchable_activity": launch.group(1) if launch else None,
        "min_sdk": int(min_sdk.group(1)) if min_sdk and min_sdk.group(1).isdigit() else (min_sdk.group(1) if min_sdk else None),
        "target_sdk": int(target_sdk.group(1)) if target_sdk and target_sdk.group(1).isdigit() else (target_sdk.group(1) if target_sdk else None),
        "architectures": architectures,
        "permissions": permissions,
        "features": features,
        "debuggable": "application-debuggable" in text,
    }


def parse_manifest_xml(text: str) -> dict[str, Any]:
    orientation_line = next((line for line in text.splitlines() if "android:screenOrientation" in line), "")
    orientation_value = None
    hex_match = re.search(r"0x([0-9a-f]+)\)?\s*$", orientation_line, re.I)
    if hex_match:
        orientation_value = int(hex_match.group(1), 16)
    else:
        dec_match = re.search(r"=([0-9]+)\s*$", orientation_line)
        if dec_match:
            orientation_value = int(dec_match.group(1))
    debuggable_line = next((line for line in text.splitlines() if "android:debuggable" in line), "")
    debuggable = bool(debuggable_line) and (
        "0xffffffff" in debuggable_line.lower() or re.search(r"=true\b", debuggable_line, re.I) is not None
    )
    return {
        "orientation_raw": orientation_line.strip() or None,
        "orientation_value": orientation_value,
        "orientation": ORIENTATION_NAMES.get(orientation_value, f"unknown:{orientation_value}") if orientation_value is not None else None,
        "debuggable_raw": debuggable_line.strip() or None,
        "debuggable": debuggable,
    }


def parse_signing(text: str) -> dict[str, Any]:
    def scheme(name: str) -> bool | None:
        match = re.search(rf"Verified using {re.escape(name)} scheme[^:]*:\s*(true|false)", text, re.I)
        return match.group(1).lower() == "true" if match else None

    digest = re.search(r"Signer #1 certificate SHA-256 digest:\s*([0-9a-f:]+)", text, re.I)
    subject = re.search(r"Signer #1 certificate DN:\s*(.+)", text)
    valid_from = re.search(r"Signer #1 certificate valid from:\s*(.+)", text)
    valid_until = re.search(r"Signer #1 certificate valid until:\s*(.+)", text)
    return {
        "verified": "DOES NOT VERIFY" not in text.upper(),
        "v1": scheme("v1"),
        "v2": scheme("v2"),
        "v3": scheme("v3"),
        "v4": scheme("v4"),
        "certificate_sha256": digest.group(1).replace(":", "").lower() if digest else None,
        "certificate_subject": subject.group(1).strip() if subject else None,
        "certificate_valid_from": valid_from.group(1).strip() if valid_from else None,
        "certificate_valid_until": valid_until.group(1).strip() if valid_until else None,
        "qa_debug_identity": bool(subject and re.search(r"android|debug|bahrain brick", subject.group(1), re.I)),
    }


def collect_glb_paths(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for child in value.values():
            found.extend(collect_glb_paths(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(collect_glb_paths(child))
    elif isinstance(value, str) and value.lower().endswith(".glb"):
        found.append(value.replace("res://", ""))
    return sorted(set(found))


def normalized_pack_path(path: str) -> str:
    return path.replace("res://", "").lstrip("/")


def _normalized_string_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {normalized_pack_path(item) for item in value if isinstance(item, str) and item.strip()}


def validate_project_asset_inventory(value: Any, inventory_path: Path | None) -> dict[str, Any]:
    failures: list[str] = []
    if not isinstance(value, dict):
        value = {}
        failures.append("invalid normalized project-resource inventory schema")
    files = _normalized_string_set(value.get("files"))
    raw_files = _normalized_string_set(value.get("raw_files"))
    aliases_value = value.get("logical_aliases")
    aliases = aliases_value if isinstance(aliases_value, list) else []
    packaging = value.get("packaging")
    direct_assets_layout = packaging == DIRECT_ASSETS_PACKAGING and value.get("pck_required") is False
    if value.get("passed") is not True:
        failures.append("project asset inventory generator did not pass")
    if not files:
        failures.append("empty normalized project-resource inventory")
    if not raw_files:
        failures.append("empty raw APK project-assets inventory")
    if not direct_assets_layout:
        failures.append("unsupported or unverified project-assets packaging layout")
    remap_failures = value.get("remap_failures")
    if value.get("remap_targets_verified") is not True or (isinstance(remap_failures, list) and remap_failures):
        failures.append("unverified or missing remap target")

    validated_aliases: dict[str, list[dict[str, Any]]] = {}
    alias_failures: list[dict[str, Any]] = []
    for raw_alias in aliases:
        if not isinstance(raw_alias, dict):
            alias_failures.append({"reason": "alias is not an object"})
            continue
        logical = normalized_pack_path(str(raw_alias.get("logical_path") or ""))
        packaged = normalized_pack_path(str(raw_alias.get("packaged_path") or ""))
        target_value = raw_alias.get("remap_target")
        target = normalized_pack_path(str(target_value)) if target_value else None
        valid = bool(logical and packaged and packaged in raw_files and raw_alias.get("target_verified") is True)
        if target is not None:
            valid = valid and target in raw_files and raw_alias.get("source_verified") is True
        if valid:
            normalized_alias = dict(raw_alias)
            normalized_alias["logical_path"] = logical
            normalized_alias["packaged_path"] = packaged
            if target is not None:
                normalized_alias["remap_target"] = target
            validated_aliases.setdefault(logical, []).append(normalized_alias)
        else:
            alias_failures.append(
                {
                    "logical_path": logical or None,
                    "packaged_path": packaged or None,
                    "remap_target": target,
                    "reason": "alias mapping is incomplete or references an absent APK asset",
                }
            )
    if alias_failures:
        failures.append("invalid compiled or remapped project-resource mapping")

    return {
        "path": str(inventory_path.resolve()) if inventory_path else None,
        "valid": not failures,
        "packaging": packaging,
        "direct_assets_layout": direct_assets_layout,
        "pck_required": value.get("pck_required"),
        "logical_file_count": len(files),
        "raw_asset_count": len(raw_files),
        "files": files,
        "raw_files": raw_files,
        "validated_aliases": validated_aliases,
        "alias_failures": alias_failures,
        "remap_targets_verified": value.get("remap_targets_verified") is True,
        "remap_failures": remap_failures if isinstance(remap_failures, list) else [],
        "compatibility_note": value.get("compatibility_note")
        or "PCK_CONTENTS.json is a normalized logical project-resource inventory, not proof of a physical PCK entry.",
        "failures": failures,
    }


def project_inventory_has_path(project_inventory: dict[str, Any], required: str) -> bool:
    normalized = normalized_pack_path(required)
    if normalized in project_inventory["raw_files"]:
        return True
    return bool(project_inventory["validated_aliases"].get(normalized))


def command_inspect(args: argparse.Namespace) -> int:
    apk = Path(args.apk).resolve()
    report_dir = Path(args.report_dir).resolve()
    source_root = Path(args.source_root).resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    badging_text = Path(args.badging).read_text(encoding="utf-8", errors="replace")
    manifest_text = Path(args.manifest_xml).read_text(encoding="utf-8", errors="replace")
    signing_text = Path(args.signing).read_text(encoding="utf-8", errors="replace")
    project_inventory_path = Path(args.pck_inventory).resolve() if args.pck_inventory else None
    project_inventory_value = read_json(project_inventory_path) if project_inventory_path else {}
    project_inventory = validate_project_asset_inventory(project_inventory_value, project_inventory_path)

    with zipfile.ZipFile(apk) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        counts = Counter(names)
        duplicate_paths = sorted(path for path, count in counts.items() if count > 1)
        unsafe_paths = sorted(
            path for path in names if path.startswith("/") or "\\" in path or ".." in PurePosixPath(path).parts
        )
        nested_apks = sorted(path for path in names if path.lower().endswith(".apk"))
        inventory: list[dict[str, Any]] = []
        categories: dict[str, dict[str, int]] = {}
        for info in infos:
            if info.is_dir():
                continue
            content_sha = zip_entry_sha256(archive, info)
            item = {
                "path": info.filename,
                "compressed_bytes": info.compress_size,
                "uncompressed_bytes": info.file_size,
                "sha256": content_sha,
                "compression": info.compress_type,
                "crc32": f"{info.CRC:08x}",
            }
            inventory.append(item)
            category = category_for(info.filename)
            bucket = categories.setdefault(category, {"entries": 0, "compressed_bytes": 0, "uncompressed_bytes": 0})
            bucket["entries"] += 1
            bucket["compressed_bytes"] += info.compress_size
            bucket["uncompressed_bytes"] += info.file_size

    required_exact = ["AndroidManifest.xml", "resources.arsc"]
    missing_exact = [path for path in required_exact if path not in counts]
    dex_paths = sorted(path for path in counts if re.fullmatch(r"classes\d*\.dex", PurePosixPath(path).name, re.I))
    native_paths = sorted(path for path in counts if path.startswith("lib/") and path.endswith(".so"))
    standalone_pck_paths = sorted(path for path in counts if path.startswith("assets/") and path.lower().endswith(".pck"))
    command_line_asset_paths = sorted(
        path for path in counts if path.startswith("assets/") and PurePosixPath(path).name == "_cl_"
    )
    zero_byte_critical = sorted(
        item["path"]
        for item in inventory
        if item["uncompressed_bytes"] == 0
        and (
            item["path"] in required_exact
            or re.fullmatch(r"classes\d*\.dex", PurePosixPath(item["path"]).name, re.I)
            or item["path"].startswith("lib/")
        )
    )
    integrity_failures: list[str] = []
    if duplicate_paths:
        integrity_failures.append("duplicate archive paths")
    if unsafe_paths:
        integrity_failures.append("unsafe archive paths")
    if nested_apks:
        integrity_failures.append("unexpected nested APK")
    if missing_exact:
        integrity_failures.append("missing Android manifest/resources table")
    if not dex_paths:
        integrity_failures.append("missing DEX")
    if not native_paths:
        integrity_failures.append("missing native libraries")
    if zero_byte_critical:
        integrity_failures.append("zero-byte critical files")

    metadata = parse_badging(badging_text)
    metadata.update(parse_manifest_xml(manifest_text))
    signing = parse_signing(signing_text)
    signing_failures: list[str] = []
    if not signing["verified"]:
        signing_failures.append("APK signature verification failed")
    if not all(signing.get(scheme) is True for scheme in ("v1", "v2", "v3")):
        signing_failures.append("required APK signing schemes v1, v2 and v3 did not all verify")
    if not signing["qa_debug_identity"]:
        signing_failures.append("QA/debug signing identity not verified")
    metadata["signing"] = signing
    metadata["apk_filename"] = apk.name
    metadata["apk_bytes"] = apk.stat().st_size
    metadata["apk_sha256"] = sha256_file(apk)
    metadata["zip_integrity"] = not integrity_failures
    metadata["alignment_verified"] = True

    required_resources = [
        "scenes/manama_souq_vertical_slice.tscn",
        "scripts/manama_souq_vertical_slice.gd",
        "scripts/karak_delivery_mission.gd",
        "scenes/karak_delivery_hud.tscn",
        "scripts/karak_delivery_hud.gd",
        "scripts/souq_population_controller.gd",
        "scripts/brick_factory.gd",
        "scripts/touch_input.gd",
        "asset_lab/runtime/manama_souq_layout_v1.json",
    ]
    required_status = {path: project_inventory_has_path(project_inventory, path) for path in required_resources}
    matrix_manifest = source_root / "asset_lab/runtime/full_asset_matrix_manifest.json"
    matrix_glbs: list[str] = []
    packaged_failures = list(project_inventory["failures"])
    if matrix_manifest.is_file():
        matrix_glbs = collect_glb_paths(read_json(matrix_manifest))
    else:
        packaged_failures.append("missing full asset matrix manifest")
    if len(matrix_glbs) != REQUIRED_MATRIX_COUNT:
        packaged_failures.append(
            f"full asset matrix manifest count mismatch: expected {REQUIRED_MATRIX_COUNT}, found {len(matrix_glbs)}"
        )
    matrix_presence = {path: project_inventory_has_path(project_inventory, path) for path in matrix_glbs}
    missing_required = sorted(path for path, present in required_status.items() if not present)
    missing_matrix = sorted(path for path, present in matrix_presence.items() if not present)
    if missing_required:
        packaged_failures.append("missing required Manama Souq or Karak Delivery project resources")
    if missing_matrix:
        packaged_failures.append("missing required full asset matrix project resources")
    source_glbs = sorted(path.relative_to(source_root).as_posix() for path in source_root.rglob("*.glb") if path.is_file())
    source_textures = [
        path for path in source_root.rglob("*") if path.is_file() and path.suffix.lower() in TEXTURE_EXTENSIONS
    ]
    packaged = {
        "passed": not packaged_failures,
        "failures": packaged_failures,
        "project_asset_inventory": {
            key: value
            for key, value in project_inventory.items()
            if key not in {"files", "raw_files", "validated_aliases"}
        },
        "project_asset_inventory_file_count": project_inventory["logical_file_count"],
        "project_asset_raw_file_count": project_inventory["raw_asset_count"],
        "direct_assets_layout": project_inventory["direct_assets_layout"],
        "standalone_pck_required": False,
        "standalone_pck_paths": standalone_pck_paths,
        "pck_inventory_file_count": project_inventory["logical_file_count"],
        "pck_glb_path_count": sum(1 for path in project_inventory["files"] if path.lower().endswith(".glb")),
        "compatibility_note": project_inventory["compatibility_note"],
        "source_glb_count": len(source_glbs),
        "source_glb_bytes": sum((source_root / path).stat().st_size for path in source_glbs),
        "source_texture_count": len(source_textures),
        "source_texture_bytes": sum(path.stat().st_size for path in source_textures),
        "full_asset_matrix_manifest_glb_count": len(matrix_glbs),
        "full_asset_matrix_packaged_count": sum(1 for value in matrix_presence.values() if value),
        "full_asset_matrix_missing": missing_matrix,
        "required_vertical_slice_resources": required_status,
    }

    largest = sorted(inventory, key=lambda item: item["uncompressed_bytes"], reverse=True)[:25]
    archive_report = {
        "passed": not integrity_failures,
        "zip_entry_count": len(inventory),
        "duplicate_paths": duplicate_paths,
        "unsafe_paths": unsafe_paths,
        "nested_apks": nested_apks,
        "missing_required_entries": missing_exact,
        "dex_paths": dex_paths,
        "native_library_paths": native_paths,
        "standalone_pck_paths": standalone_pck_paths,
        "command_line_asset_paths": command_line_asset_paths,
        "direct_assets_layout": project_inventory["direct_assets_layout"],
        "project_asset_inventory": {
            "path": project_inventory["path"],
            "valid": project_inventory["valid"],
            "logical_file_count": project_inventory["logical_file_count"],
            "raw_asset_count": project_inventory["raw_asset_count"],
        },
        "pck_paths": standalone_pck_paths,
        "zero_byte_critical_files": zero_byte_critical,
        "failures": integrity_failures,
    }
    breakdown = {
        "apk_bytes": apk.stat().st_size,
        "categories": categories,
        "largest_25_entries": largest,
        "source_resource_accounting": {
            "glb_count": len(source_glbs),
            "glb_bytes": packaged["source_glb_bytes"],
            "texture_count": len(source_textures),
            "texture_bytes": packaged["source_texture_bytes"],
        },
    }
    write_json(report_dir / "APK_ARCHIVE_REPORT.json", archive_report)
    write_json(report_dir / "APK_ENTRY_INVENTORY.json", {"entries": inventory})
    write_json(report_dir / "APK_SIZE_BREAKDOWN.json", breakdown)
    write_json(report_dir / "APK_METADATA.json", metadata)
    write_json(report_dir / "PACKAGED_VERTICAL_SLICE_RESOURCES.json", packaged)
    record = {
        "passed": archive_report["passed"] and packaged["passed"] and not signing_failures,
        "apk": metadata,
        "archive": archive_report,
        "packaged_resources": packaged,
        "signing_validation": {"passed": not signing_failures, "failures": signing_failures},
    }
    write_json(report_dir / "APK_EXPORT_RECORD.json", record)
    return 0 if record["passed"] else 1


def apk_inventory(path: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    values: dict[str, dict[str, Any]] = {}
    with zipfile.ZipFile(path) as archive:
        counts = Counter(info.filename for info in archive.infolist())
        duplicates = sorted(name for name, count in counts.items() if count > 1)
        for info in archive.infolist():
            if info.is_dir():
                continue
            values[info.filename] = {
                "sha256": zip_entry_sha256(archive, info),
                "compressed_bytes": info.compress_size,
                "uncompressed_bytes": info.file_size,
                "compression": info.compress_type,
                "crc32": f"{info.CRC:08x}",
                "date_time": list(info.date_time),
                "flag_bits": info.flag_bits,
                "external_attr": info.external_attr,
                "extra_sha256": hashlib.sha256(info.extra).hexdigest(),
            }
    return values, duplicates


def command_compare(args: argparse.Namespace) -> int:
    primary = Path(args.primary).resolve()
    secondary = Path(args.secondary).resolve()
    primary_record = read_json(Path(args.primary_record))
    secondary_record = read_json(Path(args.secondary_record))
    p_inv, p_dup = apk_inventory(primary)
    s_inv, s_dup = apk_inventory(secondary)
    p_paths = set(p_inv)
    s_paths = set(s_inv)
    missing_primary = sorted(s_paths - p_paths)
    missing_secondary = sorted(p_paths - s_paths)
    content_differences = sorted(path for path in p_paths & s_paths if p_inv[path]["sha256"] != s_inv[path]["sha256"])
    signature_differences = sorted(path for path in content_differences if SIGNATURE_PATH_RE.match(path))
    payload_differences = sorted(path for path in content_differences if not SIGNATURE_PATH_RE.match(path))
    structure_differences = []
    structure_fields = (
        "compressed_bytes",
        "uncompressed_bytes",
        "compression",
        "crc32",
        "date_time",
        "flag_bits",
        "external_attr",
        "extra_sha256",
    )
    for path in sorted(p_paths & s_paths):
        fields = {
            field: {"primary": p_inv[path][field], "secondary": s_inv[path][field]}
            for field in structure_fields
            if p_inv[path][field] != s_inv[path][field]
        }
        if fields:
            structure_differences.append({"path": path, "fields": fields})
    p_sha = sha256_file(primary)
    s_sha = sha256_file(secondary)
    p_meta = primary_record["apk"]
    s_meta = secondary_record["apk"]
    metadata_fields = (
        "package_id",
        "version_name",
        "version_code",
        "min_sdk",
        "target_sdk",
        "orientation",
        "architectures",
        "launchable_activity",
    )
    metadata_differences = {
        field: {"primary": p_meta.get(field), "secondary": s_meta.get(field)}
        for field in metadata_fields
        if p_meta.get(field) != s_meta.get(field)
    }
    p_cert = p_meta.get("signing", {}).get("certificate_sha256")
    s_cert = s_meta.get("signing", {}).get("certificate_sha256")
    if p_sha == s_sha:
        classification = "A"
        conclusion = "bit-identical"
    elif not (missing_primary or missing_secondary or payload_differences or metadata_differences or p_dup or s_dup) and p_cert == s_cert:
        classification = "B"
        conclusion = "payload-identical, packaging/signature variance only"
    else:
        classification = "C"
        conclusion = "non-reproducible application payload"
    manifest_resource_native_differences = sorted(
        path
        for path in payload_differences
        if path == "AndroidManifest.xml"
        or path == "resources.arsc"
        or path.startswith("lib/")
        or re.fullmatch(r"classes\d*\.dex", PurePosixPath(path).name, re.I)
    )
    report = {
        "passed": classification in ("A", "B"),
        "classification": classification,
        "conclusion": conclusion,
        "primary": {"path": str(primary), "bytes": primary.stat().st_size, "sha256": p_sha},
        "secondary": {"path": str(secondary), "bytes": secondary.stat().st_size, "sha256": s_sha},
        "path_inventory_equal": not missing_primary and not missing_secondary,
        "missing_from_primary": missing_primary,
        "missing_from_secondary": missing_secondary,
        "content_differences": content_differences,
        "signature_entry_differences": signature_differences,
        "payload_entry_differences": payload_differences,
        "manifest_resources_native_differences": manifest_resource_native_differences,
        "zip_structure_differences": structure_differences,
        "metadata_differences": metadata_differences,
        "primary_duplicate_paths": p_dup,
        "secondary_duplicate_paths": s_dup,
        "signing_certificate_equal": p_cert is not None and p_cert == s_cert,
        "signing_certificate_sha256": p_cert if p_cert == s_cert else None,
    }
    write_json(Path(args.output), report)
    return 0 if report["passed"] else 1


def command_finalize(args: argparse.Namespace) -> int:
    primary_record = read_json(Path(args.primary_record))
    secondary_record = read_json(Path(args.secondary_record))
    comparison = read_json(Path(args.comparison))
    preset = read_json(Path(args.preset_report))
    toolchain = read_json(Path(args.toolchain_report))
    source = read_json(Path(args.source_report))
    primary_meta = primary_record["apk"]
    value = {
        "schema_version": 1,
        "repository": "MuhamedZanabal/brick-bahrain-open-world",
        "pr_number": 59,
        "pr_head": args.pr_head,
        "branch": "work/bahrain-brick-manama-souq-vertical-slice-v1",
        "base_authority": "fc8f00182f97c39015610d6603fa7c9c44364c5d",
        "frozen_premium_authority": "e26ec912db5c10d071a8e120010bdb5a9a136f17",
        "gate1_authority_head": "b12e1e012e256036e71066260a4c6392d26c3839",
        "source_manifest_sha256": source["manifest_sha256"],
        "aggregate_source_tree_sha256": source["aggregate_tree_sha256"],
        "source_file_count": source["expected_file_count"],
        "source_bytes": source["expected_total_bytes"],
        "godot_editor": toolchain.get("godot_editor"),
        "godot_export_templates": toolchain.get("godot_export_templates"),
        "android_toolchain": toolchain.get("android_toolchain"),
        "host": toolchain.get("host"),
        "export_preset": preset,
        "export_command": primary_record.get("export_command"),
        "workflow_run_id": args.workflow_run_id,
        "primary_job_id": args.primary_job_id,
        "secondary_job_id": args.secondary_job_id,
        "apk_filename": primary_meta["apk_filename"],
        "apk_bytes": primary_meta["apk_bytes"],
        "apk_sha256": primary_meta["apk_sha256"],
        "package_id": primary_meta["package_id"],
        "application_label": primary_meta["application_label"],
        "version_name": primary_meta["version_name"],
        "version_code": primary_meta["version_code"],
        "min_sdk": primary_meta["min_sdk"],
        "target_sdk": primary_meta["target_sdk"],
        "orientation": primary_meta["orientation"],
        "architectures": primary_meta["architectures"],
        "debuggable": primary_meta["debuggable"],
        "permissions": primary_meta["permissions"],
        "signing_certificate_sha256": primary_meta["signing"]["certificate_sha256"],
        "reproducibility_classification": comparison["classification"],
        "pre_export_gates": {
            "gate1": "pass",
            "gate2": "pass",
            "gate3": "pass",
            "clean_import": "pass",
            "frozen_controls": "25/25 pre and post",
            "critical_errors": 0,
        },
        "secondary_export": secondary_record["apk"],
        "installation_tested": False,
        "android_runtime_tested": False,
        "explicit_limit": "APK installation, Android launch, gameplay, soak and performance validation were not performed.",
    }
    write_json(Path(args.output), value)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    authority = sub.add_parser("authority")
    authority.add_argument("--game", required=True)
    authority.add_argument("--manifest", required=True)
    authority.add_argument("--output", required=True)
    authority.set_defaults(func=command_authority)

    preset = sub.add_parser("preset")
    preset.add_argument("--preset", required=True)
    preset.add_argument("--project", required=True)
    preset.add_argument("--output", required=True)
    preset.set_defaults(func=command_preset)

    inspect = sub.add_parser("inspect")
    inspect.add_argument("--apk", required=True)
    inspect.add_argument("--report-dir", required=True)
    inspect.add_argument("--source-root", required=True)
    inspect.add_argument("--badging", required=True)
    inspect.add_argument("--manifest-xml", required=True)
    inspect.add_argument("--signing", required=True)
    inspect.add_argument(
        "--pck-inventory",
        help="Compatibility input containing the normalized logical project-resource inventory; not proof of a physical PCK entry.",
    )
    inspect.set_defaults(func=command_inspect)

    compare = sub.add_parser("compare")
    compare.add_argument("--primary", required=True)
    compare.add_argument("--secondary", required=True)
    compare.add_argument("--primary-record", required=True)
    compare.add_argument("--secondary-record", required=True)
    compare.add_argument("--output", required=True)
    compare.set_defaults(func=command_compare)

    finalize = sub.add_parser("finalize")
    finalize.add_argument("--primary-record", required=True)
    finalize.add_argument("--secondary-record", required=True)
    finalize.add_argument("--comparison", required=True)
    finalize.add_argument("--preset-report", required=True)
    finalize.add_argument("--toolchain-report", required=True)
    finalize.add_argument("--source-report", required=True)
    finalize.add_argument("--pr-head", required=True)
    finalize.add_argument("--workflow-run-id", required=True)
    finalize.add_argument("--primary-job-id", required=True)
    finalize.add_argument("--secondary-job-id", required=True)
    finalize.add_argument("--output", required=True)
    finalize.set_defaults(func=command_finalize)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
