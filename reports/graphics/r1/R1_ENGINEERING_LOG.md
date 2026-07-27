# R1 Engineering Log

## GL Compatibility — light-cap mitigation

- **Defect:** `GL_COMPATIBILITY_ENGINE_GENERATED_FRAGMENT_UNIFORM_OVERFLOW`
- **Root cause:** Godot 4.3 Compatibility generates a scene-shader specialization requiring 261 fragment-uniform vectors on a 256-vector emulator/device budget. It reproduces in the unshaded one-box control; no user-authored shader or production material complexity is required.
- **Files changed:** `tools/graphics/apply_r1_gl_compatibility_fix.py`, `tests/graphics/test_r1_gl_compatibility_fix.py`, targeted GL runner/workflow.
- **Fix tested:** QA/project mitigation `rendering/limits/opengl/max_lights_per_object`.
- **Targeted tests:** focused setting contract, Godot 4.3 GL export, one Android launch, critical-log count, screenshot validation.
- **Android result:** baseline 45 link failures; cap 7 produced 44; caps 6, 5, and 4 remained 44. Export, launch, scene readiness, 1920×1080 screenshot, process liveness, and zero critical runtime errors passed.
- **Decision:** cap 7 is a proven one-count improvement, but the R1 exit criterion is not met because 44 link failures remain. The authorized project-level cap range is exhausted; no additional cap reduction is authorized.

## Mobile Vulkan — rendered-frame progression

- **Defect:** `RENDER_PIPELINE_STALL`
- **Root-cause boundary:** rendered-frame progression is the blocking subsystem. The render-disabled control reached frame 300 while normal rendering reached frame 90 in the same 240-second window. The exact renderer/engine operation causing the stall is not uniquely proven.
- **Targeted verification common to all corrections:** focused patch contract, Godot 4.3 Mobile export, one Android launch, 240-second frame window, screenshot validation, process liveness, critical-log scan, and pause/resume.

### Correction 1 — disable the remaining sun shadow

- **Change:** disable `LateAfternoonSun` shadowing in the reconstructed Mobile QA source; `SkyFill` was already unshadowed.
- **Result:** frame progression regressed from 90 to 80.
- **Operational gates:** export, launch, scene readiness, valid non-black 1920×1080 screenshot, process liveness, pause/resume, and zero critical runtime errors passed.
- **Decision:** reverted.

### Correction 2 — reduce Mobile directional-shadow size

- **Change:** `rendering/lights_and_shadows/directional_shadow/size.mobile` `2048 → 1024` in a QA-only project override.
- **Evidence:** workflow run `30310393343`, artifact `8670646110`.
- **Result:** frame progression remained `90 → 90`; frame 180 and frame 300 were not reached.
- **Operational gates:** export, launch, scene readiness, valid non-black 1920×1080 screenshot, process liveness, pause/resume, and zero critical runtime errors passed.
- **Decision:** reverted.

### Correction 3 — reduce LateAfternoonSun shadow distance

- **Change:** `sun.directional_shadow_max_distance` `150.0 → 100.0` for `LateAfternoonSun` only; `SkyFill` remained unshadowed.
- **Evidence:** workflow run `30312058073`, artifact `8671241285`.
- **Result:** frame progression regressed from 90 to 70; frame 180 and frame 300 were not reached.
- **Operational gates:** export, launch, scene readiness, valid non-black 1920×1080 screenshot, process liveness, pause/resume, and zero critical runtime errors passed.
- **Decision:** reverted.

## Engineering stop

- Three isolated Mobile corrections failed to improve the proven render-pipeline stall: completed-frame outcomes were 80, 90, and 70 against the frame-90 baseline.
- The queued `1.0 → 0.75` render-scale experiment was not executed and is removed; a fourth parameter tweak is not authorized without renewed root-cause evidence.
- R1 exit criteria remain unmet for both tracks. No production fix is authorized, renderer defaults remain unchanged, no renderer is selected, `G0_EVIDENCE_INSUFFICIENT` remains governing, and G1 remains unauthorized.
- **Next action:** return to root-cause diagnosis at the renderer/engine boundary and obtain named physical-device evidence before authorizing another correction.
