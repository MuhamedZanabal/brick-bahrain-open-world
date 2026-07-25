# Bahrain Brick — Stage G0.2 Android Paired-Renderer Functional Qualification

## Objective

Apply the accepted G0.1 harness-only correction and obtain independent API 34 x86_64 Android functional evidence for the existing GL Compatibility and Mobile Vulkan APKs derived from renderer-evidence authority `6ade72ed02084791128dcf4a91223e695d802c15`.

## Architecture

G0.2 recovers both exact APKs and their original shared-import manifests from Tier B artifact `8586122615`; it does not rebuild or re-import. One manual/PR-open workflow executes GL first, destroys and recreates the same declared AVD baseline, then executes Mobile. Each candidate uses a complete explicit state machine and receives its own terminal classification regardless of the other candidate result.

The collector resolves the exact launcher, starts logcat before launch, uses `am start -W -S`, retains ActivityManager process evidence, and evaluates PID plus top-resumed visible-window state. The finalizer emits all required reports, paired screenshot comparison, diagnostic metrics, terminal G0.2 outcome, and an unexecuted dual-renderer physical-device handoff.

## Boundaries

No production scene, gameplay, control, mission, material, art, shader, asset, or renderer-default change is permitted. Emulator measurements are diagnostic only. G0 remains `G0_EVIDENCE_INSUFFICIENT`, no renderer is selected, and G1 remains unauthorized.
