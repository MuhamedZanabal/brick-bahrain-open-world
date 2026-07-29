# Bahrain Brick Graphics — G0.2 Checkpoint

Recorded: 2026-07-25

## Terminal state

- Stage: **BAHRAIN BRICK — STAGE G0.2**
- Outcome: `G0_2_ANDROID_NEITHER_RENDERER_FUNCTIONAL`
- GL Compatibility: `ANDROID_CRITICAL_RUNTIME_FAILURE`
- Mobile Vulkan: `ANDROID_SCENE_READINESS_FAILURE`
- Shared imported-state equivalence: passed
- Renderer selected: no
- Renderer defaults changed: no
- Physical-device tests: not executed
- Graphics gate: `G0_EVIDENCE_INSUFFICIENT`
- G1: unauthorized

## Decisive evidence

GL completed launch, rendering, scene, capture, screenshot, liveness, and lifecycle, but emitted 45 renderer-blocking GLES3 program-link failures. Mobile completed launch, process, visible window, Vulkan identity, mission, and scene readiness, but did not reach warm-up frame 180 or capture frame 300 before the bounded timeout.

## Evidence authority

- Android run `30175169997`, job `89722664363`
- Raw artifact `8624075667`
- Reducer run `30175596770`, job `89723763711`
- Reduced artifact `8624118896`
- Reports: `reports/graphics/g0_2/`
- Dual-device handoff: `reports/graphics/g0/device_handoff/` — generated, not executed

## Boundary

No renderer is selected. Renderer defaults and production paths remain unchanged. Named physical-device evidence is still required. Do not begin G1.
