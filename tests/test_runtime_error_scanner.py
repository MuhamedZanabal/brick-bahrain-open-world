import tempfile
import unittest
from pathlib import Path

from tools.scan_godot_runtime_errors import DUMMY_MESH_ERROR, DUMMY_MESH_STACK, scan


class RuntimeErrorScannerTests(unittest.TestCase):
    def test_asset_name_containing_crash_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "import.log").write_text(
                "EditorFileSystem: Importing res://bh_prop_crash_barrier_4m_01.glb\n",
                encoding="utf-8",
            )
            report = scan(root)
            self.assertEqual(report["raw_error_count"], 0)
            self.assertEqual(report["conclusion"], "pass")

    def test_standalone_crash_signature_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "runtime.log").write_text("CRASH while loading world\n", encoding="utf-8")
            report = scan(root)
            self.assertEqual(report["unresolved_count"], 1)
            self.assertEqual(report["conclusion"], "fail")

    def test_exact_dummy_renderer_pair_remains_narrowly_allowlisted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "runtime.log").write_text(
                f"{DUMMY_MESH_ERROR}\n   {DUMMY_MESH_STACK}\n",
                encoding="utf-8",
            )
            report = scan(root)
            self.assertEqual(report["allowlisted_count"], 1)
            self.assertEqual(report["unresolved_count"], 0)
            self.assertEqual(report["conclusion"], "pass")


if __name__ == "__main__":
    unittest.main()
