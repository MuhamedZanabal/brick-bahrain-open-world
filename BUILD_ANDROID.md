# Brick Bahrain v1.4 Android Build and Verification

## Required versions

- Godot 4.3 stable
- Godot 4.3 stable export templates
- OpenJDK 17
- Android platform 34
- Android build-tools 34.0.0
- Android platform-tools

## Local smoke test

Linux:

```bash
tools/run_godot_smoke_test_linux.sh
```

Windows PowerShell:

```powershell
./tools/run_godot_smoke_test_windows.ps1
```

## Export

Linux:

```bash
tools/export_android_linux.sh
```

Windows PowerShell:

```powershell
./tools/export_android_windows.ps1
```

Direct command:

```bash
godot --headless --path . --export-debug Android build/brick_bahrain_v14-debug.apk
```

## CI

The branch `v14-runtime-verification` runs `.github/workflows/godot_android_build.yml`. The workflow imports the project, runs the real smoke test, captures rendered screenshots under Xvfb, exports and verifies the APK, then attempts installation and two launches on an Android API 34 emulator.

Artifacts are named with the `v14-` prefix. The APK artifact contains `build/brick_bahrain_v14-debug.apk`, its SHA-256 file and the complete export/verification logs.

## Device install and diagnostics

```bash
adb install -r build/brick_bahrain_v14-debug.apk
AAPT="$ANDROID_SDK_ROOT/build-tools/34.0.0/aapt"
PACKAGE="$($AAPT dump badging build/brick_bahrain_v14-debug.apk | sed -n "s/^package: name='\([^']*\)'.*/\1/p")"
ACTIVITY="$($AAPT dump badging build/brick_bahrain_v14-debug.apk | sed -n "s/^launchable-activity: name='\([^']*\)'.*/\1/p")"
adb logcat -c
adb shell am start -W -n "$PACKAGE/$ACTIVITY"
adb logcat -v threadtime
```
