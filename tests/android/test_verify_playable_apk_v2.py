#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/android/verify_playable_apk_v2.py"


def load_module():
    spec = importlib.util.spec_from_file_location("verify_playable_apk_v2", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PlayableApkVerifierV2Test(unittest.TestCase):
    def test_exact_observed_aapt_warning_has_no_trailing_period(self) -> None:
        module = load_module()
        self.assertEqual(
            module.EXACT_AAPT_WARNING,
            "AndroidManifest.xml:0: error: failed to read attribute 'android:required': "
            "attribute is not an integer value",
        )
        self.assertFalse(module.EXACT_AAPT_WARNING.endswith("."))

    def test_loaded_verifier_uses_normalized_warning(self) -> None:
        module = load_module()
        verifier = module.load_verifier()
        self.assertEqual(verifier.KNOWN_AAPT_WARNING, module.EXACT_AAPT_WARNING)


if __name__ == "__main__":
    unittest.main()
