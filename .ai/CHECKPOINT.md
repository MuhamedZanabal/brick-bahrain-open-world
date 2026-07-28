# Bahrain Brick Graphics — R1 Diagnostic Continuation

Recorded: 2026-07-28

## Current state

- Stage: **BAHRAIN BRICK — STAGE R1: RENDERER RUNTIME DEBUGGING**
- Outcome: `DIAGNOSTIC_CONTINUATION`
- Governing gate: `G0_EVIDENCE_INSUFFICIENT`
- R1 exit criteria met: no
- Production fix authorized: no
- Renderer selected: no
- Renderer defaults changed: no
- G1: unauthorized

## Track A — GL Compatibility

- Baseline: 45 `SceneShaderGLES3` link failures.
- Best project-level result: 44 failures at `rendering/limits/opengl/max_lights_per_object=7`.
- Caps 6, 5, and 4 also produced 44 failures.
- The authorized project-level light-cap range is exhausted; the zero-failure criterion remains unmet.

## Track B — Mobile Vulkan

- Classification: `RENDER_PIPELINE_STALL`.
- Baseline: frame 90; render-disabled control: frame 300.
- Four isolated corrections were reverted: sun shadow frame 80; shadow size frame 90; shadow distance frame 70; render scale frame 90.
- Render-scale evidence: run `30313623186`, artifact `8671766622`, digest `sha256:8091552aa33eccfebf9ac1cbd757682bf8e90d3f09f891940a48f14509a92599`.
- All operational health gates passed with zero critical runtime errors.

## Active micro-task

Run one Mobile-only QA experiment changing `Environment.TONE_MAPPER_FILMIC` to `Environment.TONE_MAPPER_LINEAR` in `SouqWorldEnvironment`.

Decision rule:

- Frame 300 plus health gates: retain as R1 Mobile pass candidate.
- Last completed frame greater than 90: retain temporarily as proven improvement.
- Last completed frame 90 or lower: revert.

No prior shadow, render-scale, GL, gameplay, mission, asset, or renderer-default change may be stacked.
