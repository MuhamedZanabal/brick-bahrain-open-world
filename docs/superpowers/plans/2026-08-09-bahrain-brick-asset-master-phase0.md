# Bahrain Brick Asset Master Phase 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze the exact game/asset authorities, protected gameplay controls, vertical-slice scope, IP rules, repository boundaries, and rollback procedure required by Phase 0 of the Bahrain Brick 3D Asset Production master task before any new toolchain or asset-production work begins.

**Architecture:** Treat the frozen Manama vertical-slice commit as the game baseline and preserve all later renderer/debugging and Codex-control branches as separate evidence lineages. Record the standalone asset repository authority without silently promoting its open integrity-correction PR. The Phase 0 deliverable is documentation-only and must not modify gameplay, renderer, package, signing, release, or asset binaries.

**Tech Stack:** Git/GitHub immutable commit IDs, Godot 4.3 project authority, Markdown evidence records.

## Global Constraints

- Game repository: `MuhamedZanabal/brick-bahrain-open-world`.
- Asset repository: `MuhamedZanabal/Bahrain_bricks_Assets`.
- Frozen Manama vertical-slice baseline: branch `work/bahrain-brick-manama-souq-vertical-slice-v1`, commit `5b4e2466ef84f3984f3bf336b31925d4d2e97a7f`.
- Current renderer-debugging lineage remains `ENGINEERING_STOP`; do not select a renderer, change renderer defaults, or run another emulator renderer/engine experiment.
- Godot engine authority remains `4.3.stable.official.77dcf97d8`.
- First asset milestone is one 200 × 200 m playable Manama block; full-island production is deferred until the vertical slice passes Android gates.
- Gameplay controls and authority logic remain frozen unless a separately reproduced integration defect authorizes a scoped change.
- Asset identity must be original construction-toy style; protected logos, exact proprietary figure geometry, and proprietary connection systems are prohibited.
- Do not merge, publish, release, force-update, rebase protected branches, or alter signing/access controls.

---

### Task 1: Record Phase 0 authority and rollback evidence

**Files:**
- Create: `docs/asset_lab/MASTER_TASK_PHASE0_AUTHORITY.md`

**Interfaces:**
- Consumes: frozen game baseline `5b4e2466ef84f3984f3bf336b31925d4d2e97a7f`; asset source authority `84ac94399262f71f29bf65dd553cd7729d87cce0`; protected Git blob IDs for `scripts/world.gd`, `scripts/player_controller.gd`, and `scripts/touch_input.gd`.
- Produces: one human-readable Phase 0 authority record that maps `P0.001` through `P0.015` to exact evidence and defines the only permitted Phase 1 entry baseline.

- [ ] **Step 1: Verify exact protected gameplay blobs at the frozen baseline**

Read these files at commit `5b4e2466ef84f3984f3bf336b31925d4d2e97a7f` and require these Git blob IDs:

```text
scripts/world.gd             c72ca10bdde7e421f3df6421240588946bb55e4f
scripts/player_controller.gd badf5f651c33450c140e4a7bebb37a1fe25ac586
scripts/touch_input.gd       b19e59c2ce6d88e1154b8a9fa4cddcc3242898dd
```

Expected: all three paths resolve to the listed blobs.

- [ ] **Step 2: Verify source-asset authority and integrity descendant relationship**

Require:

```text
source authority branch: work/bahrain-brick-complete-asset-system-v1
source authority commit: 84ac94399262f71f29bf65dd553cd7729d87cce0
integrity branch:        work/source-integrity-ledger-v1
integrity head:          7aed2cf05f63e0c3c607a98acde454ff103584eb
relationship:            7aed2cf... is exactly 3 commits ahead of 84ac943... with 84ac943... as merge base
```

Expected: record the integrity branch as a correction lineage only; do not silently replace the frozen source authority while PR #3 remains an open draft.

- [ ] **Step 3: Write the authority record**

Create `docs/asset_lab/MASTER_TASK_PHASE0_AUTHORITY.md` with:

- exact repositories, branches, and commits;
- `P0.001`–`P0.015` status table;
- whole-file byte-protection rule for the three protected gameplay files;
- explicit 200 × 200 m Manama vertical-slice scope and full-island deferral;
- original-construction-toy IP policy;
- allowed source/runtime/evidence/quarantine directory roots to be created in Phase 2;
- hosted-execution note that GitHub API operates on committed trees and has no mutable local working tree;
- rollback procedure that abandons this child branch and returns to the immutable baseline without resetting, force-pushing, deleting, or altering unrelated branches.

Expected: no task is marked complete without named evidence; any caveat is explicitly recorded.

- [ ] **Step 4: Re-read and verify the committed authority record**

Read the file from `work/bahrain-brick-master-asset-integration-v1` and check that all 15 task IDs occur exactly once in the status table and all three protected blob IDs are present.

Expected: the document is internally consistent and contains no claim that renderer R1, physical-device qualification, or final release has passed.

- [ ] **Step 5: Verify branch isolation**

Compare `work/bahrain-brick-manama-souq-vertical-slice-v1` to `work/bahrain-brick-master-asset-integration-v1`.

Expected: only Phase 0 documentation/planning files differ; `scripts/world.gd`, `scripts/player_controller.gd`, and `scripts/touch_input.gd` are unchanged.

## Self-review

- Spec coverage: this plan covers only Phase 0 because the master task forbids entering Phase 1 before Phase 0 evidence exists.
- Placeholder scan: no implementation placeholder is permitted; every required identifier is explicit above.
- Authority consistency: the frozen vertical-slice baseline is not replaced by the later R1 diagnostic branch; the asset source authority is not silently replaced by its open integrity-correction descendant.
