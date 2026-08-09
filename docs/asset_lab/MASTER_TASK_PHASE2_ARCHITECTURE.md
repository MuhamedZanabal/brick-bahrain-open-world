# Bahrain Brick 3D Asset Production — Phase 2 Repository Architecture

Recorded: 2026-08-09
Status: **PASS — PHASE 2 EXIT GATE SATISFIED**

## Entry authority

- Phase 1 closure record commit: `d676717561072631e3e5e7ddacc1fd69a69d4ee5`.
- Phase 2 implementation commit: `40b3d1f22a5bd691c2140a7b80fe6df1133fbe1b`.
- Implementation root tree: `c94a8f97138ce3efca773742df2539db4c3ae237`.
- Frozen game baseline: `5b4e2466ef84f3984f3bf336b31925d4d2e97a7f`.
- Execution branch: `work/bahrain-brick-master-asset-integration-v1`.

## Source/runtime directory contract

New production work now has an explicit source/runtime split.

### Source-side asset lab

- `asset_lab/source/` — editable source masters.
- `asset_lab/generators/` — deterministic Blender Python and supporting generator code.
- `asset_lab/references/` — licensed references and approved concept sheets.
- `asset_lab/materials/` — palette, trims, atlases, and texture sources.
- `asset_lab/exports/glb/` — validated runtime `.glb` exports only.
- `asset_lab/manifests/` — source/generated metadata; Phase 3 owns the authoritative schema.
- `asset_lab/reports/` — durable audit, validation, and performance reports.
- `asset_lab/evidence/` — durable renders, import screenshots, videos, and logs.
- `asset_lab/quarantine/` — rejected or legally uncertain inputs that must never enter runtime production.

Legacy `asset_lab/reports/`, `asset_lab/reviews/`, `asset_lab/runtime/`, and `asset_lab/source_authority/` content was preserved. Phase 2 did not rename or delete historical evidence.

### Runtime-side game roots

- `game/assets/bahrain/`.
- Runtime categories: `architecture`, `roads`, `waterfront`, `props`, `vegetation`, `vehicles`, `characters`, `materials`, and `decals`.
- First world-slice root: `game/scenes/world/chunks/manama_demo/`.

The Manama demo README preserves the first-milestone scope as one 200 × 200 m vertical slice; it does not authorize full-island production.

## Git LFS policy

`.gitattributes` now routes controlled binary source-of-truth files through Git LFS:

- `.blend` source masters;
- `.glb` asset-lab exports and `game/assets/bahrain/` runtime GLBs;
- high-resolution reference/material source formats including PNG/JPEG/TIFF/EXR/PSD/Krita;
- durable binary evidence including screenshots, video, APK/AAB, ZIP, and PDF;
- supported binary quarantine payloads when the project is legally permitted to retain them.

Verification workflow `31307181446` checked out commit `40b3d1f22a5bd691c2140a7b80fe6df1133fbe1b` with LFS enabled and recorded Git LFS `3.7.1`.

## Ignore policy

`.gitignore` preserves trackable source-side import settings while excluding generated caches and transient output:

- `.godot/` at repository and nested project levels;
- legacy generated `.import/` cache directories, **not** `*.import` source-side import-setting sidecars;
- Android `build/` and `.gradle/` output;
- Mono/editor caches;
- Phase 2 `build/` and `tmp/` work products;
- Blender recovery files;
- Python/tool caches and OS metadata.

This intentionally avoids a blanket `*.import` ignore because the accepted pipeline has historically used explicit GLB import sidecars as reproducibility evidence.

## Repository size and duplicate-binary gate

`tools/asset_lab/check_repository_binaries.py` scans the controlled Phase 2 binary roots and rejects:

- files above extension-specific limits (for example, 50 MiB for `.glb`, 100 MiB for `.blend`, and 16 MiB for PNG/JPEG/WebP);
- duplicate binary payloads at or above 256 KiB by SHA-256.

Controlled roots are `asset_lab/source`, `references`, `materials`, `exports`, `evidence`, `quarantine`, and `game/assets/bahrain`.

The test suite proves both rejection paths and proves that tiny duplicate evidence files do not trigger the duplicate threshold.

## Manifest/schema validation entry point

The standard command is:

```bash
python3 tools/asset_lab/run_repository_checks.py --root .
```

It runs the binary policy plus `tools/asset_lab/validate_manifest_schema.py`.

Phase 2 permits exactly one bootstrap state: no schema and no manifests. If a manifest appears without the authoritative schema, the check fails. When the schema exists, JSON is parsed and the command uses `jsonschema` for semantic validation when manifests exist; Phase 3 is responsible for adding the schema, examples, semantic rules, and pinned validation dependency/route.

## Verification evidence

GitHub Actions workflow: `.github/workflows/asset-repository-checks.yml`.

- Run: `31307181446`.
- Job: `93229269884` (`architecture`).
- Exact head: `40b3d1f22a5bd691c2140a7b80fe6df1133fbe1b`.
- Runner: Ubuntu 24.04.
- Python: `3.12.3`.
- Git LFS: `3.7.1`.
- Unit tests: `6/6` passed.
- Repository architecture check: PASS.
- Oversized controlled binaries: `0`.
- Duplicate controlled binaries: `0`.
- Manifest state: `EMPTY_BOOTSTRAP`, `manifest_count=0`, PASS only because Phase 3 schema/manifests do not exist yet.

## Protected-state verification

Frozen baseline root tree: `d7aa9d9e13dfe0c7e11df47f1071f2cbc44eabb7`.
Phase 2 implementation root tree: `c94a8f97138ce3efca773742df2539db4c3ae237`.

| Protected scope | Frozen baseline | Phase 2 implementation | Result |
|---|---|---|---|
| `project.godot` Git blob | `39d2826f026a2f4897084a1efb61a47550019fc0` | `39d2826f026a2f4897084a1efb61a47550019fc0` | UNCHANGED |
| `export_presets.cfg` Git blob | `b918b069b0bd46932c3ff00953ac1f0b1f17fa31` | `b918b069b0bd46932c3ff00953ac1f0b1f17fa31` | UNCHANGED |
| entire `scripts/` Git tree | `6eb39f718706d43c58f04da1d9f00802362405e3` | `6eb39f718706d43c58f04da1d9f00802362405e3` | UNCHANGED |

## Phase 2 task ledger

| Task | State | Evidence |
|---|---|---|
| `P2.001` | PASS | `asset_lab/source/` committed. |
| `P2.002` | PASS | `asset_lab/generators/` committed. |
| `P2.003` | PASS | `asset_lab/references/` committed. |
| `P2.004` | PASS | `asset_lab/materials/` committed. |
| `P2.005` | PASS | `asset_lab/exports/glb/` committed. |
| `P2.006` | PASS | `asset_lab/manifests/` committed with bootstrap contract. |
| `P2.007` | PASS | `asset_lab/reports/` retained and documented. |
| `P2.008` | PASS | `asset_lab/evidence/` committed. |
| `P2.009` | PASS | `asset_lab/quarantine/` committed. |
| `P2.010` | PASS | `game/assets/bahrain/` runtime root committed. |
| `P2.011` | PASS | All nine required runtime category subfolders committed. |
| `P2.012` | PASS | `game/scenes/world/chunks/manama_demo/` committed. |
| `P2.013` | PASS | Git LFS rules defined in `.gitattributes`; CI LFS checkout verified. |
| `P2.014` | PASS | Generated cache/import ignore policy defined without suppressing source import sidecars. |
| `P2.015` | PASS | Size/duplicate-binary checker added; rejection behavior unit-tested. |
| `P2.016` | PASS | Manifest/schema validation entry point added to the standard repository CI check. |
| `P2.017` | PASS | Empty directory structure committed with `.gitkeep` sentinels and explanatory READMEs at architecture boundaries. |

## Gate decision

**READY — PHASE 2 CLOSED.** Stable source/runtime separation, LFS rules, ignore rules, binary guards, and validation entry points exist and pass CI. Phase 3 may begin under the master task’s phase-order rule. This record does not authorize migration/deletion of legacy asset-lab evidence, mass asset renaming, merge, release, or deployment.
