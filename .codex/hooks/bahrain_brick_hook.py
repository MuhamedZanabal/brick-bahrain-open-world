#!/usr/bin/env python3
"""Codex hook dispatcher for the Bahrain Brick project."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

ROOT = Path(os.environ.get("CODEX_PROJECT_ROOT", Path(__file__).resolve().parents[2])).resolve()
VERIFIER = ROOT / "tools/agent_env/verify_environment.py"

DESTRUCTIVE_COMMAND_PATTERNS = [
    (re.compile(r"(?:^|[;&|]\s*)git\s+push\s+[^\n]*--force(?:-with-lease)?\b", re.I), "force-push is prohibited"),
    (re.compile(r"(?:^|[;&|]\s*)git\s+reset\s+--hard\b", re.I), "git reset --hard is prohibited"),
    (re.compile(r"(?:^|[;&|]\s*)git\s+clean\s+[^\n]*-[^\n]*f", re.I), "forced git clean is prohibited"),
    (re.compile(r"(?:^|[;&|]\s*)git\s+branch\s+-D\b", re.I), "forced branch deletion is prohibited"),
    (re.compile(r"(?:^|[;&|]\s*)git\s+tag\s+-d\b", re.I), "tag deletion is prohibited"),
    (re.compile(r"(?:^|[;&|]\s*)rm\s+-[^\n]*r[^\n]*f\b", re.I), "recursive forced deletion is prohibited"),
    (re.compile(r"\b(?:DROP\s+(?:DATABASE|SCHEMA|TABLE)|TRUNCATE\s+TABLE)\b", re.I), "destructive database operation is prohibited"),
    (re.compile(r"\bgh\s+release\s+delete\b", re.I), "release deletion is prohibited"),
    (re.compile(r"\badb\s+(?:-s\s+\S+\s+)?(?:uninstall|shell\s+pm\s+clear)\b", re.I), "device uninstall or data clearing is prohibited"),
]
REMOTE_MCP_WRITE_PATTERN = re.compile(
    r"^mcp__(?!bahrain-brick-local__).*__(?:.*(?:create|update|delete|write|deploy|release|execute|sql|mutate|publish|merge).*)$",
    re.I,
)
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b"),
]
SENSITIVE_PATH = re.compile(r"(?:^|/)(?:\.env(?:\..*)?|secrets?)(?:/|$)|\.(?:pem|key|p12|pfx|jks|keystore)$", re.I)
LOCAL_MCP_TOOLS = {
    "mcp__bahrain-brick-local__godot_validate_project",
    "mcp__bahrain-brick-local__godot_export_android_debug",
    "mcp__bahrain-brick-local__android_adb_smoke_test",
    "mcp__bahrain-brick-local__blender_validate_asset",
    "mcp__bahrain-brick-local__collect_build_evidence",
}


def emit(payload: dict[str, Any]) -> int:
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    return 0


def deny(reason: str) -> int:
    return emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}})


def run_verifier(arguments: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VERIFIER), *arguments], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace",
        timeout=timeout, check=False,
    )


def command_text(tool_input: dict[str, Any]) -> str:
    for key in ("command", "cmd", "script"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    return ""


def extract_edited_paths(tool_name: str, tool_input: dict[str, Any], tool_response: Any) -> list[str]:
    paths: list[str] = []
    for source in (tool_input, tool_response if isinstance(tool_response, dict) else {}):
        for key in ("file_path", "path", "filePath"):
            value = source.get(key)
            if isinstance(value, str) and value:
                paths.append(value)
    if tool_name == "apply_patch":
        patch = command_text(tool_input)
        for match in re.finditer(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", patch, re.MULTILINE):
            paths.append(match.group(1).strip())
    # Preserve order while avoiding duplicate verifier runs.
    return list(dict.fromkeys(paths))


def pre_tool_use(data: dict[str, Any]) -> int:
    tool_name = str(data.get("tool_name", ""))
    tool_input = data.get("tool_input") or {}
    serialized = json.dumps(tool_input, sort_keys=True)

    if REMOTE_MCP_WRITE_PATTERN.search(tool_name):
        return deny("Remote or community MCP mutation tools require explicit review and are blocked by project policy.")
    if tool_name in {"Bash", "shell", "shell_command"}:
        command = command_text(tool_input)
        for pattern, reason in DESTRUCTIVE_COMMAND_PATTERNS:
            if pattern.search(command):
                return deny(reason)
        if SENSITIVE_PATH.search(command):
            return deny("Commands referencing credential, secret, or signing-key paths are blocked.")
    if tool_name.startswith("mcp__bahrain-brick-local__") and tool_name not in LOCAL_MCP_TOOLS:
        return deny("Unknown Bahrain Brick MCP tool is blocked.")
    if SENSITIVE_PATH.search(serialized):
        return deny("Tool input references a credential, secret, or signing-key path.")
    if any(pattern.search(serialized) for pattern in SECRET_PATTERNS):
        return deny("Tool input appears to contain credential material. Remove it and rotate the secret if real.")
    return 0


def validate_edited_path(raw_path: str) -> tuple[bool, str]:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    try:
        relative = str(candidate.resolve(strict=False).relative_to(ROOT))
    except ValueError:
        return False, "Edited path escapes repository root."
    if SENSITIVE_PATH.search(relative):
        return False, "A sensitive credential or signing path was edited; revert the change."
    result = run_verifier(["relevant", "--path", relative], timeout=900)
    if result.returncode != 0:
        reason = (result.stdout or result.stderr)[-9000:]
        return False, f"Post-edit verification failed for {relative}:\n{reason}"
    return True, f"Post-edit verification passed for {relative}."


def post_tool_use(data: dict[str, Any]) -> int:
    tool_name = str(data.get("tool_name", ""))
    tool_input = data.get("tool_input") or {}
    tool_response = data.get("tool_response")
    context: list[str] = []

    if tool_name in {"Edit", "Write", "apply_patch"}:
        for raw_path in extract_edited_paths(tool_name, tool_input, tool_response):
            ok, message = validate_edited_path(raw_path)
            if not ok:
                return emit({"decision": "block", "reason": message})
            context.append(message)

    if tool_name in {"Bash", "shell", "shell_command"}:
        command = command_text(tool_input)
        if "--export-debug" in command or "export_r1_playable_mobile_apk.sh" in command:
            evidence = run_verifier(["evidence-newest"], timeout=180)
            if evidence.returncode == 0:
                context.append("APK evidence was generated for the newest build artifact.")
            elif evidence.returncode == 3:
                context.append("An export command ran but no APK exists under build/ or release/; treat the export as unverified.")
            else:
                return emit({"decision": "block", "reason": f"APK evidence collection failed:\n{(evidence.stdout or evidence.stderr)[-9000:]}"})

    if tool_name == "mcp__bahrain-brick-local__godot_export_android_debug":
        evidence = run_verifier(["evidence-newest"], timeout=180)
        if evidence.returncode == 0:
            context.append("APK evidence was generated for the MCP export.")
        else:
            return emit({"decision": "block", "reason": f"MCP export lacks verified APK evidence:\n{(evidence.stdout or evidence.stderr)[-9000:]}"})

    if context:
        return emit({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": " ".join(context)}})
    return 0


def session_start() -> int:
    result = run_verifier(["inventory"], timeout=25)
    summary = (result.stdout or result.stderr)[-9000:]
    return emit({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": (
        "Bahrain Brick controlled Codex environment inventory follows. Resolve repository authority before editing; "
        "renderer selection and production fixes remain blocked by the current R1 checkpoint.\n" + summary
    )}})


def stop(data: dict[str, Any]) -> int:
    if data.get("stop_hook_active"):
        return 0
    result = run_verifier(["completion"], timeout=1190)
    if result.returncode != 0:
        reason = (result.stdout or result.stderr)[-9000:]
        return emit({"decision": "block", "reason": f"Completion verification failed. Correct the failures before stopping:\n{reason}"})
    return 0


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"invalid hook JSON: {exc}", file=sys.stderr)
        return 1
    event = str(data.get("hook_event_name", ""))
    try:
        if event == "SessionStart":
            return session_start()
        if event == "PreToolUse":
            return pre_tool_use(data)
        if event == "PostToolUse":
            return post_tool_use(data)
        if event == "Stop":
            return stop(data)
        return 0
    except subprocess.TimeoutExpired:
        if event == "PreToolUse":
            return deny("Security hook timed out; operation denied closed.")
        if event == "Stop":
            return emit({"decision": "block", "reason": "Completion hook timed out; do not claim completion."})
        return emit({"systemMessage": "Post-action verification timed out; verification remains incomplete."})
    except Exception as exc:
        if event == "PreToolUse":
            return deny(f"Security hook failed closed: {exc}")
        if event == "Stop":
            return emit({"decision": "block", "reason": f"Completion hook failed: {exc}"})
        print(f"hook error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
