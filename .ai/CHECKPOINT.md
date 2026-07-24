# Bahrain Brick Graphics — G0.1 Checkpoint

Recorded: 2026-07-24

## Terminal state

- Stage: **BAHRAIN BRICK — STAGE G0.1**
- Classification: `G0_1_CAUSE_NOT_PROVEN`
- Exact APK reused without rebuild: yes
- Package installation: passed
- Launcher resolution: passed
- Explicit `am start -W -S`: `Status: ok`
- Process remained alive: yes
- Window became visible: yes
- Java/native/linker crash: not detected
- Corrective implementation: not performed
- Renderer defaults: unchanged
- G1: unauthorized

## Evidence authority

- Android run: `30126561161`
- Raw artifact: `8609540209`
- Reducer run: `30126886903`
- Reduced artifact: `8609597152`
- Required reports: `reports/graphics/g0_1/`

## Boundary

The exact accepted APK starts and reaches the Godot renderer, mission, scene-readiness, capture, and live-evidence markers on the API 34 x86_64 emulator. The earlier Tier B no-process condition was not reproduced, so its transient cause is not proven.

The smallest proposal is harness-only: resolve the launcher component, start logcat before launch, use `am start -W -S`, preserve ActivityManager process-start evidence, and poll PID plus visible-window state. Await separate authorization before implementing it.
