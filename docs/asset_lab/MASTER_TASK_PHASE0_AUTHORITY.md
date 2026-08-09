# Bahrain Brick 3D Asset Production — Phase 0 Authority Record

Recorded: 2026-08-09

## Purpose

This record freezes the authority, safety, scope, IP, directory, and rollback controls required before the 3D Asset Production master task may enter Phase 1. It is deliberately documentation-only. It does not authorize renderer changes, gameplay-control changes, package/signing changes, mass modeling, release, merge, or publication.

## Governing repositories and immutable authorities

### Game repository

- Repository: `MuhamedZanabal/brick-bahrain-open-world`
- Accepted playable vertical-slice baseline branch: `work/bahrain-brick-manama-souq-vertical-slice-v1`
- Accepted playable vertical-slice baseline commit: `5b4e2466ef84f3984f3bf336b31925d4d2e97a7f`
- Dedicated master-asset integration branch: `work/bahrain-brick-master-asset-integration-v1`
- Integration branch creation rule: created directly from the exact baseline commit above; the baseline branch itself remains untouched.
- Godot authority: `4.3.stable.official.77dcf97d8`

The later renderer-debugging lineage remains separate. `work/bahrain-brick-renderer-runtime-debugging-r1` is governed by an `ENGINEERING_STOP` and is not promoted to the asset-production baseline. The existing Codex-control branch is also a separate control-plane lineage and is not evidence that R1 renderer gates passed.

### Asset repository

- Repository: `MuhamedZanabal/Bahrain_bricks_Assets`
- Frozen source authority branch: `work/bahrain-brick-complete-asset-system-v1`
- Frozen source authority commit: `84ac94399262f71f29bf65dd553cd7729d87cce0`
- Source bundle SHA-256 recorded by the existing game integration lineage: `98e3964a1c84200c8d764116bc027678de0019fc6481ca41825ed606aa2a9c41`
- Open integrity-correction branch: `work/source-integrity-ledger-v1`
- Integrity-correction head: `7aed2cf05f63e0c3c607a98acde454ff103584eb`
- Relationship: the integrity-correction head is exactly three commits ahead of the frozen source authority with `84ac94399262f71f29bf65dd553cd7729d87cce0` as merge base.

The integrity-correction branch fixes checksum-ledger mechanics but remains an open draft PR. It is not silently substituted for the frozen asset source authority by this record.

## Protected gameplay controls

Asset production and integration must not change these files without a separately reproduced integration defect and explicit scoped authorization:

| Protected file | Expected Git blob ID at baseline |
|---|---|
| `scripts/world.gd` | `c72ca10bdde7e421f3df6421240588946bb55e4f` |
| `scripts/player_controller.gd` | `badf5f651c33450c140e4a7bebb37a1fe25ac586` |
| `scripts/touch_input.gd` | `b19e59c2ce6d88e1154b8a9fa4cddcc3242898dd` |

Protection is whole-file byte identity. No separate function-level hash is maintained: any function edit necessarily changes the protected file blob and fails the control. Asset work must also avoid renderer defaults, package identity, signing configuration/material, release authority, and protected authority ledgers unless a separate approved change explicitly scopes them.

## Phase 0 task ledger

| Task | State | Evidence / decision |
|---|---|---|
| `P0.001` | PASS | Game repository is exactly `MuhamedZanabal/brick-bahrain-open-world`. |
| `P0.002` | PASS | Asset repository is exactly `MuhamedZanabal/Bahrain_bricks_Assets`. |
| `P0.003` | PASS | Accepted game baseline branch is `work/bahrain-brick-manama-souq-vertical-slice-v1`. |
| `P0.004` | PASS | Full baseline SHA is `5b4e2466ef84f3984f3bf336b31925d4d2e97a7f`. |
| `P0.005` | PASS | Protected gameplay controls are the three whole files listed above; renderer/package/signing/release/authority boundaries remain separately protected. |
| `P0.006` | PASS | Exact expected Git blob IDs are recorded above and were resolved directly at the frozen baseline. |
| `P0.007` | PASS — HOSTED COMMITTED-TREE MODE | This hosted execution surface mutates GitHub commits directly and has no mutable local worktree. The source baseline is therefore the exact committed tree at `5b4e2466...`; there are no uncommitted local changes to inventory here. Any later attached workstation/runner must independently run `git status --porcelain=v1` before mutation and record non-empty output. |
| `P0.008` | PASS | `work/bahrain-brick-master-asset-integration-v1` was created directly from exact baseline `5b4e2466...`; no protected branch ref was moved. |
| `P0.009` | PASS | Starting authority remains reproducible through the untouched baseline branch and exact SHA; the child integration branch preserves lineage without force-updating any existing ref. |
| `P0.010` | PASS | First deliverable is one 200 × 200 m playable Manama vertical slice. |
| `P0.011` | PASS | Full-island production is explicitly deferred until the vertical slice passes required Android gates. |
| `P0.012` | PASS | Original construction-toy style means independently authored modular geometry, exaggerated readable proportions, original connection/detail language, and project-owned or properly licensed source material; it must not imitate protected proprietary systems. |
| `P0.013` | PASS | Protected toy-brand logos, exact proprietary figure geometry, proprietary connection systems, copied commercial game assets, unlicensed meshes, and unverified redistributable binaries are prohibited. |
| `P0.014` | PASS | Allowed future roots are defined in the directory policy below. Phase 2 is responsible for creating and enforcing them. |
| `P0.015` | PASS | Non-destructive rollback procedure is defined below. |

## Scope freeze

The first production milestone is one **200 × 200 m playable Manama block**, not a full Bahrain open world. It must ultimately be walkable and drivable and use only approved assets. Full-island production is deferred until the vertical slice satisfies its Android runtime gates.

Existing historical asset/runtime evidence may be reused only when its exact commit, artifact, toolchain, and test conditions match the requirement being claimed. Emulator evidence must never be relabeled as named physical-device evidence.

## Original construction-toy IP policy

Permitted:

- original modular plastic/construction-toy-inspired proportions;
- independent project-owned geometry and deterministic generators;
- properly licensed external source material whose commercial, modification, and redistribution rights are documented;
- fictional business branding and original decorative connection/seam language.

Prohibited:

- protected toy-brand logos or word marks;
- exact copies of proprietary figure/minifigure geometry;
- proprietary connection systems reproduced as exact manufacturer parts;
- copied commercial-game assets or ripped models;
- unlicensed or provenance-unclear meshes/textures;
- real commercial trademarks used without permission when fictional alternatives are sufficient.

Ambiguous inputs go to quarantine and cannot enter runtime production.

## Directory policy frozen for Phase 2

Phase 2 must create or reconcile these roots without moving accepted historical evidence destructively.

### Asset-source repository targets

- `asset_lab/source/` — editable `.blend` masters and other editable source files.
- `asset_lab/generators/` — deterministic Blender Python and supporting generator code.
- `asset_lab/references/` — licensed references and concept sheets only.
- `asset_lab/materials/` — palette, trims, atlases, and source textures.
- `asset_lab/exports/glb/` — validated runtime `.glb` exports only.
- `asset_lab/manifests/` — source and generated manifest metadata.
- `asset_lab/reports/` — machine/human validation and performance reports.
- `asset_lab/evidence/` — renders, import screenshots, videos, and logs.
- `asset_lab/quarantine/` — rejected, license-unclear, or technically unsafe inputs.

### Game-repository targets

- `game/assets/bahrain/architecture/`
- `game/assets/bahrain/roads/`
- `game/assets/bahrain/waterfront/`
- `game/assets/bahrain/props/`
- `game/assets/bahrain/vegetation/`
- `game/assets/bahrain/vehicles/`
- `game/assets/bahrain/characters/`
- `game/assets/bahrain/materials/`
- `game/assets/bahrain/decals/`
- `game/scenes/world/chunks/manama_demo/`

Historical repository paths remain evidence and are not automatically relocated. Phase 2 must use additive migration/compatibility rules when old references still exist.

## Known authority conflicts carried forward

1. **Asset ID convention conflict:** the current asset manifest uses historical `bh_...` IDs, while the new master task requires `bb_<category>_<family>_<variant>_<nnn>`. Phase 3 must introduce a compatibility/deprecation strategy; existing accepted references must not be broken by a blind rename.
2. **Standalone asset status is stale relative to later integration evidence:** the source repository status file records zero production GLBs and no Blender/Godot/Android runtime, while the later game-integration lineage contains verified generated/runtime evidence. Phase 1–3 reconciliation must distinguish historical integration proof from source-repository-native proof.
3. **Renderer/device boundary:** current project authority remains at `ENGINEERING_STOP` for renderer qualification pending named physical-device and/or upstream Godot/driver evidence. Asset-pipeline work must not use this master task as authority to resume exhausted emulator renderer experiments.

## Rollback procedure

Rollback is branch abandonment, not destructive Git history rewriting.

1. Do not merge `work/bahrain-brick-master-asset-integration-v1` while a mandatory gate is failing.
2. To return to the accepted game state, use the untouched branch `work/bahrain-brick-manama-souq-vertical-slice-v1` at exact commit `5b4e2466ef84f3984f3bf336b31925d4d2e97a7f`.
3. Do not force-push, hard-reset shared refs, delete evidence branches, rewrite the frozen asset authority, or alter unrelated work.
4. The standalone asset source authority remains `84ac94399262f71f29bf65dd553cd7729d87cce0` unless a later explicit authority decision promotes a reviewed descendant.
5. If a later integration defect is caused by an asset, remove/revert only the additive integration commit(s) on the child branch and preserve the evidence needed to reproduce the defect.

## Phase 0 exit decision

**PASS.** All `P0.001`–`P0.015` controls have an explicit record for the hosted committed-tree execution model. Phase 1 may begin, but its toolchain capability matrix must preserve the R1 renderer stop and must label local, connected-service, CI-runner, emulator, and physical-device evidence separately.
