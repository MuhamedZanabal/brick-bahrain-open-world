# Bahrain Brick Controlled Codex Environment Design

## Objective

Provide a project-scoped Codex operating environment for Godot gameplay, Android qualification, Blender asset validation, authoritative multiplayer, persistence, CI evidence, and release auditing without changing existing gameplay or renderer authority.

## Native Codex layout

- `AGENTS.md` is repository-wide instruction authority.
- `.agents/skills/*/SKILL.md` contains six domain skills.
- `.codex/agents/*.toml` contains five custom subagents that inherit the parent model.
- `.codex/config.toml` sets on-request approval, workspace-write sandboxing, disabled sandbox network access, agent limits, and one local typed MCP server.
- `.codex/hooks.json` and `.codex/hooks/bahrain_brick_hook.py` enforce security, post-edit verification, APK evidence, and completion checks.

## Platform compatibility

Trusted Codex CLI or desktop sessions can load the local configuration and stdio MCP. Hosted sessions that cannot start repository-local processes use the same typed handlers through `python3 tools/agent_env/bahrain_brick_mcp.py --invoke ...` or GitHub Actions. No hosted fallback introduces arbitrary shell execution.

## Security model

- Repository-root path confinement.
- Build outputs only under `build/` or `release/`.
- No signing key, token, password, or private-key inputs.
- No community or remote MCP mutation tools.
- Destructive Git, database, release, and device-data operations are blocked.
- APK export, ADB writes, and Blender execution require approval.

## Verification

The environment must parse all TOML, JSON, YAML, frontmatter, and agent definitions; expose exactly five typed tools; pass 10 static/security tests; run direct and MCP protocol smoke checks; run representative repository tests; validate the pinned Godot version; attempt a non-publishing Android debug export; and retain evidence even when the existing exporter remains blocked.

## Non-goals

This migration does not select a renderer, upgrade Godot, normalize package identities, alter production scenes, fix the R1 exporter, merge protected PRs, publish releases, or perform infrastructure/database mutation.
