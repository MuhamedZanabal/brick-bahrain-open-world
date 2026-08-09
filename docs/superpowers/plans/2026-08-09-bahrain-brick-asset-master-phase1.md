# Bahrain Brick Asset Master Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the Phase 1 toolchain gate with exact capability evidence and one isolated 1 m cube that proves Blender source → deterministic GLB → Godot 4.3 import at 1:1 scale → Android APK → API 34 runtime screenshot/log.

**Architecture:** Reuse the already-committed deterministic `tools/asset_lab/generate_validation_cube.py`; do not modify gameplay or production renderer configuration. Because Blender, Godot, Android SDK/ADB, and an Android device are unavailable in the current hosted ChatGPT container, execute the smoke path on an isolated GitHub Actions runner. Generate a throwaway Godot project under `build/` so no game scene, script, setting, or runtime asset is changed.

**Tech Stack:** Blender 4.3.2, Godot `4.3.stable.official.77dcf97d8`, Python, Java 17, Android API 34/build-tools 34.0.0, ADB/emulator, GitHub Actions.

## Global Constraints

- Phase 0 authority record must remain valid.
- Work only on `work/bahrain-brick-master-asset-integration-v1`.
- Protected gameplay blobs must remain unchanged.
- The isolated smoke project must use the baseline renderer contract and must not be treated as an R1 renderer experiment.
- No merge, release, publication, signing-authority change, or physical-device claim.
- Image-to-3D is not used; `P1.010` is not applicable.

---

### Task 1: Add isolated cube runtime qualification workflow

**Files:**
- Create: `.github/workflows/master-asset-phase1-cube.yml`

**Interfaces:**
- Consumes: `tools/asset_lab/generate_validation_cube.py`, `tools/asset_lab/validate_glb_asset.py`.
- Produces: a workflow artifact containing tool versions, two cube-generation reports, deterministic GLB comparison/hash, independent GLB validation, Godot import log, APK hash/badging/signing evidence, emulator launch logcat, runtime scale marker, and Android screenshot.

- [ ] **Step 1: Provision pinned runner dependencies**

Use full-SHA GitHub Actions for checkout, Java setup, Android setup, and artifact upload. Install/check Blender `4.3.2`, Godot `4.3.stable.official.77dcf97d8`, export templates, Android API 34/build-tools 34.0.0, emulator, and x86_64 API-34 system image.

Expected: version reports are written before generation.

- [ ] **Step 2: Generate and validate the canonical cube**

Run Blender twice with `--background --factory-startup` using `tools/asset_lab/generate_validation_cube.py`; require byte-identical `.glb` output; run `tools/asset_lab/validate_glb_asset.py --expected-name bb_validation_cube_1m --expected-size 1.0`.

Expected: generated dimensions are exactly `1.0 × 1.0 × 1.0 m` and independent validation passes.

- [ ] **Step 3: Create the throwaway Godot smoke project**

Create only under `build/master-asset-phase1/project/`. Copy the generated GLB there, construct a one-scene project with one camera, one directional light, and the cube, and add a script that logs:

```text
BAHRAIN_BRICK_CUBE_SMOKE_READY size=1.000,1.000,1.000
```

The project uses Godot 4.3 GL Compatibility, matching the frozen baseline configuration, solely for this isolated smoke.

Expected: `godot --headless --editor --import --quit --verbose` succeeds and imports the cube.

- [ ] **Step 4: Export and independently validate the smoke APK**

Create a throwaway debug keystore in runner temporary storage, export package `com.bahrainbrick.cubesmoke`, validate ZIP integrity, SHA-256, package badging, signature, and 4-byte alignment.

Expected: one non-empty signed debug APK is produced; no signing material is committed.

- [ ] **Step 5: Launch on API 34 and capture proof**

Boot a clean x86_64 API-34 emulator, install the exact hashed APK, launch `com.godot.game.GodotApp`, wait for the exact runtime-scale marker, capture logcat and a non-blank landscape screenshot, and fail on `FATAL EXCEPTION`, `Fatal signal`, or missing process/readiness.

Expected: emulator boot/install/launch pass, exact runtime marker is present, screenshot is landscape and non-blank.

- [ ] **Step 6: Upload evidence even on failure**

Upload `build/master-asset-phase1/` using pinned `actions/upload-artifact` with `if: always()`.

Expected: failures remain diagnosable; a passing run yields a durable artifact ID/digest.

### Task 2: Record Phase 1 capability matrix

**Files:**
- Create after the workflow result: `docs/asset_lab/MASTER_TASK_PHASE1_CAPABILITY.md`

**Interfaces:**
- Consumes: current hosted-container inventory, historical production artifacts, and the exact new Phase 1 workflow run.
- Produces: task-by-task `P1.001`–`P1.015` status and explicit route classification (`local`, `connected service`, `CI runner`, `manual workstation`, `blocked`).

- [ ] **Step 1: Record current hosted capabilities**

Record Python 3.13.5, Node 22.16.0, Git 2.47.3, Java 21.0.11, image/ffmpeg availability, and the absence of Blender, Godot, ADB, sdkmanager, avdmanager, Gradle, and a connected Remote Desktop device.

- [ ] **Step 2: Record verified CI capabilities**

Record historical verified versions and current smoke-run versions separately. Do not relabel emulator evidence as physical-device evidence.

- [ ] **Step 3: Close only supported task states**

Mark `P1.010` `NOT_APPLICABLE` because image-to-3D is not used. Mark `P1.015` PASS only if the exact smoke APK launches and produces both the runtime-scale marker and screenshot.

- [ ] **Step 4: Re-verify branch isolation**

Compare the master integration branch to baseline and require that only documentation/CI qualification files differ; all three protected gameplay blobs remain unchanged.

## Self-review

- The plan closes the only unsupported Phase 1 requirement without modifying production gameplay or assets.
- The test path is isolated and reversible.
- Emulator evidence remains explicitly distinct from the future named physical-reference-device gate.
