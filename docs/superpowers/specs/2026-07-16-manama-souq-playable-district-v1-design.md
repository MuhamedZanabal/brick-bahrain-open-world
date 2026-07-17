# Bahrain Brick — Manama Souq Playable District V1 Design

## Decision

Proceed with the next product milestone after the verified 436-GLB Asset Lab release gate: one compact, polished, playable Bahrain district built from the existing validated assets.

This milestone is not another asset-generation phase. The generated matrix, manifest, material authority, LOD controller, Android renderer selection, and protected gameplay controls remain frozen unless a test proves a release-blocking defect.

## Authority

- Repository: `MuhamedZanabal/brick-bahrain-open-world`
- Parent authority branch: `work/bahrain-brick-asset-lab-integration-v1`
- Parent authority commit: `fc8f00182f97c39015610d6603fa7c9c44364c5d`
- Isolated implementation branch: `work/bahrain-brick-manama-souq-vertical-slice-v1`
- Frozen premium authority: `e26ec912db5c10d071a8e120010bdb5a9a136f17`
- Asset matrix: 436 textured GLBs, already validated
- Validated QA APK SHA-256: `ba73962adbf28b5ad79be63d40ece9e417fecf2ec7d78b2a80174992cc303d13`
- Parent PR #57 remains draft and unmerged.

## Product Goal

Deliver a five-minute repeatable gameplay loop in a recognizably Bahraini Manama Souq district:

1. Player starts near a karak café.
2. Player walks to the café collection marker.
3. Player collects a sealed karak order.
4. Player enters a nearby drivable sedan.
5. Player drives through the souq route to a waterfront customer.
6. Player exits the vehicle and completes delivery on foot.
7. Mission awards coins and exposes a replay action.

The loop must be understandable without developer instructions, playable with Android touch controls, and stable under automated lifecycle and endurance validation.

## District Scope

### Playable Footprint

- Approximate footprint: 220 m × 220 m.
- Compact enough to keep the five-minute loop dense.
- Four composition zones:
  - Karak café start court.
  - Covered souq retail lane.
  - Main road and vehicle pickup.
  - Waterfront delivery court.
- No open-world expansion outside this footprint in V1.

### Asset Use

Use the verified balanced profile as the default runtime authority.

Required visible families:

- Traditional architecture: at least 8 source records.
- Souq architecture: at least 12 source records.
- Waterfront architecture: at least 5 source records.
- Commercial assets: all 4 records.
- Supporting roads, lamps, palms, barriers, benches, signs, and street props from existing validated authorities.

The scene must select asset paths through the full-matrix manifest or a deterministic layout manifest. It must not hard-code a second competing asset inventory.

### Visual Direction

- Warm late-afternoon Bahrain light.
- Sand, limestone, timber, gold-signage, and muted painted-metal palette.
- Strong pedestrian-scale storefront rhythm.
- Clear road hierarchy and curb separation.
- Waterfront skyline used as a destination landmark, not a dense skyline showcase.
- Mobile-friendly shadows and exposure.
- No claim of photorealism or 1:1 geographic reconstruction.

## Runtime Architecture

### New Scene Layer

Create an isolated vertical-slice entry scene:

- `scenes/manama_souq_vertical_slice.tscn`
- Root script: `scripts/manama_souq_vertical_slice.gd`

The root owns only slice orchestration:

- Deterministic district layout.
- Player and vehicle spawn references.
- Mission-state orchestration.
- Lightweight NPC/traffic spawners.
- Objective HUD hookup.
- Release markers for automated validation.

It must not duplicate movement, vehicle, touch, save, or global game-management logic.

### Deterministic Layout

Create `asset_lab/runtime/manama_souq_layout_v1.json` containing:

- Schema version.
- Exact source authority.
- Required asset IDs.
- Profile policy.
- Positions, rotations, and scales.
- Collision expectation.
- Zone membership.

The loader fails closed when:

- The schema version is unsupported.
- A required asset ID is missing from the full-matrix manifest.
- A path is absent.
- Duplicate placement IDs exist.
- Required zone counts are not met.

### Mission State Machine

Create `scripts/karak_delivery_mission.gd` with explicit states:

- `NOT_STARTED`
- `WALK_TO_CAFE`
- `COLLECT_ORDER`
- `ENTER_VEHICLE`
- `DRIVE_TO_WATERFRONT`
- `EXIT_VEHICLE`
- `DELIVER_ORDER`
- `COMPLETED`
- `FAILED`

The mission must expose:

- `start(player, vehicle)`
- `advance_from_player_position(position)`
- `notify_order_collected()`
- `notify_vehicle_entered(vehicle)`
- `notify_vehicle_exited()`
- `restart()`
- Signals for objective text, state changes, completion, and failure.

No objective may advance twice from the same trigger.

### Vehicle

Use one existing vehicle authority or the existing vehicle factory/controller path. Do not create a new vehicle framework.

Acceptance:

- Vehicle joins the existing `vehicles` group.
- Player can enter and exit through existing interaction controls.
- Vehicle remains inside route bounds during normal scripted traversal.
- Mission detects the actual player vehicle relationship rather than an artificial timer.

### NPC and Traffic Presence

V1 targets presence, not full simulation:

- 12 pedestrians, pooled and deterministic.
- 6 traffic vehicles, lightweight loop routes.
- No advanced crowd AI, combat, wanted system, or multiplayer synchronization in this milestone.
- NPCs and traffic must stop processing outside the compact district bounds.

### HUD

Create a slice-specific objective panel that consumes mission signals:

- Mission title.
- Current objective.
- Distance to target.
- Order possession indicator.
- Completion reward.
- Replay action after completion.

Existing touch controls remain visible and authoritative.

## Protected Boundaries

The following are protected unless a separate explicit authorization is given:

- `scripts/world.gd::_exit_tree` frozen function authority.
- Existing player movement and touch-control semantics.
- Existing regression thresholds and allowlists.
- PR #55 and PR #57 merge states.
- Frozen premium authority branch.
- Existing validated 436-GLB binary outputs.

New code must compose around these authorities.

## Test Strategy

### Source Contract Tests

Verify:

- Layout schema and exact placement IDs.
- Minimum family counts.
- No asset path outside the full-matrix manifest.
- Mission transition table.
- Duplicate-event immunity.
- Required runtime markers.
- Protected files unchanged from parent authority.

### Godot Runtime Tests

Verify headlessly:

- Scene parses and instantiates.
- Required zones exist.
- Required asset count is loaded.
- One player, one mission vehicle, 12 pedestrians, and 6 traffic vehicles exist.
- Mission can be advanced through every state deterministically.
- HUD receives objective and completion signals.
- No missing resources, parse errors, or invalid-node errors.

### Android Gates

Produce a dedicated QA APK that boots directly into the slice while leaving the production startup flow unchanged.

Required Android evidence:

- API 34 AOSP x86_64 emulator.
- Mobile Vulkan renderer.
- Landscape 2400×1080 screenshots.
- Exact readiness marker.
- Exact mission-completion marker.
- Pause/resume pass.
- Cold-start pass.
- Five-minute automated gameplay traversal.
- Thirty-minute soak.
- Bounded memory growth.
- No fatal, ANR, native crash, missing-resource, or shader-limit signature.

## Runtime Markers

The slice must emit exactly once per successful run:

- `BAHRAIN_BRICK_SOUQ_SLICE_READY assets=<n> pedestrians=12 traffic=6`
- `BAHRAIN_BRICK_KARAK_MISSION_STARTED`
- `BAHRAIN_BRICK_KARAK_MISSION_COMPLETED reward=250`

## Acceptance Criteria

The milestone is complete only when all are true:

1. Deterministic 220 m × 220 m district is assembled from validated assets.
2. Walking, vehicle entry/exit, driving, and touch controls remain operational.
3. The Karak Delivery mission completes from start to finish.
4. Twelve pedestrians and six traffic vehicles are visible and bounded.
5. Objective HUD clearly communicates every mission step.
6. Godot import and all inherited regressions pass.
7. Protected authorities remain byte-identical.
8. Signed QA APK installs and launches in landscape on API 34.
9. Automated five-minute gameplay traversal completes the mission.
10. Thirty-minute soak and memory gates pass.
11. APK, SHA-256, screenshots, logs, test reports, and evidence inventory are uploaded.
12. Child PR remains draft and unmerged until explicit release authorization.

## Non-Goals

- Another asset-generation pass.
- 436 simultaneously instantiated GLBs.
- Full Manama city recreation.
- Multiplayer production readiness.
- Combat, wanted system, economy expansion, or property system expansion.
- Final production signing or store publication.
- Merge into the premium authority.
