# INTERIM PRODUCT AUTHORITY — BAHRAIN BRICKS v15.0.1

Generated: 2026-07-12 (Asia/Bahrain)
Status: PROPOSED INTERIM AUTHORITY PENDING USER OVERRIDE
Owners: Agents 01, 02, 03, 04, 09, 26, 30

## Purpose

The claimed `Project_Bahrain_Bricks_GDD.md` is unavailable. Until that file is recovered, this document defines the narrowest evidence-backed product contract that permits stabilization work without expanding scope or contradicting the latest verified implementation lineage.

This document does not replace a recovered GDD permanently. A recovered GDD must be reconciled against this contract through the decision log before changing accepted scope.

## Source hierarchy

1. Recovered v15.0.1 authority source at commit `796b112802c83ce78f8233e9a215e97c39ca028e`.
2. Verified build provenance and test evidence generated from that commit.
3. The user-provided 30-agent operating constitution and initial production objective.
4. Historical v15 upgrade report and runtime smoke evidence.
5. Historical v14/v12 information only for regression comparison.

The connected GitHub `main` branch at commit `08378d1383eb7aeb1ae91b9eeb8994b79a96f1de` is explicitly excluded as product authority because it is the obsolete v12 baseline.

## Product identity

- Working title: Bahrain Bricks / Brick Bahrain: Open World.
- Engine: Godot 4.3 with GDScript.
- Platform priority: Android.
- Presentation: horizontal mobile-first brick-style open-world sandbox.
- Setting: an original Bahrain-inspired world using culturally appropriate, non-lethal, legally safe content.
- Primary mode for stabilization: single-player/offline.
- Multiplayer: retained only behind safe feature gating until host/join/replication/disconnect evidence exists.

## Initial release contract

A QA candidate must provide one uninterrupted path through:

1. Cold launch.
2. Main menu.
3. Character selection.
4. Staged world loading with bounded timeout and diagnostic failure state.
5. Visible player spawn with movement, camera, collision, and recovery.
6. Responsive touch movement and camera input in landscape.
7. Vehicle entry, acceleration, steering, braking, recovery, and exit.
8. Start, complete, reward, retry, and persist at least one mission.
9. Save, close, reopen, and restore progress.
10. Pause, resume, Android back handling, and safe exit.

## Existing v15 feature baseline to preserve

The following are treated as existing behavior, not new scope, because retained tests or reports record them:

- Sensor-landscape project and Android manifest intent.
- Splash, main menu, character select, and world scenes.
- Staged world loading.
- Player model, collision, and third-person camera.
- Five drivable vehicle spawns.
- At least 50 pedestrian spawns and a traffic pool.
- HUD, phone UI, and eight registered missions.
- Touch movement and camera rotation.
- Vehicle entry, drive, boost, and exit.
- Pearl, drift, and sandstorm mission execution.
- Save/reload of coin and mission progress.
- Level/XP progression, deterministic daily challenges, district discovery, freeroam combo scoring, safe checkpoints, and timed coin-rush events.

Preservation does not equal Android-device verification. Any feature may be disabled temporarily when it causes a P0/P1 stability, privacy, licensing, or performance failure.

## Explicitly deferred until gates pass

- Public multiplayer claims.
- Production economy or monetization.
- UGC, open chat, or unrestricted voice chat.
- Large world expansion.
- New weather, day/night, destruction, or high-cost visual effects.
- Additional vehicles, districts, missions, or character packs.
- Store submission and public release.

## Quality budgets

Until representative Android profiling is available, the following provisional targets apply:

- P0 crashes, infinite loads, package errors, and corrupted-save failures: 0.
- P1 navigation, input, mission, vehicle, and lifecycle failures: 0 for QA milestone closure.
- Cold launch to menu: target <= 10 seconds on declared mid-tier device.
- Menu to controllable gameplay: target <= 30 seconds on declared mid-tier device.
- Sustained gameplay: target >= 30 FPS on declared minimum device, >= 45 FPS on recommended device.
- Peak memory: must be measured and remain below the device-specific safe budget established by Agent 16.
- Touch targets and text: must remain usable across representative 16:9, 19.5:9, and notched landscape screens.

These are provisional acceptance targets, not verified current performance.

## Compliance contract

- Unknown-rights assets are release blockers.
- No protected toy-brick branding, logos, character likenesses, vehicle trademarks, or trade dress may be copied.
- Commercial music is prohibited unless separately licensed and documented.
- `RECORD_AUDIO` must be removed until voice chat has a clear purpose, consent UX, privacy disclosure, safe denial behavior, and runtime verification.
- Exposed credentials must be rotated and must never enter source or reports.
- Public claims must distinguish generated concept media from captured gameplay.

## Acceptance authority

During the interim period:

- Agent 03 controls technical feasibility and architecture.
- Agent 26 controls release test sufficiency.
- Agent 30 may stop work for licensing, privacy, security, cultural, or store-policy risk.
- Agent 01 controls scope and milestones.
- The user remains final authority for public, costly, irreversible, or major architecture decisions.

## Exit from interim authority

This document ceases to be the primary product contract when either:

1. `Project_Bahrain_Bricks_GDD.md` is recovered and reconciled; or
2. the user explicitly approves a newly authored full GDD derived from verified source behavior and revised product goals.
