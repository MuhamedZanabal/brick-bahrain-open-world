# Bahrain Brick Asset Naming and Versioning Contract

Phase 3 establishes the authoritative naming contract for new Bahrain Brick production manifests.

## Asset IDs

New mesh assets use:

`bb_<category>_<family>_<variant>_<nnn>`

The manifest carries `category`, `family`, `variant`, and `serial` separately; validators derive the expected ID from those fields. `family` and `variant` are lowercase snake_case. `serial` is an integer from 1–999 and is rendered as three digits.

Examples:

- `bb_architecture_villa_wall_window_001`
- `bb_roads_kerb_straight_003`
- `bb_props_street_bollard_012`

Repository filenames are lowercase snake_case. The editable source master and primary runtime export basename must match `asset_id` exactly. Derived files use only the controlled suffixes below.

## Derived mesh suffixes

- `_lod0`, `_lod1`, `_lod2` — explicit LOD exports.
- `_col` — collision helper.
- `_occ` — occluder helper.
- `_nav` — navigation helper.
- `_socket` — gameplay socket/helper naming suffix.

## Materials

Materials are reusable resources and do not inherit a mesh asset ID. Material IDs use:

`bb_mat_<family>_<variant>_<nnn>`

A material may be referenced by any number of mesh manifests.

## Textures

Texture resource IDs use:

`bb_tex_<family>_<variant>_<nnn>`

Texture filenames append one semantic role suffix:

- `_albedo`
- `_normal`
- `_orm`
- `_emissive`
- `_opacity`
- `_mask`

The schema caps either texture dimension at 4096 pixels. Category-specific budgets may be lower in later phases; exceeding a lower budget remains a validation failure even when the global structural maximum is not exceeded.

## Versions

Asset and generator versions use SemVer core form `MAJOR.MINOR.PATCH` with non-negative decimal integers and no leading zero padding. Asset content or compatibility changes increment the asset `version`; deterministic generator behavior changes increment the generator `version` independently.

## Legacy compatibility

The July asset-source authority used lowercase `bh_...` identifiers, including `bh_villa_wall_window_01`. Those IDs remain historical aliases only. They are never valid values for the Phase 3 `asset_id` field.

A new manifest may retain one or more old IDs in `legacy_ids` when traceability is required. This is an alias/deprecation bridge, not permission to generate new `bh_...` identifiers, rename historical evidence in place, or break references before a dedicated migration/reference scan.
