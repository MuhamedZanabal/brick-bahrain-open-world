# Bahrain Brick Graphics Upgrade v1 — G0 Terminal Report

## Classification

```text
G0_EVIDENCE_INSUFFICIENT
```

No renderer is selected, renderer defaults remain unchanged, and G1 remains blocked.

## Source authority

- Renderer-evidence authority: `6ade72ed02084791128dcf4a91223e695d802c15`
- Frozen PR #59 head: `5b4e2466ef84f3984f3bf336b31925d4d2e97a7f`
- Frozen tree: **1,256 files**
- Graphics tree: **1,279 files**
- Authorized additions: **23**
- Modified frozen paths: **0**
- Removed frozen paths: **0**
- Contracts: **21 passed, 0 failed**
- Source workflow run: `30064835410`
- Source artifact: `8585856751`
- Source artifact digest: `sha256:d95db81d7aacc2f2de57d60ce898d2df7512474e9b1fca2c1fed8428841e6842`

### `world.gd` rule

```text
BYTE_PROTECT_EXACT_FROZEN_WORLD_GD
```

`scripts/world.gd` is byte-protected at SHA-256 `a9d32157d38bee728eec54887a747ece49d070100c1750c313fa75047ce75432`. `_exit_tree` is absent; no claim is made that the symbol exists.

## Tier A — terminal host-CI result

Run `30064876927`, job `89393944500`, conclusion **success**. Artifact `8586133620`, digest `sha256:ac51acb8d82f773b6b545d67bf23c51cbb0bf8a8607f1aecea1af18a1877bf34`.

Both candidates used the same imported-state SHA-256 `0c896a4411c3352850b15a0c54972b2f33db41c7ca7a54a2efe861b912838d56` and passed final enforcement.

| Evidence | GL Compatibility | Mobile Vulkan |
|---|---:|---:|
| Runtime exit code | 0 | 0 |
| Startup identity | OpenGL Compatibility / `opengl3` | Forward Mobile / Vulkan |
| Scene readiness | PASS | PASS |
| Mission marker | PASS | PASS |
| Screenshot | 1920×1080, non-black | 1920×1080, non-black |
| Critical errors | 0 | 0 |
| Frame rows | 360 | 360 |
| Average frame time | 163.190 ms | 151.381 ms |
| Draw calls | 2,138 | 1,773 |
| Graphics memory | 262,434,231 B | 495,843,120 B |

Host metrics are diagnostic only. The screenshots differ materially: mean absolute channel delta **21.241**, RMSE **31.144**, and **59.853%** of pixels differ. This does not establish an art-quality winner.

Renderer identity is taken from Godot startup logs. The Mobile completion marker echoed the project default and is not used as renderer identity evidence.

## Tier B — existing artifact diagnosis

Original run `30064876896`, artifact `8586122615`, digest `sha256:4d4d3a696f4a326c3ddd63d1f51c278263fc25e6f2e00f68c0c3b64fb3c2e9ee`.

Primary diagnosis of the existing artifact:

```text
TIER_B_APK_VERIFICATION_FAILURE
```

- Last confirmed successful stage: Mobile APK export, signing, and `apksigner verify`.
- First failed stage: legacy `aapt dump badging` verification.
- First missing expected artifact: `APK_SHA256SUMS.txt`.
- Decisive line: `AndroidManifest.xml:0: error: failed to read attribute 'android:required': attribute is not an integer value`.
- Cause: verification harness / legacy Android build-tool parser.
- Renderer failure: **not proven**.

The reducer run `30086594777` succeeded and emitted a 6.66 MB diagnostic artifact (`8593954623`, digest `sha256:860c9a2c2b2130359f11643eb821cd3c8f0ce039302460bc739fae8e64860588`) without rerunning Android.

## Single targeted Tier B retry

One targeted retry was executed—no further retry is permitted in this checkpoint.

Run `30086966524`, job `89461293320`, artifact `8594128472`, digest `sha256:87397e8d3a3e2eac267864589140632577600176d6bac88e9bebdf40e4d27e20`.

The retry reused the exact APK bytes and repeated neither reconstruction nor export. Both APKs passed signature, AAPT2 package-name, and x86_64 ABI verification. The API 34 x86_64 emulator booted.

Terminal retry classification:

```text
TIER_B_APP_LAUNCH_FAILURE
```

- GL APK install: PASS.
- Launcher event injection: exit code 0.
- First failure: `pidof com.brickbahrain.g0gl` remained empty throughout the process-acquisition window.
- First missing runtime artifact: `reports/graphics/g0/gl_compatibility/runtime.log`.
- Renderer identity, scene readiness, screenshot, and lifecycle evidence were never reached.
- Mobile emulator execution was not attempted because the workflow failed fast on GL.
- Root cause is not proven because process-scoped logcat was not persisted before the PID gate.
- Renderer failure is **not proven**.

## Device boundary

Named physical-device evidence is unavailable. The maximum admissible result is therefore `G0_EVIDENCE_INSUFFICIENT`, even though both host renderer paths functioned.

Required device work is packaged in `reports/graphics/g0/device_handoff/` and has **not** been executed.

## Unresolved blockers

1. Prove why the GL API 34 emulator process exits or never starts.
2. Execute the Mobile Vulkan APK on the API 34 emulator.
3. Run the handoff on named minimum, target, and high-end physical devices.
4. Record five-minute traversal, memory, thermal, pause/resume, and crash evidence.
5. Select renderer and fallback policy only after physical-device evidence.

## Stop condition

Tier A is terminal; the existing Tier B artifact is reduced and diagnosed; exactly one targeted Tier B retry is complete; terminal reports and the device handoff are emitted. G1 has not begun.
