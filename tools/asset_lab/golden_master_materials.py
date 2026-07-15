#!/usr/bin/env python3
"""Deterministic mobile material specifications for Bahrain Brick golden masters."""

from __future__ import annotations

from copy import deepcopy

PROFILE_SETTINGS = {
    "low": {
        "texture_resolution": 256,
        "detail_scale": 0.55,
        "shader_feature_count": 1,
        "features": ["vertex_color"],
    },
    "balanced": {
        "texture_resolution": 512,
        "detail_scale": 1.0,
        "shader_feature_count": 2,
        "features": ["vertex_color", "packed_orm"],
    },
    "high": {
        "texture_resolution": 1024,
        "detail_scale": 1.35,
        "shader_feature_count": 3,
        "features": ["vertex_color", "packed_orm", "detail_normal"],
    },
}

MATERIAL_KEYS = (
    "sand_plaster",
    "limestone",
    "dark_timber",
    "painted_metal",
    "blue_glass",
    "souq_gold",
    "promenade_paving",
    "signage_accent",
)

_BASE_MATERIALS = {
    "sand_plaster": {
        "base_color": [0.82, 0.70, 0.53],
        "roughness": 0.86,
        "metallic": 0.0,
    },
    "limestone": {
        "base_color": [0.66, 0.56, 0.43],
        "roughness": 0.90,
        "metallic": 0.0,
    },
    "dark_timber": {
        "base_color": [0.22, 0.10, 0.05],
        "roughness": 0.72,
        "metallic": 0.0,
    },
    "painted_metal": {
        "base_color": [0.10, 0.11, 0.12],
        "roughness": 0.50,
        "metallic": 0.25,
    },
    "blue_glass": {
        "base_color": [0.08, 0.24, 0.31],
        "roughness": 0.24,
        "metallic": 0.0,
    },
    "souq_gold": {
        "base_color": [0.72, 0.48, 0.08],
        "roughness": 0.38,
        "metallic": 0.55,
    },
    "promenade_paving": {
        "base_color": [0.50, 0.49, 0.46],
        "roughness": 0.92,
        "metallic": 0.0,
    },
    "signage_accent": {
        "base_color": [0.58, 0.12, 0.08],
        "roughness": 0.62,
        "metallic": 0.05,
    },
}


def validate_profile_ordering() -> list[str]:
    """Return failures when mobile profile budgets are not monotonically ordered."""
    failures: list[str] = []
    if list(PROFILE_SETTINGS) != ["low", "balanced", "high"]:
        failures.append("profile_order:expected_low_balanced_high")
    for field in ("texture_resolution", "detail_scale"):
        values = [PROFILE_SETTINGS[profile][field] for profile in PROFILE_SETTINGS]
        if not values[0] < values[1] < values[2]:
            failures.append(f"{field}:strict_order_required")
    feature_counts = [PROFILE_SETTINGS[profile]["shader_feature_count"] for profile in PROFILE_SETTINGS]
    if not feature_counts[0] <= feature_counts[1] <= feature_counts[2]:
        failures.append("shader_feature_count:monotonic_order_required")
    for profile, settings in PROFILE_SETTINGS.items():
        if settings["texture_resolution"] not in {256, 512, 1024}:
            failures.append(f"{profile}:unsupported_texture_resolution")
        if len(settings["features"]) > settings["shader_feature_count"]:
            failures.append(f"{profile}:feature_budget_exceeded")
    return failures


def material_spec(profile: str, material_key: str) -> dict[str, object]:
    """Return an independent, profile-specific material specification."""
    if profile not in PROFILE_SETTINGS:
        raise KeyError(f"unknown quality profile: {profile}")
    if material_key not in _BASE_MATERIALS:
        raise KeyError(f"unknown material key: {material_key}")

    settings = PROFILE_SETTINGS[profile]
    spec = deepcopy(_BASE_MATERIALS[material_key])
    spec.update(
        {
            "name": f"bh_gm_{profile}_{material_key}",
            "profile": profile,
            "material_key": material_key,
            "texture_resolution": settings["texture_resolution"],
            "detail_scale": settings["detail_scale"],
            "shader_features": list(settings["features"]),
        }
    )
    return spec
