#!/usr/bin/env python3
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE_RUNNER = ROOT / "tools/graphics/run_r1_renderer_debug.sh"
RETRY_RUNNER = ROOT / "tools/graphics/run_r1_engine_retry.sh"


class R1EngineUpgradeTest(unittest.TestCase):
    def test_current_stable_engine_and_targeted_modes(self) -> None:
        base = BASE_RUNNER.read_text()
        retry = RETRY_RUNNER.read_text()
        combined = base + "\n" + retry
        self.assertIn('GODOT_RELEASE="4.7.1-stable"', base)
        self.assertIn('godotengine/godot-builds/releases/download', base)
        self.assertIn('SHA512-SUMS.txt', base)
        self.assertIn('run_target GL gl_production', base)
        self.assertIn('run_target MOBILE mobile_baseline', base)
        self.assertIn('3600s xvfb-run', retry)
        self.assertIn('R1_ENGINE_HARNESS_STATUS.json', retry)
        self.assertIn('IMPORT_COMPLETE.txt', retry)
        self.assertNotIn('gl_unshaded gl_empty gl_sun', combined)
        self.assertNotIn('mobile_render_disabled_control', combined)
        self.assertIn("'renderer_defaults_modified':False", combined)
        self.assertNotIn('renderer/rendering_method="', combined)


if __name__ == '__main__':
    unittest.main()
