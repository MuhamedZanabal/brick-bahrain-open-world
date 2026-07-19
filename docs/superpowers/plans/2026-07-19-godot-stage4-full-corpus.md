# Godot 4.4.1 Stage 4 Full-Corpus Qualification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, execute and verify the Godot 4.4.1 Stage 4 two-runner byte-determinism qualification for the exact accepted 800-model corpus.

**Architecture:** A tested Python evidence engine builds source and sidecar authorities, runs two clean full imports, shards each result into forty 20-model artifacts, compares matching shards and aggregates the exact PASS/Q3/Q6 decision. A bounded GitHub Actions workflow pins all immutable input artifacts and uploads evidence unconditionally.

**Tech Stack:** Python 3 standard library, Godot 4.4.1 headless editor, Bash, GitHub Actions, JSON and ZIP evidence artifacts.

## Global Constraints

- Modify only `ci/godot-engine-determinism-qualification-20260719`.
- Keep PR #59 at `5b4e2466ef84f3984f3bf336b31925d4d2e97a7f`, open, draft and unmerged.
- Test only Godot `4.4.1-stable`; do not run 4.5.2 or 4.6.3.
- Exact corpus counts: 800 total, 578 GLB, 203 GLTF, 18 FBX, 1 OBJ, 436 matrix GLBs.
- Use exact byte equality; never normalize generated binaries.
- Do not enter Stage 5 or run project compatibility, migration, packs, Android tooling or APK operations.
- Every risky job seeds evidence and uploads with `if: always()`.

---

### Task 1: Authority and Dependency Contract Tests

**Files:**
- Create: `.github/forensics/qualification/stage4_full_corpus/test_stage4_full_corpus.py`
- Create: `.github/forensics/qualification/stage4_full_corpus/stage4_full_corpus.py`

**Interfaces:**
- Produces constants `ENGINE_VERSION`, `MODEL_COUNTS`, `MODEL_RESULT_VALUES`.
- Produces `normalize_relative_path(str) -> str`, `extract_dependencies(Path, str, Path) -> list[str]`, `shard_bounds(int) -> tuple[int,int]`.

- [ ] **Step 1: Write failing tests**

```python
class AuthorityTests(unittest.TestCase):
    def test_fixed_authorities(self):
        self.assertEqual(stage4.ENGINE_VERSION, "4.4.1-stable")
        self.assertEqual(stage4.MODEL_COUNTS, {"GLB": 578, "GLTF": 203, "FBX": 18, "OBJ": 1})
        self.assertNotIn("4.5.2", json.dumps(stage4.__dict__, default=str))

    def test_shards_cover_exactly_800(self):
        self.assertEqual(stage4.shard_bounds(0), (0, 19))
        self.assertEqual(stage4.shard_bounds(39), (780, 799))
        self.assertEqual({i for s in range(40) for i in range(*stage4.shard_bounds(s)[:1], stage4.shard_bounds(s)[1] + 1)}, set(range(800)))

    def test_paths_reject_traversal_and_backslashes(self):
        for value in ("../x.glb", "/x.glb", "a\\x.glb", "a/./x.glb"):
            with self.assertRaises(stage4.AuthorityError):
                stage4.normalize_relative_path(value)
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `python3 -m unittest -v .github/forensics/qualification/stage4_full_corpus/test_stage4_full_corpus.py`

Expected: import or attribute failures because `stage4_full_corpus.py` is absent or incomplete.

- [ ] **Step 3: Implement constants, hashing, path safety, GLTF/OBJ dependency parsing and shard bounds**

```python
ENGINE_VERSION = "4.4.1-stable"
MODEL_COUNTS = {"GLB": 578, "GLTF": 203, "FBX": 18, "OBJ": 1}
MODEL_RESULT_VALUES = {"PASS", "NONDETERMINISTIC", "MISSING_D1", "MISSING_D2", "SOURCE_AUTHORITY_FAILURE", "SIDECAR_AUTHORITY_FAILURE", "IMPORT_FAILURE", "HARNESS_FAILURE"}

def shard_bounds(index: int) -> tuple[int, int]:
    if index not in range(40):
        raise AuthorityError(f"invalid shard: {index}")
    return index * 20, index * 20 + 19
```

Implement GLTF external URI resolution excluding `data:` URIs and OBJ `mtllib` plus MTL texture references, returning sorted unique project-relative paths.

- [ ] **Step 4: Run tests and confirm GREEN**

Run the same unittest command. Expected: all Task 1 tests pass.

- [ ] **Step 5: Commit**

Commit message: `test(stage4): lock full-corpus authority contracts`.

---

### Task 2: Full-Corpus Authority Builder

**Files:**
- Modify: `.github/forensics/qualification/stage4_full_corpus/stage4_full_corpus.py`
- Modify: `.github/forensics/qualification/stage4_full_corpus/test_stage4_full_corpus.py`

**Interfaces:**
- Produces `build_full_corpus_authority(source_root: Path, output: Path) -> dict`.
- Writes `FULL_MODEL_CORPUS_AUTHORITY.json`, `FULL_MODEL_CORPUS_PATHS.txt`, `FULL_MODEL_DEPENDENCY_AUTHORITY.json`.

- [ ] **Step 1: Add failing tests**

Create a temporary source tree with one file of each model format plus a matrix manifest. Assert stable UTF-8 ordering, sequential indices, dependency hashes, matrix membership, duplicate/case-collision rejection and exact-count validation through a separately testable `validate_authority_counts(records, matrix_paths)` function.

- [ ] **Step 2: Confirm RED**

Run the unittest file; expected failures name missing authority functions.

- [ ] **Step 3: Implement authority generation**

Enumerate only `.glb`, `.gltf`, `.fbx`, `.obj` case-insensitively while preserving exact path case. Sort using `path.encode("utf-8")`, assign indices and record source bytes/SHA-256/MD5, dependencies and expected sidecar/importer/type. Verify the accepted matrix manifest SHA-256 and normalize its path field variants into exactly 436 unique GLBs.

- [ ] **Step 4: Confirm GREEN and run against the accepted source ZIP**

Commands:

```bash
python3 -m unittest -v .github/forensics/qualification/stage4_full_corpus/test_stage4_full_corpus.py
python3 .github/forensics/qualification/stage4_full_corpus/stage4_full_corpus.py build-authority \
  --source-root /tmp/stage4-accepted-source \
  --output /tmp/stage4-authority
```

Expected accepted-source summary: total `800`, GLB `578`, GLTF `203`, FBX `18`, OBJ `1`, matrix `436`, and all failure counters `0`.

- [ ] **Step 5: Commit**

Commit message: `feat(stage4): build immutable 800-model authority`.

---

### Task 3: Engine and Sidecar Authority

**Files:**
- Modify: `.github/forensics/qualification/stage4_full_corpus/stage4_full_corpus.py`
- Modify: `.github/forensics/qualification/stage4_full_corpus/test_stage4_full_corpus.py`

**Interfaces:**
- Produces `verify_engine(engine_root: Path) -> dict`.
- Produces `parse_import_sidecar(bytes) -> dict`.
- CLI `build-sidecars` writes `GODOT_4_4_1_FULL_SIDECAR_AUTHORITY.json`, ZIP and model map.

- [ ] **Step 1: Add failing tests**

Test exact runtime identity/checksum validation, parser extraction of importer/type/UID/path/source/dest/params, rejection of destinations outside `.godot/imported/`, and sidecar ZIP exclusion of `.godot` files.

- [ ] **Step 2: Confirm RED**

Run unittest; expected missing function failures.

- [ ] **Step 3: Implement engine verification, watchdog import and sidecar packaging**

Pin runtime identity `4.4.1.stable.official.49a5bc7b6`, source commit `49a5bc7b616bd04689a2c89e89bda41f50241464`, runtime SHA-256 `54215149d52efb1d653a3dec39d0993587bdf5daa2c56e787b5ee88417fb1339`, archive SHA-512 and source archive SHA-256. Use a process-group watchdog and retain only source-adjacent `.import` bytes after verifying all 800 mappings.

- [ ] **Step 4: Confirm GREEN**

Run unittest and `python3 -m py_compile` on the implementation.

- [ ] **Step 5: Commit**

Commit message: `feat(stage4): generate verified 4.4.1 sidecar authority`.

---

### Task 4: Independent Import and Deterministic Shards

**Files:**
- Modify: `.github/forensics/qualification/stage4_full_corpus/stage4_full_corpus.py`
- Modify: `.github/forensics/qualification/stage4_full_corpus/test_stage4_full_corpus.py`

**Interfaces:**
- CLI `run-import --side D1|D2`.
- Writes full import manifest/environment/source reports and `shards/00..39`.

- [ ] **Step 1: Add failing tests**

Test that each shard has twenty consecutive global indices, copied imported binaries/companions/sidecars, deterministic inventory SHA-256 and no cross-shard paths. Test missing imports remain explicit model records.

- [ ] **Step 2: Confirm RED**

Run unittest; expected missing import/shard function failures.

- [ ] **Step 3: Implement independent import evidence**

Materialize exact source plus exact sidecars, assert no pre-existing `.godot`, capture environment/pre-post resource state, run the watchdog import, parse every sidecar destination and companion, and write forty shard directories plus a compact manifest artifact root.

- [ ] **Step 4: Confirm GREEN**

Run unittest and a single representative local import against the accepted source/engine authority; verify forty shard manifests and 800 model records.

- [ ] **Step 5: Commit**

Commit message: `feat(stage4): produce independent full-import shards`.

---

### Task 5: Shard Comparator and Aggregate Classification

**Files:**
- Modify: `.github/forensics/qualification/stage4_full_corpus/stage4_full_corpus.py`
- Modify: `.github/forensics/qualification/stage4_full_corpus/test_stage4_full_corpus.py`

**Interfaces:**
- CLI `compare-shard` writes the three required shard reports and bounded differing pairs.
- CLI `aggregate` writes the five required Stage 4 aggregate files.

- [ ] **Step 1: Add failing tests**

Test PASS for identical bytes; `NONDETERMINISTIC` for one-byte changes; exact first/final offset and range/window bounds; MISSING_D1/D2; source/sidecar failures; Q3 only when both imports completed and byte/destination-MD5 differences exist; Q6 for missing evidence; PASS only for exact 800/578/203/18/1/436 counts and zero failures.

- [ ] **Step 2: Confirm RED**

Run unittest; expected comparator/aggregate failures.

- [ ] **Step 3: Implement comparisons and aggregation**

Verify artifact metadata and inventory before comparing. Retain all differing paths/hashes and exact pairs for sorted first twenty differences. Aggregate exactly forty reports and emit `STAGE4_PASS_PENDING_STAGE5`, `Q3` or `Q6` without automatically authorizing another engine.

- [ ] **Step 4: Confirm GREEN**

Run all tests. Expected: zero failures.

- [ ] **Step 5: Commit**

Commit message: `feat(stage4): compare shards and classify full corpus`.

---

### Task 6: Workflow Contract and GitHub Actions Topology

**Files:**
- Create: `.github/forensics/qualification/stage4_full_corpus/test_stage4_workflow.py`
- Create: `.github/workflows/godot-engine-qualification-stage4-full-corpus.yml`

**Interfaces:**
- Workflow produces the run locator, authority, sidecar, D1/D2 manifest and shard artifacts, forty comparison artifacts, aggregate evidence and optional differing-pair evidence.

- [ ] **Step 1: Write failing static workflow tests**

Assert exact job names, one 40-entry comparison matrix, `max-parallel` bounded to at most 8, pinned action SHAs, `if: always()` on every upload, no `4.5.2`, `4.6.3`, Android, export, pack or APK command, and exact frozen PR/source/engine authorities.

- [ ] **Step 2: Confirm RED**

Run both unittest files; workflow test must fail because the YAML is absent.

- [ ] **Step 3: Implement workflow**

Use source artifact `8424275568` from run `29627302405` with digest `0292e1686ac49aaad7523f4c1011d506149b98c2227f099a2348b2e3afac185b`, Stage 3 artifacts `8443812617` and `8443809946`, and official engine download verification. Set authority timeout 240m, D1/D2 timeout 300m and comparator timeout 30m. Use separate `/tmp/bahrain-stage4-d1` and `/tmp/bahrain-stage4-d2` roots.

- [ ] **Step 4: Confirm GREEN and YAML parse**

Commands:

```bash
python3 -m unittest -v \
  .github/forensics/qualification/stage4_full_corpus/test_stage4_full_corpus.py \
  .github/forensics/qualification/stage4_full_corpus/test_stage4_workflow.py
python3 - <<'PY'
import yaml
p='.github/workflows/godot-engine-qualification-stage4-full-corpus.yml'
yaml.safe_load(open(p))
print('YAML_OK')
PY
```

Expected: all tests pass and `YAML_OK`.

- [ ] **Step 5: Commit**

Commit message: `ci(stage4): install full 800-model qualification workflow`.

---

### Task 7: Execute, Inspect and Report

**Files:**
- Workflow-generated locator: `.github/forensics/qualification/LATEST_STAGE4_FULL_CORPUS_RUN.json`

**Interfaces:**
- Consumes the completed workflow run, jobs and artifacts.
- Produces the exact 56-point checkpoint response.

- [ ] **Step 1: Trigger only the Stage 4 workflow by committing its workflow path**

Record the immutable workflow commit SHA and run locator.

- [ ] **Step 2: Inspect every job conclusion and artifact**

Verify D1/D2 are distinct hosted jobs/runners/roots, all forty comparators completed, all artifact digests match downloaded ZIP bytes, all internal inventories verify, and the aggregate is consistent with shard reports.

- [ ] **Step 3: Recheck PR #59 and prohibited boundaries**

Fetch PR #59 after completion and confirm exact frozen head/state. Inspect workflow and evidence for absence of Stage 5, compatibility, migration, pack, Android and APK activity.

- [ ] **Step 4: Run final verification**

Re-run the full contract tests from the immutable workflow commit, independently hash aggregate and relevant artifacts, and validate the 56 required fields against evidence.

- [ ] **Step 5: Stop after Stage 4**

Do not trigger any fallback or downstream workflow. Return only the required numbered checkpoint.
