#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

GOVERNING_GATE = "G0_EVIDENCE_INSUFFICIENT"
GL_ERROR = "Fragment shader active uniforms exceed GL_MAX_FRAGMENT_UNIFORM_VECTORS"
GL_MODES = (
    "gl_unshaded",
    "gl_empty",
    "gl_sun",
    "gl_sun_shadow",
    "gl_two_directional",
    "gl_two_directional_shadow",
    "gl_production",
)
MOBILE_MODES = ("mobile_baseline", "mobile_render_disabled_control")
MOBILE_CLASSIFICATIONS = (
    "FRAME_LOOP_STALLED",
    "ASYNC_RESOURCE_WAIT",
    "SCENE_TRANSITION_WAIT",
    "SCRIPT_RUNTIME_ERROR",
    "GPU_DRIVER_TIMEOUT",
    "RENDER_PIPELINE_STALL",
    "UNKNOWN_RUNTIME_BLOCK",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def read_json(path: Path, default: Any) -> Any:
    if not path.is_file() or path.stat().st_size == 0:
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_gl_scenario(directory: Path, mode: str) -> dict[str, Any]:
    text = read_text(directory / "logcat_full.txt")
    link_failures = len(re.findall(r"SceneShaderGLES3: Program linking failed", text))
    uniform_lines = re.findall(
        r"Fragment shader active uniforms exceed GL_MAX_FRAGMENT_UNIFORM_VECTORS(?:\s*\((\d+)\))?",
        text,
    )
    active_counts = sorted({int(value) for value in uniform_lines if value})
    complete = f"R1_GL_SCENARIO_COMPLETE mode={mode}" in text
    renderer = next(
        (line.strip() for line in text.splitlines() if "OpenGL API" in line and "Compatibility" in line),
        None,
    )
    return {
        "mode": mode,
        "scenario_complete": complete,
        "link_failures": link_failures,
        "uniform_overflow_failures": len(uniform_lines),
        "active_uniform_vectors": active_counts,
        "exact_error": GL_ERROR if uniform_lines else None,
        "renderer_identity": renderer,
        "screenshot_present": (directory / "screenshot.png").is_file() and (directory / "screenshot.png").stat().st_size > 0,
        "log_path": f"track_a/{mode}/logcat_full.txt",
        "material_inventory": read_json(directory / "r1_material_inventory.json", {}),
    }


def classify_gl(scenarios: dict[str, dict[str, Any]]) -> dict[str, Any]:
    failing = [mode for mode in GL_MODES if scenarios.get(mode, {}).get("uniform_overflow_failures", 0) > 0]
    earliest = failing[0] if failing else None
    diagnosis_proven = False
    root_cause = "NO_REPRODUCED_GLES3_LINK_FAILURE"
    production_fix_authorized = False
    decisive_evidence: list[str] = []

    if earliest == "gl_unshaded":
        diagnosis_proven = True
        root_cause = "GLES3_CORE_SCENE_SHADER_UNIFORM_VECTOR_OVERFLOW"
        decisive_evidence.append("The unshaded minimal control reproduces the exact active-uniform overflow.")
    elif earliest == "gl_empty":
        diagnosis_proven = scenarios.get("gl_unshaded", {}).get("uniform_overflow_failures", 0) == 0
        root_cause = "GLES3_SHADED_SCENE_SHADER_UNIFORM_VECTOR_OVERFLOW"
        decisive_evidence.append("The unshaded control passes while the first shaded no-light scene reproduces the exact overflow.")
    elif earliest in {"gl_sun", "gl_sun_shadow", "gl_two_directional", "gl_two_directional_shadow"}:
        previous = GL_MODES[GL_MODES.index(earliest) - 1]
        diagnosis_proven = scenarios.get(previous, {}).get("uniform_overflow_failures", 0) == 0
        root_cause = {
            "gl_sun": "DIRECTIONAL_LIGHT_SHADER_SPECIALIZATION_UNIFORM_OVERFLOW",
            "gl_sun_shadow": "DIRECTIONAL_SHADOW_SHADER_SPECIALIZATION_UNIFORM_OVERFLOW",
            "gl_two_directional": "SECOND_DIRECTIONAL_LIGHT_SHADER_SPECIALIZATION_UNIFORM_OVERFLOW",
            "gl_two_directional_shadow": "TWO_LIGHT_SHADOW_SHADER_SPECIALIZATION_UNIFORM_OVERFLOW",
        }[earliest]
        decisive_evidence.append(f"{previous} passes and {earliest} is the first mode with the exact overflow.")
        production_fix_authorized = diagnosis_proven
    elif earliest == "gl_production":
        diagnosis_proven = all(scenarios.get(mode, {}).get("uniform_overflow_failures", 0) == 0 for mode in GL_MODES[:-1])
        root_cause = "PRODUCTION_MATERIAL_OR_SCENE_FEATURE_UNIFORM_OVERFLOW"
        decisive_evidence.append("All minimal controls pass and only the production scene reproduces the exact overflow.")
        production_fix_authorized = diagnosis_proven

    counts = sorted({value for mode in failing for value in scenarios[mode].get("active_uniform_vectors", [])})
    if counts:
        decisive_evidence.append(f"Observed active fragment-uniform vector count(s): {counts}.")
    return {
        "schema_version": 1,
        "baseline_link_failures": 45,
        "observed_modes_with_overflow": failing,
        "earliest_failing_mode": earliest,
        "root_cause": root_cause,
        "diagnosis_proven": diagnosis_proven,
        "production_fix_authorized": production_fix_authorized,
        "exact_error": GL_ERROR,
        "active_uniform_vectors": counts,
        "decisive_evidence": decisive_evidence,
        "corrected_shaders": [],
        "shader_modifications_performed": False,
    }


def _last_record(progress: dict[str, Any]) -> dict[str, Any]:
    records = progress.get("records") if isinstance(progress, dict) else None
    if not isinstance(records, list) or not records:
        return {}
    return records[-1] if isinstance(records[-1], dict) else {}


def classify_mobile(
    baseline: dict[str, Any],
    control: dict[str, Any],
    *,
    baseline_log: str,
    baseline_backtrace: str,
) -> dict[str, Any]:
    baseline_last = _last_record(baseline)
    control_last = _last_record(control)
    baseline_frame = int(baseline_last.get("local_frame", 0) or 0)
    control_frame = int(control_last.get("local_frame", 0) or 0)
    baseline_complete = bool(baseline.get("complete")) or baseline_frame >= 300
    control_complete = bool(control.get("complete")) or control_frame >= 300
    script_errors = bool(re.search(r"SCRIPT ERROR|Parse Error|Invalid call|Invalid get index", baseline_log, re.I))
    gpu_timeout = bool(re.search(r"device lost|GPU hang|watchdog.*GPU|VK_ERROR_DEVICE_LOST", baseline_log, re.I))
    async_wait = bool(re.search(r"ResourceLoader|load_threaded|async resource", baseline_log, re.I))
    scene_wait = bool(re.search(r"await.*scene|scene transition|change_scene", baseline_log, re.I))
    rendering_stack = bool(re.search(r"RenderingServer|render|vulkan|draw|swapchain", baseline_backtrace, re.I))

    classification = "UNKNOWN_RUNTIME_BLOCK"
    diagnosis_proven = False
    evidence: list[str] = []

    if script_errors:
        classification = "SCRIPT_RUNTIME_ERROR"
        diagnosis_proven = True
        evidence.append("Godot script runtime error evidence occurs after scene readiness.")
    elif gpu_timeout:
        classification = "GPU_DRIVER_TIMEOUT"
        diagnosis_proven = True
        evidence.append("GPU device-loss or driver-watchdog evidence is present.")
    elif baseline_complete:
        classification = "UNKNOWN_RUNTIME_BLOCK"
        evidence.append("The baseline reached frame 300; the historical bounded timeout was not reproduced.")
    elif control_complete and not baseline_complete:
        classification = "RENDER_PIPELINE_STALL"
        diagnosis_proven = True
        evidence.append(
            f"Baseline stopped at local frame {baseline_frame}; render-disabled control reached local frame {control_frame}."
        )
        if rendering_stack:
            evidence.append("Captured native backtrace contains rendering/Vulkan frames.")
    elif async_wait:
        classification = "ASYNC_RESOURCE_WAIT"
        diagnosis_proven = True
        evidence.append("Post-readiness asynchronous resource wait evidence is present.")
    elif scene_wait:
        classification = "SCENE_TRANSITION_WAIT"
        diagnosis_proven = True
        evidence.append("Post-readiness scene-transition wait evidence is present.")
    elif baseline_frame == 0 and control_frame == 0:
        classification = "UNKNOWN_RUNTIME_BLOCK"
        diagnosis_proven = False
        evidence.append("Neither baseline nor control advanced beyond the initial progress record; a frame-loop stall is possible but not proven.")
    else:
        evidence.append(
            f"Baseline last local frame={baseline_frame}; control last local frame={control_frame}; unique subsystem evidence is absent."
        )

    if classification not in MOBILE_CLASSIFICATIONS:
        raise AssertionError(classification)
    return {
        "schema_version": 1,
        "classification": classification,
        "diagnosis_proven": diagnosis_proven,
        "production_fix_authorized": False,
        "baseline_last_frame": baseline_frame,
        "control_last_frame": control_frame,
        "baseline_complete": baseline_complete,
        "control_complete": control_complete,
        "decisive_evidence": evidence,
        "script_runtime_error_detected": script_errors,
        "gpu_timeout_detected": gpu_timeout,
        "async_resource_wait_detected": async_wait,
        "scene_transition_wait_detected": scene_wait,
        "rendering_stack_detected": rendering_stack,
    }


def finalize(raw: Path, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    track_a_output = output / "track_a_gl"
    track_b_output = output / "track_b_mobile"
    track_a_output.mkdir(parents=True, exist_ok=True)
    track_b_output.mkdir(parents=True, exist_ok=True)

    scenarios = {
        mode: parse_gl_scenario(raw / "track_a" / mode, mode)
        for mode in GL_MODES
    }
    gl_diagnosis = classify_gl(scenarios)
    write_json(track_a_output / "scenario_matrix.json", scenarios)
    write_json(track_a_output / "diagnosis.json", gl_diagnosis)
    write_json(
        track_a_output / "offending_shader_inventory.json",
        {
            "schema_version": 1,
            "engine_generated_scene_shader": True,
            "user_authored_shader_inventory": scenarios.get("gl_production", {}).get("material_inventory", {}),
            "failure_modes": gl_diagnosis["observed_modes_with_overflow"],
            "exact_error": GL_ERROR,
        },
    )
    write_json(
        track_a_output / "uniform_mismatch_report.json",
        {
            "schema_version": 1,
            "uniform_name_or_type_mismatch_proven": False,
            "aggregate_active_uniform_vector_overflow_proven": bool(gl_diagnosis["observed_modes_with_overflow"]),
            "active_uniform_vectors": gl_diagnosis["active_uniform_vectors"],
            "exact_error": GL_ERROR,
        },
    )
    write_json(
        track_a_output / "precision_mismatch_report.json",
        {"schema_version": 1, "precision_mismatch_proven": False, "evidence": []},
    )
    write_json(
        track_a_output / "unsupported_feature_report.json",
        {
            "schema_version": 1,
            "diagnosis_proven": gl_diagnosis["diagnosis_proven"],
            "root_cause": gl_diagnosis["root_cause"],
            "earliest_failing_mode": gl_diagnosis["earliest_failing_mode"],
        },
    )
    write_json(
        track_a_output / "corrected_shaders.json",
        {"schema_version": 1, "shader_modifications_performed": False, "items": []},
    )

    baseline_dir = raw / "track_b" / "mobile_baseline"
    control_dir = raw / "track_b" / "mobile_render_disabled_control"
    baseline = read_json(baseline_dir / "r1_mobile_progress.json", {"records": [], "complete": False})
    control = read_json(control_dir / "r1_mobile_progress.json", {"records": [], "complete": False})
    mobile_diagnosis = classify_mobile(
        baseline,
        control,
        baseline_log=read_text(baseline_dir / "logcat_full.txt"),
        baseline_backtrace=read_text(baseline_dir / "debuggerd-backtrace.txt"),
    )
    write_json(track_b_output / "baseline_progress.json", baseline)
    write_json(track_b_output / "render_disabled_control_progress.json", control)
    write_json(track_b_output / "classification.json", mobile_diagnosis)
    write_json(
        track_b_output / "subsystem_instrumentation.json",
        {
            "schema_version": 1,
            "frame_counter": True,
            "scene_tree": (baseline_dir / "r1_scene_tree.json").is_file(),
            "physics_counter": True,
            "rendering_loop_counter": True,
            "loading_thread_inventory": (baseline_dir / "r1_wait_inventory.json").is_file(),
            "coroutine_await_site": "SceneTree.process_frame",
            "signal_inventory": (baseline_dir / "r1_scene_tree.json").is_file(),
            "async_resource_loading_inventory": (baseline_dir / "r1_wait_inventory.json").is_file(),
            "watchdog": True,
            "debuggerd_backtrace": (baseline_dir / "debuggerd-backtrace.txt").is_file(),
        },
    )

    report = {
        "schema_version": 1,
        "stage": "BAHRAIN BRICK — STAGE R1",
        "title": "RENDERER RUNTIME DEBUGGING",
        "governing_gate": GOVERNING_GATE,
        "track_a_gl": gl_diagnosis,
        "track_b_mobile": mobile_diagnosis,
        "diagnosis_proven": bool(gl_diagnosis["diagnosis_proven"] and mobile_diagnosis["diagnosis_proven"]),
        "production_fix_authorized": False,
        "production_fixes_applied": False,
        "renderer_defaults_modified": False,
        "gameplay_modified": False,
        "missions_modified": False,
        "g1_authorized": False,
        "r1_exit_criteria_met": False,
        "next_action": "Apply no production fix until each track has a unique evidence-backed diagnosis and a failing regression test.",
    }
    write_json(output / "R1_DIAGNOSTIC_REPORT.json", report)
    (output / "R1_DIAGNOSTIC_REPORT.md").write_text(
        "# Bahrain Brick — Stage R1 Diagnostic Report\n\n"
        f"- Governing gate: `{GOVERNING_GATE}`\n"
        f"- GL root cause: `{gl_diagnosis['root_cause']}`\n"
        f"- GL diagnosis proven: `{str(gl_diagnosis['diagnosis_proven']).lower()}`\n"
        f"- Mobile classification: `{mobile_diagnosis['classification']}`\n"
        f"- Mobile diagnosis proven: `{str(mobile_diagnosis['diagnosis_proven']).lower()}`\n"
        "- Production fixes applied: `false`\n"
        "- Renderer defaults modified: `false`\n"
        "- G1 authorized: `false`\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize Bahrain Brick R1 renderer runtime diagnostic evidence.")
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = finalize(args.raw, args.output)
    print(json.dumps({
        "gl_root_cause": report["track_a_gl"]["root_cause"],
        "mobile_classification": report["track_b_mobile"]["classification"],
        "diagnosis_proven": report["diagnosis_proven"],
        "production_fix_authorized": report["production_fix_authorized"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
