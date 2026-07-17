# PR #59 Gate 1 Composite Authority Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish PR #59 as a deterministically reconstructable composite source authority without modifying gameplay or advancing beyond Authority Gate 1.

**Architecture:** Promote the exact accepted 436-asset Actions artifact bytes to the existing `v1.4.0.3-graphics-qa` release, then make the final workflow read-only and reconstruct the disposable Godot source twice in independent jobs. A focused Python authority tool validates the contract, records origins, rejects unsafe filesystem states, creates a normalized manifest and aggregate tree hash, creates a deterministic source archive, inventories retained evidence, and compares both runs byte-for-byte.

**Tech Stack:** GitHub Actions, Bash, Python 3.12.3, Pillow 12.3.0, Ubuntu 24.04.4 runner image `20260714.240.1`, `librsvg2-bin=2.58.0+dfsg-1build1`, Godot 4.3 metadata only, SHA-256, ZIP.

## Global Constraints

- Repository: `MuhamedZanabal/brick-bahrain-open-world`.
- Existing branch only: `work/bahrain-brick-manama-souq-vertical-slice-v1`.
- Starting authority head: `43f80b2ff5f51fc00ddc9d9fe11231df65ae0879`.
- Base authority: `fc8f00182f97c39015610d6603fa7c9c44364c5d`.
- Frozen premium authority: `e26ec912db5c10d071a8e120010bdb5a9a136f17`.
- Historical source SHA-256: `5c4d8ac4497eda7752058424062a74a97c1f6f5e0c9a1ff393abac2a2c7c828a`.
- 436-asset authority ZIP SHA-256: `76964c58c283cacaee137152189727d678aa83230d7211dc6a15aa9af9d4a67a`.
- Do not modify gameplay scripts, scenes, controls, visual assets, or generated GLBs.
- Do not run Godot import, Android export, APK inspection, or any later release gate.
- Do not create a branch, pull request, release, or merge.

---

### Task 1: Add failing authority-tool tests

**Files:**
- Modify: `tests/test_manama_souq_source_gate.py`
- Create: `tests/test_manama_souq_composite_authority.py`

**Interfaces:**
- Consumes: planned CLI `tools/vertical_slice/composite_source_authority.py`.
- Produces: behavioral requirements for contract validation, manifest generation, unsafe-path rejection, evidence inventory validation, tree mutation detection, and run comparison.

- [ ] Write tests that fail because the authority tool and contract do not yet exist.
- [ ] Run `python3 -m unittest tests.test_manama_souq_composite_authority tests.test_manama_souq_source_gate -v` and confirm failures reference missing authority implementation.
- [ ] Commit only the failing tests.

### Task 2: Implement normalized manifest and fail-closed validation

**Files:**
- Create: `tools/vertical_slice/composite_source_authority.py`
- Create: `authority/manama_souq_composite_source.json`

**Interfaces:**
- `validate-contract --contract PATH --repo-root PATH`
- `manifest --contract PATH --game-root PATH --origin-ledger PATH --output PATH --report PATH`
- `archive --game-root PATH --manifest PATH --output PATH --report PATH`
- `inventory --root PATH --output PATH`
- `verify-inventory --root PATH --inventory PATH`
- `compare --run-a PATH --run-b PATH --output PATH`

- [ ] Implement path normalization, case-collision detection, path-traversal rejection, symbolic-link rejection, duplicate-origin rejection, expected/missing/unexpected file checks, SHA-256/byte accounting, ordered aggregate hashing, deterministic ZIP metadata, and byte-for-byte run comparison.
- [ ] Validate every reconstruction-script SHA-256 from the checked-in contract.
- [ ] Run the tests and confirm green.
- [ ] Commit implementation and initial contract without an invented final tree hash.

### Task 3: Implement deterministic reconstruction driver

**Files:**
- Create: `tools/vertical_slice/reconstruct_manama_souq_composite.sh`
- Create: `tools/vertical_slice/promote_manama_souq_asset_authority.sh`

**Interfaces:**
- Reconstruction driver receives run label, workspace root, contract path, and candidate SHA.
- Promotion driver receives exact Actions artifact ID, existing release tag, expected SHA-256, expected byte size, and final release asset name.

- [ ] Download each external input from its immutable locator and verify byte size and SHA-256 before extraction.
- [ ] Pin and verify OS image, Python, Pillow, `librsvg2-bin`, Godot download checksum metadata, and every script digest before assembly.
- [ ] Record origin snapshots before and after historical source, asset matrix, checkout copies, premium overlay, and correction stages.
- [ ] Generate frozen-control pre/post reports without importing Godot.
- [ ] Generate the final manifest, aggregate report, deterministic source archive, and retained evidence inventory.
- [ ] Run contract tests and shell syntax checks.
- [ ] Commit the drivers.

### Task 4: One-time exact-byte release promotion

**Files:**
- Modify temporarily: `.github/workflows/manama-souq-vertical-slice.yml`

**Interfaces:**
- Existing release tag: `v1.4.0.3-graphics-qa`.
- Release asset name: `bahrain-brick-full-asset-matrix-authority-76964c58c283caca.zip`.

- [ ] Temporarily grant only `contents: write` and `actions: read`.
- [ ] Download Actions artifact `8360668742`, verify exact accepted checksum and size, and upload it without clobbering an existing asset.
- [ ] If the named release asset already exists, download and verify it instead of replacing it.
- [ ] Capture release asset metadata and checksum in workflow evidence.
- [ ] Confirm the promotion run succeeds.

### Task 5: Final read-only dual reconstruction workflow

**Files:**
- Modify: `.github/workflows/manama-souq-vertical-slice.yml`

**Interfaces:**
- Two independent jobs: `authority_run_a`, `authority_run_b`.
- Comparison job: `authority_compare`.

- [ ] Restore workflow permissions to `contents: read` only.
- [ ] Remove Actions artifact ID as a reconstruction dependency.
- [ ] Download both source inputs only from checksum-pinned release URLs.
- [ ] Run two clean reconstructions with no shared generated state.
- [ ] Upload complete per-run manifests, reports, logs, frozen-control evidence, deterministic source archives, and truthful inventories.
- [ ] Compare the two run artifacts byte-for-byte and fail on any mismatch.
- [ ] Do not run the existing Godot source gate.
- [ ] Commit the final workflow.

### Task 6: Establish and lock the expected final authority

**Files:**
- Modify: `authority/manama_souq_composite_source.json`

**Interfaces:**
- Consumes the first successful dual-reconstruction manifest and aggregate reports.
- Produces checked-in expected manifest SHA-256, file count, total bytes, and aggregate game-tree SHA-256.

- [ ] Record the established values from a successful clean dual run.
- [ ] Re-run the final workflow with strict expected-value enforcement.
- [ ] Confirm run A and run B remain identical and equal the contract.
- [ ] Confirm all required negative tests pass.
- [ ] Confirm PR #59 remains open, draft, and unmerged.

### Task 7: Final verification and checkpoint

- [ ] Inspect changed filenames and confirm no prohibited path changed.
- [ ] Verify all contract/unit tests freshly pass.
- [ ] Verify the final GitHub workflow conclusion and artifact digests.
- [ ] Verify source archive contents match the retained manifest and inventory.
- [ ] Report exactly the 16 requested checkpoint fields and stop at Gate 1.
