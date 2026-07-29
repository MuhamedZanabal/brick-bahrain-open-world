# Bahrain Brick Graphics — R1 Final Engineering Stop

Recorded: 2026-07-28

## Current state

- Stage: **BAHRAIN BRICK — STAGE R1: RENDERER RUNTIME DEBUGGING**
- Outcome: `ENGINEERING_STOP`
- Governing gate: `G0_EVIDENCE_INSUFFICIENT`
- R1 exit criteria met: no
- Production fix authorized: no
- Production engine upgrade authorized: no
- Renderer selected: no
- Renderer defaults changed: no
- G1: unauthorized

## Final emulator evidence

### GL Compatibility

- Godot 4.3 baseline: 45 `SceneShaderGLES3` link failures.
- Best project-level result: 44 at `rendering/limits/opengl/max_lights_per_object=7`; caps 6, 5, and 4 also remained 44.
- Godot 4.7.1 production-scene comparison: 44 link failures and 46 active-uniform overflow messages.
- Export, launch, scene readiness, valid 1920×1080 screenshot, liveness, pause/resume, and zero classified critical runtime errors passed.
- Exit criterion remains unmet because link failures are not zero.

### Mobile Vulkan

- Godot 4.3 baseline: frame 90 in 240 seconds.
- Render-disabled control: frame 300.
- Five isolated corrections were reverted with outcomes 80, 90, 70, 90, and 70.
- Godot 4.7.1 comparison: frame 0, zero heartbeats, and six `Couldn't present to Vulkan queue` failures after scene readiness.
- Launch, scene readiness, non-black 1920×1080 screenshot, liveness, and pause/resume passed, but the first rendered frame never completed.
- Exit criterion remains unmet.

## Engine comparison authority

- Attempt 1: run `30373598142`, artifact `8694707194`; `HARNESS_IMPORT_TIMEOUT`, non-adjudicative.
- Corrected attempt: run `30376596221`, artifact `8696886506`, digest `sha256:2398209b65bb8a38fa809b9d70b3ace95c362b522bdfdb87fc364c17243f33be`.
- The corrected harness completed import, both APK exports, both Android launches, proof validation, and decision enforcement.
- Decision: retain the 4.7.1 result as diagnostic engine-boundary evidence because GL improved below 45; reject production engine adoption because Mobile regressed from frame 90 to frame 0.

## Final boundary

The authorized emulator-side correction and engine-comparison graph is exhausted. Do not run another emulator parameter tweak or engine-version experiment, select a renderer, change renderer defaults, apply a production engine upgrade, or begin G1.

The remaining dependency is named physical-device evidence and/or upstream Godot/driver investigation outside the current emulator evidence boundary.
