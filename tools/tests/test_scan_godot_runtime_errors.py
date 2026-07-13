#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import tempfile
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / 'scan_godot_runtime_errors.py'
spec = importlib.util.spec_from_file_location('scanner', MODULE_PATH)
scanner = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(scanner)


class RuntimeErrorScannerTests(unittest.TestCase):
    def test_exact_dummy_renderer_pair_is_allowlisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'runtime.log'
            log.write_text(
                'ERROR: Parameter "m" is null.\n'
                '   at: mesh_get_surface_count (servers/rendering/dummy/storage/mesh_storage.h:120)\n'
            )
            report = scanner.scan(Path(tmp))
            self.assertEqual(report['raw_error_count'], 1)
            self.assertEqual(report['allowlisted_count'], 1)
            self.assertEqual(report['unresolved_count'], 0)
            self.assertEqual(report['conclusion'], 'pass')

    def test_same_message_with_different_stack_is_unresolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'runtime.log'
            log.write_text('ERROR: Parameter "m" is null.\n   at: project/script.gd:12\n')
            report = scanner.scan(Path(tmp))
            self.assertEqual(report['allowlisted_count'], 0)
            self.assertEqual(report['unresolved_count'], 1)
            self.assertEqual(report['conclusion'], 'fail')

    def test_project_error_is_never_allowlisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'runtime.log'
            log.write_text("ERROR: The object does not have any 'meta' values with the key 'anim_player'.\n")
            report = scanner.scan(Path(tmp))
            self.assertEqual(report['unresolved_count'], 1)
            self.assertEqual(report['conclusion'], 'fail')


if __name__ == '__main__':
    unittest.main()
