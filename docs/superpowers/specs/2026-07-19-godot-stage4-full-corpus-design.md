# Godot 4.4.1 Stage 4 Full-Corpus Qualification Design

## Objective

Determine whether official Godot 4.4.1-stable produces byte-identical imported resources for the accepted complete 800-model Bahrain Brick source corpus under two independent clean full-source imports. Stop at Stage 4 classification.

## Frozen Boundaries

- Repository: `MuhamedZanabal/brick-bahrain-open-world`.
- PR #59 remains at `5b4e2466ef84f3984f3bf336b31925d4d2e97a7f`, open, draft and unmerged.
- Work is restricted to `ci/godot-engine-determinism-qualification-20260719`.
- Only Godot `4.4.1-stable` is authorized.
- Godot `4.5.2-stable` remains an inactive fallback; Godot `4.6.3-stable` is excluded.
- No Stage 5, Bahrain Brick compatibility execution, project migration, pack generation, Android tooling, APK work, merge or publication.

## Selected Architecture

The user-authorized deterministic sharded design is binding:

1. Verify the accepted source artifact and reconstruct the exact 1,502-file, 369,162,800-byte composite source tree.
2. Build an immutable, UTF-8-path-sorted authority containing exactly 800 model records: 578 GLB, 203 GLTF, 18 FBX and 1 OBJ. Verify the 436 required matrix GLBs as a strict subset.
3. Reverify the official Godot 4.4.1 release archive, source tag and extracted runtime.
4. Run one disposable authority import, retain only the 800 source-adjacent `.import` sidecars, and discard generated `.godot` state.
5. Run D1 and D2 as separate GitHub-hosted jobs with different runner identities and absolute roots, empty `.godot` directories and isolated XDG homes.
6. Materialize exactly forty 20-model binary shards per import plus one compact manifest-only artifact per import.
7. Run forty independent comparator jobs, one per matching shard pair.
8. Aggregate all shard reports into the Stage 4 engine decision and evidence artifacts.

A monolithic evidence artifact is rejected because it risks upload-size and failure-recovery problems. An 800-job per-model design is rejected because it creates unnecessary scheduling, API and evidence-assembly complexity.

## Components

### `stage4_full_corpus.py`

A single audited Python CLI with bounded subcommands:

- `build-authority`: enumerate models and dependencies; validate source and matrix authorities.
- `build-sidecars`: verify engine, run the authority import and package exact source-adjacent sidecars.
- `run-import`: execute D1 or D2 and produce complete per-model manifests and forty deterministic shard directories.
- `compare-shard`: verify two artifact inventories and compare exactly twenty models byte-for-byte.
- `aggregate`: require all forty shard reports and generate the final Stage 4 result.
- `inventory`: generate deterministic file inventories and SHA-256 values.

The CLI must never normalize generated binaries or substitute semantic equality for byte equality.

### Workflow

The GitHub Actions workflow uses these jobs:

- `record_locator`
- `contracts`
- `prepare_authority`
- `prepare_sidecars`
- `import_d1`
- `import_d2`
- `compare_shards` with a 40-entry matrix and bounded parallelism
- `aggregate_stage4`

Every evidence upload executes under `if: always()` semantics. Each job seeds a valid failure report before risky steps so infrastructure failure remains classifiable as Q6 rather than disappearing.

## Source and Dependency Authority

Model paths are sorted by exact UTF-8 bytes and assigned indices `0..799`. Safety validation rejects absolute paths, traversal, backslashes, NULs, duplicate normalized paths and case collisions.

Dependencies are format-aware:

- GLB and FBX normally have no external payload dependency unless explicitly discovered.
- GLTF JSON is parsed and all external non-data URIs are resolved relative to the model path.
- OBJ text is parsed for `mtllib` records; referenced MTL files are included, and each MTL is parsed for texture-map references.

Each source and dependency records byte size, SHA-256 and MD5. Missing dependencies or mismatched fixed counts stop authority construction without modifying the source tree.

The matrix manifest at `asset_lab/runtime/full_asset_matrix_manifest.json` must hash to `6aa202e2298fa514bfdb2ba10fd66237cc2d15005cdb2d6316a57d847ece8eff` and identify exactly 436 unique GLB paths, all present in the 578-GLB corpus.

## Sidecar Authority

The authority job performs one clean Godot 4.4.1 import. Only source-adjacent `.import` files are retained. Each of 800 sidecars must map to its exact source and contain the expected importer, resource type, canonical destination under `.godot/imported/`, source MD5, UID, destination list and importer parameters. The sidecar ZIP contains no `.godot` data.

## Independent Imports

D1 and D2 independently download and verify the same source artifact, engine artifact and sidecar authority. Each uses:

- a fresh hosted runner;
- a distinct fixed absolute root;
- empty `.godot` and isolated XDG directories;
- `LC_ALL=C.UTF-8`, `LANG=C.UTF-8`, `TZ=UTC` and `umask 022`;
- a 240-minute process-tree watchdog;
- pre/post CPU, memory and disk evidence.

Each model manifest records source, sidecar, imported binary and companion `.md5` identity. Any missing imported output is evidence, not an omission.

## Sharding and Comparison

Shard `NN` contains global indices `NN*20` through `NN*20+19`. Each shard includes only the twenty imported binaries, twenty companions, twenty source-adjacent sidecars, bounded logs and a deterministic inventory.

Each comparator verifies artifact metadata, internal inventory, model/path sets, source authority, sidecar bytes and fields, imported bytes, companion bytes and parsed source/destination MD5 values. One differing imported byte or destination MD5 yields `NONDETERMINISTIC` for that model. Missing or invalid evidence yields the exact non-pass category required by the directive.

Difference diagnostics are bounded but complete in path/hash coverage. Exact differing pairs are retained for all differences up to twenty, otherwise for the deterministic first twenty sorted paths.

## Classification

`STAGE4_PASS_PENDING_STAGE5` requires all 800 model comparisons with exact format and matrix counts, zero byte/MD5/sidecar differences, zero missing models, zero authority failures, zero import/harness failures and zero missing shard reports.

`Q3` requires both full imports to complete and at least one imported binary or destination-MD5 difference.

`Q6` covers timeout, missing evidence, source or sidecar authority failure, import failure not conclusively attributable to the engine, missing model/artifact/shard or harness failure. Q6 is not a determinism failure.

## Verification Strategy

Contract tests cover:

- exact engine/version exclusion rules;
- exact 800/578/203/18/1/436 count assertions;
- path safety and case-collision rejection;
- GLTF/OBJ dependency extraction;
- sidecar parsing and canonical destination validation;
- deterministic 40-by-20 shard mapping;
- byte-difference diagnostics;
- model and shard result enums;
- Q3/Q6/PASS aggregation boundaries;
- workflow job topology, bounded parallelism, unconditional uploads and explicit prohibitions.

Before triggering the workflow, the implementation is compiled, tested locally against the accepted source artifact and audited for forbidden commands and references to unauthorized engines.
