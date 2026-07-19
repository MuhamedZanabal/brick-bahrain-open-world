# Godot 4.4.1 and 4.5.2 Stage 3 Repeatability Qualification Design

## Objective

Determine whether the two Stage 2-qualified official Godot engines remain byte-deterministic for the exact authoritative eight-resource corpus under sequential repetition, absolute-path variation, independent GitHub-hosted runners, and concurrent isolated imports. Stop at Stage 3 classification. Do not execute Stage 4, Bahrain Brick, migration, packs, Android tooling, or APK work.

## Frozen Authorities

- Repository: `MuhamedZanabal/brick-bahrain-open-world`
- Frozen PR #59 head: `5b4e2466ef84f3984f3bf336b31925d4d2e97a7f`
- Detached qualification branch: `ci/godot-engine-determinism-qualification-20260719`
- Accepted Stage 2 run: `29685721858`
- Accepted Stage 2 workflow commit: `23efeab85489ef1efafca60a0c0791507fc3f5dc`
- Accepted corpus artifact: `stage2-exact-corpus-29685721858`, artifact `8442001215`, digest `sha256:9b2d4b4746567b98abd20800159aafe47eb6cf9688921f2e51ae81ff4da5e12f`
- Godot 4.4.1 engine artifact: `stage2-engine-package-4.4.1-stable-29685721858`, artifact `8441999232`, digest `sha256:267c4d2d5fb9388c92ef537443142fbff6a6d939188c32905d7b0f6a53ba2809`
- Godot 4.5.2 engine artifact: `stage2-engine-package-4.5.2-stable-29685721858`, artifact `8441999064`, digest `sha256:86847c1a5a31a11d7208f8daf4917e2022d613ac31d40918765ac45f25331ad9`

Godot 4.6.3 is excluded from every Stage 3 matrix and downstream decision.

## Architecture

The workflow uses immutable Stage 2 artifacts as its only corpus, engine, and sidecar inputs. It creates exactly 16 engine-resource authorities. Each authority has one A/B/D job, two independent C-side jobs, and one C comparator. Per-engine and cross-version aggregators classify results without executing imports.

The implementation is split into:

1. `stage3_qualification.py`: deterministic materialization, authority verification, watchdog execution, snapshots, byte comparisons, bounded diagnostics, and aggregation.
2. `test_stage3_qualification.py`: contract tests for matrix shape, sidecar verification, path isolation, overlap proof, comparison classification, and aggregate classification.
3. `godot-engine-qualification-stage3-repeatability.yml`: bounded GitHub Actions orchestration, artifact retrieval, sharding, independent-runner comparison, unconditional evidence uploads, and locator recording.

## Input and Sidecar Authority

For every engine-resource pair, the workflow downloads the exact successful Stage 2 per-resource artifact named `stage2-resource-<engine>-<resource>-29685721858`. The analyzer verifies:

- artifact provenance and non-expiry;
- `RESOURCE_QUALIFICATION.json` reports `PASS` for the exact engine and resource;
- the source path and hashes match `CORPUS_AUTHORITY.json`;
- the source-adjacent sidecar exists beneath `sidecar_authority/`;
- sidecar SHA-256, source path, destination path, importer, type, UID, and parameter hash are recorded;
- the same authority directory bytes are copied into every repetition for that engine-resource pair.

No generated `.godot` content, imported binary, `uid_cache.bin`, editor cache, or Stage 2 generated output is reused.

## Import Materialization

Each repetition creates a new project root containing only:

- a minimal deterministic `project.godot`;
- the selected source and dependency bytes from the accepted corpus artifact;
- exact Stage 2 source-adjacent `.import` sidecars;
- an initially absent `.godot` directory;
- isolated `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, and `HOME`.

Locale is `C.UTF-8`, timezone is `UTC`, umask is `0022`, and thread-related controls are normalized. The official Stage 2 engine binary is verified by SHA-256 and `--version` before use.

## Experiment Semantics

### Experiment A

A1, A2, and A3 use the same canonical absolute path. The project root is fully deleted and rematerialized between imports. All three pairwise comparisons must pass imported-byte, destination-MD5, and generated-path-set equality.

### Experiment B

B1 and B2 use deliberately different absolute roots while preserving the same project-relative layout. The analyzer records and proves the roots differ. Imported bytes, destination MD5, path sets, and export-relevant UID state must match.

### Experiment C

C1 and C2 execute as separate matrix jobs on separate GitHub-hosted runners. Each uploads an independent result artifact containing generated snapshots and evidence. A separate comparator downloads both artifacts and proves distinct runner IDs before exact comparison.

### Experiment D

D1 and D2 are materialized in separate roots and launched concurrently. Each process has isolated mutable state. The analyzer records start and completion timestamps and requires strict interval overlap. Lack of overlap is `HARNESS_FAILURE`, never `PASS`.

## Evidence and Classification

Every import snapshot records all fields mandated by the Stage 3 directive. Byte differences generate bounded diagnostics only. Every cell is one of `PASS`, `NONDETERMINISTIC`, `IMPORT_FAILURE`, `TIMEOUT`, `HARNESS_FAILURE`, or `MISSING_EVIDENCE`.

An engine is `STAGE3_PASS_PENDING_STAGE4` only if all 32 experiment cells pass with no differing binaries, MD5 values, failures, timeouts, harness failures, or missing evidence. A proven byte or destination-MD5 mismatch is `Q2`. Any incomplete or operationally inconclusive evidence is `Q6`.

If both pass, both remain Stage 4 eligible; 4.4.1 is the preferred first candidate and 4.5.2 is the qualified fallback. Gate 4 remains failed from the retained APK reproducibility boundary; Gate 5 remains passed only for the two original retained APKs.

## Safety Boundary

The workflow contains no reference to Godot 4.6.3, the 800-model corpus, Bahrain Brick project execution, project migration, pack generation, Android SDK tooling, APK/AAB export, installation, execution, merge, or publication. PR #59 is read and revalidated only; it is never checked out for execution or modified.
