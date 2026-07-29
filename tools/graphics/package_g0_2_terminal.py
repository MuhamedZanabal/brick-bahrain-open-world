#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ARTIFACT_ID = 8624118896
ARTIFACT_SHA256 = "6581fef39feed0501af438ae73ef6abbb9118851fd10e7ec8ffa6dac0b6f7156"
REPO = "MuhamedZanabal/brick-bahrain-open-world"

REQUIRED_REPORTS = [
    "authority.json", "shared_import_equivalence.json", "emulator_environment.json", "apk_inventory.json",
    "gl_compatibility/state_machine.json", "gl_compatibility/package_report.json",
    "gl_compatibility/launch_report.json", "gl_compatibility/runtime.json",
    "gl_compatibility/frame_metrics.csv", "gl_compatibility/logcat_full.txt",
    "gl_compatibility/logcat_critical.txt", "gl_compatibility/screenshot.png",
    "gl_compatibility/classification.json", "mobile_vulkan/state_machine.json",
    "mobile_vulkan/package_report.json", "mobile_vulkan/launch_report.json",
    "mobile_vulkan/runtime.json", "mobile_vulkan/frame_metrics.csv",
    "mobile_vulkan/logcat_full.txt", "mobile_vulkan/logcat_critical.txt",
    "mobile_vulkan/screenshot.png", "mobile_vulkan/classification.json",
    "screenshot_comparison.json", "screenshot_difference.png",
    "G0_2_TERMINAL_REPORT.json", "G0_2_TERMINAL_REPORT.md",
]
HANDOFF_FILES = [
    "README.md", "device_result.schema.json", "run_device_test.sh", "run_device_test.ps1",
    "adb_capture_commands.txt", "expected_markers.txt", "apk_sha256.txt",
]


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def obtain_artifact(target: Path, supplied: Path | None) -> None:
    if supplied:
        shutil.copy2(supplied, target)
    else:
        token = os.environ.get("GH_TOKEN")
        if not token:
            raise SystemExit("GH_TOKEN is required when --artifact-zip is omitted")
        request = urllib.request.Request(
            f"https://api.github.com/repos/{REPO}/actions/artifacts/{ARTIFACT_ID}/zip",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urllib.request.urlopen(request) as response, target.open("wb") as output:
            shutil.copyfileobj(response, output)
    actual = digest(target)
    if actual != ARTIFACT_SHA256:
        raise SystemExit(f"reduced artifact digest mismatch: {actual}")


def postprocess(reports: Path) -> dict:
    terminal_path = reports / "G0_2_TERMINAL_REPORT.json"
    terminal = json.loads(terminal_path.read_text())
    gl = json.loads((reports / "gl_compatibility/runtime.json").read_text())
    mobile = json.loads((reports / "mobile_vulkan/runtime.json").read_text())
    shared = json.loads((reports / "shared_import_equivalence.json").read_text())
    gl_class = json.loads((reports / "gl_compatibility/classification.json").read_text())
    mobile_class = json.loads((reports / "mobile_vulkan/classification.json").read_text())
    comparison = json.loads((reports / "screenshot_comparison.json").read_text())
    terminal.update({
        "execution_authority": {
            "adjudicative_workflow_run_id": 30175169997,
            "adjudicative_job_id": 89722664363,
            "raw_artifact_id": 8624075667,
            "raw_artifact_digest": "sha256:677c0b55a937ee46f1f85dc600c9ac09c716bae58fd92638824f868792f90d69",
            "reducer_run_id": 30175596770,
            "reducer_job_id": 89723763711,
            "reduced_artifact_id": ARTIFACT_ID,
            "reduced_artifact_digest": f"sha256:{ARTIFACT_SHA256}",
            "android_rerun_during_finalization": False,
        },
        "non_adjudicative_exceptions": [
            {"run_id": 30174847173, "boundary": "pre-emulator shell-scope harness failure", "evidence_use": "EXCLUDED_FROM_ADJUDICATION"},
            {"run_id": 30175107599, "boundary": "pre-Android contract failure", "evidence_use": "EXCLUDED_FROM_ADJUDICATION"},
            {"run_id": 30175210630, "boundary": "duplicate run cancelled during candidate execution", "cancellation_run_id": 30175548334, "evidence_use": "EXCLUDED_FROM_ADJUDICATION"},
        ],
        "shared_import_file_count": shared.get("file_count"),
        "shared_import_aggregate_byte_count": shared.get("aggregate_byte_count"),
        "shared_import_aggregate_sha256": shared.get("aggregate_sha256"),
        "gl_compatibility": {
            "classification": "ANDROID_CRITICAL_RUNTIME_FAILURE",
            "functional_pass": False,
            "earliest_failed_state": gl_class.get("earliest_failed_state"),
            "decisive_evidence": "45 renderer-blocking SceneShaderGLES3 program-link failures; Java/native/linker/ANR/missing-resource counts were zero.",
            "launch_status": gl.get("launch", {}).get("status"),
            "renderer_identity": gl.get("renderer_identity"),
            "screenshot": gl.get("screenshot"),
            "critical_log_scan": gl.get("critical_log_scan"),
            "frame_metrics": gl.get("frame_metrics"),
            "memory": gl.get("memory"),
        },
        "mobile_vulkan": {
            "classification": "ANDROID_SCENE_READINESS_FAILURE",
            "functional_pass": False,
            "earliest_failed_state": mobile_class.get("earliest_failed_state"),
            "decisive_evidence": "Process, visible window, Godot, Vulkan renderer identity, mission, and scene readiness passed; warm-up/capture-frame markers were absent at the bounded timeout.",
            "launch_status": mobile.get("launch", {}).get("status"),
            "renderer_identity": mobile.get("renderer_identity"),
            "process_created": mobile.get("process_created"),
            "window_became_visible": mobile.get("window_became_visible"),
            "screenshot": mobile.get("screenshot"),
        },
        "terminal_outcome": "G0_2_ANDROID_NEITHER_RENDERER_FUNCTIONAL",
        "screenshot_comparison": comparison,
        "gate_g0": "G0_EVIDENCE_INSUFFICIENT",
        "renderer_decision": None,
        "renderer_defaults_modified": False,
        "physical_device_evidence_complete": False,
        "device_handoff_tests_performed": False,
        "g1_authorized": False,
        "unresolved_blockers": [
            "GL Compatibility emitted renderer-blocking GLES3 shader program-link failures on the API 34 emulator.",
            "Mobile Vulkan did not reach warm-up frame 180 or capture frame 300 within the bounded evidence window.",
            "Paired valid Android screenshots and paired lifecycle evidence are incomplete because Mobile stopped before capture.",
            "Named physical-device qualification is unavailable.",
            "Emulator measurements are diagnostic only and cannot select the production renderer.",
        ],
    })
    terminal_path.write_text(json.dumps(terminal, indent=2, sort_keys=True) + "\n")
    (reports / "G0_2_TERMINAL_REPORT.md").write_text(f"""# Bahrain Brick — Stage G0.2 Terminal Report

## Terminal outcome

`G0_2_ANDROID_NEITHER_RENDERER_FUNCTIONAL`

- GL Compatibility: `ANDROID_CRITICAL_RUNTIME_FAILURE`. Package, explicit launch, process, visible window, OpenGL renderer identity, mission, scene readiness, capture frame 300, valid 1920 × 1080 screenshot, 60-second liveness, and pause/resume passed. The earliest failed state was `CRITICAL_LOG_SCAN_PASSED`, with 45 `SceneShaderGLES3: Program linking failed` events.
- Mobile Vulkan: `ANDROID_SCENE_READINESS_FAILURE`. Package, explicit launch, process creation, visible window, Godot, Vulkan renderer identity, mission, and scene readiness passed. The earliest failed state was `CAPTURE_FRAME_REACHED`: warm-up frame 180 and capture frame 300 were absent at the bounded timeout.
- Shared imported-state equivalence: `{shared.get('byte_identical_clones')}` across `{shared.get('file_count')}` files, aggregate SHA-256 `{shared.get('aggregate_sha256')}`.
- Emulator measurements are `DIAGNOSTIC_ONLY_NOT_PHYSICAL_DEVICE_ACCEPTANCE`.

## Screenshot boundary

GL produced a valid non-black 1920 × 1080 screenshot. Mobile did not reach screenshot capture. Its required PNG output is an explicit black missing-evidence placeholder marked `source_evidence_present=false`; structural and pixel comparison were not performed.

## Execution authority

- Adjudicative Android run: `30175169997`, job `89722664363`.
- Raw artifact: `8624075667`, digest `sha256:677c0b55a937ee46f1f85dc600c9ac09c716bae58fd92638824f868792f90d69`.
- Reducer/finalizer replay: `30175596770`, job `89723763711`.
- Reduced artifact: `{ARTIFACT_ID}`, digest `sha256:{ARTIFACT_SHA256}`.
- No Android rerun was performed during terminal report generation.

## Gate boundary

The graphics gate remains `G0_EVIDENCE_INSUFFICIENT`. No renderer is selected, renderer defaults remain unchanged, the dual-renderer physical-device handoff remains unexecuted, and G1 remains unauthorized.
""")
    return terminal


def update_state() -> None:
    state_path = Path(".ai/project-state.json")
    state = json.loads(state_path.read_text())
    state["stage_g0_2"] = {
        "title": "ANDROID PAIRED-RENDERER FUNCTIONAL QUALIFICATION",
        "state": "CLOSED",
        "terminal_outcome": "G0_2_ANDROID_NEITHER_RENDERER_FUNCTIONAL",
        "gl_classification": "ANDROID_CRITICAL_RUNTIME_FAILURE",
        "mobile_classification": "ANDROID_SCENE_READINESS_FAILURE",
        "adjudicative_run_id": 30175169997,
        "raw_artifact_id": 8624075667,
        "reducer_run_id": 30175596770,
        "reduced_artifact_id": ARTIFACT_ID,
        "shared_import_equivalence_passed": True,
        "renderer_decision": None,
        "renderer_defaults_modified": False,
        "physical_device_evidence_complete": False,
        "device_handoff_tests_performed": False,
        "g1_authorized": False,
    }
    state["next_action"] = {
        "stage": "G0.2 closed",
        "action": "Execute the dual-renderer handoff on named physical devices only after explicit authorization. Do not select a renderer or begin G1.",
    }
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    Path(".ai/CHECKPOINT.md").write_text("""# Bahrain Brick Graphics — G0.2 Checkpoint

Recorded: 2026-07-25

## Terminal state

- Stage: **BAHRAIN BRICK — STAGE G0.2**
- Outcome: `G0_2_ANDROID_NEITHER_RENDERER_FUNCTIONAL`
- GL Compatibility: `ANDROID_CRITICAL_RUNTIME_FAILURE`
- Mobile Vulkan: `ANDROID_SCENE_READINESS_FAILURE`
- Shared imported-state equivalence: passed
- Renderer selected: no
- Renderer defaults changed: no
- Physical-device tests: not executed
- Graphics gate: `G0_EVIDENCE_INSUFFICIENT`
- G1: unauthorized

## Decisive evidence

GL completed launch, rendering, scene, capture, screenshot, liveness, and lifecycle, but emitted 45 renderer-blocking GLES3 program-link failures. Mobile completed launch, process, visible window, Vulkan identity, mission, and scene readiness, but did not reach warm-up frame 180 or capture frame 300 before the bounded timeout.

## Evidence authority

- Android run `30175169997`, job `89722664363`
- Raw artifact `8624075667`
- Reducer run `30175596770`, job `89723763711`
- Reduced artifact `8624118896`
- Reports: `reports/graphics/g0_2/`
- Dual-device handoff: `reports/graphics/g0/device_handoff/` — generated, not executed

## Boundary

No renderer is selected. Renderer defaults and production paths remain unchanged. Named physical-device evidence is still required. Do not begin G1.
""")


def validate(reports: Path, handoff: Path, terminal: dict) -> None:
    for rel in REQUIRED_REPORTS:
        path = reports / rel
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"required report missing or empty: {rel}")
    for path in reports.rglob("*.json"):
        json.loads(path.read_text())
    if terminal["terminal_outcome"] != "G0_2_ANDROID_NEITHER_RENDERER_FUNCTIONAL":
        raise RuntimeError("unexpected terminal outcome")
    if terminal["gl_compatibility"]["classification"] != "ANDROID_CRITICAL_RUNTIME_FAILURE":
        raise RuntimeError("unexpected GL classification")
    if terminal["mobile_vulkan"]["classification"] != "ANDROID_SCENE_READINESS_FAILURE":
        raise RuntimeError("unexpected Mobile classification")
    if terminal["renderer_decision"] is not None or terminal["renderer_defaults_modified"]:
        raise RuntimeError("renderer boundary violated")
    if terminal["g1_authorized"] or terminal["device_handoff_tests_performed"]:
        raise RuntimeError("gate boundary violated")
    if terminal["screenshot_comparison"].get("comparison_performed"):
        raise RuntimeError("comparison must remain unperformed without Mobile screenshot evidence")
    for name in HANDOFF_FILES:
        path = handoff / name
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"handoff file missing: {name}")
    json.loads((handoff / "device_result.schema.json").read_text())
    run("bash", "-n", str(handoff / "run_device_test.sh"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-zip", type=Path)
    parser.add_argument("--work-dir", type=Path, default=Path("build/g0_2_terminal"))
    args = parser.parse_args()
    if Path("reports/graphics/g0_2/G0_2_TERMINAL_REPORT.json").is_file():
        print("G0.2 terminal reports already exist; no packaging required.")
        return 0
    run(sys.executable, "tools/graphics/apply_g0_2_finalizer_fix.py")
    run(sys.executable, "-m", "py_compile", "tools/graphics/finalize_g0_2_android_evidence.py")
    run(sys.executable, "-m", "unittest", "tests/graphics/test_finalize_g0_2_android_evidence.py", "-v")
    work = args.work_dir
    if work.exists(): shutil.rmtree(work)
    reduced = work / "reduced"; reduced.mkdir(parents=True)
    archive = work / "reduced.zip"
    obtain_artifact(archive, args.artifact_zip)
    with zipfile.ZipFile(archive) as zf: zf.extractall(reduced)
    archive.unlink()
    reports = work / "reports"; handoff = work / "handoff"
    run(sys.executable, "tools/graphics/finalize_g0_2_android_evidence.py",
        "--raw", str(reduced / "retained/raw"), "--output", str(reports), "--handoff-output", str(handoff))
    terminal = postprocess(reports)
    update_state()
    validate(reports, handoff, terminal)
    target_reports = Path("reports/graphics/g0_2")
    if target_reports.exists(): shutil.rmtree(target_reports)
    target_reports.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(reports, target_reports)
    target_handoff = Path("reports/graphics/g0/device_handoff")
    target_handoff.mkdir(parents=True, exist_ok=True)
    for name in HANDOFF_FILES: shutil.copy2(handoff / name, target_handoff / name)
    print(json.dumps({"terminal_outcome": terminal["terminal_outcome"], "reports": len(REQUIRED_REPORTS), "handoff": len(HANDOFF_FILES)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
