# Bahrain Brick Asset Pack Option A Design

## Objective

Rebuild the existing Bahrain Brick Asset Lab as a production-ready Android asset pipeline in which 48 core architecture source assets act as artistic golden masters and deterministically generate 432 runtime derivatives across three quality profiles and three LOD levels. Preserve the additional commercial outputs so the final validated production set contains 436 GLBs, integrate the appropriate variants into the real Godot world, and produce an installable, runtime-validated Android APK with complete evidence.

## Authorized Scope

This design implements Option A only.

- Improve the existing 48 architecture source records rather than create 436 independently authored assets.
- Generate three quality profiles: `low`, `balanced`, and `high`.
- Generate three LOD levels: `LOD0`, `LOD1`, and `LOD2`.
- Preserve the existing deterministic output matrix of 432 architecture derivatives.
- Preserve and improve the four separately generated commercial outputs required to reach 436 GLBs.
- Integrate one selected quality profile at runtime and select LOD by distance.
- Package required runtime variants in the Android build without instantiating all 436 simultaneously.
- Keep PR #57 open, draft, and unmerged until every acceptance gate in this document passes.

## Non-Goals

- Do not create 436 unique handcrafted source models.
- Do not expand multiplayer, mission, economy, traffic, or unrelated gameplay systems.
- Do not modify frozen gameplay controls or protected authority functions.
- Do not merge PR #57 automatically.
- Do not claim art completion from structural GLB validation alone.
- Do not add new districts solely to display every generated derivative.

## Authorities and Safety Boundaries

- Game repository: `MuhamedZanabal/brick-bahrain-open-world`.
- Asset repository: `MuhamedZanabal/Bahrain_bricks_Assets`.
- Integration branch: `work/bahrain-brick-asset-lab-integration-v1`.
- Draft PR: `#57`.
- Frozen premium authority: `e26ec912db5c10d071a8e120010bdb5a9a136f17`.
- Current authorized integration lineage begins from corrective head `f2cd112b7d5c5c5fd7c2a92aaf7a2694d56e569e`.
- Existing protected-control checks remain mandatory before and after asset generation, world integration, Android export, and runtime validation.
- Any protected hash mismatch is a hard failure and blocks further integration.

## Production Architecture

### 1. Golden-master layer

The 48 source records remain the canonical semantic asset definitions. Geometry generation must be upgraded from box-dominant blockouts to family-specific procedural construction with authored proportions, silhouette rules, façade depth, trim systems, openings, canopies, screens, railings, signs, roof details, utility details, and Bahrain-specific visual motifs.

Each source record must define:

- Stable asset ID and family.
- Nominal real-world dimensions in metres.
- Visual role and district usage.
- Required silhouette features.
- Material slots from the shared mobile material library.
- Collision policy.
- LOD simplification policy.
- Quality-profile policy.
- Deterministic generation seed.

### 2. Shared material and texture layer

Create a compact mobile material library shared across families. Textures must be generated or project-owned, provenance-recorded, atlas-compatible, and limited to resolutions suitable for Android.

Required material groups:

- Sand plaster.
- Weathered limestone.
- Dark timber.
- Painted metal.
- Blue and neutral glass.
- Souq fabric and awnings.
- Road asphalt and markings.
- Promenade paving.
- Vegetation surfaces.
- Accent signage.

Balanced profile is the visual authority for gameplay review. Low profile reduces texture resolution, material complexity, mesh detail, and shader features. High profile preserves the strongest mobile-safe detail while remaining within the project performance budget.

### 3. Geometry and derivative layer

For each of the 48 source records, generate exactly nine derivatives:

- `low/LOD0`, `low/LOD1`, `low/LOD2`.
- `balanced/LOD0`, `balanced/LOD1`, `balanced/LOD2`.
- `high/LOD0`, `high/LOD1`, `high/LOD2`.

The generator must produce distinct geometry where LOD reduction is meaningful. Renaming or re-exporting identical meshes as separate LODs is prohibited.

LOD policy:

- `LOD0`: close-range gameplay model with complete silhouette and required façade details.
- `LOD1`: medium-range model with reduced secondary detail and preserved primary silhouette.
- `LOD2`: distant model with aggressively reduced geometry, simplified materials, and preserved recognizable massing.

Each derivative must include deterministic metadata recording source asset ID, quality profile, LOD level, generator version, seed, triangle count, material count, collision status, and SHA-256.

### 4. Runtime selection layer

Replace the current fixed `balanced` and `LOD0` runtime behavior with a dedicated controller.

The controller must:

- Select `low`, `balanced`, or `high` from an explicit project setting and a deterministic device-capability fallback.
- Load only the selected quality profile for normal gameplay.
- Select LOD by camera distance using family-appropriate thresholds.
- Apply hysteresis to prevent rapid LOD oscillation.
- Preserve district placement and protected gameplay behavior.
- Log the active quality profile and LOD transitions in QA builds.
- Fail visibly in CI when a manifest entry references a missing resource.

### 5. Godot integration layer

The runtime manifest becomes the single authority mapping source asset IDs to profile and LOD paths. Godot integration must use the manifest rather than hardcoded parallel arrays.

The integration must cover:

- Villas.
- Traditional architecture.
- Souq architecture.
- Waterfront architecture.
- Roads and sidewalks.
- Street props.
- Commercial modules.
- Existing clean-room vegetation, vehicle, road, shader, and supporting assets where their provenance and runtime status permit use.

The world must display representative assets in coherent district compositions rather than a diagnostic grid. Asset placement must support walkable and drivable gameplay and must not overlap the player spawn, navigation-critical paths, or vehicle routes.

## Batch Execution and Gates

### Batch 1: Five golden masters

Produce one approved representative from each highest-impact family:

1. Traditional Bahrain building module.
2. Manama Souq storefront.
3. Waterfront module.
4. Commercial storefront.
5. Hero Bahrain landmark or skyline element.

Batch 1 passes only when each asset has:

- Approved silhouette and Bahrain-specific details.
- Shared mobile materials and UVs.
- Genuine LOD0, LOD1, and LOD2 meshes.
- Low, balanced, and high profiles.
- Collision appropriate to use.
- Successful Blender generation and GLB validation.
- Successful Godot import.
- Visible Android runtime screenshot from the real game world.
- No protected-authority mutation.

Mass regeneration is blocked until Batch 1 passes.

### Batch 2: Traditional and souq families

Upgrade and regenerate all traditional and souq source records using the approved golden-master language. Review for repetition, storefront identity, alley readability, signage variation, and mobile cost.

### Batch 3: Waterfront and commercial families

Upgrade and regenerate waterfront and commercial source records. Preserve skyline readability, promenade modularity, shop readability, and mobile-safe glass and lighting behavior.

### Batch 4: Supporting runtime families

Complete integration-quality roads, sidewalks, street props, vegetation, vehicle, clean-room supporting assets, and the shared mobile shader. Existing valid assets may be preserved when they pass the new visual, provenance, and runtime gates.

### Batch 5: Full matrix generation

Generate all 432 architecture derivatives and the four separately counted commercial outputs. The final production matrix must contain exactly 436 GLBs with no duplicates by path and no missing expected outputs.

### Batch 6: Runtime integration and APK validation

Integrate the manifest-driven quality and LOD system, export the Android APK, install it in the API 34 emulator, launch in landscape, traverse the representative world route, capture screenshots and logs, and package the final evidence.

## Quality Standards

### Visual acceptance

An asset is not art-approved merely because it is valid GLB geometry.

Family review must confirm:

- Recognizable Bahrain or Gulf-region architectural language.
- Strong primary silhouette at gameplay distance.
- Sufficient façade depth to avoid cardboard-flat appearance.
- Controlled material variation without random visual noise.
- Reduced repetition when multiple modules are adjacent.
- Consistent scale and proportions.
- No visible UV stretching in the balanced profile.
- No obvious LOD collapse, holes, floating parts, or silhouette inversion.

### Technical acceptance

Every GLB must pass:

- Deterministic generation from the recorded seed.
- Structural validator.
- Khronos glTF validation.
- Godot import.
- Triangle and material budget validation.
- Collision validation where required.
- Manifest path and checksum validation.
- Duplicate-output detection.

### Android acceptance

The APK must:

- Export successfully using the pinned Godot and Android toolchain.
- Install successfully on the API 34 emulator.
- Launch the expected package and activity.
- Enter landscape gameplay.
- Load the selected quality profile.
- Render representative assets from each required family.
- Complete the fixed traversal without a critical error.
- Produce runtime logs, screenshots, package metadata, APK SHA-256, and an evidence inventory.

The emulator workflow must implement bounded stage-specific timeouts and diagnostics so a single 65-minute opaque timeout cannot recur without identifying the stalled stage.

## Testing Strategy

Development follows test-first changes.

Required automated coverage:

- Manifest record count and family distribution.
- Exact derivative matrix count of 432.
- Exact final GLB count of 436.
- Profile and LOD path uniqueness.
- Deterministic output hashes for unchanged inputs.
- LOD triangle monotonicity: `LOD0 >= LOD1 >= LOD2`.
- Low-profile resource cost not exceeding balanced; balanced not exceeding high for the defined metrics.
- Required collision presence.
- Material-library path validity.
- Runtime manifest completeness.
- Quality-profile selection.
- LOD threshold and hysteresis behavior.
- Godot resource loading.
- Protected-control pre-test and post-test hashes.
- APK export, signing, install, launch, orientation, and runtime marker checks.

## Failure Handling

- A golden-master visual failure blocks family scaling.
- A structural or Khronos failure blocks Godot import.
- A Godot import failure blocks world integration.
- A protected-authority mismatch blocks all writes and APK production.
- A missing runtime asset is a CI failure, not a warning-only release condition.
- An emulator timeout must emit the current stage, process list, emulator state, ADB state, logcat tail, and produced artifacts before failure.
- Failed outputs remain evidence; they must not be labeled released or complete.

## Evidence Package

The final workflow artifact must contain:

- All 436 GLBs or a checksum-addressed package containing them.
- Source-to-derivative manifest.
- Generator versions and seeds.
- Triangle, material, texture, collision, and LOD reports.
- Structural and Khronos validation reports.
- Godot import report.
- Runtime manifest.
- Protected-authority pre/post reports.
- APK and APK SHA-256.
- Package metadata.
- Emulator installation and launch evidence.
- Landscape gameplay screenshots.
- Fixed-route runtime log.
- Critical-error scan.
- Final evidence inventory with SHA-256 for each file.

## Completion Criteria

Option A is complete only when all conditions below are simultaneously true:

1. Exactly 48 core architecture records remain authoritative.
2. Exactly 432 architecture derivatives are generated from those records.
3. The final expected production matrix contains exactly 436 GLBs.
4. Every required GLB passes structural and Khronos validation.
5. Every runtime-required asset imports into Godot.
6. Five golden masters have documented visual and Android approval.
7. Required families are integrated into coherent game-world districts.
8. Runtime quality selection and distance-based LOD switching operate correctly.
9. The Android APK exports, installs, launches, and enters landscape gameplay.
10. The fixed runtime traversal completes without critical errors.
11. Protected gameplay authorities remain byte-identical to their expected values.
12. The complete evidence package is uploaded and its checksums are recorded.
13. PR #57 remains draft and unmerged pending explicit user authorization.

## Design Decision

Proceed with the generator-first rebuild. Artistic effort is concentrated in the 48 canonical source assets and shared materials. The 436 production GLBs are deterministic runtime derivatives and separately counted commercial outputs, not 436 independent handcrafted models. This preserves scope, improves visual quality, enables Android optimization, and converts the existing Asset Lab work into a releasable game build.