# Bahrain Brick Controlled Codex Environment Implementation Plan

**Goal:** Replace the project control plane with Codex-native instructions, skills, subagents, hooks, typed tools, and CI evidence while preserving R1 authority.

## Tasks

- [x] Establish the R1 base SHA and protected authority boundaries.
- [x] Replace the root instruction file with `AGENTS.md`.
- [x] Move six project skills to `.agents/skills/` with Codex-compatible frontmatter.
- [x] Move five subagents to `.codex/agents/*.toml` with inherited model selection and scoped sandboxes.
- [x] Add `.codex/config.toml` with on-request approval, workspace-write sandboxing, disabled sandbox network access, agent limits, and exact MCP tool approvals.
- [x] Add `.codex/hooks.json` and a fail-closed hook dispatcher for destructive operations, secrets, post-edit tests, APK evidence, and completion verification.
- [x] Preserve one least-privilege typed tool implementation and add direct `--invoke` support for hosted environments.
- [x] Add configuration, security, direct-tool, MCP-protocol, baseline, Godot, and Android-attempt CI gates.
- [x] Remove all legacy provider-specific project files and scan remaining control files for references.
- [x] Run local Python compilation, TOML/JSON/YAML validation, 10 contract tests, direct smoke, MCP smoke, and nested-directory MCP launch verification.
- [ ] Inspect remote CI artifacts and record the exact Android exporter outcome.
- [ ] Keep the pull request draft and unmerged until the user explicitly authorizes integration.

## Acceptance evidence

- Exact branch and before/after commit SHA.
- Complete changed-file inventory.
- Zero secret or legacy-reference findings.
- Exactly six skills, five subagents, four hook events, one local MCP, and five typed tools.
- Terminal results for static contracts, representative tests, pinned Godot validation, and Android attempt.
- Explicit statement that hosted web sessions cannot launch the local stdio MCP and must use typed CLI or CI fallback.
