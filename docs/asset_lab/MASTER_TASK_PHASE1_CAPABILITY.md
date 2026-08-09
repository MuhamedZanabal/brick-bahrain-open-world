# Bahrain Brick 3D Asset Production — Phase 1 Capability Matrix

Recorded: 2026-08-09

## Execution surfaces

This phase distinguishes the current hosted ChatGPT container from connected GitHub Actions runners and from unavailable physical hardware. Historical evidence is retained as historical evidence; it is not relabeled as a current local capability or a physical-device pass.

### Current hosted ChatGPT container

| Capability | State | Verified detail |
|---|---|---|
| Python | local | Python `3.13.5` at `/opt/pyvenv/bin/python3`. |
| Node | local | Node `v22.16.0`. |
| Git | local | Git `2.47.3`. |
| Java/Javac | local | OpenJDK `21.0.11`; suitable for inspection, but the production Android CI route remains pinned to Java 17. |
| Image tools | local | ImageMagick 7 (`magick`; legacy `convert` shim also present). |
| FFmpeg | local | `7.1.5`. |
| Blender | blocked locally | No `blender` executable. |
| Godot | blocked locally | No `godot4` or `godot` executable. |
| Android ADB | blocked locally | No `adb` executable. |
| Android SDK manager | blocked locally | No `sdkmanager` or `avdmanager`. |
| Gradle | blocked locally | No `gradle` executable. |
| Android emulator/device | blocked locally | No local Android tools/device. |
| Connected workstation | blocked | Remote Desktop Commander reported no connected device. |

### Verified GitHub Actions CI route

Historical production artifact `8332600113` from successful run `29388970114` records:

- Blender `4.3.2`, build hash `32f5fdce0a0a`;
- Godot `4.3.stable.official.77dcf97d8`;
- Temurin OpenJDK `17.0.19`;
- Android `sdkmanager 20.0`;
- ADB `1.0.41`, platform-tools `37.0.0-14910828`;
- Khronos `gltf-validator 2.0.0-dev.3.10`;
- deterministic `bb_validation_cube_1m` GLB SHA-256 `00b2e146a7af0cc1043e9492f87c9ef2747d884aa0ada987e9be812537de8e2b`;
- cube dimensions exactly `1.0 × 1.0 × 1.0 m`, 12 triangles, one mesh, one material;
- clean Khronos cube validation with zero errors and zero warnings;
- Godot import of `res://assets/validation/bb_validation_cube_1m.glb`;
- Android APK export that contains the imported cube resource.

That historical artifact is valid evidence for the route, but it did not contain a cube-specific Android launch screenshot/log. Therefore it did not by itself close `P1.015`.

A dedicated current-branch qualification run was created specifically to close that gap:

- workflow: `.github/workflows/master-asset-phase1-cube.yml`;
- triggering commit: `cc2d66c52500138930f2200b403c255f51c443ac`;
- workflow run: `31289359822`;
- required final marker: `BAHRAIN_BRICK_CUBE_SMOKE_READY size=1.000,1.000,1.000`;
- required screenshot: `cube-smoke-android.png` from the exact exported APK on an API-34 x86_64 emulator.

At the time this record was first created, that run was still executing. `P1.015` remains pending until the run concludes and its artifact is independently inspected.

## Phase 1 task ledger

| Task | State | Evidence / route |
|---|---|---|
| `P1.001` | PASS | Current hosted tools inventoried; verified CI tools identified separately. |
| `P1.002` | PASS | Exact local and historical CI versions recorded above. |
| `P1.003` | PASS | Local/CI/blocked routes classified above. |
| `P1.004` | PASS — CI ROUTE | Historical successful CI ran Blender with `--background --factory-startup`; the current qualification workflow repeats this exact headless route. |
| `P1.005` | PASS — CI ROUTE | Historical successful CI ran Godot `4.3` headlessly for clean import; the current qualification workflow repeats the headless import route. |
| `P1.006` | PASS — CI ROUTE | Java 17, Android SDK/build-tools, ADB, export templates, APK signing/alignment were historically verified in CI and are reprovisioned by the current qualification workflow. They are absent from the hosted ChatGPT container. |
| `P1.007` | PASS FOR EMULATOR / BLOCKED FOR PHYSICAL | API-34 emulator route is historically verified and is being requalified. No physical Android reference device is currently connected; later physical-device release gates remain blocked. |
| `P1.008` | PASS | Blender execution route is GitHub Actions CI using checksum-verified Blender `4.3.2`; user workstation remains an optional future route, not a requirement for this phase. |
| `P1.009` | PASS | Godot import/build route is GitHub Actions CI using checksum-verified Godot `4.3.stable.official.77dcf97d8` and official export templates. |
| `P1.010` | NOT_APPLICABLE | Image-to-3D is not used. The project explicitly rejects one-shot image-to-3D conversion as a source-of-truth path. |
| `P1.011` | PASS | Canonical cube generator exists and historical artifact contains editable `.blend` source; current workflow regenerates it. |
| `P1.012` | PASS | Historical CI exported deterministic `.glb` twice with identical GLB bytes and independently validated 1 m dimensions; current workflow repeats it. |
| `P1.013` | PASS | Historical CI imported the cube into Godot and packaged its imported resource; current workflow additionally requires runtime AABB marker `1.000,1.000,1.000`. |
| `P1.014` | PASS | Historical CI exported a signed Android debug APK containing the cube import; current workflow exports a dedicated minimal cube-smoke APK. |
| `P1.015` | PENDING | Must not pass until exact run `31289359822` produces a successful API-34 launch, exact runtime-scale marker, non-blank landscape screenshot, and uploaded evidence artifact. |

## Gate decision

**PENDING.** Phase 1 is not yet exited because `P1.015` is still executing. Phase 2 must not begin until this record is updated with the exact successful run/artifact evidence or with a diagnosed blocker.
