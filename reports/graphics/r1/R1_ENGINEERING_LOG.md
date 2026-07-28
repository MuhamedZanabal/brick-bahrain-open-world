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
- **Evidence:** workflow run `30310393343`, artifact `8670646110`, artifact digest `sha256:14a663d4821e09e33cc349ded7914169b49fffb82de489cc0ec9fb7169b98ca1`.
- **Result:** frame progression remained `90 → 90`; frame 180 and frame 300 were not reached.
- **Operational gates:** export, launch, scene readiness, valid non-black 1920×1080 screenshot, process liveness, pause/resume, and zero critical runtime errors passed.
- **Decision:** reverted.

### Correction 3 — reduce LateAfternoonSun shadow distance

- **Change:** `sun.directional_shadow_max_distance` `150.0 → 100.0` for `LateAfternoonSun` only; `SkyFill` remained unshadowed.
- **Evidence:** workflow run `30312058073`, artifact `8671241285`, artifact digest `sha256:8f132bc2de7b2312e26cead44395b5145c3a62f6f3cb3a35331e0c4e739c1bab`.
- **Result:** frame progression regressed from 90 to 70; frame 180 and frame 300 were not reached.
- **Operational gates:** export, launch, scene readiness, valid non-black 1920×1080 screenshot, process liveness, pause/resume, and zero critical runtime errors passed.
- **Decision:** reverted.

### Correction 4 — reduce Mobile QA render scale

- **Change:** `rendering/scaling_3d/scale` `1.0 → 0.75` in a QA-only project override.
- **Evidence:** workflow run `30313623186`, artifact `8671766622`, artifact digest `sha256:8091552aa33eccfebf9ac1cbd757682bf8e90d3f09f891940a48f14509a92599`.
- **Result:** frame progression remained `90 → 90`; frame 180 and frame 300 were not reached.
- **Operational gates:** export, launch, scene readiness, valid non-black 1920×1080 screenshot, process liveness, pause/resume, and zero critical runtime errors passed.
- **Decision:** reverted.

### Correction 5 — replace filmic tonemapping with linear tonemapping

- **Change:** `SouqWorldEnvironment` tonemapper `Environment.TONE_MAPPER_FILMIC → Environment.TONE_MAPPER_LINEAR` in reconstructed Mobile QA source only.
- **Evidence:** workflow run `30370527664`, artifact `8693475134`, artifact digest `sha256:90e0e65a3b3b9f232a3cee83bbff28d3ec32591d4ad50f4882e1c13c5927bd83`.
- **Result:** frame progression regressed from 90 to 70; frame 180 and frame 300 were not reached.
- **Operational gates:** export, launch, scene readiness, valid non-black 1920×1080 screenshot, process liveness, pause/resume, and zero critical runtime errors passed.
- **Decision:** reverted.

## Current engineering boundary

- Five isolated render-cost reductions did not improve the proven Mobile render-pipeline stall: completed-frame outcomes were 80, 90, 70, 90, and 70 against the frame-90 baseline.
- R1 exit criteria remain unmet for both tracks. Renderer defaults remain unchanged, no renderer is selected, `G0_EVIDENCE_INSUFFICIENT` remains governing, and G1 remains unauthorized.
- **Next highest-leverage action:** compare unmodified GL production and Mobile baseline on Godot `4.7.1-stable` using one imported state. This tests the shared engine boundary for both unresolved defects without stacking any project-level correction.

### Engine comparison attempt 1 — harness timeout

- **Evidence:** workflow run `30373598142`, artifact `8694707194`, artifact digest `sha256:21ddb7af32a2797cfe695e27b0574e55fbdf4d183756f6bffde5376629edfff2`.
- **Observed engine:** `4.7.1.stable.official.a13da4feb`; official binary and template checksums passed.
- **Result:** the shared source import exceeded the historical 1,200-second ceiling and was terminated before either APK export or Android target. No GL or Mobile engine result exists.
- **Classification:** `HARNESS_IMPORT_TIMEOUT`; non-adjudicative.
- **Harness correction:** extend only the 4.7.1 import ceiling to 3,600 seconds and emit phase status to `R1_ENGINE_HARNESS_STATUS.json` before rerunning the same two targets.
