# Bahrain Brick Premium Visual Upgrade Design

## Status
Approved by the project owner on 2026-07-13.

## Objective
Transform the verified v1.4.0.3 graphics QA fallback into a substantially richer Bahrain-specific Android build while preserving the frozen mobile-control path and all accepted startup, loading, presentation, and input behavior.

## Source authority
- Functional graphics provenance commit: `464a8811a818bd6bb9e102566e0a525396b11515`
- Frozen controls commit: `c5548465627942a2889a0bd09f8979c3a29fbcdd`
- Integrated source SHA-256: `5c4d8ac4497eda7752058424062a74a97c1f6f5e0c9a1ff393abac2a2c7c828a`
- This remains a historical v1.4 fallback and must not be represented as v15 authority.

## Architecture
The upgrade is implemented as deterministic overlays and focused project-source changes. World rendering changes are isolated in environment, world-building, material, shader, quality-profile, and visual-evidence modules. Protected controls and their tests remain byte-identical. Presentation assets remain native-control-driven and are upgraded only after the gameplay-world benchmark is operational.

## First shippable slice
1. Freeze repository baseline and create premium branch.
2. Add deterministic before/after world visual benchmark cameras.
3. Calibrate environment lighting, tone mapping, fog, shadows, and sky.
4. Upgrade road, curb, pavement, façade, window, vegetation, coastal, and prop materials using mobile-safe procedural resources.
5. Add real Android quality profiles that alter rendering behavior.
6. Capture equivalent runtime screenshots and performance metadata.
7. Re-run controls, startup, presentation, import, Android export, package integrity, and frozen-file checks.

## Protected systems
No changes to virtual joystick, touch routing, TouchInput movement state, player movement controller, camera-touch routing, HUD input propagation, world touch reset, local authority logic, mobile-input tests, or rendered-control evidence tests unless an unchanged regression test proves modification is required.

## Acceptance
The first slice is accepted only when world screenshots demonstrate reduced overexposure, improved material separation, stronger atmospheric depth, clearer Bahrain identity, unchanged controls hashes, 28/28 control regression, 10/10 presentation regression, successful Android export, and a traceable QA artifact.
