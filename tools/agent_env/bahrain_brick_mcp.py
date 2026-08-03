#!/usr/bin/env python3
"""Least-privilege local MCP server for Bahrain Brick development.

The server exposes only typed Godot, Android, Blender, and evidence operations.
It never executes caller-provided shell text and never accepts signing material.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any
import zipfile

PROTOCOL_VERSION = "2025-06-18"
MAX_OUTPUT_CHARS = 40_000
APPROVED_OUTPUT_ROOTS = ("build", "release")
PROTECTED_SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    return parser.parse_args()


class ToolUnavailable(RuntimeError):
    pass


class ValidationError(RuntimeError):
    pass


class BahrainBrickMCP:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve(strict=True)
        self._busy = False

    def _resolve(self, raw: str, *, must_exist: bool = True) -> Path:
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = self.root / candidate
        candidate = candidate.resolve(strict=must_exist)
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValidationError(f"path escapes repository root: {raw}") from exc
        if candidate.suffix.lower() in PROTECTED_SECRET_SUFFIXES:
            raise ValidationError("secret/signing file types are not accepted")
        return candidate

    def _resolve_output(self, raw: str) -> Path:
        candidate = self._resolve(raw, must_exist=False)
        rel = candidate.relative_to(self.root)
        if not rel.parts or rel.parts[0] not in APPROVED_OUTPUT_ROOTS:
            raise ValidationError("output must be under build/ or release/")
        candidate.parent.mkdir(parents=True, exist_ok=True)
        return candidate

    @staticmethod
    def _bounded_timeout(value: Any, default: int, maximum: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = default
        if parsed < 1 or parsed > maximum:
            raise ValidationError(f"timeout_seconds must be between 1 and {maximum}")
        return parsed

    @staticmethod
    def _find_executable(env_name: str, candidates: tuple[str, ...]) -> str:
        configured = os.environ.get(env_name, "").strip()
        if configured:
            path = Path(configured).expanduser().resolve()
            if path.is_file() and os.access(path, os.X_OK):
                return str(path)
            raise ToolUnavailable(f"{env_name} does not point to an executable")
        for candidate in candidates:
            found = shutil.which(candidate)
            if found:
                return found
        raise ToolUnavailable(f"required executable unavailable: {', '.join(candidates)}")

    @staticmethod
    def _run(command: list[str], *, cwd: Path, timeout: int) -> dict[str, Any]:
        started = time.monotonic()
        try:
            process = subprocess.run(
                command,
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="replace",
                timeout=timeout,
                check=False,
                env=os.environ.copy(),
            )
            elapsed_ms = int((time.monotonic() - started) * 1000)
            stdout = process.stdout[-MAX_OUTPUT_CHARS:]
            stderr = process.stderr[-MAX_OUTPUT_CHARS:]
            return {
                "command": command,
                "exit_code": process.returncode,
                "elapsed_ms": elapsed_ms,
                "stdout": stdout,
                "stderr": stderr,
                "passed": process.returncode == 0,
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "command": command,
                "exit_code": 124,
                "elapsed_ms": int((time.monotonic() - started) * 1000),
                "stdout": (exc.stdout or "")[-MAX_OUTPUT_CHARS:] if isinstance(exc.stdout, str) else "",
                "stderr": (exc.stderr or "")[-MAX_OUTPUT_CHARS:] if isinstance(exc.stderr, str) else "",
                "passed": False,
                "timed_out": True,
            }

    def _git_sha(self) -> str | None:
        git = shutil.which("git")
        if not git:
            return None
        result = self._run([git, "rev-parse", "HEAD"], cwd=self.root, timeout=10)
        if result["passed"]:
            return str(result["stdout"]).strip()
        return None

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "godot_validate_project",
                "description": "Run a fixed headless Godot 4.3 import and project validation command inside the repository.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string", "default": "."},
                        "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 1800, "default": 900},
                    },
                    "additionalProperties": False,
                },
            },
            {
                "name": "godot_export_android_debug",
                "description": "Export an Android debug APK using a fixed Godot command. Output is restricted to build/ or release/.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string", "default": "."},
                        "preset": {"type": "string", "default": "Android", "maxLength": 80},
                        "output_path": {"type": "string", "default": "build/agent-export/bahrain-brick-debug.apk"},
                        "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 3600, "default": 1800},
                    },
                    "additionalProperties": False,
                },
            },
            {
                "name": "android_adb_smoke_test",
                "description": "Install and launch an approved debug APK on an explicitly selected ADB device and collect bounded diagnostics. Never uninstalls or clears data.",
                "inputSchema": {
                    "type": "object",
                    "required": ["apk_path", "package_name", "device_serial"],
                    "properties": {
                        "apk_path": {"type": "string"},
                        "package_name": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_.]+$"},
                        "device_serial": {"type": "string", "minLength": 1, "maxLength": 160},
                        "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 900, "default": 300},
                    },
                    "additionalProperties": False,
                },
            },
            {
                "name": "blender_validate_asset",
                "description": "Validate a repository Blender/glTF asset with a fixed background-mode validator and mobile triangle budget.",
                "inputSchema": {
                    "type": "object",
                    "required": ["asset_path"],
                    "properties": {
                        "asset_path": {"type": "string"},
                        "triangle_budget": {"type": "integer", "minimum": 1, "maximum": 5000000, "default": 100000},
                        "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 1800, "default": 600},
                    },
                    "additionalProperties": False,
                },
            },
            {
                "name": "collect_build_evidence",
                "description": "Collect SHA-256, size, ZIP integrity, source commit, and available Android metadata for an existing artifact under build/ or release/.",
                "inputSchema": {
                    "type": "object",
                    "required": ["artifact_path"],
                    "properties": {
                        "artifact_path": {"type": "string"},
                        "output_path": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
            },
        ]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if self._busy:
            raise ValidationError("server is busy; concurrent tool execution is disabled")
        self._busy = True
        try:
            handlers = {
                "godot_validate_project": self.godot_validate_project,
                "godot_export_android_debug": self.godot_export_android_debug,
                "android_adb_smoke_test": self.android_adb_smoke_test,
                "blender_validate_asset": self.blender_validate_asset,
                "collect_build_evidence": self.collect_build_evidence,
            }
            if name not in handlers:
                raise ValidationError(f"unknown tool: {name}")
            return handlers[name](arguments)
        finally:
            self._busy = False

    def godot_validate_project(self, args: dict[str, Any]) -> dict[str, Any]:
        project = self._resolve(str(args.get("project_path", ".")))
        if not project.is_dir() or not (project / "project.godot").is_file():
            raise ValidationError("project_path must contain project.godot")
        godot = self._find_executable("BAHRAIN_BRICK_GODOT", ("godot4", "godot"))
        timeout = self._bounded_timeout(args.get("timeout_seconds"), 900, 1800)
        command = [godot, "--headless", "--path", str(project), "--editor", "--import", "--quit", "--verbose"]
        result = self._run(command, cwd=project, timeout=timeout)
        combined = f"{result.get('stdout', '')}\n{result.get('stderr', '')}"
        signatures = {
            "script_error": len(re.findall(r"SCRIPT ERROR|Parse Error|Parser Error", combined, re.I)),
            "missing_resource": len(re.findall(r"Failed to load|No loader found|Can't open", combined, re.I)),
            "fatal": len(re.findall(r"\bFATAL\b|Fatal signal|crash", combined, re.I)),
        }
        result.update({"tool": "godot_validate_project", "project": str(project.relative_to(self.root)), "error_signatures": signatures})
        result["passed"] = bool(result["passed"] and sum(signatures.values()) == 0)
        return result

    def godot_export_android_debug(self, args: dict[str, Any]) -> dict[str, Any]:
        project = self._resolve(str(args.get("project_path", ".")))
        if not project.is_dir() or not (project / "project.godot").is_file():
            raise ValidationError("project_path must contain project.godot")
        preset = str(args.get("preset", "Android"))
        if not re.fullmatch(r"[A-Za-z0-9 _.-]{1,80}", preset):
            raise ValidationError("preset contains unsupported characters")
        output = self._resolve_output(str(args.get("output_path", "build/agent-export/bahrain-brick-debug.apk")))
        if output.suffix.lower() != ".apk":
            raise ValidationError("debug export output must end in .apk")
        godot = self._find_executable("BAHRAIN_BRICK_GODOT", ("godot4", "godot"))
        timeout = self._bounded_timeout(args.get("timeout_seconds"), 1800, 3600)
        command = [godot, "--headless", "--path", str(project), "--verbose", "--export-debug", preset, str(output)]
        result = self._run(command, cwd=project, timeout=timeout)
        result.update({"tool": "godot_export_android_debug", "artifact": str(output.relative_to(self.root)), "artifact_exists": output.is_file(), "artifact_bytes": output.stat().st_size if output.is_file() else 0})
        result["passed"] = bool(result["passed"] and output.is_file() and output.stat().st_size > 0)
        return result

    def android_adb_smoke_test(self, args: dict[str, Any]) -> dict[str, Any]:
        apk = self._resolve(str(args.get("apk_path", "")))
        if apk.suffix.lower() != ".apk" or not apk.is_file():
            raise ValidationError("apk_path must reference an existing repository APK")
        rel = apk.relative_to(self.root)
        if not rel.parts or rel.parts[0] not in APPROVED_OUTPUT_ROOTS:
            raise ValidationError("ADB APK must be under build/ or release/")
        package = str(args.get("package_name", ""))
        serial = str(args.get("device_serial", ""))
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.]+", package):
            raise ValidationError("invalid package_name")
        if not serial or any(ch in serial for ch in "\r\n\x00"):
            raise ValidationError("invalid device_serial")
        adb = self._find_executable("BAHRAIN_BRICK_ADB", ("adb",))
        timeout = self._bounded_timeout(args.get("timeout_seconds"), 300, 900)
        steps: list[dict[str, Any]] = []
        commands = [
            [adb, "-s", serial, "get-state"],
            [adb, "-s", serial, "install", "-r", str(apk)],
            [adb, "-s", serial, "shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"],
            [adb, "-s", serial, "shell", "pidof", package],
            [adb, "-s", serial, "shell", "dumpsys", "meminfo", package],
        ]
        for command in commands:
            step = self._run(command, cwd=self.root, timeout=timeout)
            steps.append(step)
            if not step["passed"]:
                break
        return {
            "tool": "android_adb_smoke_test",
            "apk": str(rel),
            "package": package,
            "device_serial": serial,
            "steps": steps,
            "passed": len(steps) == len(commands) and all(step["passed"] for step in steps),
            "destructive_actions_performed": False,
        }

    def blender_validate_asset(self, args: dict[str, Any]) -> dict[str, Any]:
        asset = self._resolve(str(args.get("asset_path", "")))
        if asset.suffix.lower() not in {".blend", ".glb", ".gltf"}:
            raise ValidationError("asset_path must be .blend, .glb, or .gltf")
        rel = asset.relative_to(self.root)
        if not rel.parts or rel.parts[0] not in {"assets", "asset_lab"}:
            raise ValidationError("asset must be under assets/ or asset_lab/")
        try:
            budget = int(args.get("triangle_budget", 100000))
        except (TypeError, ValueError) as exc:
            raise ValidationError("triangle_budget must be an integer") from exc
        if budget < 1 or budget > 5_000_000:
            raise ValidationError("triangle_budget outside supported range")
        timeout = self._bounded_timeout(args.get("timeout_seconds"), 600, 1800)
        blender = self._find_executable("BAHRAIN_BRICK_BLENDER", ("blender",))
        validator = self._resolve("tools/agent_env/blender_asset_validator.py")
        digest = hashlib.sha256(str(rel).encode()).hexdigest()[:16]
        report = self._resolve_output(f"build/agent-evidence/blender/{digest}.json")
        command = [
            blender, "--background", "--factory-startup", "--python", str(validator), "--",
            "--root", str(self.root), "--asset", str(asset), "--triangle-budget", str(budget), "--output", str(report),
        ]
        result = self._run(command, cwd=self.root, timeout=timeout)
        payload: dict[str, Any] = {"tool": "blender_validate_asset", "asset": str(rel), "report": str(report.relative_to(self.root)), **result}
        if report.is_file():
            try:
                payload["validation"] = json.loads(report.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                payload["report_error"] = str(exc)
        payload["passed"] = bool(result["passed"] and payload.get("validation", {}).get("passed") is True)
        return payload

    def collect_build_evidence(self, args: dict[str, Any]) -> dict[str, Any]:
        artifact = self._resolve(str(args.get("artifact_path", "")))
        if not artifact.is_file():
            raise ValidationError("artifact_path must reference an existing file")
        rel = artifact.relative_to(self.root)
        if not rel.parts or rel.parts[0] not in APPROVED_OUTPUT_ROOTS:
            raise ValidationError("artifact must be under build/ or release/")
        output_arg = args.get("output_path")
        if output_arg:
            output = self._resolve_output(str(output_arg))
        else:
            output = self._resolve_output(f"build/agent-evidence/{artifact.name}.evidence.json")
        digest = hashlib.sha256()
        with artifact.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        evidence: dict[str, Any] = {
            "schema_version": 1,
            "artifact": str(rel),
            "bytes": artifact.stat().st_size,
            "sha256": digest.hexdigest(),
            "source_commit": self._git_sha(),
            "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "zip_integrity": None,
            "zip_bad_entry": None,
            "android": {},
            "signing_material_accessed": False,
        }
        if zipfile.is_zipfile(artifact):
            with zipfile.ZipFile(artifact) as archive:
                bad = archive.testzip()
                evidence["zip_integrity"] = bad is None
                evidence["zip_bad_entry"] = bad
                names = archive.namelist()
                evidence["zip_entry_count"] = len(names)
                evidence["contains_project_binary"] = "assets/project.binary" in names
                if "assets/project.binary" in names:
                    project = archive.read("assets/project.binary")
                    evidence["production_splash_scene_occurrences"] = project.count(b"res://scenes/splash_screen.tscn")
                    evidence["diagnostic_scene_present"] = b"res://tests/graphics/r1_renderer_runtime_debug.tscn" in project
        aapt = self._optional_android_tool("aapt")
        if aapt and artifact.suffix.lower() == ".apk":
            evidence["android"]["aapt_badging"] = self._run([aapt, "dump", "badging", str(artifact)], cwd=self.root, timeout=60)
        apksigner = self._optional_android_tool("apksigner")
        if apksigner and artifact.suffix.lower() == ".apk":
            evidence["android"]["signature_verification"] = self._run([apksigner, "verify", "--verbose", "--print-certs", str(artifact)], cwd=self.root, timeout=60)
        output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {"tool": "collect_build_evidence", "passed": evidence["zip_integrity"] is not False, "evidence_path": str(output.relative_to(self.root)), "evidence": evidence}

    @staticmethod
    def _optional_android_tool(name: str) -> str | None:
        found = shutil.which(name)
        if found:
            return found
        sdk = os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME")
        if sdk:
            build_tools = Path(sdk) / "build-tools"
            if build_tools.is_dir():
                candidates = sorted(build_tools.glob(f"*/{name}"), reverse=True)
                if candidates:
                    return str(candidates[0])
        return None


def tool_result(payload: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(payload, indent=2, sort_keys=True)}],
        "isError": is_error,
        "structuredContent": payload,
    }


def serve(server: BahrainBrickMCP) -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        request_id: Any = None
        try:
            message = json.loads(line)
            request_id = message.get("id")
            method = message.get("method")
            params = message.get("params") or {}
            if method == "initialize":
                result = {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "bahrain-brick-local", "version": "1.0.0"},
                    "instructions": "Typed local-only Bahrain Brick validation tools. No arbitrary shell, secrets, signing, remote writes, or destructive database operations.",
                }
            elif method in {"notifications/initialized", "notifications/cancelled"}:
                continue
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": server.list_tools()}
            elif method == "tools/call":
                name = str(params.get("name", ""))
                arguments = params.get("arguments") or {}
                if not isinstance(arguments, dict):
                    raise ValidationError("tool arguments must be an object")
                try:
                    result = tool_result(server.call_tool(name, arguments))
                except ToolUnavailable as exc:
                    result = tool_result({"tool": name, "status": "unavailable", "reason": str(exc), "passed": False}, is_error=False)
                except (ValidationError, OSError, subprocess.SubprocessError, ValueError) as exc:
                    result = tool_result({"tool": name, "status": "failed", "reason": str(exc), "passed": False}, is_error=True)
            else:
                raise ValidationError(f"unsupported method: {method}")
            response = {"jsonrpc": "2.0", "id": request_id, "result": result}
        except Exception as exc:
            response = {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32603, "message": str(exc)}}
        sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
        sys.stdout.flush()
    return 0


def main() -> int:
    args = parse_args()
    root = Path(args.root)
    if not root.is_dir():
        print("repository root is not a directory", file=sys.stderr)
        return 2
    return serve(BahrainBrickMCP(root))


if __name__ == "__main__":
    raise SystemExit(main())
