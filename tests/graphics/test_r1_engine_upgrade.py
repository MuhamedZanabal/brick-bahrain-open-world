#!/usr/bin/env python3
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "tools/graphics/run_r1_renderer_debug.sh"


class R1EngineUpgradeTest(unittest.TestCase):
    def test_current_stable_engine_and_targeted_modes(self) -> None:
        text = RUNNER.read_text()
        self.assertIn('GODOT_RELEASE="4.7.1-stable"', text)
        self.assertIn('godotengine/godot-builds/releases/download', text)
        self.assertIn('SHA512-SUMS.txt', text)
        self.assertIn('run_target GL gl_production', text)
        self.assertIn('3600s xvfb-run', text)
        self.assertIn('R1_ENGINE_HARNESS_STATUS.json', text)
        self.assertIn('run_target MOBILE mobile_baseline', text)
        self.assertNotIn('gl_unshaded gl_empty gl_sun', text)
        self.assertNotIn('mobile_render_disabled_control', text)
        self.assertIn("'renderer_defaults_modified':False", text)
        self.assertNotIn('renderer/rendering_method="', text)


if __name__ == '__main__':
    unittest.main()
