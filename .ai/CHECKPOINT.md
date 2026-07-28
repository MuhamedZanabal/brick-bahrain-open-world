# Bahrain Brick Graphics — R1 Engine-Boundary Comparison

Recorded: 2026-07-28

## Current state

- Stage: **BAHRAIN BRICK — STAGE R1: RENDERER RUNTIME DEBUGGING**
- Outcome: `DIAGNOSTIC_CONTINUATION`
- Governing gate: `G0_EVIDENCE_INSUFFICIENT`
- R1 exit criteria met: no
- Production fix authorized: no
- Renderer selected: no
- Renderer defaults changed: no
- G1: unauthorized

## Completed evidence

- GL 4.3 baseline: 45 link failures; best project cap result: 44 at `max_lights_per_object=7`.
- Mobile 4.3 baseline: frame 90; render-disabled control: frame 300.
- Five isolated Mobile corrections were reverted with frame outcomes 80, 90, 70, 90, and 70.
- Correction 5, filmic-to-linear tonemapping: run `30370527664`, artifact `8693475134`, digest `sha256:90e0e65a3b3b9f232a3cee83bbff28d3ec32591d4ad50f4882e1c13c5927bd83`.
- All correction runs retained export, launch, scene readiness, non-black screenshot, process/lifecycle health, and zero critical runtime errors.

## Active micro-task

Compare Godot `4.7.1-stable` against the 4.3 evidence using one imported state and only:

- `GL gl_production`
- `MOBILE mobile_baseline`

No prior shadow, render-scale, tonemapper, GL cap, gameplay, mission, asset, or renderer-default change may be stacked.

Decision rule:

- Both tracks meet exit criteria: retain as R1 exit candidate.
- GL link failures below 45 or Mobile frame above 90 with health gates: retain as proven engine-boundary improvement.
- Neither track improves: revert and stop emulator-side parameter work.
