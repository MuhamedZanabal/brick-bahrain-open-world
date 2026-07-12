# V1.4 LANDSCAPE FALLBACK QA BUILD REPORT

Generated: 2026-07-12 (Asia/Bahrain)

## Classification

**Historical v1.4 fallback QA artifact — not v15.0.1 authority and not a production release.**

## Source provenance

- Base repository commit: `08378d1383eb7aeb1ae91b9eeb8994b79a96f1de`
- Delta branch: `v14-phone-apk`
- Delta branch head: `721e8c9df6cb8a4e142c18723a7fc72c27350159`
- Delta chunks: 17
- Decoded delta size: 76,132 bytes
- Decoded delta SHA-256: `7d1f637c83f32824dadf9d5b3a675184507707d3ddc2f557036d7afad1ac45a7`
- Delta members: 43

## Build identity

- Workflow: `Build v1.4 Landscape Fallback QA v3`
- Workflow run: `29177458351`
- Job: `86609013775`
- Head commit: `b915236c9d97db8bbae0f31a1e17941523318dad`
- Workflow conclusion: **success**
- Artifact ID: `8255363306`
- Artifact archive SHA-256: `3e8126fe16abc44d4ff4d8ca3954c0e109643fa05cb02ee7a1c73b78310392de`

## APK identity

- File: `brick_bahrain_v14.0.1-landscape-fallback-qa.apk`
- Size: 192,884,937 bytes
- SHA-256: `6ed01acb418b75cbdeb69239bcc8eacc8c43665cb7f01010eb6d5dc5d2f44cad`
- Package: `com.brickbahrain.openworld.fallbackqa`
- App label: `Brick Bahrain Fallback QA`
- Version code: `1401`
- Version name: `1.4.0.1-fallback-qa`
- Minimum SDK: 21
- Target/compile SDK: 34
- Native ABIs: `arm64-v8a`, `armeabi-v7a`, `x86_64`

## Orientation and Android verification

- Manifest `screenOrientation`: `0xb` / 11 / `sensorLandscape`
- APK ZIP integrity: PASS
- ZIP alignment: PASS
- APK Signature Scheme v1: PASS
- APK Signature Scheme v2: PASS
- APK Signature Scheme v3: PASS
- Signer certificate DN: `CN=Brick Bahrain Fallback QA, O=Zanabal Gaming, C=BH`
- Signer certificate SHA-256: `0a1af8918d1fd6eb73be149a7fdffa65b35692469d1679c951bf4df8dc34634a`
- Signing class: ephemeral Android debug certificate; controlled QA only
- Signing keystore packaged: false

## Permission disposition

Declared permissions:

- `android.permission.ACCESS_NETWORK_STATE`
- `android.permission.INTERNET`

Explicitly absent:

- `android.permission.RECORD_AUDIO`
- implied `android.hardware.microphone`

The incomplete push-to-talk path is feature-gated in this controlled QA build. It does not request microphone permission.

## Source/import/runtime verification

- Godot version: 4.3 stable
- Export templates: verified present
- Android SDK path: configured and verified
- Java SDK path: OpenJDK 17, configured and verified
- Project import and script/autoload compilation: PASS
- Project-loaded runtime smoke contract: **43 passed, 0 failed**
- Android export: PASS
- APK content verification: 837 ZIP entries, 6 native libraries, 751 asset entries, manifest present

## Known limitations

1. No physical Android device or controllable emulator was available in this conversation.
2. Install, launch, touch alignment, pause/resume, rotation, lifecycle, thermal, and phone frame-rate behavior remain unverified.
3. Headless Dummy-renderer execution emits repeated null-mesh diagnostics and shutdown resource-leak messages despite 43/43 functional smoke checks passing.
4. Asset provenance and complete project licensing remain release blockers.
5. This artifact is debug-signed and must not be distributed as production.
6. This source lineage predates the verified but currently unavailable v15.0.1 authority.

## QA decision

- Structural Android build gate: PASS
- Source import gate: PASS
- Headless functional smoke gate: PASS
- Landscape manifest gate: PASS
- Microphone/privacy fallback gate: PASS
- Physical Android runtime gate: BLOCKED pending user/device test
- Production release gate: NO-GO
