# Godot Stage 3 Repeatability Qualification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute and classify the exact Stage 3 byte-repeatability matrix for Godot 4.4.1-stable and 4.5.2-stable without modifying PR #59 or entering Stage 4.

**Architecture:** A Python evidence engine performs immutable authority verification, clean project materialization, bounded imports, snapshots, exact comparisons, diagnostics, and aggregation. A GitHub Actions workflow shards A/B/D by engine-resource, C by engine-resource-side, C comparison by engine-resource, then aggregates per engine and cross-version.

**Tech Stack:** Python 3.12 standard library, Bash, GitHub Actions on `ubuntu-24.04`, official Godot Linux binaries retained from Stage 2, immutable Stage 2 artifacts.

## Global Constraints

- Frozen PR #59 head must remain `5b4e2466ef84f3984f3bf336b31925d4d2e97a7f`, open, draft, and unmerged.
- Qualification branch is `ci/godot-engine-determinism-qualification-20260719`.
- Only Godot `4.4.1-stable` and `4.5.2-stable` may be tested.
- The exact eight-resource Stage 2 corpus and per-pair sidecar authorities are mandatory.
- Every import starts without `.godot` and with isolated XDG/HOME state.
- Byte inequality is a determinism failure; semantic equivalence is irrelevant.
- Every job uploads evidence under `if: always()`.
- Stop after Stage 3 classification. No Stage 4, Bahrain Brick execution, migration, packs, Android tooling, APK/AAB work, merge, or publication.

---

### Task 1: Stage 3 Evidence Engine Contracts

**Files:**
- Create: `.github/forensics/qualification/stage3/test_stage3_qualification.py`
- Create: `.github/forensics/qualification/stage3/stage3_qualification.py`

**Interfaces:**
- Produces CLI subcommands: `verify-authority`, `run-abd`, `run-c-side`, `compare-c`, `aggregate-engine`, `aggregate-cross`, `inventory`.
- Produces JSON schemas: import snapshot, experiment cell, resource result, engine result, cross-version result.

- [ ] **Step 1: Write failing contract tests**

Create tests that assert the exact two-engine/eight-resource matrix; allowed cell values; strict different-path proof; strict independent-runner proof; strict overlap proof; exact byte/MD5/path-set comparison; Q2 versus Q6 boundaries; and both-pass version preference.

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m unittest -v .github/forensics/qualification/stage3/test_stage3_qualification.py
```

Expected: failure because `stage3_qualification.py` does not exist.

- [ ] **Step 3: Implement pure validation and comparison functions**

Implement typed helpers for SHA-256/MD5, sidecar parsing, interval overlap, generated-path inventory, snapshot comparison, bounded byte diagnostics, and classification. Keep filesystem and process execution behind narrow functions.

- [ ] **Step 4: Implement project materialization and watchdog execution**

Materialize source/dependency/sidecar bytes into fresh roots, create deterministic `project.godot`, isolate XDG/HOME, normalize locale/timezone/umask/thread controls, run Godot with process-group termination, and record complete snapshots.

- [ ] **Step 5: Implement experiment and aggregate commands**

Implement A1/A2/A3 sequential rematerialization, B1/B2 different roots, C single-side execution, C comparator, concurrent D with overlap proof, per-resource result assembly, per-engine aggregation, and cross-version candidate ordering.

- [ ] **Step 6: Run unit tests**

Run:

```bash
python3 -m py_compile .github/forensics/qualification/stage3/stage3_qualification.py
python3 -m unittest -v .github/forensics/qualification/stage3/test_stage3_qualification.py
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add .github/forensics/qualification/stage3
git commit -m "ci(stage3): add repeatability evidence engine"
```

### Task 2: Stage 3 Sharded Workflow

**Files:**
- Create: `.github/workflows/godot-engine-qualification-stage3-repeatability.yml`

**Interfaces:**
- Consumes Stage 2 run `29685721858` artifacts.
- Produces 16 A/B/D artifacts, 32 C-side artifacts, 16 C-comparison artifacts, two engine aggregates, one cross-version aggregate, and a locator commit.

- [ ] **Step 1: Add static workflow contract checks**

Add an initial job that compiles and unit-tests the analyzer, validates the exact 16/32/16 matrix cardinalities, rejects `4.6.3-stable`, and verifies all retained artifact metadata by ID, name, digest, run ID, head SHA, and non-expiry.

- [ ] **Step 2: Add A/B/D matrix jobs**

Use `2 × 8 = 16` jobs with bounded parallelism. Download the exact corpus, engine artifact, and Stage 2 per-resource artifact. Run `verify-authority` and `run-abd`. Seed fallback `HARNESS_FAILURE` evidence before risky steps. Upload under `if: always()`.

- [ ] **Step 3: Add independent C-side jobs**

Use `2 × 8 × 2 = 32` jobs. Each job runs exactly one side, records GitHub runner identity, and uploads independently. Do not copy generated output between sides.

- [ ] **Step 4: Add C comparison jobs**

Use `2 × 8 = 16` jobs. Download both side artifacts, prove distinct job and runner identities, compare exact bytes/MD5/path sets, and upload comparator evidence under `if: always()`.

- [ ] **Step 5: Add per-engine and cross-version aggregates**

Download all resource and comparator artifacts. Generate `ENGINE_STAGE3_RESULT.json`, `ENGINE_STAGE3_EXPERIMENT_MATRIX.json`, `ENGINE_STAGE3_DIFFERING_PATHS.txt`, and `STAGE3_CROSS_VERSION_QUALIFICATION.json`. Preserve Gate 4 and Gate 5 inherited statuses and downstream blocker text.

- [ ] **Step 6: Add locator recording**

Record the Stage 3 run ID and workflow SHA on the detached qualification branch only after the workflow starts. Rebase before push so the locator commit is fast-forward and does not alter the workflow authority commit.

- [ ] **Step 7: Validate YAML and prohibition surface**

Run a static parser and assertions proving no references to Godot 4.6.3, the 800-model corpus, Android SDK, export templates, APK/AAB commands, project packs, or PR #59 branch writes.

- [ ] **Step 8: Commit and trigger**

```bash
git add .github/workflows/godot-engine-qualification-stage3-repeatability.yml
git commit -m "ci(stage3): run repeatability qualification"
git push origin HEAD:ci/godot-engine-determinism-qualification-20260719
```

Expected: push triggers exactly one Stage 3 workflow run.

### Task 3: Run Inspection and Evidence Verification

**Files:**
- Read only: GitHub Actions jobs, logs, and artifacts from the Stage 3 run.

**Interfaces:**
- Consumes all Stage 3 artifacts.
- Produces the mandated 36-point checkpoint response.

- [ ] **Step 1: Verify run and job topology**

Confirm workflow head SHA, branch, expected job counts, independent C job IDs, bounded parallelism, and no Stage 4/Android jobs.

- [ ] **Step 2: Inspect failures before classification**

For every non-success job, retrieve steps and logs. Distinguish engine import failure from timeout, harness failure, missing evidence, and proven nondeterminism.

- [ ] **Step 3: Verify every artifact**

List artifacts, record IDs and GitHub artifact digests, download all per-engine and cross-version aggregates, and verify internal inventories and JSON schemas.

- [ ] **Step 4: Revalidate frozen PR**

Fetch PR #59 after the run and confirm the head, state, draft status, merge state, branch, and commit count are unchanged.

- [ ] **Step 5: Revalidate qualification branch locator**

Confirm the branch head is the Stage 3 locator commit and the locator points to the immutable Stage 3 workflow commit and run ID.

- [ ] **Step 6: Return exact checkpoint**

Return only numbered items 1 through 36 in the user-mandated order. Do not begin Stage 4.
