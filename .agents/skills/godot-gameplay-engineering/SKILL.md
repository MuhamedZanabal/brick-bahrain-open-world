---
name: godot-gameplay-engineering
description: Implement or review Bahrain Brick Godot gameplay, scenes, missions, controls, vehicles, UI, save integration, or GDScript while preserving project authority.
---

## Authority first

1. Read `AGENTS.md`, `.ai/CHECKPOINT.md`, `.ai/project-state.json`, and the relevant specification or authority file.
2. Identify protected files and the exact base commit before editing.
3. Do not change renderer defaults, engine version, autoloads, input semantics, package identity, or frozen movement/touch behavior without a separate approved ADR.

## Engineering procedure

1. Reproduce the defect or define a failing contract test.
2. Prefer composition around existing systems over a parallel framework.
3. Keep GDScript typed, deterministic, signal-driven, and narrowly scoped.
4. Use explicit state transitions and reject duplicate or out-of-order events.
5. Validate scene/resource paths and fail closed when required data is missing.
6. Preserve Android touch controls, landscape safe areas, and mobile budgets.
7. Add or update the smallest relevant Python or Godot runtime tests.

## Verification

- Run targeted tests selected by `python3 tools/agent_env/verify_environment.py changed`.
- Use `godot_validate_project` through the local MCP when available; otherwise run the direct typed invocation.
- For Android-impacting changes, run the authoritative debug export workflow and collect APK evidence.
- Report exact files, commands, exit codes, unresolved risks, and completion classification.
