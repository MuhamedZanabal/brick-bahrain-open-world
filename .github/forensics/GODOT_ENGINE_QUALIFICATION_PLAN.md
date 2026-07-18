# Official Godot Engine Determinism Qualification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Qualify official Godot stable releases against the frozen Bahrain Brick model-import reproducibility defect without modifying PR #59 or producing Android artifacts.

**Architecture:** A detached CI branch builds a compact, hash-verified eight-resource corpus from the accepted source archive. Each available official stable release is downloaded from `godotengine/godot-builds`, verified against GitHub release SHA-256 metadata, source-audited, and run through two independent clean imports seeded with one candidate-specific sidecar authority. Candidates stop at their first failed stage; later stages are added only for candidates that pass Stage 2.

**Tech Stack:** GitHub Actions, official Godot Linux x86_64 binaries, Python 3 standard library, GDScript semantic diagnostics, GitHub REST release metadata.

## Global Constraints

- PR #59 must remain at `5b4e2466ef84f3984f3bf336b31925d4d2e97a7f`, open, draft, unmerged, 99 commits.
- No Android export, APK generation, APK mutation, installation, execution, project migration, merge, or publication.
- No product, source-asset, importer-setting, `project.godot`, `export_presets.cfg`, keystore, or comparison-policy changes.
- Official checksummed stable binaries and official source tags only.
- Candidate tests run on disposable copies with independent project `.godot` directories.

---

### Task 1: Freeze and verify corpus authority

**Files:**
- Create: `.github/forensics/qualification_corpus.json`
- Create: `.github/forensics/godot_engine_qualification.py`

- [x] Encode the eight artifact-backed source paths, SHA-256 values, byte sizes, dependencies, and alias discrepancies.
- [x] Verify the accepted source ZIP, extract only required corpus files, and produce a deterministic compact corpus archive.
- [x] Fail on any path, byte-size, or digest mismatch.

### Task 2: Implement source audit and Stage 2 runtime qualification

**Files:**
- Create: `.github/forensics/godot_qualification_semantic.gd`
- Create: `.github/forensics/godot_engine_qualification.py`

- [x] Audit scene-unique ID generation, binary local-ID assignment, seed calls, and dictionary key iteration.
- [x] Generate one candidate-specific source-adjacent sidecar authority.
- [x] Import two independent minimal corpus projects without shared project caches.
- [x] Compare source hashes, sidecars, imported paths, bytes, destination MD5, UID cache, generated path sets, and semantic graphs.
- [x] Classify any candidate with one differing imported model as Q1.

### Task 3: Orchestrate official release qualification

**Files:**
- Create: `.github/workflows/pr59-godot-engine-qualification.yml`

- [x] Verify PR #59 frozen authority before qualification.
- [x] Query official release availability.
- [x] Download and SHA-256 verify official Linux binary and source archives.
- [x] Record exact source tag commit and engine version output.
- [x] Run 4.4.1, 4.5.2, and 4.6.3 in parallel; record unavailable requested versions honestly.
- [x] Upload one evidence artifact per candidate and one aggregate artifact.

### Task 4: Conditional later stages

- [ ] Enter Stage 3 only for candidates whose Stage 2 result is byte-identical across all eight resources.
- [ ] Enter Stage 4 only after Stage 3 passes.
- [ ] Enter Stage 5 only after all 800 model imports pass.
- [ ] Enter non-Android pack diagnostics only after project compatibility passes.
- [ ] Stop and prepare the exact 39-item checkpoint without migration or Android export.
