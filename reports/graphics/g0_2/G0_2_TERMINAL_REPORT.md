# Bahrain Brick — Stage G0.2 Terminal Report

## Terminal outcome

`G0_2_ANDROID_NEITHER_RENDERER_FUNCTIONAL`

- GL Compatibility: `ANDROID_CRITICAL_RUNTIME_FAILURE`. Package, explicit launch, process, visible window, OpenGL renderer identity, mission, scene readiness, capture frame 300, valid 1920 × 1080 screenshot, 60-second liveness, and pause/resume passed. The earliest failed state was `CRITICAL_LOG_SCAN_PASSED`, with 45 `SceneShaderGLES3: Program linking failed` events.
- Mobile Vulkan: `ANDROID_SCENE_READINESS_FAILURE`. Package, explicit launch, process creation, visible window, Godot, Vulkan renderer identity, mission, and scene readiness passed. The earliest failed state was `CAPTURE_FRAME_REACHED`: warm-up frame 180 and capture frame 300 were absent at the bounded timeout.
- Shared imported-state equivalence: `True` across `8214` files, aggregate SHA-256 `e0360a68b2ac1d4ccfc0ced390a822950ac38a7f18509dfc585e98caea097197`.
- Emulator measurements are `DIAGNOSTIC_ONLY_NOT_PHYSICAL_DEVICE_ACCEPTANCE`.

## Screenshot boundary

GL produced a valid non-black 1920 × 1080 screenshot. Mobile did not reach screenshot capture. Its required PNG output is an explicit black missing-evidence placeholder marked `source_evidence_present=false`; structural and pixel comparison were not performed.

## Execution authority

- Adjudicative Android run: `30175169997`, job `89722664363`.
- Raw artifact: `8624075667`, digest `sha256:677c0b55a937ee46f1f85dc600c9ac09c716bae58fd92638824f868792f90d69`.
- Reducer/finalizer replay: `30175596770`, job `89723763711`.
- Reduced artifact: `8624118896`, digest `sha256:6581fef39feed0501af438ae73ef6abbb9118851fd10e7ec8ffa6dac0b6f7156`.
- No Android rerun was performed during terminal report generation.

## Gate boundary

The graphics gate remains `G0_EVIDENCE_INSUFFICIENT`. No renderer is selected, renderer defaults remain unchanged, the dual-renderer physical-device handoff remains unexecuted, and G1 remains unauthorized.
