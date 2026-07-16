#!/usr/bin/env python3
"""Evaluate the complete Bahrain Brick golden-master release evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ASSET_IDS = {
    "bh_traditional_projecting_window_01",
    "bh_souq_shop_gold_01",
    "bh_waterfront_tower_a_01",
    "bh_supermarket_storefront_a_01",
    "bh_cr_skyscraper_tower_01",
}


def _exact_asset_records(
    evidence: dict[str, Any],
    key: str,
    failures: list[str],
    *,
    predicate=None,
) -> list[dict[str, Any]]:
    records = evidence.get(key)
    if not isinstance(records, list):
        failures.append(f"{key}:expected_list")
        return []
    valid = [record for record in records if isinstance(record, dict)]
    ids = [record.get("asset_id") for record in valid]
    if len(valid) != 5 or set(ids) != ASSET_IDS or len(ids) != len(set(ids)):
        failures.append(f"{key}:exact_five_unique_assets_required")
    if predicate is not None:
        for record in valid:
            reason = predicate(record)
            if reason:
                failures.append(f"{key}:{record.get('asset_id','unknown')}:{reason}")
    return valid


def _sha256_valid(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value.lower())


def evaluate_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    technical = evidence.get("technical_validation")
    if not isinstance(technical, dict):
        failures.append("technical_validation:expected_object")
    else:
        if technical.get("passed") is not True:
            failures.append("technical_validation:passed_required")
        if technical.get("validated_assets") != 45:
            failures.append("technical_validation:validated_assets_expected_45")
        if technical.get("texture_count") != 24:
            failures.append("technical_validation:texture_count_expected_24")

    protected = evidence.get("protected_authority")
    if not isinstance(protected, dict) or protected.get("passed") is not True:
        failures.append("protected_authority:passed_required")

    godot = evidence.get("godot_import")
    if not isinstance(godot, dict):
        failures.append("godot_import:expected_object")
    else:
        if godot.get("passed") is not True:
            failures.append("godot_import:passed_required")
        imported = godot.get("imported_assets")
        if not isinstance(imported, list) or set(imported) != ASSET_IDS or len(imported) != 5:
            failures.append("godot_import:exact_asset_coverage_required")

    android = evidence.get("android_runtime")
    if not isinstance(android, dict):
        failures.append("android_runtime:expected_object")
    else:
        if android.get("passed") is not True:
            failures.append("android_runtime:passed_required")
        if android.get("landscape") is not True:
            failures.append("android_runtime:landscape_required")
        visible = android.get("visible_assets")
        if not isinstance(visible, list) or set(visible) != ASSET_IDS or len(visible) != 5:
            failures.append("android_runtime:exact_visible_asset_coverage_required")

    _exact_asset_records(
        evidence,
        "contact_sheets",
        failures,
        predicate=lambda record: (
            "balanced_lod0_required"
            if record.get("profile") != "balanced" or record.get("lod") != 0
            else "path_required"
            if not isinstance(record.get("path"), str) or not record["path"]
            else "sha256_required"
            if not _sha256_valid(record.get("sha256"))
            else None
        ),
    )
    _exact_asset_records(
        evidence,
        "android_screenshots",
        failures,
        predicate=lambda record: (
            "path_required"
            if not isinstance(record.get("path"), str) or not record["path"]
            else "sha256_required"
            if not _sha256_valid(record.get("sha256"))
            else None
        ),
    )
    approvals = _exact_asset_records(
        evidence,
        "art_approvals",
        failures,
        predicate=lambda record: (
            "approved_required"
            if record.get("approved") is not True
            else "human_reviewer_required"
            if record.get("reviewer") != "human"
            else "criteria_required"
            if not isinstance(record.get("criteria"), dict) or not record["criteria"]
            else None
        ),
    )

    failures = sorted(set(failures))
    approved_assets = sorted(
        record["asset_id"]
        for record in approvals
        if record.get("asset_id") in ASSET_IDS and record.get("approved") is True and record.get("reviewer") == "human"
    )
    return {
        "mass_regeneration_allowed": not failures,
        "approved_assets": approved_assets if not failures else [],
        "expected_assets": sorted(ASSET_IDS),
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    if not isinstance(evidence, dict):
        raise ValueError("evidence root must be a JSON object")
    result = evaluate_evidence(evidence)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if result["mass_regeneration_allowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
