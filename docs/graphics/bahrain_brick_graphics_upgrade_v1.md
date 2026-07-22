# BAHRAIN BRICK GRAPHICS UPGRADE SPECIFICATION v1.0

Target: Godot Android  
Repository: `MuhamedZanabal/brick-bahrain-open-world`  
Implementation branch: `work/bahrain-brick-graphics-upgrade-v1`  
Parent authority: PR #59 at `5b4e2466ef84f3984f3bf336b31925d4d2e97a7f`  
Authority rule: PR #59 remains unchanged, draft, open, and unmerged.

## 1. Objective

Upgrade the existing compact Manama Souq vertical slice into an original, premium, mobile-readable Bahrain construction-toy experience while preserving gameplay, touch controls, mission transitions, vehicle behaviour, validated asset authority, and Android QA contracts.

The visual target is:

**Original construction-toy Bahrain + premium mobile open-world interface + warm Gulf cinematic lighting + recognisable Manama architecture + readable arcade gameplay.**

Reference concept screens are aspirational key art. They define art direction, composition, colour, readability, brand identity, and perceived polish. They do not require every visible brick, reflection, building, NPC, shadow, or light to be rendered dynamically on Android.

## 2. Current State

The frozen PR #59 vertical slice provides:

- a deterministic 220 × 220-metre Manama Souq district;
- café, souq, vehicle-route, and waterfront zones;
- existing player and touch controls;
- one mission vehicle;
- 12 pedestrians and 6 traffic vehicles;
- the Karak Delivery mission and replay flow;
- an objective HUD;
- Android source/export QA infrastructure;
- a validated authority of 436 GLB assets;
- a 1920 × 1080 landscape design resolution.

Current presentation is dominated by procedural runtime construction, colour-only materials, simple geometry, limited shadows, runtime-built splash/menu UI, and a functional but minimal mission HUD.

## 3. Constraints and Frozen Boundaries

### 3.1 Renderer qualification gate

`project.godot` forces GL Compatibility for desktop and mobile, while the accepted PR #59 design requires Mobile Vulkan Android evidence. No large visual implementation may begin until evidence resolves:

1. the authoritative production renderer;
2. target-device and driver support;
3. single-path versus dual-path implementation;
4. compatibility fallbacks for effects and materials.

### 3.2 Gameplay boundary

The graphics program must not alter:

- protected touch-control semantics;
- player movement behaviour;
- vehicle physics or entry/exit relationships;
- Karak Delivery state transitions;
- mission/HUD public integration contracts;
- protected regression thresholds or allowlists;
- validated asset authority without explicit evidence;
- PR #59.

New work composes around these systems.

### 3.3 Original identity and rights

The final game must use a proprietary Bahrain Brick construction-toy aesthetic. It must not ship copied minifigure proportions, third-party toy logos, trademarked markings, recognisable protected connector geometry, reference-image assets, or unlicensed fonts, textures, models, music, logos, or icons.

Characters, bricks, vehicles, faces, connectors, proportions, branding, and interface artwork must be original and provenance-recorded.

## 4. Selected Delivery Strategy

The selected approach is a staged hybrid upgrade:

1. establish authority, renderer policy, baselines, and risk controls;
2. build a reusable UI design system;
3. upgrade splash, loading, menu, character selection, pause, settings, and HUD;
4. upgrade lighting, sky, roads, water, and shared materials;
5. improve the most visible environment assets and skyline composition;
6. add original character and vehicle presentation;
7. optimise and validate on Android after every visual batch.

A simultaneous full rebuild is rejected because it maximises regression risk and prevents useful Android profiling isolation. A UI-only reskin is rejected because it leaves gameplay presentation materially below the target.

## 5. Visual Pillars

### P1 — Recognisable Bahrain

Every hero composition should contain at least two identifiers such as a Bahrain World Trade Center-inspired silhouette, Manama waterfront, traditional fort architecture, Bahrain flags, bilingual signage, souq storefront rhythm, palms, or Gulf road markings.

### P2 — Construction-toy coherence

Major assets share simplified geometry, controlled bevels, intentional modular seams, consistent scale language, strong mobile-distance silhouettes, and coherent plastic, metal, stone, glass, fabric, road, and water materials.

### P3 — Warm cinematic contrast

Primary contrast uses warm gold sunlight, cool cyan sky and glass, Bahrain red accents, dark charcoal framing, white typography, and selective semantic action colours.

### P4 — Mobile readability

No essential text may fall below approved minimum size. Interaction cannot depend only on colour. Critical panels cannot disappear over bright scenery. Touch targets must be at least 48 logical pixels and remain outside unsafe cutout regions.

### P5 — Original premium branding

Canonical visible name: **BAHRAIN BRICK**.

Legacy package identifiers may remain during compatibility migration, but visible titles must not alternate among previous naming variants.

## 6. UI Design System

### 6.1 Layout

Primary authored layout: 1920 × 1080 landscape. Supported: 16:9, 18:9, 19.5:9, 20:9, and tablet landscape. Use anchors, containers, safe-area containers, and focus navigation rather than manual viewport coordinates.

### 6.2 Tokens

Centralise exact values in a shared theme/config resource:

- `BB_RED`: logo, danger, Bahrain identity;
- `BB_GOLD`: rewards, selected states, premium framing;
- `BB_GREEN`: primary play/confirm;
- `BB_BLUE`: multiplayer/navigation;
- `BB_ORANGE`: character selection/progression;
- `BB_PURPLE`: missions/special actions;
- `BB_CYAN`: credits/information/skyline highlights;
- `BB_CHARCOAL`: panels/framing;
- `BB_WHITE`: primary text;
- `BB_MUTED`: secondary text;
- `BB_ERROR`: failure/destructive actions.

### 6.3 Typography

Use a licensed heavy display family and a licensed readable Latin/Arabic interface family with complete Arabic glyph coverage, clear numerals, medium/bold weights, and recorded redistribution rights.

### 6.4 Components

Panels use 12–20-pixel baseline corner radii, dark translucent bodies, thin gold or semantic outlines, shallow highlights, soft shadows, and explicit normal/hover/focus/pressed/disabled states.

Buttons use a consistent icon family, minimum 48-pixel interaction height, semantic action colour, physical-depth treatment, and press feedback.

One original icon family covers play, character, multiplayer, mission, settings, credits, exit, pause, health, stamina, currencies, location, vehicle, interaction, jump, attack/use, inventory, audio, graphics, privacy, and support.

## 7. Screen Specifications

### 7.1 Startup sequence

`Zanabal Gaming → Mansoory Games → Bahrain Brick loading → Main menu`

Each studio splash uses original full-screen artwork, a 1.5–2.5-second minimum, fade in/hold/fade out, permitted skip after minimum display, no fake progress, and no active controls behind it.

### 7.2 Main menu

Composition uses dominant BAHRAIN BRICK branding, hero character/vehicle background, right-side action rail, profile/currency, and approved community links.

Required actions:

1. Play
2. Character Select
3. Multiplayer
4. Missions
5. Settings
6. Credits
7. Exit

Unavailable features display an explicit unavailable state such as `Coming Soon` rather than opening a broken path. Touch, keyboard, mouse, and controller focus must work at all supported ratios.

### 7.3 Character selection

Use one lightweight 3D presentation stage with three pedestals and persisted selection through `SaveManager`.

Initial archetypes:

- Pearl Diver — cyan, black, silver;
- Street Racer — red, black, blue;
- Sky Pilot — white, black, gold.

Selected state uses elevation/illumination, gold outline, card emphasis, and a short idle animation. Locked characters show explicit unlock criteria.

### 7.4 Loading

Replace simulated timing with actual threaded world-load progress. Required states: Preparing world, Loading district, Loading characters, Preparing gameplay, Ready, and Failure. Failure provides meaningful error, retry, return to menu, and QA diagnostic code.

### 7.5 Pause and settings

Pause uses a left action rail, right settings panel, dimmed gameplay, and optional qualified blur.

Tabs include Graphics, Controls, and Audio. Graphics covers quality preset, render scale, brightness, FOV, shadow quality, effects quality, and frame-rate target. Gameplay covers invert Y, camera shake, auto-jump, and tutorial hints. Settings persist and apply safely at runtime.

### 7.6 HUD

The premium HUD uses safe-area composition:

- top-left player identity, level, health, stamina/energy;
- top-right currency, minimap, district, environment/time state;
- right-middle mission title, objective, distance, icon, collapse state;
- bottom-left protected virtual movement control;
- bottom-centre inventory quick bar;
- bottom-right contextual interaction, vehicle, jump, attack/use, and driving controls.

Do not show every action simultaneously. Preserve mission binding, objective updates, status messages, replay signal, mission-state integration, and protected touch semantics.

## 8. World Graphics

The authoritative four-zone district remains unchanged in function:

1. Karak café start court;
2. covered souq retail lane;
3. main road and vehicle pickup;
4. waterfront delivery court.

Each zone receives distinct visual identity while preserving deterministic placement and collision.

Skyline composition uses three layers: playable foreground, reduced-geometry midground landmarks, and low-cost background skyline representation with atmospheric colour.

Roads migrate from plain boxes to instanced modular straights, curves, intersections, lane overlays, shoulders, curbs, sidewalks, drainage, crosswalks, and parking bays using shared atlases.

Brick detail follows distance:

| Distance | Detail policy |
|---|---|
| 0–8 m | selective physical studs, bevels, seams |
| 8–30 m | clustered geometry and normal detail |
| 30–80 m | simplified silhouette and baked detail |
| 80 m+ | landmark proxy or skyline representation |

## 9. Materials, Shaders, Lighting, and Camera

Shared material families:

`BB_MAT_BrickPlastic`, `BB_MAT_PaintedMetal`, `BB_MAT_Stone`, `BB_MAT_AsphaltDry`, `BB_MAT_AsphaltWet`, `BB_MAT_Sidewalk`, `BB_MAT_Glass`, `BB_MAT_Water`, `BB_MAT_Fabric`, `BB_MAT_EmissiveSign`, `BB_MAT_Character`, `BB_MAT_Vehicle`.

Wet asphalt uses darker albedo, lower roughness, static environment contribution, puddle mask, subtle normal variation, and an optional high-tier highlight. It must not require real-time screen-space reflections.

Glass uses transparent hero windows and opaque/dithered distant substitutes. Water uses animated normals, gradient, sun highlight, distance fade, and no default full planar reflection.

The first production state is fixed late afternoon. Use one shadow-casting sun, environment/ambient contribution, selective static/local lights, restrained fog and colour grading, optional subtle bloom, no strong gameplay depth of field, and no constant motion blur.

On-foot and vehicle camera tuning may change presentation, FOV, collision, and limited speed pullback without changing gameplay movement or vehicle physics.

## 10. Original Characters and Vehicles

Create an original modular construction-character system with proprietary proportions, original hands/connectors, shared skeleton/material atlas, three hero characters, at least 12 NPC combinations, and LODs.

Hero vehicle presentation includes an original red sports car, white utility SUV, and yellow taxi/support family. Visual shells, panels, wheels, glass, lights, and LODs may change; physics and controller behaviour remain unchanged.

## 11. Android Profiles and Budgets

### Low

Compatibility-safe path, 0.65–0.75 render scale, reduced shadows, simplified water, minimal particles, reduced visual density, skyline card.

### Medium

0.80–0.90 render scale, one sun shadow, basic wet road, standard water, moderate particles, standard LODs.

### High

1.0 render scale where sustainable, improved shadow filtering/water, subtle bloom, denser props, improved landmark LOD.

### Ultra

Qualified-device allowlist only. Increased shadows/LOD/effects and optional pause blur. Never required for standard acceptance.

Standard performance target:

- sustained 30 FPS;
- total frame time ≤ 33.3 ms;
- no repeated spikes above 100 ms;
- no thermal collapse in 30-minute soak.

Initial scene budgets:

- visible triangles ≤ 1.2 million;
- opaque draw calls ≤ 450;
- transparent draw calls ≤ 40;
- shadow-casting local lights 0–2;
- visible skinned characters 12;
- unique visible material families ≤ 40;
- zero uncompressed 4K gameplay textures.

## 12. Repository Architecture

Planned additions:

```text
docs/graphics/
assets/ui/premium_v1/
assets/materials/premium_v1/
assets/environment/premium_v1/
assets/characters/premium_v1/
assets/vehicles/premium_v1/
scenes/ui/
scenes/ui/components/
scripts/ui/
scripts/graphics/
themes/
shaders/
tests/graphics/
tools/graphics/
```

Architecture rules:

- presentational scenes use containers and anchors;
- design tokens are centralised;
- UI scripts handle behaviour, not pixel-by-pixel construction;
- materials are shared;
- quality settings are data-driven;
- graphics changes require visual and performance evidence;
- gameplay APIs remain stable.

## 13. Phase and Gate Structure

| Phase | ID range | Scope | Gate |
|---|---|---|---|
| G0 | GFX-000–015 | authority, baseline, protected hashes, renderer qualification, device tiers, provenance, CI | Authority immutable; renderer resolved; baseline evidence exists; protected tests pass; provenance policy exists. |
| G1 | GFX-020–043 | art bible, canonical brand, colour/typography/spacing tokens, theme, components, icons, atlas | One test scene proves fonts, states, panels, icons, Arabic/English, 16:9 and 20:9. |
| G2 | GFX-050–088 | studio splash, actual-progress loading, premium main menu | Deterministic startup, actual progress, correct actions, unavailable-state handling, touch/aspect pass. |
| G3 | GFX-090–125 | character selection, pause, settings, persistence | Selection applies to spawn; settings persist/apply safely; Android pause/resume passes. |
| G4 | GFX-130–159 | premium HUD and contextual controls | Complete Karak Delivery mission passes with protected controls unchanged. |
| G5 | GFX-160–178 | environment resource, sky, sun, atmosphere, quality profiles, camera | Renderer-specific visual and effect-cost evidence passes. |
| G6 | GFX-180–224 | shared materials, roads, water, skyline, architecture, props, signage, LOD/instancing | Full mission path upgraded; collision/resources correct; standard Android profile within budget. |
| G7 | GFX-230–248 | original hero/NPC characters and vehicle presentation | Animation/skeleton/LOD cost acceptable; vehicle physics unchanged. |
| G8 | GFX-250–262 | VFX, transitions, mission presentation, reduced motion | No effect obscures controls/objectives. |
| G9 | GFX-270–293 | audits, compression, batching, LOD, profiling, traversal, soak | Minimum device meets performance, memory, thermal, crash/ANR/shader gates. |
| G10 | GFX-300–321 | inherited tests, flows, aspect/language/device QA, APK, hashes, evidence, variance report | Release and evidence inventory complete; PR #59 unchanged. |

A failed authority, renderer, import, protected-control, or performance gate blocks cosmetic progression.

## 14. Pull Request Sequence

| PR | Scope |
|---|---|
| GFX-PR1 | Authority, renderer qualification, baseline |
| GFX-PR2 | Design system and shared UI components |
| GFX-PR3 | Splash, loading, main menu |
| GFX-PR4 | Character select and pause/settings |
| GFX-PR5 | Premium HUD |
| GFX-PR6 | Lighting, sky, camera, quality profiles |
| GFX-PR7 | Materials, roads, water, skyline |
| GFX-PR8 | Architecture, props, signage, palms |
| GFX-PR9 | Characters and vehicles |
| GFX-PR10 | VFX, Android optimisation, evidence |

Every PR remains draft until its own acceptance gate passes.

## 15. Measurable Completion Output

The program is complete only when it produces:

- one locked Bahrain Brick art bible;
- one original UI design system;
- two studio splash screens;
- one actual-progress loading screen;
- one premium main menu;
- one functional three-character selection screen;
- one premium pause/settings system;
- one responsive gameplay HUD;
- one upgraded late-afternoon rendering profile;
- one modular road/sidewalk kit;
- one waterfront/skyline presentation;
- one shared mobile material library;
- three original hero characters;
- twelve modular NPC combinations;
- three upgraded vehicle families;
- four Android graphics presets;
- one signed QA APK;
- one five-minute traversal recording;
- one thirty-minute soak report;
- one performance/memory report;
- one provenance manifest;
- one SHA-256 evidence inventory;
- zero modifications to frozen PR #59.

## Current Execution Rule

Begin with G0 only. Do not generate or ingest large asset batches and do not start cosmetic implementation until the renderer discrepancy, engine authority, baseline performance, protected hashes, and Android device matrix are resolved with direct evidence.
