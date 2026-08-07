---
name: blender-brick-asset-validation
description: Produce or validate original modular plastic-brick assets in Blender for Bahrain Brick, including geometry, transforms, materials, textures, LODs, provenance, and mobile budgets.
---

## Originality and licensing

- Create an original modular brick language; do not reproduce LEGO or minifigure geometry, trademarks, proprietary pieces, copied game assets, manufacturer logos, or unverified community models.
- Require a provenance record, license classification, source hash, author/tool, and destination for every asset.

## Asset procedure

1. Use metric units and apply rotation and scale before export.
2. Use deterministic `bh_<family>_<asset>_<variant>_<lod>` naming.
3. Keep pivots useful for modular placement and physics.
4. Bound triangle, material, texture, and bone counts for Android.
5. Generate LODs and collision proxies where required; do not use render meshes as complex collision by default.
6. Keep textures inside approved repository roots, use compressed formats, and avoid unbounded 4K residency.
7. Export GLB or glTF deterministically and update the authority manifest rather than replacing accepted binaries in place.

## Verification

- Invoke `blender_validate_asset` with the target triangle budget, through MCP or direct typed CLI.
- Inspect transforms, dimensions, triangle count, materials, texture paths, protected-name findings, and non-manifold warnings.
- Verify Godot import and representative scene rendering before acceptance.
