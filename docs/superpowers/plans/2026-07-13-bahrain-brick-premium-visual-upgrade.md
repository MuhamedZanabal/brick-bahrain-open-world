# Bahrain Brick Premium Visual Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a runtime-verified Bahrain-specific gameplay-world visual upgrade and Android QA build without changing the frozen mobile-control architecture.

**Architecture:** Continue the checksum-locked v1.4 reconstruction model and apply deterministic premium-world overlays to the integrated source. Isolate environment, materials, props, quality profiles, and evidence capture so each can be tested independently while protected control files remain byte-identical.

**Tech Stack:** Godot 4.3, GDScript, GL Compatibility renderer, Android export, Bash/Python CI verification, GitHub Actions.

## Global Constraints

- Official title: `Bahrain Brick`.
- Package: `com.bahrainbrick.game.qa` until the QA release version is intentionally incremented.
- Android orientation: `sensorLandscape`.
- Historical v1.4 fallback only; never label as v15 authority.
- Frozen controls commit: `c5548465627942a2889a0bd09f8979c3a29fbcdd`.
- Protected controls and tests remain byte-identical.
- Native UI controls remain functional; no baked buttons, percentages, settings states, or unsupported counters.
- Do not claim physical-device performance without a physical-device run.

---

### Task 1: Freeze Baseline and Isolate Premium Branch

**Files:**
- Create: repository refs `baseline/bahrain-brick-v14.0.3-functional-graphics` and `work/bahrain-brick-premium-visual-v14`
- Create: `docs/audit/2026-07-13/PREMIUM_VISUAL_BASELINE.md`

- [ ] Record graphics commit, source ZIP hash, APK hash, and controls commit.
- [ ] Create immutable baseline branch at graphics commit.
- [ ] Create premium branch from the same commit.
- [ ] Verify premium branch ancestry against the controls commit.

### Task 2: Deterministic World Benchmark

**Files:**
- Create: `premium_world_overlay/tests/premium_world_visual_test.gd`
- Create: `premium_world_overlay/scenes/premium_world_visual_test.tscn`
- Modify: `.github/workflows/build_bahrain_brick_premium_visual_qa.yml`

- [ ] Define fixed world camera transforms and capture names.
- [ ] Capture equivalent baseline and upgraded viewpoints.
- [ ] Verify screenshots are nonblank and dimensions match.
- [ ] Emit JSON evidence with camera transforms and render settings.

### Task 3: Mobile Environment Calibration

**Files:**
- Modify: `scripts/day_night_cycle.gd`
- Modify: `scripts/world.gd`
- Modify: `scenes/world.tscn`
- Test: `tests/premium_environment_test.gd`

- [ ] Add failing assertions for exposure, ambient energy, fog, shadow range, and daylight temperature.
- [ ] Implement warm Bahrain daylight and bounded exposure.
- [ ] Configure mobile-safe fog and distance color.
- [ ] Verify day/night readability and no protected-file hash changes.

### Task 4: Bahrain World Material System

**Files:**
- Create: `scripts/premium_world_materials.gd`
- Modify: `scripts/hero_district_builder.gd`
- Test: `tests/premium_world_materials_test.gd`

- [ ] Define reusable asphalt, pavement, red-white curb, sand, plaster, stone, glass, metal, palm, and emissive-window materials.
- [ ] Replace flat color-only district surfaces with material variants.
- [ ] Add deterministic variation without unique per-instance materials.
- [ ] Verify material count and reuse budgets.

### Task 5: Bahrain Props and Coastal Treatment

**Files:**
- Create: `scripts/bahrain_environment_props.gd`
- Modify: `scripts/hero_district_builder.gd`
- Modify: `shaders/mobile_waterfront.gdshader`
- Test: `tests/bahrain_environment_props_test.gd`

- [ ] Add instanced lamps, benches, bollards, planters, bilingual signs, flags, barriers, and market props.
- [ ] Improve palm variation and placement.
- [ ] Improve shoreline fade, water color, sun response, and mobile reflection approximation.
- [ ] Verify object-count and visibility-range budgets.

### Task 6: Real Android Quality Profiles

**Files:**
- Modify: `scripts/quality_manager.gd`
- Modify: `scripts/settings_panel.gd`
- Test: `tests/quality_profiles_test.gd`

- [ ] Define Low, Balanced, and High rendering profiles.
- [ ] Apply real shadow, fog, render-scale, AA, reflection, vegetation, and visibility changes.
- [ ] Persist selected profile.
- [ ] Verify each profile changes runtime values and settings UI remains functional.

### Task 7: Context-Safe HUD Visual Upgrade

**Files:**
- Modify: `scenes/hud.tscn`
- Modify only presentation portions of: `scripts/hud.gd`
- Test: existing mobile-control and presentation suites plus `tests/hud_context_visual_test.gd`

- [ ] Improve icon hierarchy, safe margins, opacity, and pressed states.
- [ ] Retain walking/vehicle visibility logic unchanged.
- [ ] Verify walking and vehicle controls never display simultaneously.
- [ ] Verify touch regions and control hashes remain accepted.

### Task 8: Screen-Specific Runtime Art and Branding

**Files:**
- Create/replace optimized screen-specific assets under `assets/ui/runtime/premium/`
- Create source masters under `assets/ui/source/premium/`
- Modify presentation scenes/scripts only as needed to reference assets.

- [ ] Create distinct Zanabal, Mansoory, menu, loading, selection, and pause compositions.
- [ ] Integrate exact typography and logo variants.
- [ ] Retain all interactive text and controls as native Godot nodes.
- [ ] Verify startup order and 10/10 presentation acceptance.

### Task 9: Character and Vehicle Presentation

**Files:**
- Modify visual-only resources and model wrappers.
- Modify: `scripts/character_select.gd` for real previews without changing selection semantics.
- Test: character selection and gameplay spawn verification.

- [ ] Add actual model previews through controlled SubViewport or project-model portraits.
- [ ] Improve character and vehicle materials, lighting, and ground contact.
- [ ] Verify selected character appears in gameplay.
- [ ] Verify no unsupported vehicles or abilities are shown.

### Task 10: Full Build, Evidence, and Release

**Files:**
- Create: build workflow, reports, change manifest, release notes, checksums.

- [ ] Run import and runtime smoke.
- [ ] Run controls regression and frozen-file checks before and after.
- [ ] Run presentation and premium visual tests.
- [ ] Export Android QA APK and verify package, alignment, signatures, permissions, version, and orientation.
- [ ] Capture matched screenshots and startup/gameplay/control videos.
- [ ] Report APK delta, startup/load timing, hosted frame metrics, memory where measurable, and unverified physical-device metrics.
- [ ] Publish APK, source ZIP, workspace ZIP, evidence, checksums, and known issues to a GitHub prerelease.
