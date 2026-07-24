# Bahrain Brick Stage G0.1 — Android Application Startup Root-Cause Qualification

## Terminal classification

`G0_1_CAUSE_NOT_PROVEN`

## Result

The exact accepted GL APK **successfully starts and remains alive** on the API 34 x86_64 emulator when launched through the resolved component with `am start -W -S`. The earlier Tier B non-live-process condition was not reproduced, so its exact cause is not proven.

## Decisive evidence

- APK SHA-256: `8461e9916b5636a35dd921d674529013b7b4623b3504f2332a9d7b4ac064b7eb`; no rebuild was performed.
- Package installation and `pm path` passed.
- Launcher: `com.brickbahrain.g0gl/com.godot.game.GodotApp`; exported and enabled.
- `am start -W -S`: `Status: ok`, total 819 ms, wait 828 ms.
- PID `2704` remained alive after 60 seconds.
- GodotApp remained top-resumed with a visible window and Surface.
- Godot reached renderer identity, mission start, scene readiness, warmup, capture frame 300, and live-evidence markers.
- No Java crash, native crash, linker failure, ANR, ABI failure, or manifest startup failure was detected.

## Why the classification is not stronger

The historical targeted Tier B run reported no PID after its acquisition loop. This G0.1 run shows both monkey and explicit-component launch paths can create the process, but it cannot reconstruct the transient state of the earlier emulator run. Therefore the exact historical cause remains unproven. No application or renderer failure is authorized.

## Smallest corrective proposal

Do not rebuild or modify the APK. Harden only the Tier B evidence harness: resolve the exact launcher component, begin logcat before launch, use `am start -W -S`, retain ActivityManager process-start evidence, and poll both PID and visible-window state before declaring startup failure.

No corrective implementation was performed. Renderer defaults remain unchanged. G1 remains unauthorized.
