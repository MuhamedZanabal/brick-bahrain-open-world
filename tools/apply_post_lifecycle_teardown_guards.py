#!/usr/bin/env python3
"""Apply final unprotected teardown guards after the checksum-pinned v18 correction set."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

PROTECTED_WORLD_EXIT_SHA256 = "fa19607a0388e58ff970bacc77139b736e33b827d8682d5859ee2fd62c90a5bc"
WORLD_PATH = "scripts/world.gd"
LIFECYCLE_TEST_PATH = "tests/world_lifecycle_guard_test.gd"

UNSAFE_PARENT_LINE = "\tif active_player.is_inside_tree():"
SAFE_PARENT_LINE = "\tif is_inside_tree() and active_player.is_inside_tree():"

OLD_TEST_BLOCK = '''\tvar second_callback := Callable(world_two, "_on_world_child_exiting_tree")
\tworld_two.child_exiting_tree.disconnect(second_callback)
\tworld_two.remove_child(second_player)
\tawait get_tree().process_frame
\tworld_two.player = second_player
\tworld_two._on_world_child_exiting_tree(second_player)
\t_check(world_two.player == null, "detached player fallback clears the stale world reference")
\t_check(SaveManager.get_position().is_equal_approx(second_position), "detached player fallback reuses the latest valid cached position")
\tworld_two._install_world_lifecycle_guard()
\t_check(world_two.child_exiting_tree.get_connections().size() == 1, "repeated world cycle remains single-shot after fallback reconnect")
\tsecond_player.queue_free()
\tworld_two.queue_free()
\tawait get_tree().process_frame
'''

NEW_TEST_BLOCK = '''\tworld_two._cache_active_player_position()
\t_check(world_two.child_exiting_tree.get_connections().size() == 1, "repeated world cycle remains single-shot before whole-world teardown")
\tworld_two.queue_free()
\tawait get_tree().process_frame
\tawait get_tree().process_frame
\t_check(not is_instance_valid(world_two), "whole-world teardown completes with active player")
\t_check(SaveManager.get_position().is_equal_approx(second_position), "whole-world teardown reuses the latest valid cached position")
\tsecond_player = null
'''


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def function_block(text: str, name: str) -> str:
    match = re.search(rf"(?ms)^func {re.escape(name)}\b.*?(?=^func |\Z)", text)
    if match is None:
        raise RuntimeError(f"missing function: {name}")
    return match.group(0).rstrip() + "\n"


def protected_world_exit_sha(text: str) -> str:
    return sha256(function_block(text, "_exit_tree").encode("utf-8"))


def patch_world_parent_guard(text: str) -> tuple[str, str]:
    protected_before = protected_world_exit_sha(text)
    if protected_before != PROTECTED_WORLD_EXIT_SHA256:
        raise RuntimeError(
            "protected world teardown hash mismatch before parent-tree correction: "
            f"expected={PROTECTED_WORLD_EXIT_SHA256}, actual={protected_before}"
        )

    callback = function_block(text, "_on_world_child_exiting_tree")
    unsafe_count = callback.count(UNSAFE_PARENT_LINE)
    safe_count = callback.count(SAFE_PARENT_LINE)
    if unsafe_count == 1 and safe_count == 0:
        patched_callback = callback.replace(UNSAFE_PARENT_LINE, SAFE_PARENT_LINE, 1)
        if text.count(callback) != 1:
            raise RuntimeError("world lifecycle callback block is not unique")
        text = text.replace(callback, patched_callback, 1)
        state = "applied"
    elif unsafe_count == 0 and safe_count == 1:
        state = "already_satisfied"
    else:
        raise RuntimeError(
            "world parent-tree guard mismatch: "
            f"unsafe_count={unsafe_count}, safe_count={safe_count}"
        )

    protected_after = protected_world_exit_sha(text)
    if protected_after != PROTECTED_WORLD_EXIT_SHA256:
        raise RuntimeError(
            "protected world teardown changed during parent-tree correction: "
            f"expected={PROTECTED_WORLD_EXIT_SHA256}, actual={protected_after}"
        )
    return text, state


def patch_whole_world_teardown_test(text: str) -> tuple[str, str]:
    old_count = text.count(OLD_TEST_BLOCK)
    new_count = text.count(NEW_TEST_BLOCK)
    if old_count == 1 and new_count == 0:
        return text.replace(OLD_TEST_BLOCK, NEW_TEST_BLOCK, 1), "applied"
    if old_count == 0 and new_count == 1:
        return text, "already_satisfied"
    raise RuntimeError(
        "whole-world teardown test block mismatch: "
        f"old_count={old_count}, new_count={new_count}"
    )


def apply(root: Path) -> dict:
    root = root.resolve()
    world_path = root / WORLD_PATH
    test_path = root / LIFECYCLE_TEST_PATH
    if not world_path.is_file():
        raise RuntimeError(f"missing correction target: {WORLD_PATH}")
    if not test_path.is_file():
        raise RuntimeError(f"missing correction target: {LIFECYCLE_TEST_PATH}")

    world_before = world_path.read_bytes()
    world_text, world_state = patch_world_parent_guard(world_before.decode("utf-8"))
    world_path.write_text(world_text, encoding="utf-8")
    world_after = world_path.read_bytes()

    test_before = test_path.read_bytes()
    test_text, test_state = patch_whole_world_teardown_test(test_before.decode("utf-8"))
    test_path.write_text(test_text, encoding="utf-8")
    test_after = test_path.read_bytes()

    protected_actual = protected_world_exit_sha(world_path.read_text(encoding="utf-8"))
    if protected_actual != PROTECTED_WORLD_EXIT_SHA256:
        raise RuntimeError(
            "final protected world teardown hash mismatch: "
            f"expected={PROTECTED_WORLD_EXIT_SHA256}, actual={protected_actual}"
        )

    return {
        "conclusion": "pass",
        "protected_world_exit_expected_sha256": PROTECTED_WORLD_EXIT_SHA256,
        "protected_world_exit_actual_sha256": protected_actual,
        "protected_world_exit_unchanged": True,
        "changes": [
            {
                "path": WORLD_PATH,
                "state": world_state,
                "before_sha256": sha256(world_before),
                "after_sha256": sha256(world_after),
                "reason": (
                    "avoid reading a child global transform when the parent world has already left "
                    "the SceneTree; reuse the position cached during normal world processing"
                ),
            },
            {
                "path": LIFECYCLE_TEST_PATH,
                "state": test_state,
                "before_sha256": sha256(test_before),
                "after_sha256": sha256(test_after),
                "reason": (
                    "exercise whole-world teardown while the active player remains attached, "
                    "without changing the configured 12-assertion lifecycle count"
                ),
            },
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = apply(args.root)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
