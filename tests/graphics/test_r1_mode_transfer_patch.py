#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "tools/graphics/patch_r1_mode_transfer.py"


def load_module():
    spec = importlib.util.spec_from_file_location("patch_r1_mode_transfer", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("module spec unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class R1ModeTransferPatchTest(unittest.TestCase):
    def test_fragile_nested_shell_writer_is_replaced(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = root / "runner.sh"
            report = root / "report.json"
            runner.write_text("#!/usr/bin/env bash\n" + module.OLD_BLOCK)
            result = module.patch_runner(runner, report)
            patched = runner.read_text()
            self.assertEqual(result["status"], "patched")
            self.assertNotIn('run-as "$package" sh -c "mkdir -p files', patched)
            self.assertIn('run-as "$package" mkdir -p files', patched)
            self.assertLess(
                patched.index('run-as "$package" mkdir -p files'),
                patched.index('run-as "$package" cp /data/local/tmp/r1_mode.txt files/r1_mode.txt'),
            )
            self.assertIn('cmp -s "$local_mode_file" "$local_mode_file.verified"', patched)
            self.assertTrue(report.is_file())

    def test_corrected_writer_is_idempotent(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = root / "runner.sh"
            report = root / "report.json"
            runner.write_text("#!/usr/bin/env bash\n" + module.NEW_BLOCK)
            result = module.patch_runner(runner, report)
            self.assertEqual(result["status"], "already_patched")
            self.assertFalse(result["changed"])


if __name__ == "__main__":
    unittest.main()
