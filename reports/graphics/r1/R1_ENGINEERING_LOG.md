# R1 Engineering Log

## GL Compatibility — light-cap mitigation

- **Defect:** `GL_COMPATIBILITY_ENGINE_GENERATED_FRAGMENT_UNIFORM_OVERFLOW`
- **Root cause:** Godot 4.3 Compatibility generates a scene-shader specialization requiring 261 fragment-uniform vectors on a 256-vector emulator/device budget. It reproduces in the unshaded one-box control; no user-authored shader or production material complexity is required.
- **Files changed:** `tools/graphics/apply_r1_gl_compatibility_fix.py`, `tests/graphics/test_r1_gl_compatibility_fix.py`, targeted GL runner/workflow.
- **Fix:** QA/project mitigation `rendering/limits/opengl/max_lights_per_object=4`; this is not an engine source-code fix.
- **Targeted tests:** focused setting contract, Godot 4.3 GL export, one Android launch, critical-log count, screenshot validation.
- **Android result:** baseline 45 link failures; cap 7 produced 44; caps 6, 5, and 4 remained 44. Export, launch, scene readiness, 1920×1080 screenshot, process liveness, and zero critical runtime errors passed at cap 4.
- **Remaining issue:** GL R1 criterion is not met because 44 link failures remain. The authorized project-level light-cap range is exhausted.

## Mobile Vulkan — directional-shadow reduction

- **Defect:** `RENDER_PIPELINE_STALL`
- **Root cause:** rendered-frame progression is the blocking subsystem; the render-disabled control reached frame 300 while normal rendering reached frame 90 in 240 seconds.
- **Files changed:** temporary QA-only shadow patcher/test and Mobile-only runner/workflow; the patcher and test were removed after the failed experiment.
- **Fix tested:** the second directional light was already unshadowed, so the first effective experiment disabled the remaining `LateAfternoonSun` shadow in the reconstructed Mobile QA source.
- **Targeted tests:** focused patch contract, Godot 4.3 Mobile export, one Android launch, 240-second frame window, screenshot validation, process liveness, critical-log scan, pause/resume.
- **Android result:** frame progression regressed from 90 to 80. Export, launch, scene readiness, valid non-black 1920×1080 screenshot, process liveness, pause/resume, and zero critical runtime errors passed.
- **Remaining issue:** experiment reverted. Next smallest action is to reduce directional shadow size in a Mobile-only QA override.
