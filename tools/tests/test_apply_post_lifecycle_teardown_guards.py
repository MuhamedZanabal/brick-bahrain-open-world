from pathlib import Path
import importlib.util
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "apply_post_lifecycle_teardown_guards.py"
spec = importlib.util.spec_from_file_location("post_lifecycle_guards", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

PROTECTED_EXIT = '''func _exit_tree() -> void:
\tif GameManager.current_state == GameManager.GameState.IN_WORLD:
\t\tif player and player is Node3D:
\t\t\tSaveManager.set_position((player as Node3D).global_position)
\t\tSaveManager.save_game("world exit")
\tRadioSystem.stop_radio()
\tChatManager.set_world_active(false)
\tTouchInput.reset_all()
\tfor lock_name in ["phone", "shop", "chat"]:
\t\tGameManager.release_ui_lock(lock_name)
'''

CALLBACK = '''func _on_world_child_exiting_tree(node: Node) -> void:
\tif node != player or not node is Node3D:
\t\treturn
\tvar active_player := node as Node3D
\tif active_player.is_inside_tree():
\t\t_last_valid_player_position = active_player.global_position
\t\t_has_last_valid_player_position = true
\tif _has_last_valid_player_position:
\t\tSaveManager.set_position(_last_valid_player_position)
\tplayer = null


'''


class PostLifecycleGuardTests(unittest.TestCase):
    def fixture(self, root: Path) -> None:
        (root / "scripts").mkdir()
        (root / "tests").mkdir()
        (root / "scripts/world.gd").write_text(
            "extends Node3D\n\n" + CALLBACK + PROTECTED_EXIT,
            encoding="utf-8",
        )
        (root / "tests/world_lifecycle_guard_test.gd").write_text(
            "extends Node\n\nfunc _run() -> void:\n" + mod.OLD_TEST_BLOCK,
            encoding="utf-8",
        )
        (root / "scripts/npc_pedestrian.gd").write_text(
            "extends CharacterBody3D\n\n"
            + mod.NPC_FAST_SCAN_UNSAFE
            + "\n\n"
            + mod.NPC_PLAYER_SCAN_UNSAFE,
            encoding="utf-8",
        )

    def test_applies_all_guards_and_preserves_protected_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            report = mod.apply(root)
            world = (root / "scripts/world.gd").read_text(encoding="utf-8")
            test = (root / "tests/world_lifecycle_guard_test.gd").read_text(encoding="utf-8")
            npc = (root / "scripts/npc_pedestrian.gd").read_text(encoding="utf-8")
            self.assertIn(mod.SAFE_PARENT_LINE, world)
            self.assertNotIn(mod.UNSAFE_PARENT_LINE + "\n", world)
            self.assertIn("whole-world teardown completes with active player", test)
            self.assertIn("whole-world teardown reuses the latest valid cached position", test)
            self.assertIn("not is_inside_tree() or state", npc)
            self.assertIn("not vehicle_node.is_inside_tree()", npc)
            self.assertIn("not player.is_inside_tree()", npc)
            self.assertEqual(
                mod.protected_world_exit_sha(world),
                mod.PROTECTED_WORLD_EXIT_SHA256,
            )
            self.assertTrue(report["protected_world_exit_unchanged"])
            self.assertEqual(report["changes"][2]["states"], ["applied", "applied"])

    def test_pedestrian_scans_reject_detached_cross_node_transforms(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            mod.apply(root)
            npc = (root / "scripts/npc_pedestrian.gd").read_text(encoding="utf-8")
            vehicle_scan = mod.function_block(npc, "_scan_for_fast_vehicles")
            player_scan = mod.function_block(npc, "_scan_for_player")
            self.assertEqual(vehicle_scan, mod.NPC_FAST_SCAN_SAFE)
            self.assertEqual(player_scan, mod.NPC_PLAYER_SCAN_SAFE)
            self.assertLess(
                vehicle_scan.index("not vehicle_node.is_inside_tree()"),
                vehicle_scan.index("vehicle_node.global_position"),
            )
            self.assertLess(
                player_scan.index("not player.is_inside_tree()"),
                player_scan.index("player.global_position"),
            )

    def test_correction_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            mod.apply(root)
            first_world = (root / "scripts/world.gd").read_bytes()
            first_test = (root / "tests/world_lifecycle_guard_test.gd").read_bytes()
            first_npc = (root / "scripts/npc_pedestrian.gd").read_bytes()
            report = mod.apply(root)
            self.assertEqual(first_world, (root / "scripts/world.gd").read_bytes())
            self.assertEqual(first_test, (root / "tests/world_lifecycle_guard_test.gd").read_bytes())
            self.assertEqual(first_npc, (root / "scripts/npc_pedestrian.gd").read_bytes())
            self.assertEqual(report["changes"][0]["state"], "already_satisfied")
            self.assertEqual(report["changes"][1]["state"], "already_satisfied")
            self.assertEqual(
                report["changes"][2]["states"],
                ["already_satisfied", "already_satisfied"],
            )

    def test_prohibited_protected_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            path = root / "scripts/world.gd"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "if player and player is Node3D:",
                    "if player and player is Node3D and player.is_inside_tree():",
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "protected world teardown hash mismatch"):
                mod.apply(root)

    def test_unexpected_lifecycle_shape_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            path = root / "scripts/world.gd"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    mod.UNSAFE_PARENT_LINE,
                    "\tif active_player != null:",
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "world parent-tree guard mismatch"):
                mod.apply(root)

    def test_unexpected_pedestrian_scan_shape_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            path = root / "scripts/npc_pedestrian.gd"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "if not vehicle is Node3D:",
                    "if vehicle == null:",
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "_scan_for_fast_vehicles guard mismatch"):
                mod.apply(root)


if __name__ == "__main__":
    unittest.main()
