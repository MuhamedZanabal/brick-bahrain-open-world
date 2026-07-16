# Bahrain Brick Option A — Full Matrix Rollout Plan

**Goal:** Scale the approved Batch 1 V3.1 art, material, LOD, Godot, and Android authority across the complete Option A production matrix: 48 architecture sources × 3 profiles × 3 LODs plus four commercial modules, for exactly 436 validated GLBs.

## Authority and boundaries

- Integration branch: `work/bahrain-brick-asset-lab-integration-v1`.
- Batch 1 authority: `d8f2c0f18cab2cc0a0d9eee13be2e94a2e2c5fb5`.
- Frozen premium authority: `e26ec912db5c10d071a8e120010bdb5a9a136f17`.
- Keep PR #57 and PR #58 open, draft, and unmerged.
- Preserve protected gameplay blobs byte-for-byte.
- Missing evidence is a failure; technical validity never substitutes for art/runtime evidence.

## Execution batches

### 1. Contract-first full generator

- Add ordinary-Python planning and runtime-manifest APIs.
- Require 48 canonical records with family counts `14/18/16`.
- Require exactly 432 architecture paths and four commercial paths.
- Inherit the approved V3.1 builders and shared 24-texture mobile authority.
- Apply family-specific builders to every non-master record.
- Keep simplified collision only on architecture LOD0 and commercial outputs.

### 2. Fail-closed matrix validation

- Validate exact path closure and manifest ownership.
- Require embedded textures/images on all 436 outputs.
- Require strict `LOD0 > LOD1 > LOD2` triangle reduction.
- Require `low <= balanced <= high` geometry and strict profile byte ordering.
- Require exactly 148 collision-bearing outputs.
- Require 436 unique SHA-256 values.
- Run Khronos validation independently for every GLB.

### 3. Real Godot-world integration

- Install all profiles at `assets/generated/full_matrix`.
- Make the generated runtime manifest the architecture authority.
- Select one explicit quality profile and load three LOD resources per placed asset.
- Use distance thresholds with hysteresis through the approved runtime controller.
- Preserve existing villas, roads, street props, clean-room supporting assets, world spawn, and protected controls.
- Import every runtime resource cleanly before overlay/regression execution.

### 4. Full regression and APK gate

- Run existing smoke, controls, presentation, premium-world, premium-presentation, lifecycle, and resource-repeat suites.
- Require protected pre/post reports to be byte-identical.
- Export a new API-34 signed QA APK with version code 1405.
- Derive the emulator candidate hash from the exact exported APK.
- Install, launch, enter landscape, observe world readiness, perform the fixed 10-minute traversal and 30-minute soak, sample memory, and scan continuous logcat.

### 5. Evidence and checkpoint closure

- Upload all 436 GLBs, 24 textures, reports, APK, screenshots, logs, and checksum inventory.
- Refresh the persistent 467-task ledger only for evidence-backed tasks.
- Record physical-device verification separately as incomplete unless the exact APK is executed on a named device.
- Add a factual evidence comment to PR #57 and leave it draft/unmerged.

## Completion criteria

The rollout is complete only when the workflow proves: `48` sources, `432` architecture derivatives, `4` commercial outputs, `436/436` structural and Khronos passes, `436/436` textured outputs, `436` unique hashes, `148/148` collision-policy passes, clean Godot import, all recorded regressions green, protected authorities unchanged, signed APK exported and structurally valid, API-34 traversal/soak green, and complete evidence uploaded.
