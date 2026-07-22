# Bahrain Brick Graphics Upgrade v1 — G0 Authority and Baseline

Recorded: 2026-07-22  
Repository: `MuhamedZanabal/brick-bahrain-open-world`  
Child branch: `work/bahrain-brick-graphics-upgrade-v1`

## Current State

PR #59 is the frozen parent authority for this graphics program.

| Field | Verified value |
|---|---|
| PR | `#59` |
| State | open |
| Draft | yes |
| Merged | no |
| Base branch | `work/bahrain-brick-asset-lab-integration-v1` |
| Base SHA | `fc8f00182f97c39015610d6603fa7c9c44364c5d` |
| Head branch | `work/bahrain-brick-manama-souq-vertical-slice-v1` |
| Head SHA | `5b4e2466ef84f3984f3bf336b31925d4d2e97a7f` |
| Commits | 99 |
| Changed files | 54 |
| Additions / deletions | 8,821 / 0 |

The child branch was created directly from the exact frozen PR #59 head before any graphics-program commits.

## Verified Project Baseline

- Godot configuration version: 5.
- Godot feature declaration: `4.3`, `Forward Plus`.
- Godot toolchain authority: `4.3.stable.official.77dcf97d8`.
- Visible project title: `Brick Bahrain: Open World`.
- Startup scene: `res://scenes/splash_screen.tscn`.
- Authored resolution: 1920 × 1080 landscape.
- Stretch mode: `canvas_items`; aspect: `expand`.
- Desktop renderer forced to `gl_compatibility`.
- Mobile renderer forced to `gl_compatibility`.
- Android export includes ARMv7, ARM64, and x86_64.
- Android export is immersive and declares network-state and internet permissions.
- Validated asset authority: 436 GLBs.
- Deterministic Manama Souq layout: 220 × 220 metres, seed 1409, balanced profile.
- Runtime population authority: 12 pedestrians and 6 traffic vehicles.
- Karak Delivery authority: 300-second mission, 250-coin reward.

## Renderer Authority Conflict

The conflict is confirmed and remains unresolved:

1. `project.godot` forces GL Compatibility for desktop and mobile.
2. The accepted PR #59 design requires Android evidence using the Mobile Vulkan renderer.
3. No workflow run or combined CI status is attached to frozen head `5b4e2466…`.
4. No same-scene renderer comparison, physical-device matrix, or effect-by-effect frame-cost evidence is currently attached to this graphics branch.

**Decision:** no renderer is selected by G0 yet. No large visual implementation, shader library, or asset batch may proceed until the qualification matrix passes.

## Protected Authority

The byte-authoritative protected set is stored in `authority/bahrain_brick_graphics_upgrade_v1.json` and enforced by `tests/graphics/test_graphics_upgrade_g0_contract.py`.

Protected domains:

- virtual joystick and touch input;
- player movement;
- protected mobile input test scenes and scripts;
- vehicle behaviour and player/vehicle relationships;
- Karak Delivery mission transitions and HUD integration;
- existing regression thresholds and allowlists;
- validated 436-GLB asset authority;
- PR #59 state and head.

### Authority inconsistency G0-AUTH-001

The accepted vertical-slice design identifies `scripts/world.gd::_exit_tree` as a frozen function authority. The symbol was not found in the inspected PR #59 head source ranges. Until reconstructed-source evidence resolves this discrepancy, the entire `scripts/world.gd` file is treated as protected from graphics-program edits.

## UI and Presentation Inventory

### Verified startup and menu implementation

- `scenes/splash_screen.tscn` is a scene shell whose UI is built by `scripts/splash_screen.gd`.
- The splash uses `assets/splash_screen.png`, a timed simulated progress bar, manually positioned `ColorRect` and `Label` nodes, and then changes to `scenes/main_menu.tscn`.
- `scenes/main_menu.tscn` is a scene shell whose UI is built by `scripts/main_menu.gd`.
- The menu uses `assets/splash_screen.png`, `assets/app_icon.png`, local colour literals, locally generated `StyleBoxFlat` resources, manual coordinates, and runtime-created controls.
- Current menu branding includes `BRICK BAHRAIN`, `Open World Sandbox`, and `Brick Bahrain: Open World`; visible branding is not canonicalised.
- Current multiplayer actions are presented as enabled navigation paths.
- The vertical slice adds `scenes/karak_delivery_hud.tscn` and `scripts/karak_delivery_hud.gd`.
- `scripts/world.gd` references `scenes/hud.tscn` and constructs a separate runtime loading overlay.

### Verified theme, font, texture, shader, environment, and material state

- No shared premium `Theme` resource is verified in the inspected startup or menu path.
- No licensed Latin/Arabic font authority or licence record is verified in the inspected startup or menu path.
- Verified startup/menu textures: `assets/splash_screen.png`, `assets/app_icon.png`.
- Verified Android launcher textures: `assets/icons/icon_main_192.png`, `assets/icons/icon_adaptive_fg_432.png`, `assets/icons/icon_adaptive_bg_432.png`.
- The current startup and menu scripts duplicate colours, font sizes, spacing, corner radii, and button styles.
- The inspected world code creates `StandardMaterial3D` and light resources procedurally.
- No shared Bahrain Brick material-family library is verified.
- No qualified renderer-specific fallback resource is verified.

This inventory is repository-grounded but not yet a complete tree-wide file census. A full checkout or reconstruction artifact is required before GFX-004 can be marked complete.

## Visible Manama Souq Layout Inventory

The deterministic layout contains **35 placements** across four families and four zones.

| Family | Count | Verified asset IDs |
|---|---:|---|
| Commercial | 4 | `bh_cafe_storefront_karak_a_01`, `bh_cafe_table_chair_set_a_01`, `bh_supermarket_storefront_a_01`, `bh_supermarket_shelf_1m_01` |
| Traditional | 10 | `bh_traditional_party_wall_01`, `bh_traditional_timber_door_01`, `bh_traditional_projecting_window_01`, `bh_traditional_alley_arch_01`, `bh_traditional_parapet_01`, `bh_traditional_courtyard_hint_01`, `bh_traditional_shop_bay_01`, `bh_traditional_shade_canopy_01`, `bh_traditional_traditional_lamp_01`, `bh_traditional_bench_01` |
| Souq | 14 | `bh_souq_shop_gold_01`, `bh_souq_shop_spice_01`, `bh_souq_shop_tailor_01`, `bh_souq_shop_perfume_01`, `bh_souq_shop_electronics_01`, `bh_souq_shop_fabric_01`, `bh_souq_shop_toy_01`, `bh_souq_shop_grocery_01`, `bh_souq_shop_cafe_01`, `bh_souq_shop_bakery_01`, `bh_souq_shop_souvenir_01`, `bh_souq_awning_01`, `bh_souq_covered_passage_01`, `bh_souq_sign_panel_01` |
| Waterfront | 7 | `bh_waterfront_promenade_10m_01`, `bh_waterfront_promenade_20m_01`, `bh_waterfront_marina_edge_01`, `bh_waterfront_railing_01`, `bh_waterfront_bench_01`, `bh_waterfront_cafe_terrace_01`, `bh_waterfront_tower_a_01` |

Zones remain authoritative:

1. `cafe_start`
2. `souq_lane`
3. `vehicle_route`
4. `waterfront_delivery`

## G0 Microtask Status

| ID | State | Evidence / blocker |
|---|---|---|
| GFX-000 | COMPLETED | PR metadata, base/head SHAs, 99 commits, 54 changed files recorded. |
| GFX-001 | COMPLETED | PR #59 re-checked immediately before branch creation. |
| GFX-002 | COMPLETED | Child branch created from exact frozen head. |
| GFX-003 | COMPLETED | Machine-readable protected-file and behaviour contract committed. |
| GFX-004 | IN_PROGRESS | Startup/menu/HUD and inspected resource inventory recorded; full repository census requires a checkout or reconstructed source artifact. |
| GFX-005 | COMPLETED | All 35 deterministic layout placements inventoried by family and asset ID. |
| GFX-006 | BLOCKED | Runtime screenshot capture requires Godot execution and display/device access. |
| GFX-007 | BLOCKED | Frame time, draw calls, triangles, memory, load time, and APK size require runtime and package evidence. |
| GFX-008 | COMPLETED | GL Compatibility versus Mobile Vulkan conflict confirmed. |
| GFX-009 | BLOCKED | Same-scene renderer execution evidence absent. |
| GFX-010 | BLOCKED | Renderer-specific visual/failure comparison absent. |
| GFX-011 | BLOCKED | Authoritative renderer and fallback policy cannot be selected without GFX-009/010 evidence. |
| GFX-012 | COMPLETED (PROVISIONAL) | Tier criteria defined in `docs/graphics/device_matrix.md`; named physical devices remain unassigned. |
| GFX-013 | COMPLETED | Graphics licence and provenance ledger created. |
| GFX-014 | COMPLETED | Originality and no-unlicensed-asset rule recorded as a hard gate. |
| GFX-015 | COMPLETED | Read-only G0 GitHub Actions workflow committed. |

## Gate G0 Result

**FAILED / OPEN.**

Authority preservation controls are established, but the mandatory renderer, baseline capture, performance, and device evidence do not yet exist. Cosmetic phases G1–G10 remain blocked.

## Exact Next Execution Step

Run the deterministic Manama Souq scene under both `gl_compatibility` and `mobile` using the same source, camera, resolution, and quality settings. Capture configuration, screenshots, frame metrics, load metrics, memory, shader/resource diagnostics, and Android device/driver identity. Then select the authoritative renderer and fallback policy from evidence.
