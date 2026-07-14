# Asset Lab Integration Blocker Report

## Current record accounting

- Total records: `98`
- Accounted records: `98`
- Silent omissions: `0`
- Current `INTEGRATED_RUNTIME`: `0`
- Current manifest records eligible to be called integrated: `0`
- Current `BLOCKED`: `98`

## Blocking classes

### 1. Pending project ownership/distribution license — 81 records

These records use `PROJECT_OWNED_PENDING`. The source policy states that no public license grant is implied and a root distribution license must be selected before public release. Their declared GLB outputs are absent.

Required resolution:

- confirm project ownership and redistribution rights;
- select a root distribution license or explicit proprietary distribution notice;
- generate runtime GLBs;
- validate Godot import and Android budgets.

### 2. Quarantined third-party provenance — 8 records

These records have unknown or incomplete provenance and cannot enter runtime. This includes generic buildings, vehicles, nature, roads and the exact local Flexible Toon derivative mapping.

Required resolution:

- identify exact upstream archive/revision;
- preserve license and attribution;
- verify redistribution and modification rights;
- hash the original archive and map every file;
- replace or canonicalize when provenance cannot be proven.

### 3. Generator-ready but no runtime derivative — 9 records

These records are described as original project assets and have Blender generators, but no generated GLB, Godot 4.3 import evidence or Android benchmark exists. The current execution container has no Blender or Godot executable.

Required resolution:

- execute generators using a pinned Blender toolchain;
- import with Godot 4.3 GL Compatibility;
- produce Low/Balanced/High variants;
- integrate into real world scenes;
- run complete regression and Android export.

## Integrity defect

The source `SHA256SUMS` contains 11 stale tracked hashes and 29 untracked bytecode entries. A new independent tracked-file ledger was generated, but the original source defect remains documented.

## CI transport limitation

The exact bundle is accessible through the authenticated Google Drive connector and verifies locally, but GitHub-hosted runners cannot authenticate to that private Drive object. This affects remote re-execution of the authority gate; it does not invalidate the locally verified Git bundle.

## Classification at this checkpoint

`ASSET AUTHORITY OR LICENSING BLOCKED`

This classification prevents runtime use of the 89 records lacking closed licensing/provenance and prevents completion claims for all 98 records.
