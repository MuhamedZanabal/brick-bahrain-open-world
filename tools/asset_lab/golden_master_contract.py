#!/usr/bin/env python3
"""Contract validation and release gating for Bahrain Brick golden masters."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EXPECTED_IDS = {
    "bh_traditional_projecting_window_01",
    "bh_souq_shop_gold_01",
    "bh_waterfront_tower_a_01",
    "bh_supermarket_storefront_a_01",
    "bh_cr_skyscraper_tower_01",
}
EXPECTED_PROFILES = ["low", "balanced", "high"]
EXPECTED_LODS = [0, 1, 2]
REQUIRED_VISUAL_CRITERIA = {
    "bahrain_identity",
    "primary_silhouette",
    "facade_depth",
    "material_control",
    "adjacent_variation",
    "scale_consistency",
    "uv_integrity",
    "lod_integrity",
}
REQUIRED_BOOLEAN_EVIDENCE = (
    "technical_pass",
    "protected_authority_pass",
    "godot_import_pass",
    "android_runtime_pass",
)
REQUIRED_ASSET_EVIDENCE = (
    "balanced_lod0_contact_sheets",
    "android_screenshots",
    "approved_assets",
)


def load_contract(path: Path) -> dict[str, Any]:
    """Load a UTF-8 JSON contract and require an object at the root."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("golden-master contract root must be a JSON object")
    return data


def validate_contract(contract: dict[str, Any]) -> list[str]:
    """Return deterministic validation failures; an empty list is a valid contract."""
    failures: list[str] = []
    if contract.get("schema_version") != 1:
        failures.append("schema_version:expected_1")
    if contract.get("quality_profiles") != EXPECTED_PROFILES:
        failures.append("quality_profiles:expected_low_balanced_high")
    if contract.get("lod_levels") != EXPECTED_LODS:
        failures.append("lod_levels:expected_0_1_2")
    if contract.get("expected_derivative_count") != 45:
        failures.append("expected_derivative_count:expected_45")
    if contract.get("mass_regeneration_default") is not False:
        failures.append("mass_regeneration_default:must_be_false")

    records = contract.get("golden_masters")
    if not isinstance(records, list):
        return failures + ["golden_masters:expected_list"]
    if len(records) != 5:
        failures.append(f"golden_masters:expected_5:actual_{len(records)}")

    ids: list[str] = []
    seeds: list[int] = []
    for index, record in enumerate(records):
        prefix = f"golden_masters[{index}]"
        if not isinstance(record, dict):
            failures.append(f"{prefix}:expected_object")
            continue
        asset_id = record.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id:
            failures.append(f"{prefix}.asset_id:required")
        else:
            ids.append(asset_id)
        if not isinstance(record.get("family"), str) or not record["family"].strip():
            failures.append(f"{prefix}.family:required")
        if not isinstance(record.get("visual_role"), str) or not record["visual_role"].strip():
            failures.append(f"{prefix}.visual_role:required")
        if record.get("profiles") != EXPECTED_PROFILES:
            failures.append(f"{prefix}.profiles:invalid")
        if record.get("lod_levels") != EXPECTED_LODS:
            failures.append(f"{prefix}.lod_levels:invalid")
        seed = record.get("seed")
        if not isinstance(seed, int) or isinstance(seed, bool) or seed <= 0:
            failures.append(f"{prefix}.seed:positive_integer_required")
        else:
            seeds.append(seed)
        criteria = record.get("visual_acceptance")
        if not isinstance(criteria, dict):
            failures.append(f"{prefix}.visual_acceptance:expected_object")
        else:
            keys = set(criteria)
            if keys != REQUIRED_VISUAL_CRITERIA:
                failures.append(f"{prefix}.visual_acceptance:criteria_mismatch")
            for key in sorted(REQUIRED_VISUAL_CRITERIA & keys):
                value = criteria[key]
                if not isinstance(value, str) or not value.strip():
                    failures.append(f"{prefix}.visual_acceptance.{key}:required")

    if set(ids) != EXPECTED_IDS:
        failures.append("golden_master_ids:exact_set_mismatch")
    if len(ids) != len(set(ids)):
        failures.append("golden_master_ids:duplicates")
    if len(seeds) != len(set(seeds)):
        failures.append("golden_master_seeds:duplicates")
    return failures


def evaluate_gate(contract: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    """Evaluate whether full 436-GLB regeneration is authorized."""
    failures = [f"contract:{item}" for item in validate_contract(contract)]
    expected_ids = {
        record.get("asset_id")
        for record in contract.get("golden_masters", [])
        if isinstance(record, dict) and isinstance(record.get("asset_id"), str)
    }

    for key in REQUIRED_BOOLEAN_EVIDENCE:
        if evidence.get(key) is not True:
            failures.append(f"evidence:{key}:required_true")

    for key in REQUIRED_ASSET_EVIDENCE:
        supplied = evidence.get(key)
        if not isinstance(supplied, list):
            failures.append(f"evidence:{key}:expected_list")
            continue
        supplied_ids = {value for value in supplied if isinstance(value, str)}
        if supplied_ids != expected_ids or len(supplied) != len(expected_ids):
            failures.append(f"evidence:{key}:exact_asset_coverage_required")

    failures = sorted(set(failures))
    return {
        "mass_regeneration_allowed": not failures,
        "expected_golden_masters": sorted(expected_ids),
        "failures": failures,
    }
