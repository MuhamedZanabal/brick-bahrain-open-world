# Bahrain Brick Controlled Agent Environment Design

## Decision

Create an isolated project-scoped Claude Code control plane on top of the current R1 authority branch. The control plane wraps existing Godot, Android, asset, and CI authorities; it does not alter gameplay, renderer defaults, protected branches, package authority, or release state.

## Authority

- Repository: `MuhamedZanabal/brick-bahrain-open-world`
- Base branch: `work/bahrain-brick-renderer-runtime-debugging-r1`
- Base commit: `ac8edaef8853fb7e344b2e347f5de36a008c6ba7`
- New branch: `work/bahrain-brick-controlled-agent-os-v1`
- Godot authority: `4.3.stable.official.77dcf97d8`
- Android CI authority: JDK 17, Android platform 34, build-tools 34.0.0
- Renderer authority remains unresolved; production renderer changes are out of scope.

## Components

1. Root `CLAUDE.md` records immutable project facts, authority resolution, architecture, security, tests, and release evidence.
2. Six project skills provide domain procedures without loading all procedural detail into every session.
3. Five project subagents use worktree isolation and least-privilege tool sets.
4. One Python hook dispatcher blocks destructive operations, scans secrets, validates edits, runs relevant tests, and enforces completion evidence.
5. One local stdio MCP server exposes exactly five typed tools: Godot validation, debug export, ADB smoke testing, Blender asset validation, and artifact evidence collection.
6. One verifier validates configuration, agent/skill contracts, MCP behavior, tests, Godot availability, and evidence.
7. One CI workflow exercises configuration, baseline contracts, Godot headless validation, and a non-publishing Android debug build attempt.

## Security model

- No project community plugins.
- No remote MCP servers.
- Project MCP approval remains subject to workspace trust.
- The MCP server resolves and confines every path to the repository root and approved `build/` or `release/` output roots.
- MCP tools use fixed executable/argument templates; there is no arbitrary command or shell tool.
- Keystores and credential files are denied to project file tools and are never MCP inputs or outputs.
- Remote writes, releases, deployments, infrastructure mutation, database destruction, and high-impact Git actions require explicit permission or are denied.
- Hooks inspect all Bash and MCP calls, including user-scoped MCP tools, and deny write/delete/deploy patterns outside the local allowlisted server.

## Verification strategy

- Static contract tests validate JSON, frontmatter, required files, exact MCP tool names, permissions, and absence of embedded secrets.
- MCP smoke initializes the server, lists tools, invokes every non-destructive tool, and distinguishes pass, unavailable dependency, and execution failure.
- Baseline tests execute representative existing vertical-slice and APK-export contracts.
- Godot validation imports/parses the project headlessly using the pinned engine.
- Android CI reuses the repository's existing debug-export script and uploads evidence only; it never publishes a release.

## Acceptance criteria

- All configuration files parse.
- Exactly six skills, five agents, one project MCP server, and the required hooks are discoverable.
- Destructive Git and secret-access contracts are denied.
- MCP exposes no arbitrary shell, signing, remote write, release, infrastructure, or database mutation tool.
- Static tests and MCP protocol smoke pass.
- Godot and Android outcomes are reported as pass, fail, or unavailable with retained logs.
- Existing protected authority files remain unchanged.
