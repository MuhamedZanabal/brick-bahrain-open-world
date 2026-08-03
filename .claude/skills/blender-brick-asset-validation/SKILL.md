---
name: blender-brick-asset-validation
description: Produce or validate original modular plastic-brick assets in Blender for Bahrain Brick, including geometry, transforms, materials, textures, LODs, provenance, and mobile budgets.
paths:
  - "assets/**/*.blend"
  - "assets/**/*.glb"
  - "assets/**/*.gltf"
  - "asset_lab/**"
allowed-tools:
  - Read
  - Glob
  - Grep
  - mcp__bahrain-brick-local__blender_validate_asset
---

## Originality and licensing

- Create original modular brick language; do not reproduce LEGO/minifigure geometry, trademarks, proprietary pieces, copied game assets, manufacturer logos, or unverified community models.
- Require a provenance record, license classification, source hash, author/tool, and destination for every asset.

## Asset procedure

1. Use metric units and apply rotation/scale before export.
2. Use deterministic `bh_<family>_<asset>_<variant>_<lod>` naming.
3. Keep pivots useful for modular placement and physics.
4. Bound triangle, material, texture, and bone counts for Android.
5. Generate LODs and collision proxies where required; never use render meshes as complex collision by default.
6. Keep textures inside approved repository roots, use compressed formats, and avoid unbounded 4K residency.
7. Export GLB/glTF deterministically and update the authority manifest rather than replacing accepted binaries in place.

## Verification

- Invoke `blender_validate_asset` with the target triangle budget.
- Inspect transform, dimensions, triangle count, materials, texture paths, protected-name findings, and non-manifold warnings.
- Verify Godot import and representative scene rendering before acceptance.
