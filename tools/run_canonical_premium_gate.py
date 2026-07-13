#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


MISSING_RELEASE_SMOKE_SCENE = "res://build/ci/runtime_smoke_runner_v14.tscn"


def load_blocks(workflow: Path) -> list[str]:
    lines = workflow.read_text(encoding="utf-8").splitlines()
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        if lines[index].startswith("        run: |"):
            index += 1
            block: list[str] = []
            while index < len(lines):
                line = lines[index]
                if line.startswith("          "):
                    block.append(line[10:])
                    index += 1
                    continue
                if not line.strip():
                    block.append("")
                    index += 1
                    continue
                break
            blocks.append("\n".join(block).rstrip() + "\n")
            continue
        index += 1
    return blocks


def replace_exactly_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label} replacement mismatch: expected 1, found {count}")
    return text.replace(old, new)


def prepare_release_smoke_harness(project: Path) -> None:
    """Adapt the release-contained SceneTree smoke test to a normal project scene.

    Running the source script with Godot's --script mode bypasses project autoload
    registration. The generated Node harness runs through ordinary project startup,
    preserving SaveManager/GameManager/QualityManager and all other autoloads.
    """
    source = project / "tests/runtime_smoke_test_v14.gd"
    if not source.is_file():
        raise SystemExit(f"release smoke source missing: {source}")

    text = source.read_text(encoding="utf-8")
    text = replace_exactly_once(text, "extends SceneTree", "extends Node", "base type")
    text = replace_exactly_once(
        text, "func _initialize() -> void:", "func _ready() -> void:", "entry point"
    )
    text = replace_exactly_once(
        text, "\t\tawait process_frame", "\t\tawait get_tree().process_frame", "frame wait"
    )
    text = replace_exactly_once(
        text, "\troot.add_child(world)", "\tget_tree().root.add_child(world)", "world parent"
    )
    text = replace_exactly_once(
        text,
        "\tquit(1 if _failed > 0 else 0)",
        "\tget_tree().quit(1 if _failed > 0 else 0)",
        "exit",
    )

    harness_dir = project / "build/ci"
    harness_dir.mkdir(parents=True, exist_ok=True)
    script_path = harness_dir / "runtime_smoke_runner_v14.gd"
    scene_path = harness_dir / "runtime_smoke_runner_v14.tscn"
    script_path.write_text(text, encoding="utf-8")
    scene_path.write_text(
        "[gd_scene load_steps=2 format=3]\n\n"
        "[ext_resource type=\"Script\" path=\"res://build/ci/runtime_smoke_runner_v14.gd\" id=\"1_smoke\"]\n\n"
        "[node name=\"RuntimeSmokeRunnerV14\" type=\"Node\"]\n"
        "script = ExtResource(\"1_smoke\")\n",
        encoding="utf-8",
    )


def normalize_gate_script(gate: int, script: str) -> str:
    if gate == 5:
        occurrence_count = script.count(MISSING_RELEASE_SMOKE_SCENE)
        if occurrence_count != 1:
            raise SystemExit(
                "gate 5 smoke reference mismatch: "
                f"expected one {MISSING_RELEASE_SMOKE_SCENE!r}, found {occurrence_count}"
            )
    return script


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("gate", type=int)
    parser.add_argument(
        "--workflow",
        type=Path,
        default=Path(".github/workflows/build_bahrain_brick_premium_visual_qa.yml"),
    )
    args = parser.parse_args()

    blocks = load_blocks(args.workflow)
    if len(blocks) != 10:
        raise SystemExit(f"expected 10 canonical shell gates, found {len(blocks)}")
    if args.gate < 1 or args.gate > len(blocks):
        raise SystemExit(f"gate out of range: {args.gate}")

    diagnostics = Path("validation-diagnostics")
    diagnostics.mkdir(parents=True, exist_ok=True)
    number = args.gate
    script = normalize_gate_script(number, blocks[number - 1])
    if number == 5:
        prepare_release_smoke_harness(Path("recovery/v14"))

    script_path = diagnostics / f"gate-{number:02d}.sh"
    log_path = diagnostics / f"gate-{number:02d}.log"
    script_path.write_text(script, encoding="utf-8")

    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            ["bash", "-lc", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
            log.write(line)
        returncode = process.wait()

    if returncode != 0:
        (diagnostics / "FAILED_GATE.txt").write_text(
            f"gate={number}\nreturncode={returncode}\nscript={script_path}\nlog={log_path}\n",
            encoding="utf-8",
        )
        return returncode

    (diagnostics / f"GATE_{number:02d}_PASSED.txt").write_text(
        f"canonical gate {number} passed\n", encoding="utf-8"
    )
    if number == len(blocks):
        (diagnostics / "ALL_GATES_PASSED.txt").write_text(
            "10 canonical gates passed\n", encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
