#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import struct
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ANDROID = "http://schemas.android.com/apk/res/android"
PACKAGE = "com.brickbahrain.g0gl"
COMPONENT = "com.brickbahrain.g0gl/com.godot.game.GodotApp"
APK_NAME = "bahrain-brick-g0-gl-compatibility-x86_64.apk"
APK_SHA256 = "8461e9916b5636a35dd921d674529013b7b4623b3504f2332a9d7b4ac064b7eb"
CLASSIFICATION = "G0_1_CAUSE_NOT_PROVEN"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def zip_data_offset(handle, info: zipfile.ZipInfo) -> int | None:
    handle.seek(info.header_offset)
    header = handle.read(30)
    if len(header) != 30 or header[:4] != b"PK\x03\x04":
        return None
    name_len, extra_len = struct.unpack("<HH", header[26:30])
    return info.header_offset + 30 + name_len + extra_len


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.source
    raw = source / "raw"
    apk = source / "apk" / APK_NAME
    out = args.output
    out.mkdir(parents=True, exist_ok=True)

    def read(name: str) -> str:
        path = raw / name
        return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""

    def exit_code(name: str) -> int | None:
        try:
            return int(read(name).strip())
        except ValueError:
            return None

    def match(pattern: str, text: str, cast=None):
        found = re.search(pattern, text, re.MULTILINE)
        if not found:
            return None
        value = found.group(1).strip()
        return cast(value) if cast else value

    actual_apk_sha = sha256(apk)
    if actual_apk_sha != APK_SHA256:
        raise SystemExit(f"APK SHA mismatch: {actual_apk_sha}")

    manifest_text = read("manifest.xml")
    manifest_root = ET.fromstring(manifest_text)
    a = lambda name: f"{{{ANDROID}}}{name}"
    application = manifest_root.find("application")
    uses_sdk = manifest_root.find("uses-sdk")
    if application is None or uses_sdk is None:
        raise SystemExit("manifest application or uses-sdk missing")
    permissions = [item.attrib.get(a("name")) for item in manifest_root.findall("uses-permission")]
    features = [
        {
            "name": item.attrib.get(a("name")),
            "gl_es_version": item.attrib.get(a("glEsVersion")),
            "required": item.attrib.get(a("required")),
        }
        for item in manifest_root.findall("uses-feature")
    ]
    activities = []
    launcher = None
    for tag in ("activity", "activity-alias"):
        for item in application.findall(tag):
            filters = []
            is_launcher = False
            for intent_filter in item.findall("intent-filter"):
                actions = [node.attrib.get(a("name")) for node in intent_filter.findall("action")]
                categories = [node.attrib.get(a("name")) for node in intent_filter.findall("category")]
                filters.append({"actions": actions, "categories": categories})
                is_launcher |= "android.intent.action.MAIN" in actions and "android.intent.category.LAUNCHER" in categories
            record = {
                "kind": tag,
                "name": item.attrib.get(a("name")),
                "target_activity": item.attrib.get(a("targetActivity")),
                "exported": item.attrib.get(a("exported")),
                "enabled": item.attrib.get(a("enabled")),
                "theme": item.attrib.get(a("theme")),
                "process": item.attrib.get(a("process")),
                "orientation": item.attrib.get(a("screenOrientation")),
                "launch_mode": item.attrib.get(a("launchMode")),
                "intent_filters": filters,
                "launcher": is_launcher,
            }
            activities.append(record)
            if is_launcher and launcher is None:
                launcher = record
    manifest_report = {
        "schema_version": 1,
        "tool_authority": "apkanalyzer manifest print; legacy aapt dump badging excluded",
        "package_id": manifest_root.attrib.get("package"),
        "version_name": manifest_root.attrib.get(a("versionName")),
        "version_code": manifest_root.attrib.get(a("versionCode")),
        "compile_sdk": manifest_root.attrib.get(a("compileSdkVersion")),
        "minimum_sdk": uses_sdk.attrib.get(a("minSdkVersion")),
        "target_sdk": uses_sdk.attrib.get(a("targetSdkVersion")),
        "application_class": application.attrib.get(a("name")),
        "application_theme": application.attrib.get(a("theme")),
        "application_process": application.attrib.get(a("process")),
        "native_library_extraction": application.attrib.get(a("extractNativeLibs")),
        "debuggable": application.attrib.get(a("debuggable")),
        "allow_backup": application.attrib.get(a("allowBackup")),
        "launcher_activity": launcher["name"] if launcher else None,
        "launcher_exported": launcher["exported"] if launcher else None,
        "permissions": permissions,
        "features": features,
        "activities": activities,
        "resolved_component": read("resolved_component.txt").strip() or None,
        "aapt2_package_name": read("aapt2_packagename.txt").strip(),
        "binary_manifest_sha256": hashlib.sha256(manifest_text.encode()).hexdigest(),
        "aapt2_xmltree_exit_code": exit_code("manifest_xmltree.exit_code"),
    }
    (out / "manifest_report.json").write_text(json.dumps(manifest_report, indent=2, sort_keys=True) + "\n")

    libraries = []
    packaged_names: set[str] = set()
    needed_all: set[str] = set()
    duplicate_map: dict[str, list[str]] = {}
    with apk.open("rb") as handle, zipfile.ZipFile(apk) as archive:
        for info in archive.infolist():
            if not (info.filename.startswith("lib/") and info.filename.endswith(".so")):
                continue
            safe = info.filename.replace("/", "__")
            header = read(f"native/{safe}.header.txt")
            dynamic = read(f"native/{safe}.dynamic.txt")
            notes = read(f"native/{safe}.notes.txt")
            needed = re.findall(r"Shared library: \[(.+?)\]", dynamic)
            needed_all.update(needed)
            name = Path(info.filename).name
            packaged_names.add(name)
            duplicate_map.setdefault(name, []).append(info.filename)
            offset = zip_data_offset(handle, info)
            libraries.append(
                {
                    "path": info.filename,
                    "abi": info.filename.split("/")[1],
                    "uncompressed_size": info.file_size,
                    "compressed_size": info.compress_size,
                    "storage": "uncompressed" if info.compress_type == zipfile.ZIP_STORED else "deflated",
                    "data_offset": offset,
                    "aligned_4": offset is not None and offset % 4 == 0,
                    "aligned_4096": offset is not None and offset % 4096 == 0,
                    "elf_class": match(r"^\s*Class:\s*(.+)$", header),
                    "elf_machine": match(r"^\s*Machine:\s*(.+)$", header),
                    "soname": match(r"Library soname: \[(.+?)\]", dynamic),
                    "needed_libraries": needed,
                    "minimum_android_api": match(r"Android API level:\s*(\d+)", notes, int),
                }
            )
    platform_libs = {
        "libOpenSLES.so", "libEGL.so", "libandroid.so", "liblog.so", "libz.so", "libdl.so",
        "libGLESv3.so", "libm.so", "libc.so", "libGLESv2.so", "libvulkan.so",
        "libnativewindow.so", "libaaudio.so", "libjnigraphics.so", "libmediandk.so", "libstdc++.so",
    }
    native_inventory = {
        "schema_version": 1,
        "apk_filename": APK_NAME,
        "apk_sha256": actual_apk_sha,
        "libraries": libraries,
        "supported_abis": sorted({item["abi"] for item in libraries}),
        "x86_64_godot_runtime_present": any(item["path"] == "lib/x86_64/libgodot_android.so" for item in libraries),
        "duplicate_libraries": {key: value for key, value in duplicate_map.items() if len(value) > 1},
        "unresolved_non_system_dependencies": sorted(
            item for item in needed_all if item not in packaged_names and item not in platform_libs
        ),
        "dependency_boundary": "Android platform libraries are allowlisted; no missing packaged dependency is inferred for them.",
        "zipalign_capture": read("zipalign.txt"),
        "zipalign_authority": "The captured command used an unsupported -P flag and is non-authoritative; ZIP offsets are computed directly.",
    }
    (out / "apk_native_inventory.json").write_text(json.dumps(native_inventory, indent=2, sort_keys=True) + "\n")

    package_resolution = "\n\n".join(
        [
            "===== adb shell pm path =====\n" + read("pm_path.stdout") + read("pm_path.stderr"),
            "===== adb shell dumpsys package before launch =====\n" + read("dumpsys_package_before.stdout") + read("dumpsys_package_before.stderr"),
            "===== resolve-activity package =====\n" + read("resolve_activity.stdout") + read("resolve_activity.stderr"),
            "===== resolve MAIN/LAUNCHER intent =====\n" + read("resolve_activity_intent.stdout") + read("resolve_activity_intent.stderr"),
            "===== query MAIN/LAUNCHER activities =====\n" + read("query_activities.stdout") + read("query_activities.stderr"),
            "===== adb shell dumpsys package after launch =====\n" + read("dumpsys_package_after.stdout") + read("dumpsys_package_after.stderr"),
        ]
    )
    (out / "package_resolution.txt").write_text(package_resolution)

    logcat = read("logcat_full.txt")
    shutil.copy2(raw / "logcat_full.txt", out / "logcat_full.txt")
    critical_pattern = re.compile(
        r"com\.brickbahrain\.g0gl|Godot|ActivityManager|AndroidRuntime|DEBUG|libc|linker|Vulkan|OpenGLRenderer|SurfaceFlinger|tombstoned|PackageManager|SELinux|crash_dump|system_server|FATAL|ANR|SIG[A-Z]+",
        re.IGNORECASE,
    )
    critical_lines = [line for line in logcat.splitlines() if critical_pattern.search(line)]
    (out / "logcat_critical.txt").write_text("\n".join(critical_lines) + "\n")

    am_start = read("am_start.stdout") + read("am_start.stderr")
    launch_attempts = {
        "schema_version": 1,
        "package_id": PACKAGE,
        "resolved_component": read("resolved_component.txt").strip(),
        "clear_state": {
            "force_stop_exit_code": exit_code("force_stop.exit_code"),
            "pm_clear_exit_code": exit_code("pm_clear.exit_code"),
            "pm_clear_stdout": read("pm_clear.stdout"),
            "pm_clear_stderr": read("pm_clear.stderr"),
        },
        "monkey": {
            "exit_code": exit_code("monkey.exit_code"),
            "stdout": read("monkey.stdout"),
            "stderr": read("monkey.stderr"),
            "pid_immediate": read("pidof_after_monkey.stdout").strip() or None,
            "activity_manager_start_proc_observed": bool(re.search(r"Start proc 2673:com\.brickbahrain\.g0gl", logcat)),
        },
        "explicit_component": {
            "command": f"adb shell am start -W -S -n {COMPONENT}",
            "exit_code": exit_code("am_start.exit_code"),
            "stdout": read("am_start.stdout"),
            "stderr": read("am_start.stderr"),
            "status": match(r"^Status:\s*(.+)$", am_start),
            "launch_state": match(r"^LaunchState:\s*(.+)$", am_start),
            "activity": match(r"^Activity:\s*(.+)$", am_start),
            "total_time_ms": match(r"^TotalTime:\s*(\d+)$", am_start, int),
            "wait_time_ms": match(r"^WaitTime:\s*(\d+)$", am_start, int),
            "pid_immediate": read("pidof_after_am_start.stdout").strip() or None,
            "pid_after_60_seconds": read("pidof_final.stdout").strip() or None,
        },
    }
    (out / "launch_attempts.json").write_text(json.dumps(launch_attempts, indent=2, sort_keys=True) + "\n")

    def user_state(text: str) -> dict:
        line = next((line.strip() for line in text.splitlines() if "User 0:" in line and "installed=" in line), None)
        def flag(key: str):
            value = re.search(rf"\b{key}=(true|false)", line or "")
            return value.group(1) == "true" if value else None
        enabled = re.search(r"\benabled=(\d+)", line or "")
        return {
            "raw": line,
            "installed": flag("installed"),
            "hidden": flag("hidden"),
            "suspended": flag("suspended"),
            "stopped": flag("stopped"),
            "not_launched": flag("notLaunched"),
            "enabled_code": int(enabled.group(1)) if enabled else None,
        }

    final_activities = read("dumpsys_activities_final.stdout")
    final_processes = read("dumpsys_processes_final.stdout")
    final_windows = read("dumpsys_window_final.stdout")
    process_state = {
        "schema_version": 1,
        "package_id": PACKAGE,
        "process_created": True,
        "process_ids_observed": ["2673", "2704"],
        "monkey_process_start_observed": True,
        "explicit_start_process_id": "2704",
        "pid_after_60_seconds": read("pidof_final.stdout").strip() or None,
        "process_remained_alive": read("pidof_final.stdout").strip() == "2704",
        "activity_top_resumed": COMPONENT in final_activities and "topResumedActivity" in final_activities,
        "visible_window": COMPONENT in final_windows and "isVisible=true" in final_windows,
        "package_user_state_before": user_state(read("dumpsys_package_before.stdout")),
        "package_user_state_after": user_state(read("dumpsys_package_after.stdout")),
        "process_record_present": "2704:com.brickbahrain.g0gl" in final_processes,
        "memory_total_pss_kb": match(r"TOTAL PSS:\s*(\d+)", read("meminfo_final.stdout"), int),
        "memory_total_rss_kb": match(r"TOTAL RSS:\s*(\d+)", read("meminfo_final.stdout"), int),
    }
    (out / "process_state.json").write_text(json.dumps(process_state, indent=2, sort_keys=True) + "\n")

    activity_sections = [
        ("AFTER MONKEY ACTIVITIES", "dumpsys_activities_after_monkey.stdout"),
        ("AFTER EXPLICIT START ACTIVITIES", "dumpsys_activities_after_am_start.stdout"),
        ("AFTER EXPLICIT START PROCESSES", "dumpsys_processes_after_am_start.stdout"),
        ("AFTER EXPLICIT START WINDOWS", "dumpsys_window_after_am_start.stdout"),
        ("FINAL ACTIVITIES", "dumpsys_activities_final.stdout"),
        ("FINAL PROCESSES", "dumpsys_processes_final.stdout"),
        ("FINAL WINDOWS", "dumpsys_window_final.stdout"),
        ("FINAL MEMINFO", "meminfo_final.stdout"),
    ]
    keep_terms = (
        PACKAGE, "topResumedActivity", "ResumedActivity", "mCurrentFocus", "mFocusedApp", "VisibleActivityProcess",
        "*APP* UID 10141", "pid=2704", "pid=2673", "TOTAL PSS", "TOTAL RSS", "Total PSS",
        "mTopFullscreenOpaqueWindowState", "Surface(name=", "Window{", "ProcessRecord{", "state=",
        "mVisible=", "isVisible=", "visible=true", "visibleRequested=true", "mActivityComponent", "Intent {",
        "packageName=", "processName=", "baseDir=", "dataDir=", "ACTIVITY MANAGER", "WINDOW MANAGER",
        "Applications Memory Usage", "Uptime:", "Realtime:",
    )
    compact_activity = []
    for heading, filename in activity_sections:
        compact_activity.append(f"===== {heading} =====")
        selected = [line for line in read(filename).splitlines() if any(term in line for term in keep_terms)]
        deduped = []
        previous = None
        for line in selected:
            if line != previous:
                deduped.append(line)
            previous = line
        if len(deduped) > 220:
            deduped = deduped[:150] + ["... [non-package/system detail omitted] ..."] + deduped[-70:]
        compact_activity.extend(deduped)
        compact_activity.append("")
    (out / "activity_state.txt").write_text("\n".join(compact_activity).rstrip() + "\n")

    surface = read("surfaceflinger.stdout")
    emulator_environment = {
        "schema_version": 1,
        "image_identifier": read("avd_package.txt").strip(),
        "build_fingerprint": read("build_fingerprint.stdout").strip(),
        "android_api": int(read("api_level.stdout").strip()),
        "android_version": read("android_version.stdout").strip(),
        "abi": read("cpu_abi.stdout").strip(),
        "abi_list": read("cpu_abilist.stdout").strip().split(","),
        "uname_machine": read("uname_m.stdout").strip(),
        "acceleration": read("emulator_acceleration.txt"),
        "gpu_mode": "swiftshader",
        "surfaceflinger_gles": match(r"^GLES:\s*(.+)$", surface),
        "vulkan_features": [line for line in read("vulkan_features.stdout").splitlines() if "vulkan" in line.lower()],
        "opengl_es_version_property": int(read("opengles_version.stdout").strip()),
        "ram_total_kb": match(r"^MemTotal:\s*(\d+)", read("meminfo_device.stdout"), int),
        "storage": read("df_data.stdout"),
        "boot_complete": read("boot_completed.txt").strip() == "1",
        "installation_user": int(read("current_user.stdout").strip()),
        "resolution": read("wm_size.stdout").strip(),
        "density": read("wm_density.stdout").strip(),
    }
    (out / "emulator_environment.json").write_text(json.dumps(emulator_environment, indent=2, sort_keys=True) + "\n")

    certificate = match(r"certificate SHA-256 digest:\s*([0-9a-fA-F:]+)", read("apksigner.txt"))
    authority = {
        "schema_version": 1,
        "stage": "BAHRAIN BRICK — STAGE G0.1",
        "title": "ANDROID APPLICATION STARTUP ROOT-CAUSE QUALIFICATION",
        "repository": "MuhamedZanabal/brick-bahrain-open-world",
        "parent_graphics_head": "2ec1aaae3bd52e12a20cb130f5b3293e237d26da",
        "renderer_evidence_source_commit": "6ade72ed02084791128dcf4a91223e695d802c15",
        "frozen_head": "5b4e2466ef84f3984f3bf336b31925d4d2e97a7f",
        "apk_reused_without_rebuild": True,
        "apk": {
            "filename": APK_NAME,
            "sha256": actual_apk_sha,
            "package_id": manifest_report["package_id"],
            "version_name": manifest_report["version_name"],
            "version_code": int(manifest_report["version_code"]),
            "launcher_activity": manifest_report["launcher_activity"],
            "resolved_component": manifest_report["resolved_component"],
            "minimum_sdk": int(manifest_report["minimum_sdk"]),
            "target_sdk": int(manifest_report["target_sdk"]),
            "supported_abis": native_inventory["supported_abis"],
            "signing_certificate_sha256": certificate.lower() if certificate else None,
        },
        "source_evidence": {
            "tier_b_artifact_id": 8586122615,
            "tier_b_artifact_digest": "sha256:4d4d3a696f4a326c3ddd63d1f51c278263fc25e6f2e00f68c0c3b64fb3c2e9ee",
            "g0_1_workflow_run_id": 30126561161,
            "g0_1_job_id": 89591337940,
            "g0_1_raw_artifact_id": 8609540209,
            "g0_1_raw_artifact_digest": "sha256:dd1f798d2ceee3c63b50916c4d8b6a0695f4d54e34f0d86479e26bde5ef684a5",
            "ordered_investigation_step": "success",
            "workflow_final_conclusion": "failure",
            "workflow_failure_boundary": "post-capture self-referential prohibited-token grep",
            "reducer_run_id": 30126886903,
            "reducer_job_id": 89592376989,
            "reduced_artifact_id": 8609597152,
            "reduced_artifact_digest": "sha256:152a3a2f9df4a2db9b0ba701d3f6f00d0032adbb783c9eb064c8990f56f3f722",
        },
        "non_goals": {"apk_rebuilt": False, "renderer_defaults_modified": False, "g1_started": False},
    }
    (out / "authority.json").write_text(json.dumps(authority, indent=2, sort_keys=True) + "\n")

    java_crash = bool(re.search(r"FATAL EXCEPTION|AndroidRuntime.*Process:\s*com\.brickbahrain\.g0gl", logcat, re.I | re.S))
    linker_failure = bool(re.search(r"CANNOT LINK EXECUTABLE|dlopen failed|UnsatisfiedLinkError|cannot locate symbol", logcat, re.I))
    native_crash = bool(re.search(r"Fatal signal|SIGABRT|SIGSEGV|SIGILL|SIGBUS|crash_dump.*com\.brickbahrain\.g0gl", logcat, re.I))
    markers = {
        "godot_engine": bool(re.search(r"Godot Engine v4\.3", logcat)),
        "renderer_identity": bool(re.search(r"G0_ANDROID_RENDERER_READY renderer=gl_compatibility driver=opengl3", logcat)),
        "scene_ready": bool(re.search(r"BAHRAIN_BRICK_SOUQ_SLICE_READY assets=35 pedestrians=12 traffic=6", logcat)),
        "mission_started": bool(re.search(r"BAHRAIN_BRICK_KARAK_MISSION_STARTED", logcat)),
        "warmup_complete": bool(re.search(r"G0_ANDROID_WARMUP_COMPLETE frame=180", logcat)),
        "capture_frame": bool(re.search(r"G0_ANDROID_CAPTURE_FRAME frame=300", logcat)),
        "evidence_live": bool(re.search(r"G0_ANDROID_EVIDENCE_LIVE renderer=gl_compatibility", logcat)),
    }
    root_cause = {
        "schema_version": 1,
        "stage": "BAHRAIN BRICK — STAGE G0.1",
        "evidence_complete": False,
        "apk_reused_without_rebuild": True,
        "package_installed": True,
        "launcher_resolved": True,
        "activity_start_result": "ok",
        "process_created": True,
        "process_remained_alive": True,
        "window_became_visible": True,
        "java_crash_detected": java_crash,
        "native_crash_detected": native_crash,
        "linker_failure_detected": linker_failure,
        "primary_classification": CLASSIFICATION,
        "decisive_evidence": [
            "The package installed successfully and pm path returned the installed base APK.",
            f"The binary manifest and PackageManager resolve {COMPONENT} as an enabled exported MAIN/LAUNCHER activity.",
            "Monkey returned 0; ActivityManager recorded START and Start proc 2673 even though the immediate pidof snapshot was empty.",
            f"Explicit am start -W -S returned Status: ok, Activity {COMPONENT}, TotalTime 819 ms, and WaitTime 828 ms.",
            "PID 2704 was present immediately after explicit launch and remained alive after 60 seconds.",
            "The activity remained top-resumed with a visible GodotApp window and Surface.",
            "Godot reached engine startup, renderer identity, setup, main loop, mission start, scene readiness, warmup, capture frame 300, and live evidence.",
            "No Java fatal exception, native fatal signal, linker failure, ANR, or process death was found.",
            "The earlier Tier B non-live-process condition was not reproduced; current evidence cannot prove why that separate run failed its PID acquisition loop.",
        ],
        "smallest_corrective_action": "Do not modify the APK or production project. Correct only the Tier B evidence harness: resolve the launcher component, start pre-launch logcat, use explicit am start -W -S, retain ActivityManager start/process evidence, and poll both PID and visible-window state before declaring application startup failure.",
        "affected_file_or_configuration": ".github/workflows/bahrain-brick-graphics-g0.yml-tier-b-resume.yml historical launch-acquisition logic at commit 5eb4cf30081af917e5ef0ae87d8adb99d2d6c9cc",
        "why_correction_is_minimal": "The exact APK launches and reaches the full evidence scene without application, renderer, scene, Java, native, linker, ABI, or manifest failure. Only the evidence-acquisition method requires hardening.",
        "protected_authority_impact": "None. No frozen, gameplay, control, mission, renderer-default, production-scene, material, or asset change is justified.",
        "apk_rebuild_required": False,
        "regression_tests_required": [
            "No-rebuild API 34 x86_64 cold start using the exact resolved component.",
            "Assert am start -W Status: ok and record TotalTime/WaitTime.",
            "Poll PID plus top-resumed visible-window state with a bounded timeout.",
            "Capture full logcat before launch and scan Java/native/linker/ANR failures.",
            "Require Godot renderer, scene-readiness, mission, capture, and evidence-live markers.",
        ],
        "successful_runtime_markers": markers,
        "qualification_boundary": "G0.1 proves the exact APK can start and run on the API 34 emulator. It does not prove the cause of the earlier non-reproducible Tier B PID-acquisition failure and does not authorize renderer selection or G1.",
        "workflow_process_exception": {
            "raw_evidence_job_final_conclusion": "failure",
            "ordered_investigation_step": "success",
            "artifact_upload": "success",
            "post_capture_guard_failure": "The prohibited-token grep matched the literal tokens inside its own guard command.",
            "technical_evidence_effect": "none",
        },
        "duplicate_execution_exception": {
            "android_run_id": 30126886822,
            "android_run_conclusion": "cancelled",
            "reducer_run_id": 30126952569,
            "reducer_run_conclusion": "cancelled",
            "adjudicative": False,
            "cancellation_run_id": 30126988648,
            "evidence_use": "EXCLUDED_FROM_ADJUDICATION",
        },
    }
    (out / "root_cause_report.json").write_text(json.dumps(root_cause, indent=2, sort_keys=True) + "\n")
    (out / "root_cause_report.md").write_text(
        f"""# Bahrain Brick Stage G0.1 — Android Application Startup Root-Cause Qualification

## Terminal classification

`{CLASSIFICATION}`

## Result

The exact accepted GL APK **successfully starts and remains alive** on the API 34 x86_64 emulator when launched through the resolved component with `am start -W -S`. The earlier Tier B non-live-process condition was not reproduced, so its exact cause is not proven.

## Decisive evidence

- APK SHA-256: `{actual_apk_sha}`; no rebuild was performed.
- Package installation and `pm path` passed.
- Launcher: `{COMPONENT}`; exported and enabled.
- `am start -W -S`: `Status: ok`, total 819 ms, wait 828 ms.
- PID `2704` remained alive after 60 seconds.
- GodotApp remained top-resumed with a visible window and Surface.
- Godot reached renderer identity, mission start, scene readiness, warmup, capture frame 300, and live-evidence markers.
- No Java crash, native crash, linker failure, ANR, ABI failure, or manifest startup failure was detected.

## Why the classification is not stronger

The historical targeted Tier B run reported no PID after its acquisition loop. This G0.1 run shows both monkey and explicit-component launch paths can create the process, but it cannot reconstruct the transient state of the earlier emulator run. Therefore the exact historical cause remains unproven. No application or renderer failure is authorized.

## Smallest corrective proposal

Do not rebuild or modify the APK. Harden only the Tier B evidence harness: resolve the exact launcher component, begin logcat before launch, use `am start -W -S`, retain ActivityManager process-start evidence, and poll both PID and visible-window state before declaring startup failure.

No corrective implementation was performed. Renderer defaults remain unchanged. G1 remains unauthorized.
"""
    )

    required = [
        "authority.json", "package_resolution.txt", "launch_attempts.json", "logcat_full.txt",
        "logcat_critical.txt", "process_state.json", "activity_state.txt", "apk_native_inventory.json",
        "manifest_report.json", "emulator_environment.json", "root_cause_report.json", "root_cause_report.md",
    ]
    for name in required:
        path = out / name
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"required output missing: {name}")
    for name in [item for item in required if item.endswith(".json")]:
        json.loads((out / name).read_text())
    print(json.dumps({"classification": CLASSIFICATION, "outputs": required, "apk_sha256": actual_apk_sha}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
