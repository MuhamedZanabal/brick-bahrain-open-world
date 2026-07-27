# Bahrain Brick Graphics — R1 Engineering Checkpoint

Recorded: 2026-07-28

## Current state

- Stage: **BAHRAIN BRICK — STAGE R1: RENDERER RUNTIME DEBUGGING**
- Outcome: `ENGINEERING_STOP`
- Governing gate: `G0_EVIDENCE_INSUFFICIENT`
- R1 exit criteria met: no
- Production fix authorized: no
- Renderer selected: no
- Renderer defaults changed: no
- G1: unauthorized

## Track A — GL Compatibility

- Classification: `GL_COMPATIBILITY_ENGINE_GENERATED_FRAGMENT_UNIFORM_OVERFLOW`
- Baseline: 45 `SceneShaderGLES3` link failures.
- Best project-level result: 44 failures at `rendering/limits/opengl/max_lights_per_object=7`.
- Caps 6, 5, and 4 also produced 44 failures.
- Export, launch, scene readiness, screenshot, liveness, and zero critical runtime errors passed.
- Decision: the authorized project-level light-cap range is exhausted; the zero-failure R1 criterion is unmet.

## Track B — Mobile Vulkan

- Classification: `RENDER_PIPELINE_STALL`
- Baseline: frame 90 in the 240-second window.
- Render-disabled control: frame 300.
- Correction 1, disable `LateAfternoonSun` shadow: frame 80 — reverted.
- Correction 2, shadow size `2048 → 1024`: frame 90 — reverted. Run `30310393343`, artifact `8670646110`.
- Correction 3, shadow distance `150 → 100`: frame 70 — reverted. Run `30312058073`, artifact `8671241285`.
- All three correction runs retained successful export, launch, scene readiness, valid non-black 1920×1080 screenshot, process liveness, pause/resume, and zero critical runtime errors.
- The queued render-scale experiment was not executed.

## Decision boundary

Three isolated Mobile corrections failed to improve progression. Do not execute a fourth parameter tweak, select a renderer, change renderer defaults, or begin G1 without renewed root-cause evidence.

## Next action

Return to root-cause diagnosis at the renderer/engine boundary and obtain named physical-device evidence before authorizing another correction.

## Evidence authority

- GL improvement run `30208525378`, artifact `8633929596`.
- Mobile shadow-size run `30310393343`, artifact `8670646110`.
- Mobile shadow-distance run `30312058073`, artifact `8671241285`.
- Reports: `reports/graphics/r1/R1_ENGINEERING_LOG.md` and `reports/graphics/r1/R1_ENGINEERING_STOP.json`.
