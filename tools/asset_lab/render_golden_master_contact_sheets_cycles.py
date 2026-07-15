#!/usr/bin/env python3
"""Run golden-master evidence rendering with bounded Cycles CPU settings."""

from __future__ import annotations

import render_golden_master_contact_sheets as renderer

_ORIGINAL_SETUP = renderer._setup_scene


def _cycles_setup(bpy, minimum, maximum, output):
    camera, center, radius = _ORIGINAL_SETUP(bpy, minimum, maximum, output)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.tile_x = 256
    scene.render.tile_y = 256
    return camera, center, radius


renderer._setup_scene = _cycles_setup

if __name__ == "__main__":
    raise SystemExit(renderer.main())
