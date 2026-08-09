# Bahrain Brick 3D Asset Production — Phase 1 Capability Matrix

Recorded: 2026-08-09
Status: **PASS — PHASE 1 EXIT GATE SATISFIED**

## Authority

- Frozen game baseline: `5b4e2466ef84f3984f3bf336b31925d4d2e97a7f`.
- Execution branch: `work/bahrain-brick-master-asset-integration-v1`.
- Qualification head: `e3be62defd1b58ce0ce2d99f6385a68f1c6b5ba1`.
- Asset-source authority: `MuhamedZanabal/Bahrain_bricks_Assets`, branch `work/bahrain-brick-complete-asset-system-v1`, head `84ac94399262f71f29bf65dd553cd7729d87cce0`.
- Renderer contract remains Godot GL Compatibility. No production renderer setting was changed for this phase.
- No production gameplay, project, export-preset, or asset file was changed by the Phase 1 qualification work.

## Verified provenance chain

Phase 1 is closed from three linked evidence stages. Historical evidence is retained for audit, but the exit decision below is based on the current branch qualification chain.

| Stage | Run | Artifact | Verified result |
|---|---:|---:|---|
| Canonical Blender cube generation and independent validation | `31290094969` | `9031108247` | Blender headless route produced two byte-identical GLBs. Canonical cube SHA-256 is `00b2e146a7af0cc1043e9492f87c9ef2747d884aa0ada987e9be812537de8e2b`; independent bounds are exactly `1.0 × 1.0 × 1.0 m`. |
| Godot import and exact Android APK export | `31306171669` | `9036038870` | Godot `4.3.stable.official.77dcf97d8` imported the canonical GLB, executed the scene smoke with the exact `1.000,1.000,1.000` marker, and exported the dedicated API-34 x86_64 APK. APK SHA-256 is `5e56042a9f035459cbc618ad5b603703c7588597d5dace0fc49bb65145ec7d21`. |
| Fail-closed Android runtime and visual qualification | `31306428749` | `9036106518` (`swangle`) | The unchanged V3 APK installed and launched on an API-34 x86_64 emulator; the exact runtime marker was observed; crash/ANR/shader-failure scan passed; the Godot activity was resumed and focused; the 2400×1080 landscape screenshot visibly contains the cube. |

### Android visual/runtime evidence

Successful GPU route: Android Emulator software ANGLE/SwiftShader mode `swangle`.

- Renderer evidence: OpenGL ES 3.1 Compatibility through ANGLE using the Android Emulator SwiftShader device.
- Runtime marker: `BAHRAIN_BRICK_CUBE_SMOKE_READY size=1.000,1.000,1.000`.
- Package: `com.bahrainbrick.cubesmoke`.
- Activity: `com.godot.game.GodotApp`.
- API: `34`.
- ABI: `x86_64`.
- Orientation: landscape.
- Screenshot: `2400 × 1080`.
- Visible cube check: `58,022` orange cube pixels.
- Screenshot SHA-256: `9fe4711db179406d09bbcbe364fea86b2502624db1871031c50099c21a2d2435`.
- Crash/ANR/shader-failure scan: PASS; no `FATAL EXCEPTION`, fatal signal, `am_crash`, `am_anr`, ANR, program-link failure, shader compile failure, or `GL_MAX_FRAGMENT_UNIFORM` failure is present in the successful log.
- Window/activity evidence shows `com.bahrainbrick.cubesmoke/com.godot.game.GodotApp` as resumed, focused, and visible.

## Diagnostic history and root causes

The failed qualification attempts remain useful negative evidence and are not relabeled as passes.

1. V2 run `31291336144` failed before Android because the desktop scene smoke incorrectly invoked Godot with `--editor`, so the main scene never executed. The production project was not at fault.
2. V3 run `31306171669` fixed scene execution and proved import/export/runtime launch, but its Android screenshot was blank under the explicitly forced deprecated emulator mode `swiftshader_indirect`. The runtime log exposed a GLES3 program-link failure: the fragment shader required 261 uniform vectors while that virtual GPU route exposed a 256-vector limit.
3. V4 run `31306428749` reused the exact V3 APK instead of rebuilding it and changed only the emulator graphics route. The generic `software` diagnostic failed, while `swangle` passed the full fail-closed runtime and visual gate. This isolates the V3 blank frame to the emulator GPU backend rather than the cube, GLB, Godot import, APK, or game project.
4. V4 also replaced the earlier shell negative-grep pattern with an explicit fail-closed conditional so a shader-link failure cannot be silently accepted under shell `set -e` behavior.

## Protected-state verification

Frozen baseline root tree: `d7aa9d9e13dfe0c7e11df47f1071f2cbc44eabb7`.
Qualification-head root tree: `42d4017df337f5a1c212190f925b7e55d99ed20f`.

The following Git object identities are identical at the frozen baseline and qualification head:

| Protected scope | Baseline Git object | Qualification-head Git object | Result |
|---|---|---|---|
| `project.godot` | `39d2826f026a2f4897084a1efb61a47550019fc0` | `39d2826f026a2f4897084a1efb61a47550019fc0` | UNCHANGED |
| `export_presets.cfg` | `b918b069b0bd46932c3ff00953ac1f0b1f17fa31` | `b918b069b0bd46932c3ff00953ac1f0b1f17fa31` | UNCHANGED |
| entire `scripts/` tree | `6eb39f718706d43c58f04da1d9f00802362405e3` | `6eb39f718706d43c58f04da1d9f00802362405e3` | UNCHANGED |

Because the entire `scripts/` tree object is identical, all gameplay scripts under it—including `scripts/world.gd`, `scripts/player_controller.gd`, and `scripts/touch_input.gd`—are unchanged as a set.

## Phase 1 task ledger

| Task | State | Evidence / route |
|---|---|---|
| `P1.001` | PASS | Execution surfaces were inventoried and local/CI/blocked capabilities separated. |
| `P1.002` | PASS | Required tool versions were recorded; production qualification uses Blender `4.3.2` and Godot `4.3.stable.official.77dcf97d8`. |
| `P1.003` | PASS | Required work was routed through isolated GitHub Actions without assuming an unavailable workstation or physical device. |
| `P1.004` | PASS | Blender headless automation produced the canonical deterministic cube evidence. |
| `P1.005` | PASS | Godot headless import and actual game-mode scene execution passed for the canonical cube. |
| `P1.006` | PASS | Java 17, Android API 34 SDK/build-tools, ADB, emulator, export templates, signing, alignment, and APK inspection were exercised in CI. |
| `P1.007` | PASS FOR PHASE 1 EMULATOR ROUTE | API-34 x86_64 emulator qualification passed. No claim of a physical-device pass is made. |
| `P1.008` | PASS | Blender execution route is checksum-verified CI using Blender `4.3.2`; a user workstation is not required for this phase. |
| `P1.009` | PASS | Godot route uses checksum-verified Godot `4.3` and official export templates. |
| `P1.010` | PASS — NOT USED BY DESIGN | One-shot image-to-3D is not a source-of-truth path for this project. |
| `P1.011` | PASS | Canonical editable cube generation path exists and produces the 1 m validation asset. |
| `P1.012` | PASS | Duplicate generation is byte-identical and independently validates as exactly 1 m in all axes. |
| `P1.013` | PASS | Godot imports the exact cube and executes with runtime AABB marker `1.000,1.000,1.000`. |
| `P1.014` | PASS | Dedicated Android APK exported, signed/aligned, package/manifest validated, x86_64 library present, and canonical cube import packaged. |
| `P1.015` | PASS | Exact V3 APK launched on API-34 x86_64 under V4 `swangle`; exact scale marker, resumed/focused activity, clean crash/ANR/shader scan, and visible landscape screenshot all verified. |

## Gate decision

**READY — PHASE 1 CLOSED.** The Phase 1 exit evidence is complete and independently reconciled with the protected baseline. Phase 2 may begin only under its own entry gate and task ordering. This record does not authorize merge, release, deployment, renderer changes, physical-device claims, or modification of protected gameplay controls.
