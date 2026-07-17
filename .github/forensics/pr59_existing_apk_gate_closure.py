#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

SIGNATURE_RE = re.compile(r"^META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))$", re.I)
REQUIRED_MATRIX_COUNT = 436
PRIMARY_SHA256 = "0956a0c8195dc9319238b1230ef3c0291a09742c357256ae29da46aa649bf455"
SECONDARY_SHA256 = "db42d1190957a244bec5745b3dbed82ba5707796075e5d828cfb0056cb3951d0"
PRIMARY_BYTES = 347_919_106
SECONDARY_BYTES = 347_919_106


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def collect_glb_paths(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for child in value.values():
            found.extend(collect_glb_paths(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(collect_glb_paths(child))
    elif isinstance(value, str) and value.lower().endswith(".glb"):
        found.append(value.removeprefix("res://"))
    return sorted(set(found))


def verify_apk(path: Path, expected_bytes: int, expected_sha256: str) -> dict[str, Any]:
    actual = {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
    actual["bytes_match"] = actual["bytes"] == expected_bytes
    actual["sha256_match"] = actual["sha256"] == expected_sha256
    actual["passed"] = actual["bytes_match"] and actual["sha256_match"]
    if not actual["passed"]:
        raise SystemExit(f"APK authority mismatch: {actual}")
    return actual


def matrix_summary(source_root: Path, inventory_path: Path, inspector_path: Path) -> dict[str, Any]:
    inventory = read_json(inventory_path)
    inspector = read_json(inspector_path)
    matrix = collect_glb_paths(read_json(source_root / "asset_lab/runtime/full_asset_matrix_manifest.json"))
    matrix_set = set(matrix)
    files = set(inventory["files"])
    missing = sorted(path for path in matrix if path not in files)
    expected_sidecars = {path + ".import" for path in matrix}
    raw_files = set(inventory["raw_files"])
    missing_sidecars = sorted(expected_sidecars - raw_files)
    aliases = [
        alias
        for alias in inventory["logical_aliases"]
        if alias.get("logical_path") in matrix_set and alias.get("sidecar_path")
    ]
    rejected_expected = [
        item
        for item in inventory.get("glb_import_rejections", [])
        if item.get("logical_path") in matrix_set
    ]
    required = inspector["packaged_resources"]["required_vertical_slice_resources"]
    value = {
        "expected_matrix_count": len(matrix),
        "exact_glb_import_sidecar_count": len(expected_sidecars & raw_files),
        "validated_logical_glb_alias_count": len(aliases),
        "matched_matrix_count": len(matrix) - len(missing),
        "missing_matrix_count": len(missing),
        "missing_matrix_paths": missing,
        "missing_sidecar_paths": missing_sidecars,
        "rejected_expected_sidecar_count": len(rejected_expected),
        "rejected_expected_sidecars": rejected_expected,
        "all_souq_karak_resources_present": all(required.values()),
        "souq_karak_resources": required,
        "inventory_passed": inventory.get("passed") is True,
        "inspector_passed": inspector.get("passed") is True,
        "unresolved_remap_count": len(inventory.get("remap_failures", [])),
        "unresolved_import_count": len(inventory.get("glb_import_rejections", [])),
        "raw_asset_count": inventory.get("raw_asset_count"),
        "logical_file_count": inventory.get("logical_file_count"),
    }
    value["passed"] = all(
        [
            value["expected_matrix_count"] == REQUIRED_MATRIX_COUNT,
            value["exact_glb_import_sidecar_count"] == REQUIRED_MATRIX_COUNT,
            value["validated_logical_glb_alias_count"] == REQUIRED_MATRIX_COUNT,
            value["matched_matrix_count"] == REQUIRED_MATRIX_COUNT,
            value["missing_matrix_count"] == 0,
            value["rejected_expected_sidecar_count"] == 0,
            value["unresolved_remap_count"] == 0,
            value["unresolved_import_count"] == 0,
            value["all_souq_karak_resources_present"],
            value["inventory_passed"],
            value["inspector_passed"],
        ]
    )
    if not value["passed"]:
        raise SystemExit(f"matrix acceptance failed: {json.dumps(value, sort_keys=True)}")
    return value


def zip_inventory(path: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    inventory: dict[str, dict[str, Any]] = {}
    with zipfile.ZipFile(path) as archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        counts = Counter(info.filename for info in infos)
        duplicates = sorted(name for name, count in counts.items() if count > 1)
        for info in infos:
            digest = hashlib.sha256()
            with archive.open(info) as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            inventory[info.filename] = {
                "sha256": digest.hexdigest(),
                "compressed_bytes": info.compress_size,
                "uncompressed_bytes": info.file_size,
                "compression": info.compress_type,
                "crc32": f"{info.CRC:08x}",
                "date_time": list(info.date_time),
                "flag_bits": info.flag_bits,
                "external_attr": info.external_attr,
                "extra_sha256": hashlib.sha256(info.extra).hexdigest(),
            }
    return inventory, duplicates


def exact_comparison(primary: Path, secondary: Path, primary_matrix: dict[str, Any], secondary_matrix: dict[str, Any], p_record: dict[str, Any], s_record: dict[str, Any]) -> dict[str, Any]:
    p_inv, p_dup = zip_inventory(primary)
    s_inv, s_dup = zip_inventory(secondary)
    p_paths = set(p_inv)
    s_paths = set(s_inv)
    missing_from_primary = sorted(s_paths - p_paths)
    missing_from_secondary = sorted(p_paths - s_paths)
    content_differences = sorted(path for path in p_paths & s_paths if p_inv[path]["sha256"] != s_inv[path]["sha256"])
    signature_differences = sorted(path for path in content_differences if SIGNATURE_RE.match(path))
    payload_differences = sorted(path for path in content_differences if not SIGNATURE_RE.match(path))
    structural: list[dict[str, Any]] = []
    fields = ("compressed_bytes", "uncompressed_bytes", "compression", "crc32", "date_time", "flag_bits", "external_attr", "extra_sha256")
    for path in sorted(p_paths & s_paths):
        changed = {field: {"primary": p_inv[path][field], "secondary": s_inv[path][field]} for field in fields if p_inv[path][field] != s_inv[path][field]}
        if changed:
            structural.append({"path": path, "fields": changed})
    metadata_fields = ("package_id", "version_name", "version_code", "min_sdk", "target_sdk", "orientation", "architectures", "launchable_activity")
    p_meta = p_record["apk"]
    s_meta = s_record["apk"]
    metadata_differences = {field: {"primary": p_meta.get(field), "secondary": s_meta.get(field)} for field in metadata_fields if p_meta.get(field) != s_meta.get(field)}
    p_cert = p_meta["signing"]["certificate_sha256"]
    s_cert = s_meta["signing"]["certificate_sha256"]
    logical_mapping_equal = primary_matrix["matched_matrix_count"] == secondary_matrix["matched_matrix_count"] == REQUIRED_MATRIX_COUNT and primary_matrix["missing_matrix_paths"] == secondary_matrix["missing_matrix_paths"] == []
    if sha256_file(primary) == sha256_file(secondary):
        classification = "A"
    elif not (missing_from_primary or missing_from_secondary or payload_differences or metadata_differences or p_dup or s_dup) and p_cert == s_cert and logical_mapping_equal:
        classification = "B"
    else:
        classification = "C"
    value = {
        "passed": classification in {"A", "B"},
        "classification": classification,
        "conclusion": {"A": "bit-identical", "B": "payload-identical, packaging/signature variance only", "C": "non-reproducible application payload"}[classification],
        "path_inventory_equal": not missing_from_primary and not missing_from_secondary,
        "missing_from_primary": missing_from_primary,
        "missing_from_secondary": missing_from_secondary,
        "non_signature_payload_differences": payload_differences,
        "signature_entry_differences": signature_differences,
        "all_content_differences": content_differences,
        "zip_structure_differences": structural,
        "metadata_differences": metadata_differences,
        "primary_duplicate_paths": p_dup,
        "secondary_duplicate_paths": s_dup,
        "signing_certificate_equal": p_cert == s_cert,
        "signing_certificate_sha256": p_cert if p_cert == s_cert else None,
        "logical_matrix_mapping_equal": logical_mapping_equal,
        "manifest_equal": "AndroidManifest.xml" not in payload_differences,
        "resources_table_equal": "resources.arsc" not in payload_differences,
        "dex_equal": not any(PurePosixPath(path).name.startswith("classes") and path.endswith(".dex") for path in payload_differences),
        "native_libraries_equal": not any(path.startswith("lib/") for path in payload_differences),
        "godot_project_assets_equal": not any(path.startswith("assets/") for path in payload_differences),
    }
    if not value["passed"]:
        raise SystemExit(f"Class C comparison: {json.dumps(value, sort_keys=True)}")
    return value


def main() -> int:
    if len(sys.argv) != 6:
        raise SystemExit("usage: script SOURCE_ROOT PRIMARY_ROOT SECONDARY_ROOT REPORT_ROOT CORRECTION_HEAD")
    source_root, primary_root, secondary_root, report_root = map(Path, sys.argv[1:5])
    correction_head = sys.argv[5]
    reports = report_root
    p_apk = primary_root / "artifacts/bahrain-brick-pr59-primary-debug.apk"
    s_apk = secondary_root / "artifacts/bahrain-brick-pr59-secondary-debug.apk"
    pre_primary = verify_apk(p_apk, PRIMARY_BYTES, PRIMARY_SHA256)
    pre_secondary = verify_apk(s_apk, SECONDARY_BYTES, SECONDARY_SHA256)
    p_inventory = reports / "primary/APK_PROJECT_ASSETS.json"
    s_inventory = reports / "secondary/APK_PROJECT_ASSETS.json"
    p_record_path = reports / "primary/APK_EXPORT_RECORD.json"
    s_record_path = reports / "secondary/APK_EXPORT_RECORD.json"
    p_record = read_json(p_record_path)
    s_record = read_json(s_record_path)
    p_matrix = matrix_summary(source_root, p_inventory, p_record_path)
    s_matrix = matrix_summary(source_root, s_inventory, s_record_path)
    write_json(reports / "PRIMARY_MATRIX_ACCEPTANCE.json", p_matrix)
    write_json(reports / "SECONDARY_MATRIX_ACCEPTANCE.json", s_matrix)
    comparison = exact_comparison(p_apk, s_apk, p_matrix, s_matrix, p_record, s_record)
    write_json(reports / "EXACT_APK_COMPARISON.json", comparison)
    post_primary = verify_apk(p_apk, PRIMARY_BYTES, PRIMARY_SHA256)
    post_secondary = verify_apk(s_apk, SECONDARY_BYTES, SECONDARY_SHA256)
    unchanged = {
        "primary": {"before": pre_primary, "after": post_primary, "unchanged": pre_primary == post_primary},
        "secondary": {"before": pre_secondary, "after": post_secondary, "unchanged": pre_secondary == post_secondary},
    }
    write_json(reports / "APK_BYTE_IDENTITY.json", unchanged)
    if not unchanged["primary"]["unchanged"] or not unchanged["secondary"]["unchanged"]:
        raise SystemExit("APK bytes changed during reinspection")
    original_primary = read_json(primary_root / "reports/APK_EXPORT_RECORD.json")
    source_authority = read_json(primary_root / "reports/SOURCE_AUTHORITY_POST_EXPORT.json")
    toolchain = read_json(primary_root / "reports/TOOLCHAIN_IDENTITY.json")
    artifact_authority = read_json(reports / "ARTIFACT_AUTHORITY.json")
    test_evidence = read_json(reports / "TEST_EVIDENCE.json")
    provenance = {
        "schema_version": 1,
        "repository": "MuhamedZanabal/brick-bahrain-open-world",
        "pr_number": 59,
        "original_export_authority": {
            "candidate_head": "f512fe8be09d15d2c9466f5edb089404a37a5c9b",
            "workflow_run_id": 29589205147,
            "primary_job_id": 87913824602,
            "secondary_job_id": 87913824650,
            "artifacts": artifact_authority,
            "primary_apk": pre_primary,
            "secondary_apk": pre_secondary,
            "source_authority": source_authority,
            "toolchain": toolchain,
            "signing_identity": original_primary["apk"]["signing"],
        },
        "corrective_inspection_authority": {
            "inventory_correction_commit": correction_head,
            "reinspection_workflow_run": int(os.environ["GITHUB_RUN_ID"]),
            "tests": test_evidence,
            "primary_matrix": p_matrix,
            "secondary_matrix": s_matrix,
            "primary_inspection_passed": p_record["passed"],
            "secondary_inspection_passed": s_record["passed"],
            "reproducibility": comparison,
            "apk_bytes_unchanged": unchanged,
            "no_reexport": True,
            "no_resigning": True,
            "no_apk_mutation": True,
            "no_installation_or_execution": True,
        },
        "gate_disposition": {
            "gate4": "pass" if comparison["classification"] in {"A", "B"} else "fail",
            "gate5": "pass" if p_record["passed"] and s_record["passed"] else "fail",
        },
    }
    write_json(reports / "FINAL_PROVENANCE.json", provenance)
    digest = sha256_file(reports / "FINAL_PROVENANCE.json")
    (reports / "FINAL_PROVENANCE_SHA256.txt").write_text(digest + "  FINAL_PROVENANCE.json\n", encoding="utf-8")
    summary = {
        "correction_head": correction_head,
        "primary": {"apk": pre_primary, "matrix": p_matrix, "inspection": p_record},
        "secondary": {"apk": pre_secondary, "matrix": s_matrix, "inspection": s_record},
        "comparison": comparison,
        "provenance_sha256": digest,
        "gate4": provenance["gate_disposition"]["gate4"],
        "gate5": provenance["gate_disposition"]["gate5"],
    }
    write_json(reports / "GATE_CLOSURE_SUMMARY.json", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
