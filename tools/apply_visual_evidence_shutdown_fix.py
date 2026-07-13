#!/usr/bin/env python3
"""Make premium world visual-evidence teardown explicit and lifecycle-safe."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EVIDENCE_PATH = "tests/premium_world_visual_evidence.gd"

OLD_RUN_TAIL = '''\t_set_hud_visible(true)
\tTouchInput.reset_all()
\tprint("PREMIUM WORLD VISUAL EVIDENCE COMPLETE: %d captures" % _records.size())
\tawait _wait_process_frames(2)
\tget_tree().quit(0)
'''

NEW_RUN_TAIL = '''\t_set_hud_visible(true)
\tTouchInput.reset_all()
\tprint("PREMIUM WORLD VISUAL EVIDENCE COMPLETE: %d captures" % _records.size())
\tawait _wait_process_frames(2)
\tif not await _shutdown_runtime():
\t\tget_tree().quit(1)
\t\treturn
\tget_tree().quit(0)
'''

CLEANUP_FUNCTION = '''func _shutdown_runtime() -> bool:
\t# The evidence harness owns these runtime nodes. Release them while the SceneTree
\t# is still processing instead of relying on process-wide quit ordering.
\t_set_vehicle_mode(false)
\tTouchInput.reset_all()
\tawait _wait_process_frames(2)

\tif _player and is_instance_valid(_player):
\t\tif not _player.is_inside_tree():
\t\t\tpush_error("premium evidence teardown: player detached before orderly cleanup")
\t\t\treturn false
\t\t_player.queue_free()
\t\tawait _wait_process_frames(2)
\tif _world and is_instance_valid(_world) and _world.get("player") != null:
\t\tpush_error("premium evidence teardown: world retained stale player reference")
\t\treturn false
\t_player = null

\tif _camera and is_instance_valid(_camera):
\t\t_camera.current = false
\t\t_camera.queue_free()
\t\tawait _wait_process_frames(1)
\t_camera = null

\tif _world and is_instance_valid(_world):
\t\t_world.queue_free()
\t\tawait _wait_process_frames(3)
\t\tif is_instance_valid(_world):
\t\t\tpush_error("premium evidence teardown: world failed to leave the SceneTree")
\t\t\treturn false
\t_world = null
\t_hud = null
\treturn true


'''


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def patch_evidence_source(text: str) -> tuple[str, str]:
    cleanup_count = text.count(CLEANUP_FUNCTION)
    old_count = text.count(OLD_RUN_TAIL)
    new_count = text.count(NEW_RUN_TAIL)

    if cleanup_count == 0 and old_count == 1 and new_count == 0:
        marker = "func _run() -> void:\n"
        if text.count(marker) != 1:
            raise RuntimeError(
                "premium evidence _run marker mismatch: "
                f"count={text.count(marker)}"
            )
        text = text.replace(marker, CLEANUP_FUNCTION + marker, 1)
        text = text.replace(OLD_RUN_TAIL, NEW_RUN_TAIL, 1)
        return text, "applied"

    if cleanup_count == 1 and old_count == 0 and new_count == 1:
        return text, "already_satisfied"

    raise RuntimeError(
        "premium evidence shutdown correction mismatch: "
        f"cleanup_count={cleanup_count}, old_tail_count={old_count}, "
        f"new_tail_count={new_count}"
    )


def apply(root: Path, require_evidence: bool = True) -> dict:
    root = root.resolve()
    path = root / EVIDENCE_PATH
    if not path.is_file():
        if require_evidence:
            raise RuntimeError(f"premium evidence correction target missing: {EVIDENCE_PATH}")
        return {
            "conclusion": "pass",
            "path": EVIDENCE_PATH,
            "state": "not_applicable_reduced_fixture",
            "required": False,
        }

    before = path.read_bytes()
    text, state = patch_evidence_source(before.decode("utf-8"))
    path.write_text(text, encoding="utf-8")
    after = path.read_bytes()

    final = after.decode("utf-8")
    required_order = [
        "_set_vehicle_mode(false)",
        "_player.queue_free()",
        '_world.get("player") != null',
        "_camera.queue_free()",
        "_world.queue_free()",
        "get_tree().quit(0)",
    ]
    positions = [final.index(token) for token in required_order]
    if positions != sorted(positions):
        raise RuntimeError(
            "premium evidence cleanup ordering invalid: "
            f"tokens={required_order}, positions={positions}"
        )

    return {
        "conclusion": "pass",
        "path": EVIDENCE_PATH,
        "state": state,
        "required": require_evidence,
        "before_sha256": sha256(before),
        "after_sha256": sha256(after),
        "size_bytes": len(after),
        "reason": (
            "release vehicle state, active player, evidence camera, and world through "
            "normal SceneTree frames before process quit"
        ),
        "source": final,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = apply(args.root, require_evidence=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
