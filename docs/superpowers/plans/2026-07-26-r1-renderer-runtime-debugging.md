# Bahrain Brick R1 Renderer Runtime Debugging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:systematic-debugging, superpowers:test-driven-development, and superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Identify and fix the proven GL Compatibility shader-link defect and Mobile Vulkan frame-progression defect without changing renderer defaults, gameplay, missions, assets, or graphics design.

**Architecture:** A test-only Android scene selects diagnostic modes from `user://r1_mode.txt`. One shared imported project state is cloned byte-for-byte into GL and Mobile export variants. The Android runner executes a GL feature-isolation matrix and paired Mobile baseline/render-disabled controls, then a finalizer assigns evidence-backed root causes. Production changes are prohibited until a diagnostic run uniquely identifies the failing feature or subsystem.

**Tech Stack:** Godot 4.3 GDScript, Python 3 unittest/reporting, Bash, Android API 34 AOSP x86_64, driver capability and link-error probe, GitHub Actions.

## Global Constraints

- Base exactly `6c7d49dbfb00aaaa2f90d63f47fa76af7a0f910e`.
- Renderer authority remains `6ade72ed02084791128dcf4a91223e695d802c15`.
- `project.godot` production renderer defaults must not change.
- Do not redesign graphics, replace assets, change gameplay, change missions, select a renderer, or begin G1.
- No production fix before a diagnostic hypothesis is uniquely confirmed.
- Governing graphics status remains `G0_EVIDENCE_INSUFFICIENT`.

---

### Task 1: Establish R1 contracts and diagnostic scene

**Files:**
- Create: `authority/bahrain_brick_r1_renderer_runtime_debugging.json`
- Create: `tests/graphics/test_r1_renderer_runtime_debugging_contract.py`
- Create: `tests/graphics/r1_renderer_runtime_debug.gd`
- Create: `tests/graphics/r1_renderer_runtime_debug.tscn`

**Interfaces:**
- Consumes: accepted G0.2 reports and production vertical-slice scene.
- Produces: `R1_GL_*` and `R1_MOBILE_*` markers plus `user://r1_*.json` evidence files.

- [ ] Write the contract test and verify it fails while implementation files are absent.
- [ ] Implement mode selection, GL minimal-scene matrix, production material inventory, Mobile heartbeat, and render-disabled control.
- [ ] Run contract tests and GDScript source assertions.
- [ ] Commit the diagnostic scene and contracts.

### Task 2: Build one shared import and two diagnostic APKs

**Files:**
- Create: `tools/graphics/prepare_r1_android_variant.py`
- Create: `tools/graphics/run_r1_renderer_debug.sh`
- Create: `.github/workflows/bahrain-brick-r1-renderer-runtime-debugging.yml`

**Interfaces:**
- Consumes: one deterministic reconstructed source tree and one completed `.godot/imported` state.
- Produces: GL and Mobile x86_64 debug APKs, clone-equivalence manifests, driver capability and link-error probe, raw per-mode evidence.

- [ ] Write failing tests for exact source authority, no production renderer-default changes, mode list, and independent Mobile control.
- [ ] Implement shared import, byte-identical cloning, QA-only project/preset overrides, APK export, and API 34 emulator runner.
- [ ] Execute GL modes: `gl_unshaded`, `gl_empty`, `gl_sun`, `gl_sun_shadow`, `gl_two_directional`, `gl_two_directional_shadow`, `gl_production`.
- [ ] Execute Mobile modes on equivalent fresh emulator baselines: `mobile_baseline`, `mobile_render_disabled_control`.
- [ ] Retain all logs, screenshots, frame heartbeats, thread dumps, CPU/memory/gfxinfo samples, and driver capability and uniform-overflow diagnostics.

### Task 3: Diagnose before fixing

**Files:**
- Create: `tools/graphics/finalize_r1_renderer_debug.py`
- Create: `reports/graphics/r1/diagnostic/track_a_gl.json`
- Create: `reports/graphics/r1/diagnostic/track_b_mobile.json`

**Interfaces:**
- Consumes: immutable diagnostic artifact.
- Produces: unique Track A hypothesis result and exactly one Mobile classification.

- [ ] Parse every GL program-link block and prove the device limit and active count.
- [ ] Compare the GL feature matrix and identify the smallest feature delta that changes failures from nonzero to zero.
- [ ] Inventory production material signatures and report whether any user-authored shader exists.
- [ ] Compare Mobile baseline heartbeats, native stacks, rendered frames, and render-disabled control.
- [ ] Assign exactly one Mobile classification without inference beyond retained evidence.
- [ ] Stop without production changes if either root cause is not uniquely proven.

### Task 4: Implement minimal proven fixes with TDD

**Files:**
- Modify only the exact production files identified by Task 3.
- Create focused regression tests under `tests/graphics/`.

**Interfaces:**
- Consumes: proven diagnostic root causes.
- Produces: one minimal GL correction and one minimal Mobile correction.

- [ ] Write failing regression tests that reproduce each proven defect.
- [ ] Implement one root-cause fix per track; do not bundle refactors.
- [ ] Run source contracts and focused tests.
- [ ] Commit each track separately.

### Task 5: Verify R1 exit criteria

**Files:**
- Create: `reports/graphics/r1/track_a/*`
- Create: `reports/graphics/r1/track_b/*`
- Create: `reports/graphics/r1/R1_TERMINAL_REPORT.json`
- Create: `reports/graphics/r1/R1_TERMINAL_REPORT.md`
- Update: `.ai/project-state.json`
- Update: `.ai/CHECKPOINT.md`

**Interfaces:**
- Consumes: corrected diagnostic APKs from one shared import state.
- Produces: terminal R1 evidence and a recommendation to rerun paired qualification only if all exit criteria pass.

- [ ] Re-run GL production mode and prove zero SceneShaderGLES3 link failures.
- [ ] Re-run Mobile production mode and prove frame 300, valid screenshot, and zero critical runtime errors.
- [ ] Generate before/after regression screenshots and exact compile/progression reports.
- [ ] Verify renderer defaults, gameplay, mission, and asset boundaries remained unchanged.
- [ ] Keep `G0_EVIDENCE_INSUFFICIENT`; do not select a renderer or begin G1.
