# R1 Engineering Log

## GL Compatibility — light-cap mitigation

- **Defect:** `GL_COMPATIBILITY_ENGINE_GENERATED_FRAGMENT_UNIFORM_OVERFLOW`
- **Root cause:** Godot 4.3 Compatibility generates a scene-shader specialization requiring 261 fragment-uniform vectors on a 256-vector emulator/device budget. It reproduces in the unshaded one-box control; no user-authored shader or production material complexity is required.
- **Fix tested:** QA/project mitigation `rendering/limits/opengl/max_lights_per_object`.
- **Android result:** baseline 45 link failures; cap 7 produced 44; caps 6, 5, and 4 remained 44. Operational gates passed and zero classified critical runtime errors were recorded.
- **Decision:** cap 7 is a proven one-count diagnostic improvement, but the zero-failure R1 criterion is unmet and the authorized project-level cap range is exhausted.

## Mobile Vulkan — rendered-frame progression

- **Defect:** `RENDER_PIPELINE_STALL`
- **Root-cause boundary:** the render-disabled control reached frame 300 while normal Godot 4.3 rendering reached frame 90 in the same 240-second window.

### Corrections 1–5

1. Disable `LateAfternoonSun` shadow: frame 80 — reverted.
2. Directional shadow size `2048 → 1024`: frame 90 — reverted. Run `30310393343`, artifact `8670646110`.
3. Shadow distance `150 → 100`: frame 70 — reverted. Run `30312058073`, artifact `8671241285`.
4. Mobile QA render scale `1.0 → 0.75`: frame 90 — reverted. Run `30313623186`, artifact `8671766622`.
5. Filmic-to-linear tonemapper: frame 70 — reverted. Run `30370527664`, artifact `8693475134`.

All five retained export, launch, scene readiness, valid non-black screenshot, liveness, and lifecycle health. None improved the frame-90 baseline.

## Godot 4.7.1 engine-boundary comparison

### Attempt 1 — harness timeout

- **Evidence:** run `30373598142`, artifact `8694707194`, digest `sha256:21ddb7af32a2797cfe695e27b0574e55fbdf4d183756f6bffde5376629edfff2`.
- **Result:** import exceeded 1,200 seconds before APK export or Android execution.
- **Classification:** `HARNESS_IMPORT_TIMEOUT`; non-adjudicative.
- **Correction:** import ceiling `1200 → 3600` seconds plus phase-status and mandatory result evidence.

### Attempt 2 — adjudicative

- **Evidence:** run `30376596221`, artifact `8696886506`, digest `sha256:2398209b65bb8a38fa809b9d70b3ace95c362b522bdfdb87fc364c17243f33be`.
- **Engine:** `4.7.1.stable.official.a13da4feb`.
- **Source equivalence:** 1,502 expected and actual files; production source byte equivalence passed; no import/QA-generated files were in scope.
- **GL result:** 44 link failures, 46 active-uniform overflow messages, scenario completion, scene readiness, valid 1920×1080 screenshot, liveness, pause/resume, and zero classified critical runtime errors. The zero-failure criterion remains unmet.
- **Mobile result:** scene readiness succeeded, but progression remained at frame 0 with zero heartbeats and six `Couldn't present to Vulkan queue (VkResult error 5)` messages. The process remained alive and produced a non-black 1920×1080 screenshot, but capture frame 300 was not reached.
- **Artifact decision:** retained because GL improved below the 45-failure baseline.
- **Engineering decision:** retain the result as diagnostic engine-boundary evidence only; reject production adoption of 4.7.1 because the same global engine candidate regressed Mobile from frame 90 to frame 0.

## Final engineering boundary

- Neither renderer meets the R1 exit criteria.
- No production fix or engine upgrade is authorized.
- Renderer selection remains null; renderer defaults remain unchanged.
- `G0_EVIDENCE_INSUFFICIENT` remains governing; G1–G10 remain blocked.
- The authorized emulator-side experiment graph is exhausted.
- **Next action:** obtain named physical-device evidence and/or investigate the upstream Godot/driver boundary. Do not execute another emulator parameter tweak or engine-version experiment.
