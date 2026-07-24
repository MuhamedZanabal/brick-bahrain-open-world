# Bahrain Brick Graphics Upgrade v1 — Terminal G0 Checkpoint

Recorded: 2026-07-24

## Classification

`G0_EVIDENCE_INSUFFICIENT`

G0 is terminal for this checkpoint but not passed. PR #60 remains draft. G1-G10 remain blocked.

## Frozen authority

- PR #59: open, draft, unmerged, unchanged.
- Frozen head: `5b4e2466ef84f3984f3bf336b31925d4d2e97a7f`.
- Renderer-evidence commit: `6ade72ed02084791128dcf4a91223e695d802c15`.
- Source census: 1,256 frozen files; 1,279 graphics files; 23 authorized additions; zero frozen modifications or removals.
- Contracts: 21 passed, 0 failed.
- `scripts/world.gd` rule: `BYTE_PROTECT_EXACT_FROZEN_WORLD_GD`; `_exit_tree` is absent.

## Tier A

Run `30064876927`, job `89393944500`: **success**. Both GL Compatibility and Mobile Vulkan completed the same scene under one byte-identical imported state. Both produced valid 1920×1080 non-black screenshots, readiness and mission markers, 360 metric rows, and zero critical errors. Host performance is diagnostic only.

## Tier B

Existing artifact classification: `TIER_B_APK_VERIFICATION_FAILURE` at legacy `aapt dump badging`, after both APKs were exported, signed and signature-verified.

Reducer run `30086594777`: success. It inspected the existing artifact without rerunning Android.

One targeted retry, run `30086966524`, reused exact APK bytes and corrected verification with AAPT2. Both APKs verified and the API 34 emulator booted. GL installed and launcher injection returned 0, but no application process became alive. Final classification: `TIER_B_APP_LAUNCH_FAILURE`. Mobile emulator execution was not attempted. No renderer failure is proven. No further Tier B retry is permitted in this checkpoint.

## Remaining blockers

1. Named minimum, target and high-end physical-device evidence.
2. Five-minute traversal, frame metrics, memory, thermal and lifecycle evidence.
3. Fatal/ANR/native-crash scans on physical devices.
4. API 34 GL launch root cause is unknown because no pre-PID process log was retained.
5. Renderer selection and fallback policy remain null.

## Outputs

- `reports/graphics/g0/G0_TERMINAL_REPORT.json`
- `reports/graphics/g0/G0_TERMINAL_REPORT.md`
- `reports/graphics/g0/tier_b_reduction/`
- `reports/graphics/g0/device_handoff/`

## Stop condition

Tier A is terminal; Tier B is reduced and diagnosed; exactly one targeted Tier B retry is complete; terminal reports and the physical-device handoff are emitted. No renderer defaults, production scenes, gameplay, controls, missions, materials, or production assets were changed. G1 has not begun.
