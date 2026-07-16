# Manama Souq Playable District V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and validate a compact Manama Souq vertical slice with walking, one drivable vehicle, lightweight population, a complete Karak Delivery mission, objective HUD, and a signed Android QA APK.

**Architecture:** Add a deterministic layout manifest and a new isolated scene that composes existing full-matrix assets and protected gameplay controllers. Implement the mission as an explicit state machine, keep population systems lightweight and bounded, and export a QA-only entry scene while preserving the normal product startup path.

**Tech Stack:** Godot 4.3, GDScript, Python 3 contract tests, GitHub Actions, Android API 34, Mobile Vulkan, AOSP x86_64 emulator.

## Global Constraints

- Parent authority is `fc8f00182f97c39015610d6603fa7c9c44364c5d`.
- Frozen premium authority is `e26ec912db5c10d071a8e120010bdb5a9a136f17`.
- Do not merge PR #55, PR #57, or the vertical-slice PR.
- Do not modify protected gameplay-control semantics or weaken tests.
- Reuse the validated 436-GLB matrix; do not regenerate assets.
- Default asset quality is `balanced`; LOD selection remains distance-driven.
- QA export uses Godot 4.3 Mobile Vulkan, landscape orientation, API 34, x86_64.
- Final runtime gate includes five-minute mission traversal and thirty-minute soak.

---

### Task 1: Layout Manifest Contract

**Files:**
- Create: `asset_lab/runtime/manama_souq_layout_v1.json`
- Create: `tests/test_manama_souq_layout_contract.py`

**Interfaces:**
- Consumes: `asset_lab/runtime/full_asset_matrix_manifest.json`
- Produces: schema `bahrain-brick-manama-souq-layout-v1`, deterministic placement IDs, zone records, mission positions.

- [ ] Write a failing Python contract that loads both manifests and requires unique placement IDs, required zones, family minimums, source asset membership, 220 m bounds, and exact mission points.
- [ ] Run `python3 tests/test_manama_souq_layout_contract.py`; expect failure because the layout file is absent.
- [ ] Add the deterministic layout JSON with at least 8 traditional, 12 souq, 5 waterfront, and all 4 commercial records.
- [ ] Re-run the test; expect `OK`.
- [ ] Commit `test: lock Manama Souq layout authority`.

### Task 2: Karak Delivery State Machine

**Files:**
- Create: `scripts/karak_delivery_mission.gd`
- Create: `tests/test_karak_delivery_mission_contract.py`
- Create: `tests/karak_delivery_mission_runtime.gd`

**Interfaces:**
- Produces class `KarakDeliveryMission` and methods `start`, `advance_from_player_position`, `notify_order_collected`, `notify_vehicle_entered`, `notify_vehicle_exited`, `restart`.
- Emits `objective_changed`, `state_changed`, `mission_completed`, `mission_failed`.

- [ ] Write a failing static contract for exact states, signals, transition methods, reward 250, and duplicate-trigger protection.
- [ ] Add the minimal state machine with one-way legal transitions and explicit guard conditions.
- [ ] Add a headless Godot runtime test that completes the mission and asserts every state appears exactly once.
- [ ] Run Python and Godot tests; expect both pass.
- [ ] Commit `feat: add deterministic karak delivery mission`.

### Task 3: Deterministic District Builder

**Files:**
- Create: `scripts/manama_souq_layout_loader.gd`
- Create: `tests/test_manama_souq_layout_loader.py`
- Create: `tests/manama_souq_layout_runtime.gd`

**Interfaces:**
- `load_layout(path: String, full_manifest_path: String) -> Dictionary`
- `instantiate_layout(root: Node3D, camera: Camera3D, profile: String) -> Dictionary`
- Returns counts and named zone nodes.

- [ ] Write failing contracts requiring fail-closed schema validation, full-matrix membership, duplicate rejection, and deterministic placement order.
- [ ] Implement parsing and validation without altering full-matrix runtime code.
- [ ] Implement manifest-based LOD instances for architecture and direct packed-scene instances for commercial records.
- [ ] Add headless runtime test for exact placement counts and zone names.
- [ ] Commit `feat: assemble deterministic Manama Souq layout`.

### Task 4: Vertical Slice Scene and Player/Vehicle Composition

**Files:**
- Create: `scripts/manama_souq_vertical_slice.gd`
- Create: `scenes/manama_souq_vertical_slice.tscn`
- Create: `tests/test_manama_souq_slice_contract.py`
- Create: `tests/manama_souq_slice_runtime.gd`

**Interfaces:**
- Scene exposes nodes `District`, `PlayerSpawn`, `MissionVehicleSpawn`, `Population`, `Mission`, and `HUD`.
- Emits readiness marker after assets, player, vehicle, and population are live.

- [ ] Write failing scene/script contract.
- [ ] Build environment, lighting, ground, boundaries, spawn nodes, and camera-safe scene order.
- [ ] Instantiate existing player controller and existing vehicle/factory path without changing their source files.
- [ ] Connect vehicle entry/exit state to mission methods.
- [ ] Add headless test for one player, one mission vehicle, valid current camera, and bounded district.
- [ ] Commit `feat: add playable Manama Souq slice scene`.

### Task 5: Lightweight Population

**Files:**
- Create: `scripts/souq_population_controller.gd`
- Create: `tests/test_souq_population_contract.py`
- Create: `tests/souq_population_runtime.gd`

**Interfaces:**
- `configure(bounds: AABB, pedestrian_count: int = 12, traffic_count: int = 6, seed: int = 1409)`
- `spawn_all(root: Node3D) -> Dictionary`
- Produces groups `souq_pedestrians` and `souq_traffic`.

- [ ] Write failing deterministic count, seed, pooling, and bounds contracts.
- [ ] Implement 12 waypoint pedestrians and 6 loop-route traffic vehicles using existing factories/controllers where available.
- [ ] Disable processing outside bounds and recycle actors rather than creating new ones.
- [ ] Add runtime count and bounds test.
- [ ] Commit `feat: populate Souq slice with bounded traffic`.

### Task 6: Objective HUD and Mission Interaction

**Files:**
- Create: `scripts/karak_delivery_hud.gd`
- Create: `scenes/karak_delivery_hud.tscn`
- Create: `tests/test_karak_delivery_hud_contract.py`
- Create: `tests/karak_delivery_hud_runtime.gd`

**Interfaces:**
- `bind_mission(mission: KarakDeliveryMission, player: Node3D) -> void`
- Updates title, objective, distance, order indicator, reward, and replay action.

- [ ] Write failing node-name and signal-wiring contract.
- [ ] Implement mobile-safe HUD without obscuring existing touch controls.
- [ ] Add collection and delivery interaction areas and replay action.
- [ ] Add headless HUD signal test.
- [ ] Commit `feat: add Karak Delivery objective HUD`.

### Task 7: Integrated Source and Regression Gate

**Files:**
- Create: `tools/vertical_slice/run_manama_souq_source_gate.sh`
- Create: `.github/workflows/manama-souq-vertical-slice.yml`
- Modify only if necessary: `tools/asset_lab/run_game_regressions.sh`

**Interfaces:**
- Produces source reports, protected pre/post hashes, Godot import log, slice runtime log, and exact readiness/completion markers.

- [ ] Add a workflow limited to the child branch and draft PR base.
- [ ] Recover the exact validated 436-asset artifact and real game source by checksum.
- [ ] Overlay only the vertical-slice files into the disposable game copy.
- [ ] Run all new tests plus inherited regressions and protected pre/post comparison.
- [ ] Require no parse errors, missing resources, critical errors, or control mutations.
- [ ] Commit `ci: add Manama Souq source validation gate`.

### Task 8: Android QA Export and Mission Traversal

**Files:**
- Create: `tools/vertical_slice/run_manama_souq_android_validation.sh`
- Extend: `.github/workflows/manama-souq-vertical-slice.yml`

**Interfaces:**
- QA-only `run/main_scene` points to `res://scenes/manama_souq_vertical_slice.tscn` inside the disposable build copy.
- Produces signed APK, package metadata, screenshots, memory CSV/JSON, logcat, and validation JSON.

- [ ] Export Mobile Vulkan landscape APK with unique QA version code/name.
- [ ] Independently verify SHA-256, package/version, v2/v3 signature, alignment, archive integrity, and x86_64 ABI.
- [ ] Boot AOSP API 34 through the proven landscape-holder and quiescence sequence.
- [ ] Require readiness marker and visible landscape frame.
- [ ] Automate mission triggers through the complete state sequence while exercising movement and vehicle controls.
- [ ] Require mission-completion marker within 300 seconds.
- [ ] Run pause/resume, cold start, remaining five-minute traversal duration, and thirty-minute soak.
- [ ] Reject fatal, ANR, native crash, missing-resource, shader-limit, or memory-growth failures.
- [ ] Upload APK and complete checksum-addressed evidence.
- [ ] Commit `ci: validate Manama Souq Android vertical slice`.

### Task 9: Release Checkpoint

**Files:**
- Create: `docs/evidence/manama-souq-vertical-slice-v1-checkpoint.md`

**Interfaces:**
- Records exact branch head, run ID, artifact ID/digest, APK size/SHA, test totals, screenshots, memory figures, and known limitations.

- [ ] Verify the child PR remains draft and unmerged.
- [ ] Record evidence only after the complete workflow is green.
- [ ] Add a compact PR checkpoint comment without changing merge state.
- [ ] Commit `docs: record Manama Souq vertical slice checkpoint`.
