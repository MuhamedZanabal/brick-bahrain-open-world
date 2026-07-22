# Bahrain Brick Graphics Upgrade v1 — Checkpoint

Recorded: 2026-07-22

## Objective

Deliver the accepted Bahrain Brick graphics upgrade through staged, evidence-gated pull requests without changing frozen PR #59, protected gameplay controls, mission behaviour, vehicle behaviour, regression thresholds, or validated asset authority.

## Repository State

- Repository: `MuhamedZanabal/brick-bahrain-open-world`
- Active implementation branch: `work/bahrain-brick-graphics-upgrade-v1`
- Frozen parent PR: `#59`
- Frozen parent head: `5b4e2466ef84f3984f3bf336b31925d4d2e97a7f`
- Frozen parent base: `fc8f00182f97c39015610d6603fa7c9c44364c5d`
- Current phase: G0 — Authority, Baseline, and Risk Control
- G0 gate: FAILED / OPEN

## Verified Completed Work

- Confirmed PR #59 open, draft, unmerged, and unchanged before branch creation.
- Created the child graphics branch from the exact frozen PR #59 head.
- Recorded a machine-readable authority contract.
- Added a SHA-256 and ancestry regression contract for protected files.
- Added read-only GitHub Actions G0 authority/baseline workflow.
- Recorded the renderer conflict as unresolved.
- Inventoried all 35 deterministic Manama Souq layout placements.
- Recorded startup/menu/HUD and inspected resource architecture.
- Defined provisional minimum, target, high-end, ultra, and CI-emulator device tiers.
- Added visual/performance evidence matrix.
- Added licence, provenance, originality, and no-copied-trade-dress gate.
- Added the accepted graphics specification and project state ledger.

## Active Failure / Blocker

GFX-009 cannot be executed in the current tool environment because Godot runtime, Android emulator/physical-device execution, direct repository checkout, screenshots, profiler capture, and package generation are unavailable.

This blocks:

- paired GL Compatibility versus Mobile Vulkan evidence;
- renderer-specific failure/difference record;
- authoritative renderer selection;
- compatibility fallback policy;
- baseline screenshots;
- frame time, draw calls, triangles, memory, load time, and APK size;
- named physical-device qualification;
- Gate G0.

## Authority Inconsistency

`docs/superpowers/specs/2026-07-16-manama-souq-playable-district-v1-design.md` protects `scripts/world.gd::_exit_tree`. The symbol was not found in the inspected PR #59 head source ranges. Until reconstructed-source evidence resolves this, do not modify `scripts/world.gd`.

## Unresolved Risks

1. Mobile Vulkan may fail minimum-device or driver reliability gates.
2. GL Compatibility may limit the target visual stack.
3. A dual renderer path may create unacceptable shader/material maintenance cost.
4. Baseline performance and APK size are not recorded.
5. Named physical devices and GPU drivers are not assigned.
6. The complete tree-wide UI/material/font/shader/environment inventory is not finished because a full checkout/reconstruction was unavailable.

## Exact Next Action

Execute GFX-009 on a runner with the reconstructed source, Godot 4.3 authority, Android SDK/emulator, and physical-device access:

1. Build or launch the exact same deterministic Manama Souq scene under `gl_compatibility`.
2. Repeat under `mobile`.
3. Keep source commit, camera, viewport, render scale, quality, mission state, warm-up, and capture path identical.
4. Record screenshots, logs, renderer/device identity, cold/warm load time, frame-time series, draw calls, triangles, memory, package bytes, and SHA-256.
5. Run the five-minute mission traversal and thirty-minute soak on minimum, target, and high-end physical devices.
6. Update `docs/graphics/visual_acceptance_matrix.md`, `docs/graphics/device_matrix.md`, `.ai/project-state.json`, and the renderer decision.
7. Do not begin G1 until G0 passes.

## Reproduction / Verification Commands

```bash
python3 tests/graphics/test_graphics_upgrade_g0_contract.py
```

The GitHub Actions workflow is:

```text
.github/workflows/bahrain-brick-graphics-g0.yml
```

It requires full Git history and verifies PR #59 through the GitHub API.
