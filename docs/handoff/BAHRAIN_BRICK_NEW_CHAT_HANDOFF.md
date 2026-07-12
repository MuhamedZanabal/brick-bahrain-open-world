# Bahrain Brick — New Chat Handoff

Use this document as the authoritative compact context when continuing the project in another ChatGPT conversation.

## Project identity

- Official game title: **Bahrain Brick**
- Studio splash 1: **Zanabal Gaming**
- Studio splash 2: **Mansoory Games**
- Engine: Godot 4.3 / GDScript
- Android package: `com.bahrainbrick.game.qa`
- Current QA version: `1.4.0.3-graphics-qa`
- Version code: `1403`
- Orientation: `sensorLandscape`

## Authority warning

The current deliverable is a recoverable **historical v1.4 fallback QA build**. It is not the missing v15.0.1 authority source.

Never relabel this fallback as v15 authority.

Known v15.0.1 authority identity:

- Branch: `audit/v15.0.1-authority`
- Commit: `796b112802c83ce78f8233e9a215e97c39ca028e`
- Tree: `26bb58714fa7066c1fd887cd33456553f3739462`

The exact v15 authority bytes remain unavailable.

## Frozen gameplay baseline

Accepted mobile-controls commit:

`c5548465627942a2889a0bd09f8979c3a29fbcdd`

Do not modify the repaired input pipeline unless a failing test proves it is necessary:

- `scripts/virtual_joystick.gd`
- `scripts/touch_input.gd`
- `scripts/player_controller.gd`
- HUD input propagation and walking/vehicle visibility logic
- local multiplayer authority logic
- `tests/mobile_input_pipeline_test.gd`
- `scenes/mobile_input_pipeline_test.tscn`

Verified controls regression: **28 passed, 0 failed**.

## Graphics integration state

Graphics branch:

`work/bahrain-brick-graphics-integration-v14`

Successful graphics source commit:

`464a8811a818bd6bb9e102566e0a525396b11515`

Successful workflow:

- Run: `29211024651`
- Job: `86698628299`
- Artifact: `8265202628`

Verified startup order:

1. Zanabal Gaming
2. Mansoory Games
3. Bahrain Brick main menu

Presentation acceptance: **10 passed, 0 failed**.

Frozen-control integrity:

- Before presentation tests: 25 checks, 0 failures
- After presentation tests: 25 checks, 0 failures

## Current APK

Filename:

`bahrain_brick_v14.0.3-graphics-qa.apk`

Size:

`191128589` bytes

SHA-256:

`753f9fe86a18da880886a6a6a501067aa3348dcbc8853e8f8a20e216e219ad4d`

Direct GitHub download:

https://github.com/MuhamedZanabal/brick-bahrain-open-world/releases/download/v1.4.0.3-graphics-qa/bahrain_brick_v14.0.3-graphics-qa.apk

Release page:

https://github.com/MuhamedZanabal/brick-bahrain-open-world/releases/tag/v1.4.0.3-graphics-qa

Release publication workflow:

- Run: `29212510806`
- Result: success
- Public asset URL verified by workflow

## Integrated presentation files

Presentation scripts:

- `scripts/ui_theme.gd`
- `scripts/splash_screen.gd`
- `scripts/main_menu.gd`
- `scripts/character_select.gd`
- `scripts/loading_screen.gd`
- `scripts/settings_panel.gd`
- `scripts/pause_menu.gd`

Presentation scenes:

- `scenes/loading_screen.tscn`
- `scenes/pause_menu.tscn`
- `scenes/settings_panel.tscn`
- `scenes/presentation_flow_test.tscn`
- `scenes/presentation_visual_evidence.tscn`

Runtime assets:

- `assets/ui/runtime/splash_zanabal.svg`
- `assets/ui/runtime/splash_mansoory.svg`
- `assets/ui/runtime/main_menu_background.svg`
- `assets/ui/runtime/character_select_background.svg`
- `assets/ui/runtime/loading_background.svg`
- `assets/ui/runtime/pause_background.svg`

Controlled integration points:

- `project.godot`
- `export_presets.cfg`
- `scripts/hud.gd::_on_pause_pressed`

Obsolete assets removed:

- `assets/splash_screen.png`
- `assets/splash_screen.png.import`

## What was actually verified

Hosted Godot/Linux software-rendered runtime:

- startup sequence and screen order
- main menu responsiveness
- character-selection path
- loading progress at 18%, 62%, and 100%
- loading completion
- pause/settings behavior
- Android Back resume behavior
- gameplay HUD rendering
- 28-check mobile-controls regression
- rendered control video after graphics integration
- Godot import and Android export

Android package verification:

- APK ZIP integrity
- ZIP alignment
- signature schemes v1, v2, and v3
- package, label, version, and orientation
- microphone permission absent
- signing keystore excluded from source ZIP

Not yet verified:

- physical Android installation of this graphics APK
- real-device touch latency
- real-device GPU performance and memory use
- manufacturer-specific lifecycle behavior

## Release decision

**BUILD CREATED — RUNTIME VERIFICATION BLOCKED**

Hosted runtime verification passed. Physical Android installation and human touch testing remain required before calling it a verified playable Android release.

## Known blockers and risks

1. Exact v15.0.1 authority source is still missing.
2. Full third-party asset provenance is incomplete.
3. Flexible Toon Shader upstream is MIT, but the bundled addon is a Godot 4 derivative port and requires transparent attribution.
4. The historical world produces null-mesh and cleanup diagnostics under the dummy renderer.
5. The APK uses an ephemeral QA certificate and is not production signed.
6. A previously exposed third-party credential still requires provider-side rotation; never reproduce it.

## Recommended next action

Install the GitHub Release APK on a physical Android phone and record:

- phone model
- Android version
- installation result
- first launch and exact splash order
- menu touch response
- character selection
- loading completion
- forward/backward/left/right/diagonal movement
- camera rotation
- jump
- pause/resume
- force-close and relaunch
- screenshots/video and relevant logcat if a defect occurs

Do not begin broad feature work until that phone-test result is recorded.

## New-chat bootstrap prompt

Paste the following into a new chat inside the **Bahrain Brick** ChatGPT Project:

```text
Continue the Bahrain Brick Android game project from the authoritative handoff at:
https://github.com/MuhamedZanabal/brick-bahrain-open-world/blob/handoff/bahrain-brick-v14.0.3/docs/handoff/BAHRAIN_BRICK_NEW_CHAT_HANDOFF.md

Repository:
https://github.com/MuhamedZanabal/brick-bahrain-open-world

Current APK release:
https://github.com/MuhamedZanabal/brick-bahrain-open-world/releases/tag/v1.4.0.3-graphics-qa

Read the handoff before acting. Preserve the frozen controls baseline commit c5548465627942a2889a0bd09f8979c3a29fbcdd. Treat the graphics build as a historical v1.4 fallback QA build, not v15 authority. Do not modify the repaired input pipeline unless a regression test fails. Begin by confirming the current GitHub branches, release assets, test evidence, and the result of physical Android testing. Use VERIFIED / INFERRED / PROPOSED / BLOCKED evidence labels and never fabricate builds or tests.
```
