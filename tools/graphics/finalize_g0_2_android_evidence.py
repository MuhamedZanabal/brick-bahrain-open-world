#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
from pathlib import Path
from statistics import median
from typing import Any

from PIL import Image, ImageChops, ImageEnhance, ImageOps, UnidentifiedImageError

PERFORMANCE_LABEL = "DIAGNOSTIC_ONLY_NOT_PHYSICAL_DEVICE_ACCEPTANCE"
GATE_G0 = "G0_EVIDENCE_INSUFFICIENT"
CANDIDATE_CLASSIFICATIONS = (
    "ANDROID_RENDERER_FUNCTIONAL_PASS",
    "ANDROID_PACKAGE_VERIFICATION_FAILURE",
    "ANDROID_INSTALL_FAILURE",
    "ANDROID_LAUNCHER_RESOLUTION_FAILURE",
    "ANDROID_ACTIVITY_START_FAILURE",
    "ANDROID_PROCESS_CREATION_FAILURE",
    "ANDROID_VISIBLE_WINDOW_FAILURE",
    "ANDROID_GODOT_STARTUP_FAILURE",
    "ANDROID_RENDERER_IDENTITY_FAILURE",
    "ANDROID_SCENE_READINESS_FAILURE",
    "ANDROID_SCREENSHOT_FAILURE",
    "ANDROID_LIFECYCLE_FAILURE",
    "ANDROID_CRITICAL_RUNTIME_FAILURE",
    "ANDROID_EVIDENCE_FINALIZATION_FAILURE",
    "ANDROID_INFRASTRUCTURE_FAILURE",
    "ANDROID_CAUSE_NOT_PROVEN",
)
TERMINAL_OUTCOMES = (
    "G0_2_ANDROID_BOTH_RENDERERS_FUNCTIONAL",
    "G0_2_ANDROID_GL_ONLY_FUNCTIONAL",
    "G0_2_ANDROID_MOBILE_ONLY_FUNCTIONAL",
    "G0_2_ANDROID_NEITHER_RENDERER_FUNCTIONAL",
    "G0_2_ANDROID_INFRASTRUCTURE_INSUFFICIENT",
    "G0_2_EVIDENCE_INSUFFICIENT",
)
STATE_ORDER = (
    "PACKAGE_VERIFIED",
    "LAUNCHER_RESOLVED",
    "LOG_CAPTURE_STARTED",
    "ACTIVITY_START_REQUESTED",
    "PROCESS_CREATED",
    "WINDOW_VISIBLE",
    "GODOT_STARTED",
    "RENDERER_IDENTIFIED",
    "MISSION_STARTED",
    "SCENE_READY",
    "CAPTURE_FRAME_REACHED",
    "SCREENSHOT_CAPTURED",
    "PAUSE_RESUME_PASSED",
    "CRITICAL_LOG_SCAN_PASSED",
    "EVIDENCE_FINALIZED",
)
REQUIRED_OUTPUTS = (
    "authority.json",
    "shared_import_equivalence.json",
    "emulator_environment.json",
    "apk_inventory.json",
    "gl_compatibility/state_machine.json",
    "gl_compatibility/package_report.json",
    "gl_compatibility/launch_report.json",
    "gl_compatibility/runtime.json",
    "gl_compatibility/frame_metrics.csv",
    "gl_compatibility/logcat_full.txt",
    "gl_compatibility/logcat_critical.txt",
    "gl_compatibility/screenshot.png",
    "gl_compatibility/classification.json",
    "mobile_vulkan/state_machine.json",
    "mobile_vulkan/package_report.json",
    "mobile_vulkan/launch_report.json",
    "mobile_vulkan/runtime.json",
    "mobile_vulkan/frame_metrics.csv",
    "mobile_vulkan/logcat_full.txt",
    "mobile_vulkan/logcat_critical.txt",
    "mobile_vulkan/screenshot.png",
    "mobile_vulkan/classification.json",
    "screenshot_comparison.json",
    "screenshot_difference.png",
    "G0_2_TERMINAL_REPORT.json",
    "G0_2_TERMINAL_REPORT.md",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def read_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_apksigner(text: str) -> str | None:
    match = re.search(r"certificate SHA-256 digest:\s*([0-9a-f:]+)", text, re.I)
    return match.group(1).replace(":", "").lower() if match else None


def parse_manifest(text: str, dumpsys: str, expected_package: str) -> dict[str, Any]:
    version_name = None
    version_code = None
    min_sdk = None
    target_sdk = None
    launcher_activity = None
    exported = None
    application_class = None
    orientation = None
    launch_mode = None
    process_name = None
    extract_native_libs = None
    debuggable = None

    patterns = {
        "version_name": r'android:versionName="([^"]+)"',
        "version_code": r'android:versionCode="(\d+)"',
        "min_sdk": r'android:minSdkVersion="(\d+)"',
        "target_sdk": r'android:targetSdkVersion="(\d+)"',
        "application_class": r'<application[^>]+android:name="([^"]+)"',
        "process_name": r'<application[^>]+android:process="([^"]+)"',
        "extract_native_libs": r'<application[^>]+android:extractNativeLibs="([^"]+)"',
        "debuggable": r'<application[^>]+android:debuggable="([^"]+)"',
    }
    found = {key: re.search(pattern, text, re.S) for key, pattern in patterns.items()}
    version_name = found["version_name"].group(1) if found["version_name"] else None
    version_code = int(found["version_code"].group(1)) if found["version_code"] else None
    min_sdk = int(found["min_sdk"].group(1)) if found["min_sdk"] else None
    target_sdk = int(found["target_sdk"].group(1)) if found["target_sdk"] else None
    application_class = found["application_class"].group(1) if found["application_class"] else None
    process_name = found["process_name"].group(1) if found["process_name"] else None
    extract_native_libs = found["extract_native_libs"].group(1) if found["extract_native_libs"] else None
    debuggable = found["debuggable"].group(1) if found["debuggable"] else None

    activity_blocks = re.findall(r"<activity\b.*?</activity>", text, re.S)
    for block in activity_blocks:
        if "android.intent.action.MAIN" in block and "android.intent.category.LAUNCHER" in block:
            name = re.search(r'android:name="([^"]+)"', block)
            exp = re.search(r'android:exported="([^"]+)"', block)
            orient = re.search(r'android:screenOrientation="([^"]+)"', block)
            launch = re.search(r'android:launchMode="([^"]+)"', block)
            launcher_activity = name.group(1) if name else None
            exported = exp.group(1) if exp else None
            orientation = orient.group(1) if orient else None
            launch_mode = launch.group(1) if launch else None
            break

    if version_name is None:
        m = re.search(r"versionName=([^\s]+)", dumpsys)
        version_name = m.group(1) if m else None
    if version_code is None:
        m = re.search(r"versionCode=(\d+)", dumpsys)
        version_code = int(m.group(1)) if m else None
    if min_sdk is None:
        m = re.search(r"minSdk=(\d+)", dumpsys)
        min_sdk = int(m.group(1)) if m else None
    if target_sdk is None:
        m = re.search(r"targetSdk=(\d+)", dumpsys)
        target_sdk = int(m.group(1)) if m else None

    permissions = sorted(set(re.findall(r"<uses-permission[^>]+android:name=\"([^\"]+)\"", text)))
    features = sorted(set(re.findall(r"<uses-feature[^>]+android:name=\"([^\"]+)\"", text)))
    themes = sorted(set(re.findall(r"android:theme=\"([^\"]+)\"", text)))
    return {
        "package_id": expected_package,
        "version_name": version_name,
        "version_code": version_code,
        "minimum_sdk": min_sdk,
        "target_sdk": target_sdk,
        "application_class": application_class,
        "launcher_activity": launcher_activity,
        "exported": exported,
        "theme": themes[0] if themes else None,
        "process_name": process_name,
        "native_library_extraction_policy": extract_native_libs,
        "hardware_feature_requirements": features,
        "graphics_feature_requirements": [item for item in features if "opengl" in item.lower() or "vulkan" in item.lower()],
        "permissions": permissions,
        "debuggable": debuggable,
        "orientation": orientation,
        "launch_mode": launch_mode,
    }


def parse_native_inventory(unzip_text: str) -> dict[str, Any]:
    libs: list[dict[str, Any]] = []
    for line in unzip_text.splitlines():
        match = re.match(r"\s*(\d+)\s+\S+\s+\S+\s+(lib/([^/]+)/([^\s]+\.so))$", line)
        if not match:
            continue
        libs.append({
            "path": match.group(2),
            "abi": match.group(3),
            "filename": match.group(4),
            "uncompressed_size": int(match.group(1)),
        })
    by_path: dict[str, int] = {}
    for item in libs:
        by_path[item["path"]] = by_path.get(item["path"], 0) + 1
    return {
        "libraries": libs,
        "supported_abis": sorted({item["abi"] for item in libs}),
        "x86_64_godot_runtime_present": any(item["path"] == "lib/x86_64/libgodot_android.so" for item in libs),
        "duplicate_libraries": sorted(path for path, count in by_path.items() if count > 1),
    }


def parse_am_start(text: str) -> dict[str, Any]:
    def value(pattern: str, cast: Any = str) -> Any:
        match = re.search(pattern, text, re.M)
        if not match:
            return None
        captured = match.group(1) if match.lastindex else match.group(0)
        try:
            return cast(captured)
        except (TypeError, ValueError):
            return captured

    return {
        "status": value(r"^Status:\s*(\S+)"),
        "activity": value(r"^Activity:\s*(\S+)"),
        "this_time_ms": value(r"^ThisTime:\s*(\d+)", int),
        "total_time_ms": value(r"^TotalTime:\s*(\d+)", int),
        "wait_time_ms": value(r"^WaitTime:\s*(\d+)", int),
        "complete": value(r"^Complete$", lambda _: True) or False,
        "raw_stdout": text,
    }


def parse_gfxinfo_files(directory: Path) -> list[dict[str, float | int]]:
    records: dict[int, dict[str, float | int]] = {}
    for path in sorted(directory.glob("*.txt")):
        lines = read_text(path).splitlines()
        in_profile = False
        header: list[str] | None = None
        for line in lines:
            stripped = line.strip()
            if stripped == "---PROFILEDATA---":
                in_profile = not in_profile
                header = None
                continue
            if not in_profile or not stripped:
                continue
            values = [part.strip() for part in stripped.split(",")]
            if header is None:
                header = values
                continue
            if len(values) != len(header):
                continue
            row = dict(zip(header, values))
            try:
                flags = int(row.get("Flags", "1"))
                intended = int(row["IntendedVsync"])
                completed = int(row["FrameCompleted"])
            except (KeyError, ValueError):
                continue
            if flags != 0 or completed <= intended:
                continue
            records[intended] = {"intended_vsync_ns": intended, "frame_completed_ns": completed, "frame_time_ms": (completed - intended) / 1_000_000.0}
    ordered = [records[key] for key in sorted(records)]
    selected = ordered[-360:]
    return [{"frame": index + 1, **item} for index, item in enumerate(selected)]


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def parse_meminfo_samples(directory: Path) -> dict[str, Any]:
    samples: list[dict[str, int | str | None]] = []
    for path in sorted(directory.glob("*.txt")):
        text = read_text(path)
        rss = re.search(r"TOTAL RSS:\s*(\d+)", text)
        pss = re.search(r"TOTAL PSS:\s*(\d+)", text)
        java = re.search(r"Java Heap:\s*(\d+)", text)
        native = re.search(r"Native Heap:\s*(\d+)", text)
        if pss is None:
            total = re.search(r"^\s*TOTAL\s+(\d+)\s+", text, re.M)
            pss_value = int(total.group(1)) if total else None
        else:
            pss_value = int(pss.group(1))
        samples.append({
            "sample": path.name,
            "rss_kb": int(rss.group(1)) if rss else None,
            "pss_kb": pss_value,
            "java_heap_kb": int(java.group(1)) if java else None,
            "native_heap_kb": int(native.group(1)) if native else None,
        })
    def peak(key: str) -> int | None:
        values = [int(item[key]) for item in samples if item.get(key) is not None]
        return max(values) if values else None
    return {
        "samples": samples,
        "peak_rss_kb": peak("rss_kb"),
        "peak_pss_kb": peak("pss_kb"),
        "peak_java_heap_kb": peak("java_heap_kb"),
        "peak_native_heap_kb": peak("native_heap_kb"),
    }


def materialize_screenshot(source: Path, target: Path) -> bool:
    """Retain captured evidence or create an explicit non-evidence placeholder."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_file() and source.stat().st_size > 0:
        shutil.copy2(source, target)
        return True
    Image.new("RGB", (1920, 1080), "black").save(target)
    return False


def image_report(path: Path, *, source_evidence_present: bool | None = None) -> dict[str, Any]:
    output_present = path.is_file() and path.stat().st_size > 0
    evidence_present = output_present if source_evidence_present is None else bool(source_evidence_present)
    result: dict[str, Any] = {
        "exists": evidence_present,
        "source_evidence_present": evidence_present,
        "output_file_present": output_present,
        "placeholder": output_present and not evidence_present,
        "valid_non_black": False,
    }
    if not output_present:
        result["error"] = "missing_or_empty_png"
        return result
    try:
        with Image.open(path) as image:
            rgb = image.convert("RGB")
            gray = rgb.convert("L")
            pixels = list(gray.getdata())
            average = sum(pixels) / (len(pixels) * 255.0) if pixels else 0.0
            black_ratio = sum(1 for value in pixels if value <= 5) / len(pixels) if pixels else 1.0
            small = gray.resize((8, 8), Image.Resampling.LANCZOS)
            small_values = list(small.getdata())
            threshold = sum(small_values) / len(small_values) if small_values else 0.0
            bits = "".join("1" if value >= threshold else "0" for value in small_values)
            result.update({
                "width": rgb.width,
                "height": rgb.height,
                "average_luminance": average,
                "black_pixel_ratio": black_ratio,
                "perceptual_hash": f"{int(bits, 2):016x}" if bits else None,
                "sha256": sha256(path),
                "valid_non_black": evidence_present and rgb.size == (1920, 1080) and average > 0.005 and black_ratio < 0.98,
            })
    except (UnidentifiedImageError, OSError) as exc:
        result.update({"error": f"invalid_png:{exc}", "sha256": sha256(path)})
    return result


def state_map(machine: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry.get("state"): entry for entry in machine.get("states", [])}


def is_pass(states: dict[str, dict[str, Any]], name: str) -> bool:
    return states.get(name, {}).get("result") == "PASS"


def classify_candidate(raw_dir: Path, expected_renderer: str, screenshot: dict[str, Any], frame_count: int) -> str:
    states = state_map(read_json(raw_dir / "state_machine.json", {"states": []}))
    install_code = int(read_text(raw_dir / "install-exit-code.txt").strip() or "1")
    critical = read_json(raw_dir / "critical_scan.json", {"passed": False})
    liveness = read_json(raw_dir / "liveness.json", {})
    if (raw_dir / "infrastructure_failure.json").is_file():
        return "ANDROID_INFRASTRUCTURE_FAILURE"
    if not is_pass(states, "PACKAGE_VERIFIED"):
        return "ANDROID_PACKAGE_VERIFICATION_FAILURE"
    if install_code != 0:
        return "ANDROID_INSTALL_FAILURE"
    if not is_pass(states, "LAUNCHER_RESOLVED"):
        return "ANDROID_LAUNCHER_RESOLUTION_FAILURE"
    if not is_pass(states, "ACTIVITY_START_REQUESTED"):
        return "ANDROID_ACTIVITY_START_FAILURE"
    if not is_pass(states, "PROCESS_CREATED"):
        return "ANDROID_PROCESS_CREATION_FAILURE"
    if not is_pass(states, "WINDOW_VISIBLE"):
        return "ANDROID_VISIBLE_WINDOW_FAILURE"
    if not is_pass(states, "GODOT_STARTED"):
        return "ANDROID_GODOT_STARTUP_FAILURE"
    if not is_pass(states, "RENDERER_IDENTIFIED"):
        return "ANDROID_RENDERER_IDENTITY_FAILURE"
    if not all(is_pass(states, name) for name in ("MISSION_STARTED", "SCENE_READY", "CAPTURE_FRAME_REACHED")):
        return "ANDROID_SCENE_READINESS_FAILURE"
    if not is_pass(states, "SCREENSHOT_CAPTURED") or not screenshot.get("valid_non_black"):
        return "ANDROID_SCREENSHOT_FAILURE"
    if not is_pass(states, "PAUSE_RESUME_PASSED"):
        return "ANDROID_LIFECYCLE_FAILURE"
    if not critical.get("passed") or not liveness.get("process_remained_alive_60s"):
        return "ANDROID_CRITICAL_RUNTIME_FAILURE"
    if not is_pass(states, "EVIDENCE_FINALIZED") or frame_count < 360:
        return "ANDROID_EVIDENCE_FINALIZATION_FAILURE"
    log = read_text(raw_dir / "logcat_full.txt")
    marker = re.search(r"G0_ANDROID_RENDERER_READY renderer=(\S+) driver=(\S+) gpu=([^\n]+)", log)
    if marker is None or marker.group(1) != expected_renderer:
        return "ANDROID_RENDERER_IDENTITY_FAILURE"
    return "ANDROID_RENDERER_FUNCTIONAL_PASS"


def parse_runtime_markers(log: str) -> dict[str, Any]:
    live = re.search(r"G0_ANDROID_EVIDENCE_LIVE renderer=(\S+) frames=(\d+) memory=(\d+) draw_calls=(\d+) visible_objects=(\d+) visible_primitives=(\d+)", log)
    renderer = re.search(r"G0_ANDROID_RENDERER_READY renderer=(\S+) driver=(\S+) gpu=([^\n]+)", log)
    gl_identity = re.search(r"OpenGL API[^\n]+Compatibility[^\n]+", log)
    mobile_identity = re.search(r"Vulkan [^\n]+Forward Mobile[^\n]+", log)
    return {
        "godot_started": "Godot Engine v" in log,
        "renderer_identity": renderer.group(0) if renderer else None,
        "renderer": renderer.group(1) if renderer else None,
        "rendering_driver": renderer.group(2) if renderer else None,
        "gpu": renderer.group(3).strip() if renderer else None,
        "startup_identity": gl_identity.group(0) if gl_identity else mobile_identity.group(0) if mobile_identity else None,
        "mission_started": "BAHRAIN_BRICK_KARAK_MISSION_STARTED" in log,
        "scene_ready": "BAHRAIN_BRICK_SOUQ_SLICE_READY assets=35 pedestrians=12 traffic=6" in log,
        "warmup_complete": "G0_ANDROID_WARMUP_COMPLETE frame=180" in log,
        "capture_frame_reached": "G0_ANDROID_CAPTURE_FRAME frame=300" in log,
        "evidence_live": bool(live),
        "reported_frames": int(live.group(2)) if live else None,
        "static_memory_bytes": int(live.group(3)) if live else None,
        "draw_calls": int(live.group(4)) if live else None,
        "visible_objects": int(live.group(5)) if live else None,
        "visible_triangles": int(live.group(6)) if live else None,
    }


def finalize_candidate(raw_dir: Path, out_dir: Path, *, expected_renderer: str, package: str, filename: str, apk_sha: str) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    for source_name, target_name in (
        ("state_machine.json", "state_machine.json"),
        ("logcat_full.txt", "logcat_full.txt"),
        ("logcat_critical.txt", "logcat_critical.txt"),
    ):
        source = raw_dir / source_name
        target = out_dir / target_name
        if source.is_file() and source.stat().st_size > 0:
            shutil.copy2(source, target)
        elif target_name == "logcat_critical.txt":
            target.write_text(
                "NOT_CAPTURED: candidate stopped before the critical-log-scan state; no absence-of-errors claim is made.\n",
                encoding="utf-8",
            )
        else:
            target.write_text("NOT_CAPTURED: source evidence file is absent.\n", encoding="utf-8")
    screenshot_source_present = materialize_screenshot(raw_dir / "screenshot.png", out_dir / "screenshot.png")

    manifest_text = read_text(raw_dir / "manifest.xml")
    dumpsys_text = read_text(raw_dir / "dumpsys-package.txt")
    package_report = {
        "schema_version": 1,
        "filename": filename,
        "sha256": apk_sha,
        "package_id": package,
        "signature_digest_sha256": parse_apksigner(read_text(raw_dir / "apksigner.txt")),
        "package_inspection_passed": state_map(read_json(raw_dir / "state_machine.json", {"states": []})).get("PACKAGE_VERIFIED", {}).get("result") == "PASS",
        "install_exit_code": int(read_text(raw_dir / "install-exit-code.txt").strip() or "1"),
        "pm_path": read_text(raw_dir / "pm-path.txt").strip(),
        "resolved_component": read_text(raw_dir / "resolve-activity.txt").strip().splitlines()[-1] if read_text(raw_dir / "resolve-activity.txt").strip() else None,
        "manifest": parse_manifest(manifest_text, dumpsys_text, package),
        "native_inventory": read_json(raw_dir / "native_elf_inventory.json", parse_native_inventory(read_text(raw_dir / "unzip-list.txt"))),
        "renderer_override": read_json(raw_dir / "renderer_override.json", {}),
        "source_authority": "6ade72ed02084791128dcf4a91223e695d802c15",
        "import_state_authority": "shared_import_equivalence.json",
    }
    write_json(out_dir / "package_report.json", package_report)

    launch = parse_am_start(read_text(raw_dir / "am-start.txt"))
    machine = read_json(raw_dir / "state_machine.json", {"states": []})
    states = state_map(machine)
    liveness = read_json(raw_dir / "liveness.json", {})
    launch_start = int(liveness.get("launch_start_epoch_ms") or 0)
    visible = int(liveness.get("first_visible_window_epoch_ms") or 0)
    launch.update({
        "resolved_component": package_report["resolved_component"],
        "process_created": is_pass(states, "PROCESS_CREATED"),
        "initial_pid": liveness.get("initial_pid") or (read_text(raw_dir / "pid-initial.txt").strip() or None),
        "final_pid": liveness.get("final_pid"),
        "process_remained_alive_60s": liveness.get("process_remained_alive_60s") if liveness else None,
        "window_became_visible": is_pass(states, "WINDOW_VISIBLE"),
        "first_visible_window_time_ms": visible - launch_start if visible and launch_start else None,
    })
    write_json(out_dir / "launch_report.json", launch)

    frames = parse_gfxinfo_files(raw_dir / "gfxinfo_samples")
    with (out_dir / "frame_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["frame", "intended_vsync_ns", "frame_completed_ns", "frame_time_ms"])
        writer.writeheader()
        writer.writerows(frames)
    frame_times = [float(item["frame_time_ms"]) for item in frames]
    average_ms = sum(frame_times) / len(frame_times) if frame_times else 0.0
    screenshot = image_report(out_dir / "screenshot.png", source_evidence_present=screenshot_source_present)
    memory = parse_meminfo_samples(raw_dir / "meminfo_samples")
    markers = parse_runtime_markers(read_text(raw_dir / "logcat_full.txt"))
    critical = read_json(raw_dir / "critical_scan.json", {"counts": {}, "passed": False, "total": None})
    lifecycle = read_json(raw_dir / "lifecycle.json", {})
    emulator = read_json(raw_dir / "emulator_environment.json", {})
    classification = classify_candidate(raw_dir, expected_renderer, screenshot, len(frames))
    classification_report = {
        "schema_version": 1,
        "classification": classification,
        "functional_pass": classification == "ANDROID_RENDERER_FUNCTIONAL_PASS",
        "earliest_failed_state": next((entry["state"] for entry in read_json(raw_dir / "state_machine.json", {"states": []}).get("states", []) if entry.get("result") != "PASS"), None),
        "performance_label": PERFORMANCE_LABEL,
    }
    write_json(out_dir / "classification.json", classification_report)

    runtime = {
        "schema_version": 1,
        "evidence_class": "API_34_ANDROID_EMULATOR_FUNCTIONAL",
        "classification": classification,
        "evidence_complete": classification == "ANDROID_RENDERER_FUNCTIONAL_PASS",
        "expected_renderer": expected_renderer,
        "renderer": markers.get("renderer"),
        "rendering_driver": markers.get("rendering_driver"),
        "renderer_identity": markers.get("renderer_identity"),
        "startup_identity": markers.get("startup_identity"),
        "package_id": package,
        "apk_sha256": apk_sha,
        "process_created": launch["process_created"],
        "process_remained_alive_60s": launch["process_remained_alive_60s"],
        "window_became_visible": launch["window_became_visible"],
        "markers": markers,
        "launch": {key: value for key, value in launch.items() if key != "raw_stdout"},
        "screenshot": screenshot,
        "lifecycle": lifecycle,
        "critical_log_scan": critical,
        "frame_metrics": {
            "performance_label": PERFORMANCE_LABEL,
            "row_count": len(frames),
            "mean_frame_time_ms": average_ms,
            "median_frame_time_ms": median(frame_times) if frame_times else 0.0,
            "p95_frame_time_ms": percentile(frame_times, 0.95),
            "p99_frame_time_ms": percentile(frame_times, 0.99),
            "average_fps": 1000.0 / average_ms if average_ms > 0 else 0.0,
            "one_percent_low_fps": 1000.0 / percentile(frame_times, 0.99) if percentile(frame_times, 0.99) > 0 else 0.0,
        },
        "memory": memory,
        "draw_calls": markers.get("draw_calls"),
        "visible_objects": markers.get("visible_objects"),
        "visible_triangles": markers.get("visible_triangles"),
        "startup_time_ms": launch.get("total_time_ms"),
        "first_visible_window_time_ms": launch.get("first_visible_window_time_ms"),
        "scene_readiness_time": state_map(read_json(raw_dir / "state_machine.json", {"states": []})).get("SCENE_READY", {}).get("terminal_timestamp"),
        "emulator": emulator,
        "performance_acceptance": False,
        "performance_label": PERFORMANCE_LABEL,
    }
    write_json(out_dir / "runtime.json", runtime)
    return {"classification": classification, "runtime": runtime, "package_report": package_report}


def compare_screenshots(
    gl_path: Path,
    mobile_path: Path,
    output_root: Path,
    *,
    gl_report: dict[str, Any] | None = None,
    mobile_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": 1,
        "gl": gl_report or image_report(gl_path),
        "mobile": mobile_report or image_report(mobile_path),
        "structural_comparison": None,
        "mean_absolute_channel_delta": None,
        "perceptual_hash_hamming_distance": None,
        "comparison_is_descriptive_only": True,
    }
    if not result["gl"].get("valid_non_black") or not result["mobile"].get("valid_non_black"):
        result.update({
            "comparison_performed": False,
            "comparison_reason": "both captured, valid, non-black screenshots are required",
        })
        write_json(output_root / "screenshot_comparison.json", result)
        Image.new("RGB", (1920, 1080), "black").save(output_root / "screenshot_difference.png")
        Image.new("RGB", (3840, 1080), "black").save(output_root / "screenshot_side_by_side.png")
        return result
    with Image.open(gl_path) as gl_image, Image.open(mobile_path) as mobile_image:
        gl = gl_image.convert("RGB")
        mobile = mobile_image.convert("RGB")
        if gl.size != mobile.size:
            mobile = mobile.resize(gl.size, Image.Resampling.LANCZOS)
        difference = ImageChops.difference(gl, mobile)
        enhanced = ImageEnhance.Contrast(ImageOps.autocontrast(difference)).enhance(2.0)
        enhanced.save(output_root / "screenshot_difference.png")
        side = Image.new("RGB", (gl.width * 2, gl.height))
        side.paste(gl, (0, 0)); side.paste(mobile, (gl.width, 0))
        side.save(output_root / "screenshot_side_by_side.png")
        histogram = difference.histogram()
        total_channels = gl.width * gl.height * 3
        absolute_sum = sum(index % 256 * count for index, count in enumerate(histogram))
        mean_abs = absolute_sum / total_channels if total_channels else 0.0
        gl_gray = list(gl.convert("L").resize((256, 144), Image.Resampling.BILINEAR).getdata())
        mobile_gray = list(mobile.convert("L").resize((256, 144), Image.Resampling.BILINEAR).getdata())
        mean_x = sum(gl_gray) / len(gl_gray); mean_y = sum(mobile_gray) / len(mobile_gray)
        var_x = sum((x - mean_x) ** 2 for x in gl_gray) / len(gl_gray)
        var_y = sum((y - mean_y) ** 2 for y in mobile_gray) / len(mobile_gray)
        cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(gl_gray, mobile_gray)) / len(gl_gray)
        c1 = (0.01 * 255) ** 2; c2 = (0.03 * 255) ** 2
        ssim = ((2 * mean_x * mean_y + c1) * (2 * cov + c2)) / ((mean_x ** 2 + mean_y ** 2 + c1) * (var_x + var_y + c2))
        phash_gl = int(result["gl"]["perceptual_hash"], 16)
        phash_mobile = int(result["mobile"]["perceptual_hash"], 16)
        result.update({
            "structural_comparison": ssim,
            "mean_absolute_channel_delta": mean_abs,
            "perceptual_hash_hamming_distance": (phash_gl ^ phash_mobile).bit_count(),
            "dimensions_equal": gl.size == mobile.size,
            "comparison_performed": True,
        })
    write_json(output_root / "screenshot_comparison.json", result)
    return result


def terminal_outcome(gl_class: str, mobile_class: str) -> str:
    gl_pass = gl_class == "ANDROID_RENDERER_FUNCTIONAL_PASS"
    mobile_pass = mobile_class == "ANDROID_RENDERER_FUNCTIONAL_PASS"
    if gl_pass and mobile_pass:
        return "G0_2_ANDROID_BOTH_RENDERERS_FUNCTIONAL"
    if gl_pass:
        return "G0_2_ANDROID_GL_ONLY_FUNCTIONAL"
    if mobile_pass:
        return "G0_2_ANDROID_MOBILE_ONLY_FUNCTIONAL"
    if gl_class == mobile_class == "ANDROID_INFRASTRUCTURE_FAILURE":
        return "G0_2_ANDROID_INFRASTRUCTURE_INSUFFICIENT"
    if gl_class in CANDIDATE_CLASSIFICATIONS and mobile_class in CANDIDATE_CLASSIFICATIONS:
        return "G0_2_ANDROID_NEITHER_RENDERER_FUNCTIONAL"
    return "G0_2_EVIDENCE_INSUFFICIENT"


def build_handoff(output: Path, apk_inventory: dict[str, Any], terminal: dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    variants = apk_inventory["variants"]
    hashes = "\n".join(f"{item['sha256']}  {item['filename']}" for item in variants) + "\n"
    (output / "apk_sha256.txt").write_text(hashes)
    (output / "expected_markers.txt").write_text(
        "BAHRAIN_BRICK_KARAK_MISSION_STARTED\n"
        "BAHRAIN_BRICK_SOUQ_SLICE_READY assets=35 pedestrians=12 traffic=6\n"
        "G0_ANDROID_RENDERER_READY\nG0_ANDROID_WARMUP_COMPLETE frame=180\n"
        "G0_ANDROID_CAPTURE_FRAME frame=300\nG0_ANDROID_EVIDENCE_LIVE\n"
        "G0_ANDROID_LIFECYCLE_PAUSED\nG0_ANDROID_LIFECYCLE_RESUMED\n"
    )
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Bahrain Brick paired renderer physical-device result",
        "type": "object",
        "required": ["device", "renderer_results", "tests_performed"],
        "properties": {
            "tests_performed": {"const": False, "description": "Template remains false until a named device test is actually executed."},
            "device": {
                "type": "object",
                "required": ["model", "soc", "gpu", "ram_mb", "android_version", "screen_resolution"],
                "properties": {key: {"type": ["string", "integer"]} for key in ("model", "soc", "gpu", "ram_mb", "android_version", "screen_resolution")},
            },
            "renderer_results": {
                "type": "object",
                "required": ["gl_compatibility", "mobile_vulkan"],
                "properties": {
                    key: {
                        "type": "object",
                        "required": ["renderer", "quality_preset", "apk_sha256", "cold_start", "scene_readiness", "five_minute_traversal", "peak_memory", "thermal_state", "pause_resume", "fatal_anr_native_crash_scan"],
                    } for key in ("gl_compatibility", "mobile_vulkan")
                },
            },
        },
    }
    write_json(output / "device_result.schema.json", schema)
    (output / "README.md").write_text(
        "# Bahrain Brick Dual-Renderer Physical-Device Handoff\n\n"
        "Status: **GENERATED, NOT EXECUTED**. Test GL Compatibility and Mobile Vulkan on the same named device with the same sequence.\n\n"
        "Provide the two APK paths to the shell or PowerShell runner. Each candidate uses its own package ID, cold launch, five-minute traversal, frame/memory/thermal capture, pause/resume, and fatal/ANR/native-crash scan.\n\n"
        f"G0.2 emulator result: `{terminal['terminal_outcome']}`. This does not select a renderer or satisfy physical-device acceptance.\n"
    )
    (output / "adb_capture_commands.txt").write_text(
        "# Replace <package> and <component> for each candidate.\n"
        "adb install -r -t <apk>\nadb shell pm path <package>\n"
        "adb shell cmd package resolve-activity --brief <package>\nadb logcat -c\n"
        "adb shell am force-stop <package>\nadb shell pm clear <package>\n"
        "adb shell am start -W -S -n <component>\nadb shell pidof <package>\n"
        "adb shell dumpsys activity activities\nadb shell dumpsys window windows\n"
        "adb shell dumpsys gfxinfo <package> framestats\nadb shell dumpsys meminfo <package>\n"
        "adb shell dumpsys thermalservice\nadb logcat -d -v threadtime\n"
    )
    shell_script = r'''#!/usr/bin/env bash
set -euo pipefail
GL_APK="${1:?GL APK path required}"
MOBILE_APK="${2:?Mobile APK path required}"
OUT_DIR="${3:-device-results}"
run_variant() {
  local key="$1" package="$2" apk="$3" out="$OUT_DIR/$key"
  mkdir -p "$out"
  adb install -r -t "$apk" | tee "$out/install.txt"
  adb shell pm path "$package" | tee "$out/pm-path.txt"
  component="$(adb shell cmd package resolve-activity --brief "$package" | tr -d '\r' | tail -1)"
  printf '%s\n' "$component" > "$out/resolved-component.txt"
  adb logcat -c
  adb logcat -v threadtime > "$out/logcat_full.txt" 2>&1 & logcat_pid=$!
  adb shell am force-stop "$package"; adb shell pm clear "$package"
  adb shell am start -W -S -n "$component" | tee "$out/am-start.txt"
  sleep 60
  adb shell pidof "$package" | tee "$out/pid.txt"
  adb shell dumpsys activity activities > "$out/activity.txt"
  adb shell dumpsys window windows > "$out/window.txt"
  adb exec-out screencap -p > "$out/screenshot.png"
  adb shell dumpsys gfxinfo "$package" framestats > "$out/gfxinfo.txt"
  adb shell dumpsys meminfo "$package" > "$out/meminfo.txt"
  adb shell dumpsys thermalservice > "$out/thermal.txt"
  adb shell input keyevent 3; sleep 4; adb shell am start -W -n "$component" > "$out/resume.txt"
  sleep 5; kill "$logcat_pid" || true
}
run_variant gl_compatibility com.brickbahrain.g0gl "$GL_APK"
run_variant mobile_vulkan com.brickbahrain.g0mobile "$MOBILE_APK"
echo 'Template capture completed. tests_performed remains false until reviewed and signed.'
'''
    (output / "run_device_test.sh").write_text(shell_script)
    (output / "run_device_test.sh").chmod(0o755)
    ps1 = r'''param([Parameter(Mandatory=$true)][string]$GlApk,[Parameter(Mandatory=$true)][string]$MobileApk,[string]$OutDir="device-results")
$ErrorActionPreference="Stop"
function Run-Variant($Key,$Package,$Apk) {
  $Out=Join-Path $OutDir $Key; New-Item -ItemType Directory -Force -Path $Out | Out-Null
  adb install -r -t $Apk | Tee-Object (Join-Path $Out "install.txt")
  adb shell pm path $Package | Tee-Object (Join-Path $Out "pm-path.txt")
  $Component=(adb shell cmd package resolve-activity --brief $Package | Select-Object -Last 1).Trim()
  $Component | Set-Content (Join-Path $Out "resolved-component.txt")
  adb logcat -c
  $Log=Start-Process adb -ArgumentList @("logcat","-v","threadtime") -RedirectStandardOutput (Join-Path $Out "logcat_full.txt") -PassThru
  adb shell am force-stop $Package; adb shell pm clear $Package
  adb shell am start -W -S -n $Component | Set-Content (Join-Path $Out "am-start.txt")
  Start-Sleep -Seconds 60
  adb shell pidof $Package | Set-Content (Join-Path $Out "pid.txt")
  adb shell dumpsys activity activities | Set-Content (Join-Path $Out "activity.txt")
  adb shell dumpsys window windows | Set-Content (Join-Path $Out "window.txt")
  adb exec-out screencap -p > (Join-Path $Out "screenshot.png")
  adb shell dumpsys gfxinfo $Package framestats | Set-Content (Join-Path $Out "gfxinfo.txt")
  adb shell dumpsys meminfo $Package | Set-Content (Join-Path $Out "meminfo.txt")
  adb shell dumpsys thermalservice | Set-Content (Join-Path $Out "thermal.txt")
  adb shell input keyevent 3; Start-Sleep -Seconds 4; adb shell am start -W -n $Component | Set-Content (Join-Path $Out "resume.txt")
  Stop-Process -Id $Log.Id -ErrorAction SilentlyContinue
}
Run-Variant "gl_compatibility" "com.brickbahrain.g0gl" $GlApk
Run-Variant "mobile_vulkan" "com.brickbahrain.g0mobile" $MobileApk
Write-Host "Template capture completed. tests_performed remains false until reviewed and signed."
'''
    (output / "run_device_test.ps1").write_text(ps1)


def finalize(raw_root: Path, output_root: Path, handoff_output: Path) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    authority = read_json(raw_root / "authority.json", {})
    shared = read_json(raw_root / "shared_import_equivalence.json", {})
    shutil.copy2(raw_root / "authority.json", output_root / "authority.json")
    shutil.copy2(raw_root / "shared_import_equivalence.json", output_root / "shared_import_equivalence.json")

    variants = []
    variant_authority = {item["key"]: item for item in authority.get("apk_variants", [])}
    results: dict[str, Any] = {}
    for key, expected in (("gl_compatibility", "gl_compatibility"), ("mobile_vulkan", "mobile")):
        item = variant_authority[key]
        result = finalize_candidate(
            raw_root / key,
            output_root / key,
            expected_renderer=expected,
            package=item["package_id"],
            filename=item["filename"],
            apk_sha=item["sha256"],
        )
        results[key] = result
        variants.append({
            "key": key,
            "renderer": expected,
            "filename": item["filename"],
            "sha256": item["sha256"],
            "package_id": item["package_id"],
            "version": result["package_report"]["manifest"].get("version_name"),
            "version_code": result["package_report"]["manifest"].get("version_code"),
            "launcher_component": result["package_report"].get("resolved_component"),
            "abi": result["package_report"]["native_inventory"].get("supported_abis"),
            "signature_digest_sha256": result["package_report"].get("signature_digest_sha256"),
            "renderer_override_mechanism": result["package_report"].get("renderer_override"),
            "source_authority": authority.get("renderer_evidence_source_commit"),
            "import_state_authority": shared.get("aggregate_sha256"),
        })
    apk_inventory = {"schema_version": 1, "variants": variants}
    write_json(output_root / "apk_inventory.json", apk_inventory)

    gl_env = results["gl_compatibility"]["runtime"].get("emulator", {})
    mobile_env = results["mobile_vulkan"]["runtime"].get("emulator", {})
    comparable_fields = ("api_level", "system_image", "abi", "ram_mb", "cores", "gpu_mode", "host_runner_class", "emulator_version")
    equivalence = {field: gl_env.get(field) == mobile_env.get(field) for field in comparable_fields}
    emulator_environment = {
        "schema_version": 1,
        "gl_compatibility": gl_env,
        "mobile_vulkan": mobile_env,
        "equivalent_baselines": all(equivalence.values()),
        "equivalence_fields": equivalence,
        "reset_method": "destroy and recreate identical AVD with wipe-data before each candidate",
        "performance_label": PERFORMANCE_LABEL,
    }
    write_json(output_root / "emulator_environment.json", emulator_environment)

    comparison = compare_screenshots(
        output_root / "gl_compatibility/screenshot.png",
        output_root / "mobile_vulkan/screenshot.png",
        output_root,
        gl_report=results["gl_compatibility"]["runtime"]["screenshot"],
        mobile_report=results["mobile_vulkan"]["runtime"]["screenshot"],
    )
    gl_class = results["gl_compatibility"]["classification"]
    mobile_class = results["mobile_vulkan"]["classification"]
    outcome = terminal_outcome(gl_class, mobile_class)
    terminal = {
        "schema_version": 1,
        "stage": "BAHRAIN BRICK — STAGE G0.2",
        "branch": authority.get("branch"),
        "parent_g0_1_head": authority.get("parent_g0_1_head"),
        "renderer_evidence_source_commit": authority.get("renderer_evidence_source_commit"),
        "frozen_head": authority.get("frozen_head"),
        "source_artifact_id": authority.get("source_artifact_id"),
        "shared_import_equivalence_passed": bool(shared.get("byte_identical_clones")),
        "emulator_baselines_equivalent": emulator_environment["equivalent_baselines"],
        "gl_compatibility": {"classification": gl_class, "functional_pass": gl_class == "ANDROID_RENDERER_FUNCTIONAL_PASS"},
        "mobile_vulkan": {"classification": mobile_class, "functional_pass": mobile_class == "ANDROID_RENDERER_FUNCTIONAL_PASS"},
        "terminal_outcome": outcome,
        "screenshot_comparison": comparison,
        "performance_label": PERFORMANCE_LABEL,
        "performance_acceptance": False,
        "gate_g0": GATE_G0,
        "renderer_decision": None,
        "renderer_defaults_modified": False,
        "physical_device_evidence_complete": False,
        "g1_authorized": False,
        "unresolved_blockers": [
            "Named physical-device qualification is unavailable.",
            "Emulator measurements are diagnostic only and cannot select the production renderer.",
        ],
    }
    write_json(output_root / "G0_2_TERMINAL_REPORT.json", terminal)
    md = f"""# Bahrain Brick — Stage G0.2 Terminal Report

## Terminal outcome

`{outcome}`

- GL Compatibility: `{gl_class}`
- Mobile Vulkan: `{mobile_class}`
- Shared imported-state equivalence: `{shared.get('byte_identical_clones')}`
- Equivalent emulator baselines: `{emulator_environment['equivalent_baselines']}`
- Performance label: `{PERFORMANCE_LABEL}`

## Gate boundary

The graphics gate remains `{GATE_G0}`. No renderer is selected, renderer defaults remain unchanged, physical-device evidence is incomplete, and G1 remains unauthorized.

## Visual comparison

The paired screenshots are compared descriptively. Visual differences do not select renderer authority. See `screenshot_comparison.json`, `screenshot_difference.png`, and `screenshot_side_by_side.png`.
"""
    (output_root / "G0_2_TERMINAL_REPORT.md").write_text(md, encoding="utf-8")
    build_handoff(handoff_output, apk_inventory, terminal)

    for rel in REQUIRED_OUTPUTS:
        path = output_root / rel
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"required output missing or empty: {rel}")
    return terminal


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize Bahrain Brick G0.2 paired Android renderer evidence.")
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--handoff-output", type=Path, required=True)
    args = parser.parse_args()
    terminal = finalize(args.raw, args.output, args.handoff_output)
    print(json.dumps({"terminal_outcome": terminal["terminal_outcome"], "gate_g0": terminal["gate_g0"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
