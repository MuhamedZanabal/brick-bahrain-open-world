from pathlib import Path
import importlib.util
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "apply_visual_evidence_shutdown_fix.py"
spec = importlib.util.spec_from_file_location("visual_evidence_shutdown", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

PREFIX = '''extends Node

var _world: Node3D
var _camera: Camera3D
var _player: CharacterBody3D
var _hud: CanvasLayer
var _records: Array[Dictionary] = []

func _set_vehicle_mode(enabled: bool) -> void:
\tpass

func _wait_process_frames(count: int) -> void:
\tpass

'''

RUN = '''func _run() -> void:
\t_set_hud_visible(true)
\tTouchInput.reset_all()
\tprint("PREMIUM WORLD VISUAL EVIDENCE COMPLETE: %d captures" % _records.size())
\tawait _wait_process_frames(2)
\tget_tree().quit(0)
'''


class VisualEvidenceShutdownTests(unittest.TestCase):
    def fixture(self, root: Path) -> Path:
        path = root / mod.EVIDENCE_PATH
        path.parent.mkdir(parents=True)
        path.write_text(PREFIX + RUN, encoding="utf-8")
        return path

    def test_applies_orderly_shutdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self.fixture(root)
            report = mod.apply(root)
            body = path.read_text(encoding="utf-8")
            self.assertEqual(report["state"], "applied")
            self.assertIn("func _shutdown_runtime() -> bool:", body)
            self.assertIn("if not await _shutdown_runtime():", body)
            self.assertNotIn(mod.OLD_RUN_TAIL, body)
            self.assertIn(mod.NEW_RUN_TAIL, body)

    def test_cleanup_order_preserves_valid_transform_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self.fixture(root)
            mod.apply(root)
            body = path.read_text(encoding="utf-8")
            tokens = [
                "_set_vehicle_mode(false)",
                "_player.queue_free()",
                '_world.get("player") != null',
                "_camera.queue_free()",
                "_world.queue_free()",
                "get_tree().quit(0)",
            ]
            positions = [body.index(token) for token in tokens]
            self.assertEqual(positions, sorted(positions))

    def test_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self.fixture(root)
            mod.apply(root)
            first = path.read_bytes()
            report = mod.apply(root)
            self.assertEqual(report["state"], "already_satisfied")
            self.assertEqual(first, path.read_bytes())

    def test_missing_complete_project_target_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "correction target missing"):
                mod.apply(Path(tmp), require_evidence=True)

    def test_missing_reduced_fixture_is_not_applicable(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = mod.apply(Path(tmp), require_evidence=False)
            self.assertEqual(report["state"], "not_applicable_reduced_fixture")

    def test_unexpected_run_tail_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self.fixture(root)
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "get_tree().quit(0)", "get_tree().quit(9)", 1
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "shutdown correction mismatch"):
                mod.apply(root)


if __name__ == "__main__":
    unittest.main()
