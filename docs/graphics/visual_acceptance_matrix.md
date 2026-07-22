# Bahrain Brick Graphics Visual Acceptance Matrix

Status: **G0 baseline capture pending**  
Recorded: 2026-07-22

## Capture Contract

Every comparison must use:

- the same source commit;
- the same deterministic layout seed (`1409`);
- the same camera transform and field of view;
- the same viewport and render scale;
- the same gameplay state;
- the same device/emulator identity;
- the same warm-up period;
- renderer and quality profile shown in metadata;
- lossless PNG screenshots for evidence;
- no post-processing outside the game capture path.

Reference concept images are directional art targets only. They are not production assets and must not be included in exported builds.

## Required Baseline Captures

| Evidence ID | Screen / state | Required composition | GL Compatibility | Mobile Vulkan | Acceptance notes |
|---|---|---|---|---|---|
| VIS-G0-001 | Boot splash | Full frame, no menu input visible | NOT_STARTED | NOT_STARTED | Record boot duration and image dimensions. |
| VIS-G0-002 | Runtime splash/loading | Progress UI and status text | NOT_STARTED | NOT_STARTED | Current implementation is simulated progress; capture exact behaviour. |
| VIS-G0-003 | Main menu | Full menu at 16:9 | NOT_STARTED | NOT_STARTED | Record branding, enabled actions, focus state and manual-coordinate defects. |
| VIS-G0-004 | Main menu wide | Full menu at 20:9 | NOT_STARTED | NOT_STARTED | Check clipping, dead zones and unsafe-area exposure. |
| VIS-G0-005 | Café court | Player start and karak collection marker | NOT_STARTED | NOT_STARTED | Same camera transform for both renderers. |
| VIS-G0-006 | Souq lane | Covered lane, storefront rhythm and pedestrians | NOT_STARTED | NOT_STARTED | Capture transparent overlap and shadow differences. |
| VIS-G0-007 | Main road | Mission vehicle, lanes and traffic | NOT_STARTED | NOT_STARTED | Capture aliasing, road material and skyline axis. |
| VIS-G0-008 | Waterfront | Delivery court and destination tower | NOT_STARTED | NOT_STARTED | Capture atmosphere, water placeholder and distance readability. |
| VIS-G0-009 | Mission HUD | Active objective, distance and order state | NOT_STARTED | NOT_STARTED | Verify touch controls remain visible. |
| VIS-G0-010 | Vehicle controls | Driving state with contextual input | NOT_STARTED | NOT_STARTED | Verify no input-semantic change. |
| VIS-G0-011 | Pause/resume | Android pause and restored gameplay | NOT_STARTED | NOT_STARTED | Record lifecycle logs. |
| VIS-G0-012 | Mission completion | Reward and replay action | NOT_STARTED | NOT_STARTED | Verify deterministic completion marker. |

## Required Performance Baseline

| Evidence ID | Metric | GL Compatibility | Mobile Vulkan | Target / decision use |
|---|---|---:|---:|---|
| PERF-G0-001 | Cold-start time | TBD | TBD | Compare startup reliability and latency. |
| PERF-G0-002 | Warm-start time | TBD | TBD | Detect cache/import differences. |
| PERF-G0-003 | Average frame time | TBD | TBD | Standard target ≤ 33.3 ms. |
| PERF-G0-004 | 95th percentile frame time | TBD | TBD | Must not hide recurring stalls. |
| PERF-G0-005 | Worst frame time | TBD | TBD | Record spikes above 100 ms. |
| PERF-G0-006 | Opaque draw calls | TBD | TBD | Initial target ≤ 450. |
| PERF-G0-007 | Transparent draw calls | TBD | TBD | Initial target ≤ 40. |
| PERF-G0-008 | Visible triangles | TBD | TBD | Initial target ≤ 1.2 million. |
| PERF-G0-009 | Process memory high-water mark | TBD | TBD | Device-qualified ceiling required. |
| PERF-G0-010 | Texture memory | TBD | TBD | Record capture method and uncertainty. |
| PERF-G0-011 | APK bytes | TBD | TBD | Compare against frozen baseline package. |
| PERF-G0-012 | Five-minute traversal result | TBD | TBD | Mission must complete without regression. |
| PERF-G0-013 | Thirty-minute soak result | TBD | TBD | No thermal collapse, crash or ANR. |

## Renderer Failure Matrix

| Failure class | GL Compatibility | Mobile Vulkan | Required evidence |
|---|---|---|---|
| Startup failure | UNKNOWN | UNKNOWN | Exit code, logcat and engine output. |
| Shader compilation failure | UNKNOWN | UNKNOWN | Shader/material path and driver signature. |
| Missing resource | UNKNOWN | UNKNOWN | Exact resource path and import state. |
| Unsupported GPU/driver | UNKNOWN | UNKNOWN | Device capability report. |
| Rendering corruption | UNKNOWN | UNKNOWN | Screenshot and reproducibility steps. |
| Excessive frame pacing | UNKNOWN | UNKNOWN | Frame-time series, not only average FPS. |
| ANR / native crash | UNKNOWN | UNKNOWN | Tombstone or crash signature. |
| Pause/resume failure | UNKNOWN | UNKNOWN | Lifecycle log and restored scene state. |
| Touch-control regression | UNKNOWN | UNKNOWN | Protected-control test and capture. |

## Visual Direction Acceptance

Later phases must be evaluated against these pillars without treating key art as a literal real-time geometry requirement.

| Pillar | Observable acceptance condition |
|---|---|
| Recognisable Bahrain | Every hero composition contains at least two readable Bahrain identifiers. |
| Construction-toy coherence | Major assets share simplified forms, bevelled edges, modular seams, consistent scale and controlled material families. |
| Warm cinematic contrast | Warm sunlight, cool sky/glass, Bahrain red accents, dark UI framing and readable white typography are balanced without crushing gameplay visibility. |
| Mobile readability | Essential text, touch targets, contrast, safe areas and context-sensitive actions pass handheld use. |
| Original premium branding | Visible branding is canonicalised to `BAHRAIN BRICK`; no copied toy trade dress or unlicensed production asset is present. |

## Gate Rule

Blank, simulated, desktop-only, emulator-only, or manually post-processed evidence does not satisfy G0. The renderer decision requires complete paired captures and device metadata.
