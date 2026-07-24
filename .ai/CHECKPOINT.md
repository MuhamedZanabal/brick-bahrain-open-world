# Bahrain Brick Graphics Upgrade v1 — Terminal G0 Checkpoint

Recorded: 2026-07-24

## Classification

`G0_EVIDENCE_INSUFFICIENT`

G0 is terminal for this checkpoint but not passed. PR #60 remains draft. G1-G10 remain blocked.

## Authority

PR #59 remains open, draft, unmerged and unchanged at `5b4e2466ef84f3984f3bf336b31925d4d2e97a7f`. Renderer evidence is anchored to `6ade72ed02084791128dcf4a91223e695d802c15`. Source authority and protected-file checks passed. `scripts/world.gd` uses `BYTE_PROTECT_EXACT_FROZEN_WORLD_GD`; `_exit_tree` is absent.

## Tier A

Run `30064876927`, job `89393944500` passed. GL Compatibility and Mobile Vulkan both completed the identical host-CI scene, generated valid 1920×1080 screenshots, reached readiness and mission markers, and reported zero critical errors. Host performance is diagnostic only.

## Tier B

The existing artifact is classified `TIER_B_APK_VERIFICATION_FAILURE` at legacy `aapt dump badging`. Reducer run `30086594777` succeeded without rerunning Android.

The single authorized targeted retry was run `30086966524`. Exact APK verification and emulator boot passed; GL installation and launcher injection passed, but no application process became alive. Final classification is `TIER_B_APP_LAUNCH_FAILURE`. Mobile emulator execution was not attempted. No renderer failure is proven.

## Automation exception

Packaging unintentionally retriggered the targeted workflow as run `30087878937`. It completed before cancellation run `30088001461` took effect. The duplicate is excluded from adjudication, but retry-limit compliance is false. Automatic reducer, targeted-resume and cancellation PR triggers are archived.

## Remaining blockers

- Named minimum, target and high-end physical devices.
- Five-minute traversal, frame, memory, thermal and lifecycle evidence.
- Fatal, ANR and native-crash scans.
- API 34 GL launch root cause.
- Renderer selection and fallback policy.

## Outputs

- `reports/graphics/g0/G0_TERMINAL_REPORT.json`
- `reports/graphics/g0/G0_TERMINAL_REPORT.md`
- `reports/graphics/g0/tier_b_reduction/`
- `reports/graphics/g0/device_handoff/`

No renderer defaults, production scenes, gameplay, controls, missions, materials or production assets were changed. G1 has not begun.
