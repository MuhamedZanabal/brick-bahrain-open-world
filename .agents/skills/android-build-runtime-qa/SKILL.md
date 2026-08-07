---
name: android-build-runtime-qa
description: Build, install, launch, profile, and qualify Bahrain Brick Android debug APKs using the pinned Godot and Android toolchain with retained evidence.
---

## Toolchain authority

- Godot `4.3.stable.official.77dcf97d8`.
- JDK 17, Android platform 34, build-tools 34.0.0, platform-tools.
- Preserve package and version authority; report current inconsistencies instead of silently rewriting them.

## Build procedure

1. Validate source authority and protected hashes.
2. Run Python contracts and Godot clean import/headless validation.
3. Use the existing repository debug-export script or the typed `godot_export_android_debug` operation.
4. Never pass keystore bytes, passwords, tokens, or production signing material through MCP or CLI arguments.
5. Run `collect_build_evidence` immediately after export.
6. Use `android_adb_smoke_test` only with an explicitly selected device and debug or QA package.
7. Capture install, launch, process liveness, logcat criticals, package metadata, orientation, pause/resume, memory, and screenshots.

## Acceptance

- Export exits zero and artifact is non-empty.
- ZIP integrity, package/version, startup scene, architecture, signer fingerprint, and SHA-256 are recorded.
- No fatal, ANR, native crash, missing-resource, shader-limit, or renderer-stall signature is concealed.
- Device identity is named; emulator evidence is never represented as physical-device evidence.
