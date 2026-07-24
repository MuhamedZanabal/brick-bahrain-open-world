#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import struct
import zlib
from pathlib import Path
from statistics import median
from typing import Any

READY_MARKER = "BAHRAIN_BRICK_SOUQ_SLICE_READY assets=35 pedestrians=12 traffic=6"
MISSION_MARKER = "BAHRAIN_BRICK_KARAK_MISSION_STARTED"
WARMUP_MARKER = "G0_ANDROID_WARMUP_COMPLETE frame=180"
CAPTURE_MARKER = "G0_ANDROID_CAPTURE_FRAME frame=300"
PAUSE_MARKER = "G0_ANDROID_LIFECYCLE_PAUSED"
RESUME_MARKER = "G0_ANDROID_LIFECYCLE_RESUMED"

PATTERNS = {
    "fatal_error_count": re.compile(r"\bFATAL\b|Fatal signal|SIGSEGV|Segmentation fault|ANR in |am_anr", re.I),
    "shader_error_count": re.compile(r"shader.*(?:error|failed)|failed.*shader|SPIR-V|GLSL.*error", re.I),
    "missing_resource_error_count": re.compile(r"Failed loading resource|Failed to load resource|Could not load resource|missing resource", re.I),
    "script_error_count": re.compile(r"SCRIPT ERROR|Parse Error|Parser Error|Failed to load script", re.I),
    "renderer_blocking_error_count": re.compile(r"rendering device.*failed|failed to initialize.*render|Vulkan.*(?:unavailable|failed)|OpenGL.*(?:unavailable|failed)", re.I),
}


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def inspect_png(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "captured": path.is_file(),
        "valid_non_black": False,
        "average_luminance": 0.0,
        "maximum_luminance": 0.0,
    }
    if not path.is_file():
        return result
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        result["error"] = "invalid_png_signature"
        return result
    offset = 8
    width = height = bit_depth = color_type = interlace = None
    compressed = bytearray()
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + length]
        offset += 12 + length
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _compression, _filter, interlace = struct.unpack(">IIBBBBB", payload)
        elif chunk_type == b"IDAT":
            compressed.extend(payload)
        elif chunk_type == b"IEND":
            break
    if not width or not height or bit_depth != 8 or interlace != 0 or color_type not in (0, 2, 6):
        result.update({"width": width, "height": height, "error": "unsupported_png_format"})
        return result
    channels = {0: 1, 2: 3, 6: 4}[int(color_type)]
    stride = int(width) * channels
    try:
        raw = zlib.decompress(bytes(compressed))
    except zlib.error as exc:
        result["error"] = f"png_decompression_failed:{exc}"
        return result
    expected = int(height) * (stride + 1)
    if len(raw) != expected:
        result["error"] = f"unexpected_png_payload:{len(raw)}:{expected}"
        return result
    rows: list[bytearray] = []
    cursor = 0
    prior = bytearray(stride)
    for _y in range(int(height)):
        filter_type = raw[cursor]
        cursor += 1
        scan = bytearray(raw[cursor:cursor + stride])
        cursor += stride
        reconstructed = bytearray(stride)
        for index, value in enumerate(scan):
            left = reconstructed[index - channels] if index >= channels else 0
            up = prior[index]
            up_left = prior[index - channels] if index >= channels else 0
            if filter_type == 0:
                decoded = value
            elif filter_type == 1:
                decoded = (value + left) & 0xFF
            elif filter_type == 2:
                decoded = (value + up) & 0xFF
            elif filter_type == 3:
                decoded = (value + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                decoded = (value + _paeth(left, up, up_left)) & 0xFF
            else:
                result["error"] = f"unsupported_png_filter:{filter_type}"
                return result
            reconstructed[index] = decoded
        rows.append(reconstructed)
        prior = reconstructed
    total = 0.0
    maximum = 0.0
    samples = 0
    x_step = max(1, int(width) // 64)
    y_step = max(1, int(height) // 36)
    for y in range(0, int(height), y_step):
        row = rows[y]
        for x in range(0, int(width), x_step):
            base = x * channels
            if channels == 1:
                red = green = blue = row[base]
            else:
                red, green, blue = row[base], row[base + 1], row[base + 2]
            luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255.0
            total += luminance
            maximum = max(maximum, luminance)
            samples += 1
    average = total / max(samples, 1)
    result.update({
        "width": int(width),
        "height": int(height),
        "bit_depth": int(bit_depth),
        "color_type": int(color_type),
        "average_luminance": average,
        "maximum_luminance": maximum,
        "valid_non_black": average > 0.005 and maximum > 0.02,
    })
    return result


def parse_renderer(log_text: str) -> dict[str, str | None]:
    marker = re.search(r"G0_ANDROID_RENDERER_READY renderer=(\S+) driver=(\S+)", log_text)
    if marker:
        renderer = marker.group(1)
        driver = marker.group(2)
    else:
        renderer = driver = None
    gl = re.search(r"OpenGL API\s+([^\n]+?)\s+-\s+Compatibility\s+-\s+Using Device:\s*([^\n]+)", log_text)
    mobile = re.search(r"Vulkan\s+([^\n]+?)\s+-\s+Forward Mobile\s+-\s+Using Device[^:]*:\s*([^\n]+)", log_text)
    if renderer is None and gl:
        renderer, driver = "gl_compatibility", "opengl3"
    if renderer is None and mobile:
        renderer, driver = "mobile", "vulkan"
    api = gl.group(1).strip() if gl else mobile.group(1).strip() if mobile else None
    device = gl.group(2).strip() if gl else mobile.group(2).strip() if mobile else None
    return {"renderer": renderer, "rendering_driver": driver, "rendering_api": api, "rendering_device": device}


def parse_gfxinfo(path: Path) -> list[dict[str, float | int]]:
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    in_profile = False
    header: list[str] | None = None
    frames: list[dict[str, float | int]] = []
    for line in lines:
        stripped = line.strip()
        if stripped == "---PROFILEDATA---":
            in_profile = not in_profile
            if not in_profile:
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
        record = dict(zip(header, values))
        try:
            flags = int(record.get("Flags", "1"))
            intended = int(record["IntendedVsync"])
            completed = int(record["FrameCompleted"])
        except (KeyError, ValueError):
            continue
        if flags != 0 or completed <= intended:
            continue
        frames.append({"frame": len(frames) + 1, "frame_time_ms": (completed - intended) / 1_000_000.0})
    return frames


def percentile(sorted_values: list[float], fraction: float) -> float:
    if not sorted_values:
        return 0.0
    index = max(0, min(len(sorted_values) - 1, math.ceil(len(sorted_values) * fraction) - 1))
    return sorted_values[index]


def parse_memory(path: Path) -> dict[str, int | None]:
    text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    pss = re.search(r"TOTAL PSS:\s*(\d+)", text)
    rss = re.search(r"TOTAL RSS:\s*(\d+)", text)
    if pss is None:
        total_line = re.search(r"^\s*TOTAL\s+(\d+)\s+", text, re.MULTILINE)
        pss_value = int(total_line.group(1)) if total_line else None
    else:
        pss_value = int(pss.group(1))
    return {"total_pss_kb": pss_value, "total_rss_kb": int(rss.group(1)) if rss else None}


def finalize_android_evidence(
    evidence_dir: Path,
    *,
    expected_renderer: str,
    apk_path: Path,
    package_name: str,
) -> dict[str, Any]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    log_path = evidence_dir / "runtime.log"
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
    startup = parse_renderer(log_text)
    counts = {name: len(pattern.findall(log_text)) for name, pattern in PATTERNS.items()}
    critical_lines = [line for line in log_text.splitlines() if any(pattern.search(line) for pattern in PATTERNS.values())]
    (evidence_dir / "critical_errors.txt").write_text(
        "\n".join(critical_lines) + ("\n" if critical_lines else ""), encoding="utf-8"
    )

    frames = parse_gfxinfo(evidence_dir / "gfxinfo.txt")
    with (evidence_dir / "frame_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["frame", "frame_time_ms"])
        writer.writeheader()
        writer.writerows(frames)
    times = sorted(float(frame["frame_time_ms"]) for frame in frames)
    average_ms = sum(times) / len(times) if times else 0.0
    screenshot = inspect_png(evidence_dir / "screenshot.png")
    device = json.loads((evidence_dir / "device.json").read_text()) if (evidence_dir / "device.json").is_file() else {}
    lifecycle = json.loads((evidence_dir / "lifecycle.json").read_text()) if (evidence_dir / "lifecycle.json").is_file() else {}
    memory = parse_memory(evidence_dir / "meminfo.txt")
    critical_count = sum(counts.values())
    markers = {
        "scene_ready": READY_MARKER in log_text,
        "mission_start": MISSION_MARKER in log_text,
        "renderer_ready": "G0_ANDROID_RENDERER_READY" in log_text,
        "warmup_complete": WARMUP_MARKER in log_text,
        "capture_frame": CAPTURE_MARKER in log_text,
        "paused": PAUSE_MARKER in log_text or bool(lifecycle.get("pause_observed")),
        "resumed": RESUME_MARKER in log_text or bool(lifecycle.get("resume_observed")),
    }
    renderer_matches = startup["renderer"] == expected_renderer
    evidence_complete = all((
        apk_path.is_file(),
        renderer_matches,
        all(markers.values()),
        bool(lifecycle.get("process_alive")),
        screenshot.get("valid_non_black", False),
        critical_count == 0,
    ))
    result: dict[str, Any] = {
        "schema_version": 1,
        "evidence_tier": "B",
        "evidence_class": "API_34_ANDROID_EMULATOR_FUNCTIONAL",
        "performance_acceptance": False,
        "package_name": package_name,
        "apk": {"path": apk_path.name, "bytes": apk_path.stat().st_size if apk_path.is_file() else None, "sha256": sha256(apk_path)},
        "renderer": startup["renderer"],
        "expected_renderer": expected_renderer,
        "renderer_matches_expected": renderer_matches,
        "rendering_driver": startup["rendering_driver"],
        "rendering_api": startup["rendering_api"],
        "rendering_device": startup["rendering_device"],
        "operating_system": "Android emulator",
        "android": device,
        "gpu": device.get("gpu") or startup["rendering_device"],
        "viewport": device.get("resolution", "2400x1080"),
        "render_scale": 1.0,
        "quality_settings": "frozen_baseline",
        "scene": "res://scenes/manama_souq_vertical_slice.tscn",
        "warmup_frames": 180,
        "captured_frame_number": 300,
        "protocol_markers": markers,
        "frame_metrics": {
            "row_count": len(times),
            "average_ms": average_ms,
            "median_ms": median(times) if times else 0.0,
            "p95_ms": percentile(times, 0.95),
            "p99_ms": percentile(times, 0.99),
            "average_fps": 1000.0 / average_ms if average_ms > 0 else 0.0,
            "one_percent_low_fps": 1000.0 / percentile(times, 0.99) if percentile(times, 0.99) > 0 else 0.0,
            "diagnostic_only": True,
        },
        "process_memory": memory,
        "graphics_memory_bytes": None,
        "draw_calls": None,
        "visible_objects": None,
        "visible_triangles": None,
        "lifecycle": lifecycle,
        "thermal": (evidence_dir / "thermal.txt").read_text(encoding="utf-8", errors="replace") if (evidence_dir / "thermal.txt").is_file() else None,
        "screenshot": screenshot,
        **counts,
        "critical_error_count": critical_count,
        "runtime_log_sha256": sha256(log_path),
        "frame_metrics_sha256": sha256(evidence_dir / "frame_metrics.csv"),
        "critical_errors_sha256": sha256(evidence_dir / "critical_errors.txt"),
        "screenshot_sha256": sha256(evidence_dir / "screenshot.png"),
        "exit_code": 0 if bool(lifecycle.get("process_alive")) else 1,
        "evidence_complete": evidence_complete,
        "conclusion": "Emulator results prove Android functional behavior only and are not physical-device performance acceptance.",
    }
    (evidence_dir / "runtime.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize one Android emulator G0 renderer evidence directory.")
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--expected-renderer", choices=["gl_compatibility", "mobile"], required=True)
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--package-name", required=True)
    args = parser.parse_args()
    result = finalize_android_evidence(
        args.evidence_dir,
        expected_renderer=args.expected_renderer,
        apk_path=args.apk,
        package_name=args.package_name,
    )
    print(json.dumps({"renderer": result["renderer"], "evidence_complete": result["evidence_complete"]}, sort_keys=True))
    return 0 if result["evidence_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
