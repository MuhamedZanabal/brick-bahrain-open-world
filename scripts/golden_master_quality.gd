class_name GoldenMasterQuality
extends RefCounted

const VALID_PROFILES: PackedStringArray = PackedStringArray(["low", "balanced", "high"])


static func normalize_profile(requested: String) -> String:
	var normalized := requested.strip_edges().to_lower()
	if VALID_PROFILES.has(normalized):
		return normalized
	return "balanced"


static func select_lod(
	distance_m: float,
	current_lod: int,
	lod0_max_m: float,
	lod1_max_m: float,
	hysteresis_m: float
) -> int:
	var distance := maxf(distance_m, 0.0)
	var current := clampi(current_lod, 0, 2)
	var lod0_limit := maxf(lod0_max_m, 0.01)
	var lod1_limit := maxf(lod1_max_m, lod0_limit + 0.01)
	var hysteresis := maxf(hysteresis_m, 0.0)

	match current:
		0:
			if distance > lod1_limit + hysteresis:
				return 2
			if distance > lod0_limit + hysteresis:
				return 1
		1:
			if distance < lod0_limit - hysteresis:
				return 0
			if distance > lod1_limit + hysteresis:
				return 2
		2:
			if distance < lod0_limit - hysteresis:
				return 0
			if distance < lod1_limit - hysteresis:
				return 1

	return current
