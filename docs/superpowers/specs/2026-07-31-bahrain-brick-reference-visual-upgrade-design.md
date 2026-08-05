# Bahrain Brick Reference Visual Upgrade — Design

Date: 2026-07-31
Branch: `work/bahrain-brick-reference-visual-upgrade`
Base commit: `ac8edaef8853fb7e344b2e347f5de36a008c6ba7`
Status: Approved for planning

## 1. Objective

Upgrade the actual Godot Android game so its splash, menus, gameplay HUD, pause/settings interface, and world presentation match the uploaded Bahrain Brick visual references as closely as is technically credible on ARM64 Android hardware.

The deliverable is not a collection of concept images. It is a functioning APK whose real scenes, controls, data bindings, transitions, and in-game graphics use the reference visual language.

## 2. Authority and Isolation

The renderer-diagnostics branch and PR #63 remain frozen and unchanged. This visual implementation proceeds on the separate branch `work/bahrain-brick-reference-visual-upgrade`.

No change made by this project may:

- alter the frozen evidence or conclusions in PR #63;
- claim that GL Compatibility or Mobile Vulkan has passed R1 qualification;
- authorize a production renderer selection or engine upgrade;
- weaken existing renderer tests or qualification gates;
- begin G1 work.

The visual upgrade may reuse the existing project state and assets, but all production-facing modifications must be independently testable and reversible.

## 3. Success Criteria

The upgrade is accepted when all of the following are true:

1. The APK launches into the real branded splash and loading sequence.
2. The main menu closely matches the reference composition, typography hierarchy, palette, and button treatment.
3. Character selection is functional and persists the selected character.
4. The gameplay scene contains the real HUD: health, energy, level, currencies, minimap shell, mission panel, waypoint distance, inventory hotbar, joystick, and action controls.
5. Pause and settings are functional and visually aligned with the references.
6. Graphics settings apply real quality changes without violating the frozen renderer boundary.
7. The world presentation visibly improves through lighting, environment, materials, landmark composition, vegetation, vehicles, signage, and color grading.
8. Existing gameplay entry points remain usable.
9. Android export, package inspection, signature verification, and launch smoke tests pass.
10. The final APK and screenshots are produced from the implemented game, not from image-generation mockups.

## 4. Visual Target

The uploaded references define the target visual language:

- premium toy-brick Bahrain city;
- Bahrain World Trade Center and Manama skyline framing;
- cream stone fort/tower architecture;
- palm-lined waterfront roads;
- wet or glossy brick pavement with strong reflections;
- warm golden-hour key light, blue sky, atmospheric depth, and saturated but controlled color;
- large white-and-red brick title treatment;
- black panels with gold borders;
- glossy color-coded rounded buttons;
- compact, high-contrast mobile HUD;
- English and Arabic Bahrain signage;
- visible mission marker and distance;
- LEGO-like minifigure characters and vehicles.

The references are promotional-grade renders. The implementation target is perceptual similarity in composition, art direction, UI, materials, and lighting—not pixel identity or offline-render fidelity.

## 5. Technical Approach

### 5.1 Recommended Architecture

Use native Godot scenes and reusable components for all interactive UI. Use raster artwork only where it is appropriate for splash backgrounds, logo treatments, icons, and decorative panels.

Create a visual system with:

- a central theme and token file for colors, spacing, radii, shadows, typography, and focus states;
- reusable UI scenes for buttons, panels, counters, status bars, toggles, sliders, hotbar slots, touch controls, and profile cards;
- scene-specific controllers that bind existing game state to the UI;
- quality-profile resources that apply bounded environment and rendering changes;
- a visual regression harness that captures deterministic menu and HUD screenshots.

This prevents each screen from reimplementing styling and makes later tuning fast and consistent.

### 5.2 Alternatives Considered

#### A. Full-screen static mockup images with invisible hitboxes

Advantages:

- fastest way to imitate the references;
- exact-looking menu composition at one resolution.

Rejected because:

- poor scaling and accessibility;
- brittle localization and state binding;
- controls and dynamic values would not be real;
- unusable for gameplay HUD and settings;
- would conceal rather than solve the current implementation gap.

#### B. Fully procedural UI using only primitive Godot controls

Advantages:

- minimal asset work;
- highly responsive and easy to bind.

Rejected as the sole approach because:

- current project already demonstrates that flat primitive controls do not reach the required visual quality;
- expensive to reproduce detailed logos, iconography, bevels, and decorative treatments entirely in code.

#### C. Hybrid native UI plus authored artwork

Selected approach.

- Native controls provide real behavior, responsiveness, state binding, navigation, and testing.
- Authored textures provide the detailed visual finish required by the references.
- Shared theme resources keep all screens coherent.

## 6. Screen Design

### 6.1 Studio Splash

Sequence:

1. Zanabal Gaming crest/logo on a dramatic Bahrain skyline background.
2. Short fade and scale animation.
3. Transition to Bahrain Brick loading screen.

Requirements:

- skip handling remains bounded by the minimum display time;
- no frame-blocking synchronous work on the UI thread;
- aspect-fill background with safe-area protection;
- reduced-motion fallback.

### 6.2 Loading Screen

Composition:

- large Bahrain Brick logo in the upper half;
- player character and vehicles in the foreground;
- Bahrain waterfront road and landmarks;
- gold progress bar and numeric percentage;
- rotating tip text.

The progress display must reflect actual staged loading where possible. When exact engine progress is unavailable, it may interpolate between verified loading milestones but must not reach 100% before the next scene is ready.

### 6.3 Main Menu

Composition:

- large Bahrain Brick title and `Open World Sandbox` subtitle on the left;
- player character and vehicles in the world background;
- right-side vertical button stack;
- bottom-left player profile, level progress, and coin count;
- bottom-right social/footer icon row.

Functional buttons:

- Play;
- Character Select;
- Multiplayer;
- Missions;
- Settings;
- Credits;
- Exit.

Existing single-player, host, join, mission preview, and exit behavior will be preserved or routed through the new navigation model.

### 6.4 Character Select

Characters:

- Pearl Diver;
- Street Racer;
- Sky Pilot.

Each selection has:

- a real selectable card or podium;
- name, icon, and description;
- visual selected state;
- preview model or authored portrait;
- persistent character identifier stored through `SaveManager`;
- Play and Back actions.

Character selection must affect the spawned player appearance where the existing character system permits. If the current player model architecture cannot support full appearance switching safely, the first release will at minimum persist the selection and apply the corresponding profile portrait and color treatment, with the limitation recorded explicitly.

### 6.5 Gameplay HUD

HUD regions:

- top left: crest, level, health, energy;
- top right: gold and blue currency, pause;
- right: minimap shell, district/time label, mission card;
- center-world: waypoint icon, beam, and distance;
- bottom left: virtual joystick and latency indicator;
- bottom center: inventory hotbar;
- bottom right: run/vehicle, attack/interact, jump, and context actions.

Data binding:

- health and energy bind to authoritative player state;
- currencies bind to saved economy state;
- mission panel binds to `MissionManager`;
- waypoint distance is computed from the active objective;
- hotbar binds to inventory state;
- touch controls emit existing input actions through `TouchInput`.

The HUD must not intercept world input outside its active controls.

### 6.6 Pause and Settings

Pause behavior:

- freezes single-player simulation safely;
- preserves multiplayer/network behavior where full tree pause would be invalid;
- resumes without losing touch state;
- supports Android back-button behavior.

Settings sections:

- Graphics;
- Controls;
- Audio;
- Gameplay;
- Account and support links where implemented.

Initial settings:

- quality: Low, Medium, High, Ultra;
- brightness;
- field of view;
- invert Y-axis;
- camera shake;
- auto jump;
- tutorial hints;
- master/music/effects volume;
- touch sensitivity.

Settings persist through `SaveManager` and apply immediately where safe.

## 7. World Presentation Upgrade

### 7.1 Composition

Prioritize one highly finished Manama waterfront gameplay corridor rather than superficially changing the entire world.

The corridor will include:

- Bahrain World Trade Center silhouette;
- modern glass towers;
- cream fort/tower landmark;
- waterfront promenade;
- palm trees and landscaped planters;
- Arabic-English signs;
- red sports car and white SUV hero vehicles;
- mission marker sightline;
- controlled traffic and background props.

### 7.2 Lighting and Environment

Implement bounded quality profiles:

- Low: reduced shadow distance, reflection complexity, particles, and post-processing;
- Medium: balanced mobile default;
- High: improved shadows, reflection probes, environment effects, and density;
- Ultra: strongest supported visual profile, still bounded by mobile stability.

No quality profile may silently change the renderer or engine version.

Target treatment:

- warm directional key light;
- blue ambient fill;
- sky and fog tuned for depth separation;
- controlled bloom/glow;
- filmic tonemapping where supported;
- reflection probes or low-cost planar/cubemap approximations;
- wet-road material using roughness variation and normal detail;
- strong but not crushed contrast.

### 7.3 Materials and Assets

Create or tune reusable materials for:

- glossy dark road bricks;
- painted curbs;
- cream fort stone bricks;
- glass towers;
- vehicle paint;
- palm trunks and leaves;
- water and waterfront fixtures;
- gold mission markers.

Textures must use Android-supported compression and bounded resolutions. Shared materials and atlases should be preferred over excessive unique materials.

## 8. Responsive and Mobile Behavior

Reference layout is 16:9 landscape at 1920×1080. The UI must also support wider and narrower landscape devices.

Requirements:

- safe-area margins for notches and rounded corners;
- anchored regions rather than absolute 1920×1080 coordinates;
- minimum touch target size of 48 logical pixels;
- no critical information under system gesture regions;
- scalable typography and icons;
- controller, keyboard, mouse, and touch focus behavior;
- clear pressed, focused, disabled, and selected states.

## 9. Performance Budget

The design must target a stable, playable Android build rather than maximize screenshot fidelity without bounds.

Initial budgets:

- UI should add negligible per-frame script cost when values are unchanged;
- avoid rebuilding control trees every frame;
- use event-driven updates for HUD values;
- pool recurring effects and markers;
- cap transparent overlays and full-screen sampling;
- keep hero textures within a documented memory budget;
- avoid adding dynamic lights per decorative prop;
- use LOD or visibility ranges for environment density.

The implementation plan must establish measurable frame-time, memory, and startup targets based on the available CI/emulator evidence and later named-device evidence.

## 10. Error Handling and Fallbacks

- Missing optional artwork falls back to a themed native panel rather than a blank screen.
- Missing player or mission state produces safe placeholder values and an actionable log message.
- Invalid settings are clamped and migrated to defaults.
- Unsupported quality features are skipped without changing renderer selection.
- Failed scene transitions retain the current screen and show a recoverable error panel.
- Asset load failures include the resource path in logs without exposing secrets.

## 11. Testing Strategy

### 11.1 Static and Scene Tests

- all new `.tscn`, `.gd`, `.tres`, and theme resources parse;
- referenced assets exist;
- scene transitions resolve;
- required UI nodes and signals exist;
- settings schema defaults and migration pass;
- character identifiers are stable;
- touch actions map to existing project input actions.

### 11.2 Interaction Tests

- splash advances to loading/main menu;
- every main-menu button reaches the correct destination;
- character selection persists;
- Play starts the game;
- pause/resume works;
- settings change and persist;
- mission/HUD values update from test state;
- Android back behavior is correct.

### 11.3 Visual Regression

Capture deterministic screenshots for:

- studio splash;
- loading screen;
- main menu;
- character select;
- gameplay HUD;
- pause/settings.

Tests will validate image dimensions, nonblank output, key layout regions, and perceptual change thresholds. Human comparison against the uploaded references remains required because automated metrics cannot prove art-direction similarity.

### 11.4 Android Verification

- export succeeds;
- APK is nonempty and ZIP-clean;
- package and ABI are correct;
- signing verifies;
- production main scene is selected;
- diagnostic main scene is not selected;
- launch smoke test reaches a valid screen;
- screenshots are captured from the actual APK where the environment permits.

## 12. Delivery

Deliverables:

- committed source changes on `work/bahrain-brick-reference-visual-upgrade`;
- implementation report with changed files and evidence;
- screenshot comparison set;
- Android APK;
- SHA-256 checksum and signing metadata;
- explicit list of remaining visual gaps and device-dependent limitations.

## 13. Non-Goals

This visual upgrade does not include:

- claiming pixel-identical reproduction of promotional renders;
- changing the frozen renderer decision;
- replacing the game with prerendered video or static screenshots;
- implementing unrelated gameplay systems;
- redesigning networking or authoritative-server architecture;
- publishing, merging, or production deployment without explicit authorization.

## 14. Completion Classification

`VERIFIED COMPLETE` requires a functioning, inspected APK and real runtime evidence. Source changes or generated artwork alone are not completion.
