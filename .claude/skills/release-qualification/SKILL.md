---
name: release-qualification
description: Audit Bahrain Brick builds, CI, security, licensing, device evidence, multiplayer scale, persistence integrity, and release artifacts before any completion or release claim.
paths:
  - ".github/workflows/**"
  - "reports/**"
  - "release/**"
  - "authority/**"
  - ".ai/**"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(git status *)
  - Bash(git diff *)
  - Bash(git log *)
  - Bash(python3 tools/agent_env/verify_environment.py *)
  - mcp__bahrain-brick-local__collect_build_evidence
disallowed-tools:
  - Edit
  - Write
  - mcp__bahrain-brick-local__godot_export_android_debug
  - mcp__bahrain-brick-local__android_adb_smoke_test
---

## Audit procedure

1. Resolve repository, branch, commit, frozen authorities, and open draft PR boundaries.
2. Require terminal-green applicable CI and inspect retained logs/artifacts, not status badges alone.
3. Verify APK/AAB bytes, SHA-256, package/version, startup scene, architecture, ZIP integrity, signatures, and signer fingerprint.
4. Verify named device matrix, FPS/frame pacing, peak RAM, startup time, thermal behavior, lifecycle, and soak evidence.
5. Verify multiplayer results for every claimed scale gate and persistence/economy idempotency evidence.
6. Verify privacy, moderation, security, dependency, asset-license, and rollback records.
7. List every missing gate and classify completion conservatively.

Never publish, merge, sign, deploy, or change remote state. Return one permitted completion classification and exact blocking evidence.
