# Brick Bahrain v1.4 Runtime Verification

The v1.4 gameplay/graphics source is frozen on `v14-runtime-verification`. This document covers the execution-only import, runtime, rendered evidence, Android export, APK verification and emulator pipeline.

## GitHub Actions

Workflow: `.github/workflows/godot_android_build.yml`

Artifacts:
- `v14-godot-import-logs`
- `v14-runtime-smoke-logs`
- `v14-runtime-screenshots`
- `v14-android-debug-apk`
- `v14-android-emulator-evidence`
- `v14-verification-summary`

The pipeline uses Godot 4.3 stable, its matching templates, OpenJDK 17, Android API 34 and build-tools 34.0.0. Visual evidence is captured from a real Xvfb OpenGL context; missing screenshots fail rather than generating placeholders.
