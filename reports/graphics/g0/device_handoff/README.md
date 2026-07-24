# G0 Physical-Device Test Handoff

Status: **NOT EXECUTED**.

This package is for named physical-device evidence only. It does not change renderer defaults and does not select a renderer.

## APK authority

Retrieve the diagnostic APKs from Tier B artifact `8586122615` (run `30064876896`, digest `sha256:4d4d3a696f4a326c3ddd63d1f51c278263fc25e6f2e00f68c0c3b64fb3c2e9ee`). Verify them against `apk_sha256.txt` before installation.

## Required matrix

Run each applicable renderer on named minimum, target, and high-end devices. Record exact model, SoC, GPU, RAM, Android version, display resolution, renderer, quality preset, APK SHA-256, cold start, readiness, five-minute traversal, frame metrics where available, peak memory, thermal state, pause/resume, and fatal/ANR/native-crash scan.

## Execution

```bash
bash run_device_test.sh <apk> <package> <renderer> <output-dir> [quality-preset]
```

```powershell
./run_device_test.ps1 -Apk <apk> -Package <package> -Renderer <renderer> -OutputDir <dir> -QualityPreset frozen_baseline
```

Packages:

- GL Compatibility: `com.brickbahrain.g0gl`
- Mobile Vulkan: `com.brickbahrain.g0mobile`

The scripts collect raw evidence and a preliminary `device_result.json`. Review it against `device_result.schema.json`; do not treat automated values as acceptance without a human-confirmed five-minute traversal.
