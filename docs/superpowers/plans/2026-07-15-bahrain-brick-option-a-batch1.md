# Bahrain Brick Option A — Batch 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish and execute the five-golden-master gate that must pass before regenerating the complete 436-GLB production matrix.

**Architecture:** Add a machine-readable golden-master contract, test-first validators, a dedicated Blender generator for five representative assets, a manifest-driven Godot preview scene, and a bounded Android evidence workflow. The existing 48-record generator remains frozen from mass regeneration until the gate report records technical, visual-evidence, Godot-import, and Android-runtime approval for all five masters.

**Tech Stack:** Python 3.12, unittest, Blender 4.3.2 Python API, glTF/GLB, Godot 4.3, GDScript, GitHub Actions, Android API 34.

## Global Constraints

- Work only on `work/bahrain-brick-asset-lab-integration-v1` and keep PR #57 draft and unmerged.
- Preserve frozen premium authority `e26ec912db5c10d071a8e120010bdb5a9a136f17` and all protected gameplay hashes.
- Generate exactly five golden-master source records and exactly 45 derivatives: 5 assets × 3 profiles × 3 LODs.
- Do not run the 432-derivative mass generator until the golden-master gate reports `mass_regeneration_allowed: true`.
- Balanced/LOD0 is the visual-review authority; low and high profiles must have measurable cost differences.
- LOD triangle counts must be monotonic: `LOD0 >= LOD1 >= LOD2`.
- Missing evidence is a failure, never an implicit pass.

---

### Task 1: Golden-master contract and hard gate

**Files:**
- Create: `docs/assets/GOLDEN_MASTER_CONTRACT.json`
- Create: `tools/asset_lab/golden_master_contract.py`
- Create: `tests/test_golden_master_contract.py`
- Create: `.github/workflows/golden-master-gate.yml`

**Interfaces:**
- Produces: `load_contract(path: Path) -> dict`, `validate_contract(contract: dict) -> list[str]`, and `evaluate_gate(contract: dict, evidence: dict) -> dict`.
- Contract asset IDs: `bh_traditional_projecting_window_01`, `bh_souq_shop_gold_01`, `bh_waterfront_tower_a_01`, `bh_supermarket_storefront_a_01`, `bh_cr_skyscraper_tower_01`.

- [ ] Write tests requiring five unique records, exact profiles/LODs, complete visual criteria, and a default closed mass-regeneration gate.
- [ ] Push the tests and confirm the dedicated workflow fails because the implementation and contract are absent.
- [ ] Implement the validator and contract with deterministic seeds and family-specific acceptance rules.
- [ ] Run the workflow and confirm all contract tests pass.
- [ ] Commit the green state.

### Task 2: Shared procedural mobile material library

**Files:**
- Create: `tools/asset_lab/golden_master_materials.py`
- Create: `tests/test_golden_master_materials.py`

**Interfaces:**
- Produces: `PROFILE_SETTINGS`, `material_spec(profile: str, material_key: str) -> dict`, and `validate_profile_ordering() -> list[str]`.
- Material keys: `sand_plaster`, `limestone`, `dark_timber`, `painted_metal`, `blue_glass`, `souq_gold`, `promenade_paving`, `signage_accent`.

- [ ] Write failing tests for profile ordering, allowed texture sizes, material uniqueness, and required keys.
- [ ] Implement deterministic material specifications with low/balanced/high resolution and shader-cost limits.
- [ ] Verify tests pass and commit.

### Task 3: Five-master Blender generator

**Files:**
- Create: `tools/asset_lab/generate_golden_masters.py`
- Create: `tests/test_golden_master_generation_plan.py`
- Modify: `tools/asset_lab/validate_generated_asset_batch.py`

**Interfaces:**
- Produces: `generation_plan(seed: int) -> dict`, `generate_asset(asset_id: str, profile: str, lod: int, output: Path) -> dict`, and a 45-record JSON report.
- Uses family-specific builders; identical meshes across LOD levels are prohibited.

- [ ] Write failing tests for exactly 45 unique paths, stable seeds, correct five IDs, and expected profile/LOD matrix.
- [ ] Implement geometry builders with bevelled massing, recessed openings, trim, screens, canopies, railings, signage, roof details, and collision proxies.
- [ ] Add GLB metadata and triangle/material/collision reporting.
- [ ] Generate all 45 derivatives in CI and validate GLB structure, Khronos compliance, collision policy, and LOD monotonicity.
- [ ] Commit only after the generated report passes.

### Task 4: Visual evidence and approval report

**Files:**
- Create: `tools/asset_lab/render_golden_master_contact_sheets.py`
- Create: `tools/asset_lab/evaluate_golden_master_gate.py`
- Create: `tests/test_golden_master_gate.py`

**Interfaces:**
- Produces five balanced/LOD0 turntable sheets and `GOLDEN_MASTER_GATE_REPORT.json`.
- Gate inputs: technical report, contact-sheet inventory, Godot-import report, Android screenshot inventory.

- [ ] Write failing tests proving missing screenshots, missing family coverage, or failed validators keep the gate closed.
- [ ] Implement deterministic Blender camera/light/render setup and evidence inventory.
- [ ] Implement gate evaluation with explicit failure reasons.
- [ ] Verify the gate remains closed until runtime evidence exists; commit.

### Task 5: Manifest-driven Godot preview and runtime selection

**Files:**
- Create: `assets/generated/golden_masters/runtime_manifest.json`
- Create: `scripts/golden_master_runtime.gd`
- Create: `scenes/qa/golden_master_preview.tscn`
- Create: `tests/test_golden_master_runtime.py`

**Interfaces:**
- Runtime selects one quality profile and distance-based LOD with hysteresis.
- QA scene must display one coherent composition containing all five families.

- [ ] Write failing source-level tests for manifest completeness, profile selection, LOD thresholds, hysteresis, and missing-resource hard failure.
- [ ] Implement the manifest and isolated runtime controller without touching protected controls.
- [ ] Add the preview scene and Godot headless import test.
- [ ] Verify tests pass and commit.

### Task 6: Bounded Android runtime workflow

**Files:**
- Modify: `.github/workflows/golden-master-gate.yml`
- Create: `tools/asset_lab/run_golden_master_android_validation.sh`
- Create: `tests/test_golden_master_android_workflow.py`

**Interfaces:**
- Stages: emulator boot, APK install, activity launch, landscape assertion, runtime marker, screenshot capture, logcat scan.
- Every stage has an independent timeout and diagnostic dump.

- [ ] Write failing workflow-source tests requiring stage-specific timeouts and diagnostics.
- [ ] Implement the bounded validator and wire APK export plus API 34 execution.
- [ ] Capture screenshots containing all five representative assets.
- [ ] Re-evaluate the gate; require `mass_regeneration_allowed: true` only when all evidence passes.
- [ ] Upload APK, 45 GLBs, reports, screenshots, logs, and SHA-256 inventory; commit.

### Task 7: Batch 1 completion review

**Files:**
- Create: `asset_lab/reports/GOLDEN_MASTER_BATCH1_COMPLETION.md`
- Modify: `asset_lab/reports/ASSET_PRODUCTION_EXECUTION_LEDGER.json`

- [ ] Run all contract, material, generation, validation, Godot, protected-authority, and Android checks.
- [ ] Confirm exactly 45 golden-master derivatives and five balanced/LOD0 visual authorities.
- [ ] Confirm the Android APK installs, launches, enters landscape, and emits the expected runtime marker.
- [ ] Record all hashes and failures honestly.
- [ ] Leave PR #57 draft and unmerged.

## Plan Self-Review

- Coverage: contract, materials, generation, technical validation, visual evidence, Godot runtime, Android runtime, provenance, and protected controls are represented.
- Scope: this plan covers Batch 1 only. The 436-GLB mass regeneration, complete family rollout, and final production APK each require subsequent plans after this gate passes.
- Placeholder scan: no deferred implementation language is used as an acceptance substitute.
- Safety: no task authorizes merging, weakening tests, or modifying protected gameplay controls.
