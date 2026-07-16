# Asset Lab Proposed Destination Map

This map is the integration target. It does not represent completed runtime integration.

| Records | Count | Source family | Intended game destination | Real game target |
|---|---:|---|---|---|
| Villa architecture | 18 | `villa_kit.md`, villa concept, villa generator | `assets/environment/architecture/villas/` | `world.tscn/AssetLab/VillaDistrict` |
| Traditional architecture | 14 | `traditional_kit.md`, traditional concept | `assets/environment/architecture/traditional/` | `world.tscn/AssetLab/TraditionalDistrict` |
| Souq architecture and props | 18 | `souq_kit.md`, souq concept | `assets/environment/architecture/souq/` | `world.tscn/AssetLab/SouqDistrict` |
| Waterfront architecture | 16 | `waterfront_kit.md`, waterfront concept and generator | `assets/environment/architecture/waterfront/` | `world.tscn/AssetLab/WaterfrontDistrict` |
| Roads and road geometry | 13 | road, intersection, highway, sidewalk and drainage generators/specs | `assets/environment/roads/` | `hero_district_builder.gd::road_network` |
| Street props | 6 | bollard, lamp, signal, barrier, shelter and sign generators | `assets/props/street/` | `hero_district_builder.gd::street_prop_spawner` |
| Commercial architecture/props | 5 | supermarket/cafe specs and generators | `assets/environment/architecture/{supermarket,restaurant}/`, `assets/props/commercial/` | `world.tscn/AssetLab/CommercialDistrict` |
| Quarantined inherited groups | 8 | third-party audit records | no runtime destination | source-authority quarantine only |

## Supporting production records

- Exact Git history locator: `asset_lab/source_authority/`
- Manifest accounting and checkpoint reports: `docs/asset_lab/`
- Quarantined records cannot enter runtime until license and provenance are resolved.
- Existing functional gameplay systems remain in place; asset integration must wrap around protected controls.

## Runtime placement principles

- Assets must be distributed by district; no single showcase dump.
- Every runtime GLB requires a scene/node usage reference and profile-specific visibility/LOD rule.
- Existing premium and Asset Lab equivalents require quality and Android-performance comparison before replacement.
