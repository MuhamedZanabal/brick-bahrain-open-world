# Bahrain Brick Controlled Agent Environment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install and verify a least-privilege project agent operating system for Bahrain Brick without modifying protected game or renderer authority.

**Architecture:** Use project-scoped Claude Code memory, settings, skills, agents, hooks, and one stdio MCP server. All executable integration is routed through typed Python entrypoints and existing repository build scripts, with GitHub Actions providing the toolchain unavailable in the local execution container.

**Tech Stack:** Claude Code project configuration, Python 3 standard library, Godot 4.3, Android SDK 34/build-tools 34.0.0, ADB, Blender background mode, GitHub Actions.

## Global Constraints

- Base commit: `ac8edaef8853fb7e344b2e347f5de36a008c6ba7`.
- Preserve renderer defaults and all protected authority files.
- Do not install community plugins or remote MCP servers.
- Do not publish, release, merge, deploy, or expose signing credentials.
- Every configured integration must be invoked or reported unavailable.

---

### Task 1: Project authority and configuration

**Files:**
- Create: `CLAUDE.md`
- Create: `.claude/settings.json`
- Create: `.claude/.gitignore`
- Create: `.mcp.json`

**Interfaces:**
- Produces: project authority, permission policy, hook registration, and local MCP registration.

- [ ] Write the four files with exact authority identifiers and least-privilege rules.
- [ ] Parse both JSON files with `python3 -m json.tool`.
- [ ] Confirm no token, credential, or key material is present.
- [ ] Commit as `chore(agent-env): establish project authority and permissions`.

### Task 2: Domain skills and agents

**Files:**
- Create: six `.claude/skills/*/SKILL.md` files.
- Create: five `.claude/agents/*.md` files.

**Interfaces:**
- Produces: project-scoped domain procedures and worktree-isolated specialists.

- [ ] Add each skill with precise triggers, authority checks, implementation steps, and verification criteria.
- [ ] Add each agent with unique name, description, least-privilege tools, preloaded skills, and `isolation: worktree`.
- [ ] Validate all YAML frontmatter with the project verifier.
- [ ] Commit as `chore(agent-env): add Bahrain Brick skills and agents`.

### Task 3: Hooks and typed MCP

**Files:**
- Create: `.claude/hooks/bahrain_brick_hook.py`
- Create: `tools/agent_env/bahrain_brick_mcp.py`
- Create: `tools/agent_env/blender_asset_validator.py`
- Create: `tools/agent_env/verify_environment.py`

**Interfaces:**
- MCP tools: `godot_validate_project`, `godot_export_android_debug`, `android_adb_smoke_test`, `blender_validate_asset`, `collect_build_evidence`.
- Hook events: `SessionStart`, `PreToolUse`, `PostToolUse`, `Stop`.

- [ ] Implement path confinement and fixed command templates.
- [ ] Implement destructive Git/MCP blocking and secret detection.
- [ ] Implement post-edit relevant test selection and Godot validation.
- [ ] Implement APK evidence generation without signing-key access.
- [ ] Compile all Python files.
- [ ] Commit as `feat(agent-env): add hooks and typed local MCP`.

### Task 4: Contract tests and CI qualification

**Files:**
- Create: `tests/test_controlled_agent_environment.py`
- Create: `.github/workflows/controlled-agent-environment.yml`

**Interfaces:**
- Consumes all configuration and tool contracts.
- Produces retained configuration, MCP, Godot, baseline-test, and Android build evidence.

- [ ] Add tests for required files, exact MCP tools, permissions, hook coverage, and secret absence.
- [ ] Add CI jobs for static validation, MCP smoke, representative baseline tests, pinned Godot headless validation, and non-publishing Android debug export.
- [ ] Run the static test locally.
- [ ] Push the isolated branch and inspect the workflow result.
- [ ] Commit as `ci(agent-env): qualify controlled development environment`.

### Task 5: Evidence and handoff

**Files:**
- Update only generated CI artifacts outside source control.

**Interfaces:**
- Produces the final installation inventory and exact pass/fail/unavailable report.

- [ ] List six skills, five agents, registered hooks, zero plugins, and one MCP server.
- [ ] Invoke all non-destructive MCP tools once.
- [ ] Record local and CI tool availability separately.
- [ ] Record baseline, Godot, Android, and artifact evidence results.
- [ ] Open a draft PR without merging.
