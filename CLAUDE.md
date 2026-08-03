# Bahrain Brick Project Operating Authority

## Project identity

- Product: **Bahrain Brick**
- Primary developer brand: **Zanabal Gaming**
- Secondary studio presentation: **Mansoory Games**
- Repository: `MuhamedZanabal/brick-bahrain-open-world`
- Platform priority: Android, landscape, touch-first
- Engine authority: Godot `4.3.stable.official.77dcf97d8`

## Repository authority

1. Never infer authority from `main` alone. Read `.ai/CHECKPOINT.md`, `.ai/project-state.json`, open draft PRs, and the relevant authority ledger before implementation.
2. Current configuration base: `work/bahrain-brick-renderer-runtime-debugging-r1` at `ac8edaef8853fb7e344b2e347f5de36a008c6ba7`.
3. Frozen Manama vertical-slice authority: PR `#59`, head `5b4e2466ef84f3984f3bf336b31925d4d2e97a7f`.
4. Graphics qualification authority: PR `#60`; renderer selection remains null.
5. Renderer debugging authority: PR `#63`; current status is `ENGINEERING_STOP` pending named physical-device or upstream engine/driver evidence.
6. Do not modify, merge, close, retarget, rebase, or force-update protected PRs or authority branches unless the user explicitly authorizes that exact action.
7. When authorities conflict, stop implementation, report the exact paths/commits, and preserve the newest verified authority without silently replacing prior records.

## Engine and Android toolchain authority

- Godot: `4.3.stable.official.77dcf97d8`.
- Preserve the existing renderer defaults. Do not select a renderer or migrate Godot without a new approved ADR and execution evidence.
- Android CI: JDK 17, Android platform 34, build-tools 34.0.0, platform-tools, ARM64 as the minimum retained APK architecture.
- Existing package identities are inconsistent (`com.brickbahrain.openworld`, R1 QA identities, and corrected playable identities). Do not normalize package names or versions without a package-authority ADR.
- Debug signing may use the repository-approved QA/debug identity only through existing build tooling. Never read, print, copy, upload, or expose keystore contents through an agent or MCP tool.
- Production signing material must remain outside the repository and outside MCP configuration.

## Architecture rules

### Godot gameplay

- Compose around existing player, vehicle, touch, mission, save, and world authorities. Do not create parallel frameworks.
- Prefer small typed GDScript units, explicit signals, deterministic state machines, and data-driven definitions.
- Use `snake_case` for variables/functions, `PascalCase` for `class_name`, typed parameters/returns, and explicit node ownership.
- Autoload additions, global input changes, renderer changes, and protected-scene changes require an ADR and regression tests.
- Never award durable currency, inventory, ownership, or progression solely from a client-side event.

### Multiplayer

- Dedicated authoritative simulation is the target architecture. Listen-server scaffolding is not production authority.
- Server controls movement acceptance, rewards, mission completion, inventory, property ownership, and persistence writes.
- Validate every RPC input, bind actions to authenticated peer identity, use idempotency keys for durable transactions, and reject replay/duplication.
- Add interest management, snapshot interpolation, prediction/reconciliation, and reconnect behavior incrementally with measured 2/8/16/32/64/100-player gates.
- Never claim a player-count target from constants or architecture placeholders; require load evidence.

### Backend persistence

- PostgreSQL-compatible durable storage is authoritative for production progression.
- Redis-compatible infrastructure may be used for sessions/cache only, never as the sole durable ledger.
- Economy writes require transactions, idempotency, audit records, and server-owned reward calculation.
- Schema migrations must be reversible, reviewed, tested against representative data, and never run destructively without explicit permission and a backup/rollback plan.

### Blender and assets

- All brick components, figures, vehicles, landmarks, UI, audio, and textures must be original or properly licensed.
- Do not use LEGO trademarks, minifigure geometry, proprietary brick meshes, LDraw/BrickLink assets without verified compatible licensing, manufacturer logos, or copied game assets.
- Every imported asset requires provenance, license classification, source hash, dimensions, triangle count, material/texture inventory, and runtime destination.
- Apply transforms, use metric scale, bounded material counts, mobile LODs, compressed textures, and deterministic naming.
- Do not modify accepted binary asset authorities in place; produce a new versioned asset and update manifests.

### CI and release

- Existing authority workflows are evidence, not templates to rewrite casually.
- Pin third-party GitHub Actions by full commit SHA.
- CI must retain logs and machine-readable evidence even on failure.
- No release, deployment, merge, publication, remote infrastructure mutation, or signing-key change without explicit user authority.

## Required validation commands

Run from the repository root:

```bash
python3 tools/agent_env/verify_environment.py config
python3 tests/test_controlled_agent_environment.py
python3 tools/agent_env/verify_environment.py mcp-smoke
python3 tools/agent_env/verify_environment.py baseline
python3 tools/agent_env/verify_environment.py godot
```

Targeted vertical-slice contracts:

```bash
python3 tests/test_karak_delivery_mission_contract.py
python3 tests/test_manama_souq_layout_contract.py
python3 tests/test_manama_souq_slice_contract.py
python3 tests/test_souq_population_contract.py
python3 -m unittest tests/graphics/test_r1_playable_apk_export.py -v
```

Android export authority remains the existing repository script:

```bash
bash tools/graphics/export_r1_playable_mobile_apk.sh "$PWD" "$PWD/build/agent-export"
```

Use the local MCP tool `collect_build_evidence` immediately after any APK export.

## Release gates

A release candidate requires all of the following:

1. Exact repository, branch, commit, engine, Android SDK/build-tools, package, version, variant, and source authority recorded.
2. Terminal-green required CI checks and no unresolved critical defects.
3. Godot import/headless validation and relevant gameplay/runtime tests pass.
4. APK/AAB identity, ZIP integrity, signatures, startup scene, SHA-256, size, and signer fingerprint verified.
5. Representative named physical-device coverage, measured FPS, frame pacing, peak RAM, startup time, thermal behavior, pause/resume, network interruption, and soak results.
6. Multiplayer scale evidence for the claimed player count.
7. Persistence/economy integrity, security, privacy, licensing, moderation, and rollback reviews complete.
8. Production signing and store publication explicitly authorized.

Permitted classifications only:

- `VERIFIED PRODUCTION RELEASE`
- `RELEASE CANDIDATE WITH EXTERNAL ACCEPTANCE REMAINING`
- `FUNCTIONAL ALPHA`
- `PLAYABLE VERTICAL SLICE`
- `PARTIALLY IMPLEMENTED`
- `BLOCKED`

## Prohibited destructive actions

Without exact explicit authorization, never execute or approve:

- `git push --force`, force-updating refs, destructive rebases, `git reset --hard`, `git clean -f/-x`, branch deletion, tag deletion, or overwriting unrelated changes;
- merging, publishing, releasing, deploying, changing access controls, rotating/creating credentials, or modifying remote infrastructure;
- deleting or truncating databases, destructive migrations, dropping schemas/tables, or resetting production state;
- deleting artifacts or evidence required by an authority ledger;
- disabling tests, weakening thresholds, changing protected hashes, or bypassing hooks/permissions;
- reading or exposing `.env`, keystores, signing keys, tokens, private keys, credentials, or secret-manager exports.

## Evidence requirements

Every completed implementation report must include:

- objective and completion classification;
- repository, branch, before/after commit SHA, and changed files;
- authority consulted and conflicts found;
- commands executed with exit status;
- tests, lint/static analysis, Godot validation, build, and runtime results;
- APK/AAB path, bytes, SHA-256, package/version, signer fingerprint, and evidence manifest when applicable;
- measured device/server results, known limitations, unresolved risks, and exact next action.

Never claim a tool, hook, agent, skill, MCP server, build, APK, test, device run, or release is working unless it was invoked and its output was inspected.
