# Bahrain Brick Android Graphics Device Matrix

Status: **PROVISIONAL — G0 qualification evidence pending**  
Recorded: 2026-07-22

## Authority Rule

A renderer or quality profile is not accepted because it launches once on an emulator. Acceptance requires repeatable physical-device evidence with the exact device, SoC, GPU, driver, OS/API level, renderer, resolution, thermal state, and build hash recorded.

The API 34 AOSP x86_64 emulator required by PR #59 is a deterministic compatibility and lifecycle target. It is not a substitute for minimum-tier physical-device performance evidence.

## Tier Definitions

| Tier | Purpose | Provisional hardware envelope | Required renderer qualification | Default profile target |
|---|---|---|---|---|
| Minimum | Lowest supported physical Android device | 64-bit ARM; 4 GB RAM; Android 11 / API 30 or newer; GLES 3.0 support; Vulkan 1.1 only when driver stability passes; sustained thermal operation without severe throttling | GL Compatibility must pass. Mobile Vulkan may be optional only if the exact GPU/driver is qualified. | Low, 0.65–0.75 render scale, 30 FPS target |
| Target | Primary acceptance and optimisation device | 64-bit ARM; 6 GB RAM; Android 13 / API 33 or newer; modern mid-range GPU; Vulkan 1.1+ with stable Godot 4.3 driver behaviour | Both candidates must be tested; selected authoritative renderer must pass all functional and endurance gates. | Medium, 0.80–0.90 render scale, sustained 30 FPS |
| High-end | Enhanced presentation device | 64-bit ARM; 8 GB RAM or more; Android 14 / API 34 or newer; recent high-end GPU; Vulkan 1.2+ preferred | Authoritative renderer required; compatibility fallback still tested if shipped. | High at 1.0 render scale; 45–60 FPS optional |
| Qualified Ultra | Explicit allowlist only | Named device/GPU/driver combinations proven by evidence | Mobile Vulkan expected; no exposure on unqualified devices | Ultra optional; never part of standard acceptance |
| CI Emulator | Deterministic Android lifecycle and package diagnostics | API 34 AOSP x86_64, 2400 × 1080 landscape | Mobile Vulkan evidence required by PR #59 design; GL Compatibility comparison also captured for G0 | Diagnostic only |

## Required Named Devices

The following rows must be completed with real hardware before G0 can pass.

| Tier | Manufacturer / model | SoC | GPU | RAM | Android / API | GPU driver | Renderer(s) tested | Owner | State |
|---|---|---|---|---:|---|---|---|---|---|
| Minimum | TBD | TBD | TBD | TBD | TBD | TBD | GL Compatibility + Mobile Vulkan where supported | TBD | NOT_STARTED |
| Target | TBD | TBD | TBD | TBD | TBD | TBD | GL Compatibility + Mobile Vulkan | TBD | NOT_STARTED |
| High-end | TBD | TBD | TBD | TBD | TBD | TBD | GL Compatibility + Mobile Vulkan | TBD | NOT_STARTED |
| CI emulator | API 34 AOSP x86_64 | virtual | virtual | runner-defined | Android 14 / API 34 | emulator image build | GL Compatibility + Mobile Vulkan | CI | NOT_STARTED |

## Evidence Required Per Device and Renderer

- Build commit and APK SHA-256.
- Godot version and renderer name.
- Android version, API level, security patch, build fingerprint.
- SoC, GPU, RAM, GPU driver and Vulkan/OpenGL capability report.
- Native resolution, render scale, orientation and refresh rate.
- Cold-start load time and warm-start load time.
- Five-minute deterministic Karak Delivery traversal.
- Thirty-minute thermal soak.
- Average, median, 95th percentile and worst frame time.
- Repeated frame spikes above 100 ms.
- CPU and GPU frame cost where tooling permits.
- Visible triangle count, opaque draw calls, transparent draw calls.
- Texture and process memory high-water marks.
- Thermal status and clock-throttling evidence.
- Screenshot set for splash, menu, gameplay, HUD, pause and mission completion.
- Logs proving no fatal error, ANR, native crash, missing resource, shader compilation failure or unsupported-renderer signature.

## Acceptance Thresholds

### Standard acceptance

- 30 FPS sustained target.
- Total frame time at or below 33.3 ms under the agreed capture method.
- No repeated frame spikes above 100 ms.
- No thermal collapse during the 30-minute soak.
- No gameplay regression, control regression, crash, ANR, shader failure or missing resource.

### Initial scene budgets

| Metric | Standard target |
|---|---:|
| Visible triangles | ≤ 1.2 million |
| Visible opaque draw calls | ≤ 450 |
| Transparent draw calls | ≤ 40 |
| Active shadow-casting local lights | 0–2 |
| Visible skinned characters | 12 |
| Unique visible material families | ≤ 40 |
| Uncompressed 4K gameplay textures | 0 |

These are starting budgets. Changes require device evidence and an explicit recorded decision.

## Renderer Decision Rule

Select Mobile Vulkan as authoritative only if it passes the minimum and target physical-device gates without material reliability regressions and delivers sufficient visual/performance value over GL Compatibility.

Select GL Compatibility as authoritative if Mobile Vulkan fails the minimum reliability gate, has unacceptable driver coverage, or creates a dual-path maintenance burden unsupported by measured benefit.

Ship two paths only when:

1. both are continuously testable;
2. quality differences are data-driven;
3. fallback selection is deterministic and safe;
4. shader/material assets have explicit compatibility variants;
5. package size and maintenance costs remain acceptable.
