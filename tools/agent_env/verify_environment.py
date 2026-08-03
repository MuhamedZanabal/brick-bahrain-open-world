#!/usr/bin/env python3
"""Validate and smoke-test the Bahrain Brick controlled development environment."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Iterable
import zipfile

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_SKILLS = {
    "android-build-runtime-qa",
    "bahrain-world-fidelity",
    "blender-brick-asset-validation",
    "godot-gameplay-engineering",
    "multiplayer-authority-replication",
    "release-qualification",
}
EXPECTED_AGENTS = {
    "android-performance-qa",
    "godot-gameplay-engineer",
    "multiplayer-network-engineer",
    "release-auditor",
    "technical-artist",
}
EXPECTED_MCP_TOOLS = [
    "godot_validate_project",
    "godot_export_android_debug",
    "android_adb_smoke_test",
    "blender_validate_asset",
    "collect_build_evidence",
]
CONTROL_FILES = [
    "CLAUDE.md",
    ".claude/settings.json",
    ".mcp.json",
    ".claude/hooks/bahrain_brick_hook.py",
    "tools/agent_env/bahrain_brick_mcp.py",
    "tools/agent_env/blender_asset_validator.py",
    "tools/agent_env/verify_environment.py",
    "tests/test_controlled_agent_environment.py",
]
SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "openai_key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b"),
    "anthropic_key": re.compile(r"\bsk-ant-[A-Za-z0-9_-]{24,}\b"),
    "generic_secret_assignment": re.compile(
        r"(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[:=]\s*['\"](?!android['\"])[A-Za-z0-9+/=_-]{20,}['\"]"
    ),
}


@dataclass
class CommandResult:
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    elapsed_ms: int
    status: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout[-20000:],
            "stderr": self.stderr[-20000:],
            "elapsed_ms": self.elapsed_ms,
            "status": self.status,
        }


def run(command: list[str], *, cwd: Path = ROOT, timeout: int = 900) -> CommandResult:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
        )
        return CommandResult(
            command,
            result.returncode,
            result.stdout,
            result.stderr,
            int((time.monotonic() - started) * 1000),
            "passed" if result.returncode == 0 else "failed",
        )
    except FileNotFoundError as exc:
        return CommandResult(command, 127, "", str(exc), int((time.monotonic() - started) * 1000), "unavailable")
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            command,
            124,
            exc.stdout or "" if isinstance(exc.stdout, str) else "",
            exc.stderr or "" if isinstance(exc.stderr, str) else "",
            int((time.monotonic() - started) * 1000),
            "failed",
        )


def output(payload: dict[str, Any], *, exit_code: int = 0) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return exit_code


def parse_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"missing YAML frontmatter: {path.relative_to(ROOT)}")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError(f"unterminated YAML frontmatter: {path.relative_to(ROOT)}")
    lines = text[4:end].splitlines()
    data: dict[str, Any] = {}
    current_list: str | None = None
    for raw in lines:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith("  - ") and current_list:
            data.setdefault(current_list, []).append(raw[4:].strip().strip('"'))
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):(?:\s*(.*))?$", raw)
        if not match:
            raise ValueError(f"unsupported frontmatter syntax in {path.relative_to(ROOT)}: {raw}")
        key, value = match.group(1), (match.group(2) or "").strip()
        if value:
            data[key] = value.strip('"')
            current_list = None
        else:
            data[key] = []
            current_list = key
    return data


def control_file_paths() -> list[Path]:
    paths = [ROOT / value for value in CONTROL_FILES]
    paths.extend(sorted((ROOT / ".claude/skills").glob("*/SKILL.md")))
    paths.extend(sorted((ROOT / ".claude/agents").glob("*.md")))
    return paths


def scan_secrets(paths: Iterable[Path]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path in paths:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for name, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append({"file": str(path.relative_to(ROOT)), "line": str(line), "pattern": name})
    return findings


def validate_config() -> tuple[dict[str, Any], bool]:
    issues: list[str] = []
    for raw in CONTROL_FILES:
        if not (ROOT / raw).is_file():
            issues.append(f"missing required file: {raw}")

    try:
        settings = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
    except Exception as exc:
        settings = {}
        issues.append(f"invalid .claude/settings.json: {exc}")
    try:
        mcp = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    except Exception as exc:
        mcp = {}
        issues.append(f"invalid .mcp.json: {exc}")

    skill_paths = sorted((ROOT / ".claude/skills").glob("*/SKILL.md"))
    agent_paths = sorted((ROOT / ".claude/agents").glob("*.md"))
    skills: dict[str, dict[str, Any]] = {}
    agents: dict[str, dict[str, Any]] = {}
    for path in skill_paths:
        try:
            fm = parse_frontmatter(path)
            name = str(fm.get("name", ""))
            skills[name] = fm
            if not name or not fm.get("description"):
                issues.append(f"skill frontmatter missing name/description: {path.relative_to(ROOT)}")
        except Exception as exc:
            issues.append(str(exc))
    for path in agent_paths:
        try:
            fm = parse_frontmatter(path)
            name = str(fm.get("name", ""))
            agents[name] = fm
            for required in ("name", "description", "model", "isolation", "tools"):
                if required not in fm or not fm[required]:
                    issues.append(f"agent {path.name} missing {required}")
            if fm.get("isolation") != "worktree":
                issues.append(f"agent {path.name} must use worktree isolation")
        except Exception as exc:
            issues.append(str(exc))
    if set(skills) != EXPECTED_SKILLS:
        issues.append(f"skill inventory mismatch: {sorted(skills)}")
    if set(agents) != EXPECTED_AGENTS:
        issues.append(f"agent inventory mismatch: {sorted(agents)}")

    servers = mcp.get("mcpServers", {}) if isinstance(mcp, dict) else {}
    if set(servers) != {"bahrain-brick-local"}:
        issues.append(f"MCP server inventory must be exactly bahrain-brick-local: {sorted(servers)}")
    server_cfg = servers.get("bahrain-brick-local", {}) if isinstance(servers, dict) else {}
    if server_cfg.get("command") != "python3":
        issues.append("local MCP command must be python3")
    args = server_cfg.get("args", [])
    if not isinstance(args, list) or not any("bahrain_brick_mcp.py" in str(value) for value in args):
        issues.append("local MCP must launch tools/agent_env/bahrain_brick_mcp.py")
    serialized_mcp = json.dumps(mcp).lower()
    for forbidden in ("http://", "https://", "token", "password", "keystore", "private_key"):
        if forbidden in serialized_mcp:
            issues.append(f"forbidden MCP configuration content: {forbidden}")

    hooks = settings.get("hooks", {}) if isinstance(settings, dict) else {}
    if set(hooks) != {"SessionStart", "PreToolUse", "PostToolUse", "Stop"}:
        issues.append(f"hook event inventory mismatch: {sorted(hooks)}")
    plugins = settings.get("enabledPlugins", None) if isinstance(settings, dict) else None
    if plugins != {}:
        issues.append("project community plugins must remain disabled")
    deny = settings.get("permissions", {}).get("deny", []) if isinstance(settings, dict) else []
    for required in ("Bash(git push --force*)", "Bash(git reset --hard*)", "Bash(rm -rf *)", "Read(./**/*.keystore)"):
        if required not in deny:
            issues.append(f"required deny rule missing: {required}")

    findings = scan_secrets(control_file_paths())
    if findings:
        issues.append(f"secret scan found {len(findings)} finding(s)")

    inventory = {
        "skills": sorted(skills),
        "agents": sorted(agents),
        "hooks": sorted(hooks),
        "mcp_servers": sorted(servers),
        "plugins": sorted(plugins) if isinstance(plugins, dict) else None,
        "secret_findings": findings,
        "issues": issues,
    }
    return inventory, not issues


class MCPClient:
    def __init__(self, root: Path) -> None:
        self.process = subprocess.Popen(
            [sys.executable, str(root / "tools/agent_env/bahrain_brick_mcp.py"), "--root", str(root)],
            cwd=root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            bufsize=1,
        )
        self.next_id = 1

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        assert self.process.stdin is not None and self.process.stdout is not None
        request_id = self.next_id
        self.next_id += 1
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            payload["params"] = params
        self.process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise RuntimeError(f"MCP server terminated without response: {stderr}")
        response = json.loads(line)
        if response.get("id") != request_id:
            raise RuntimeError("MCP response ID mismatch")
        return response

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        assert self.process.stdin is not None
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        self.process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        self.process.stdin.flush()

    def close(self) -> None:
        if self.process.stdin:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)


def extract_tool_payload(response: dict[str, Any]) -> dict[str, Any]:
    result = response.get("result", {})
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured
    content = result.get("content", [])
    if content and isinstance(content[0], dict):
        return json.loads(content[0].get("text", "{}"))
    return {}


def mcp_smoke() -> tuple[dict[str, Any], bool]:
    build = ROOT / "build/agent-env-smoke"
    build.mkdir(parents=True, exist_ok=True)
    fixture_project = build / "godot-project"
    fixture_project.mkdir(parents=True, exist_ok=True)
    (fixture_project / "project.godot").write_text("config_version=5\n[application]\nconfig/name=\"MCP Smoke\"\n", encoding="utf-8")
    artifact = build / "fixture.apk"
    with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("assets/project.binary", b"res://scenes/splash_screen.tscn")
        archive.writestr("AndroidManifest.xml", b"fixture")
    asset_fixture = ROOT / "asset_lab/agent_env_smoke_fixture.gltf"
    asset_fixture.parent.mkdir(parents=True, exist_ok=True)
    asset_fixture.write_text('{"asset":{"version":"2.0"},"scenes":[{"nodes":[]}],"scene":0}\n', encoding="utf-8")

    client = MCPClient(ROOT)
    report: dict[str, Any] = {"calls": {}}
    success = True
    try:
        init = client.request(
            "initialize",
            {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "bahrain-brick-verifier", "version": "1.0.0"}},
        )
        report["initialize"] = init.get("result", {})
        client.notify("notifications/initialized")
        listed = client.request("tools/list", {})
        tools = [tool.get("name") for tool in listed.get("result", {}).get("tools", [])]
        report["listed_tools"] = tools
        if tools != EXPECTED_MCP_TOOLS:
            success = False
        calls = [
            ("godot_validate_project", {"project_path": str(fixture_project.relative_to(ROOT)), "timeout_seconds": 30}),
            ("blender_validate_asset", {"asset_path": str(asset_fixture.relative_to(ROOT)), "triangle_budget": 1000, "timeout_seconds": 30}),
            ("collect_build_evidence", {"artifact_path": str(artifact.relative_to(ROOT)), "output_path": "build/agent-env-smoke/fixture-evidence.json"}),
        ]
        for name, arguments in calls:
            response = client.request("tools/call", {"name": name, "arguments": arguments})
            payload = extract_tool_payload(response)
            report["calls"][name] = payload
            if name == "collect_build_evidence" and payload.get("passed") is not True:
                success = False
            if name in {"godot_validate_project", "blender_validate_asset"}:
                status = payload.get("status")
                if not (payload.get("passed") is True or status == "unavailable"):
                    success = False
    except Exception as exc:
        report["protocol_error"] = str(exc)
        success = False
    finally:
        client.close()
        try:
            asset_fixture.unlink()
        except FileNotFoundError:
            pass
    return report, success


def baseline() -> tuple[dict[str, Any], bool, bool]:
    candidates = [
        "tests/test_karak_delivery_mission_contract.py",
        "tests/test_manama_souq_layout_contract.py",
        "tests/test_manama_souq_slice_contract.py",
        "tests/test_souq_population_contract.py",
        "tests/graphics/test_r1_playable_apk_export.py",
    ]
    present = [value for value in candidates if (ROOT / value).is_file()]
    if not present:
        return {"status": "unavailable", "reason": "representative repository tests are not present in this filesystem checkout", "tests": []}, False, True
    results = []
    passed = True
    for value in present:
        command = [sys.executable, "-m", "unittest", value, "-v"] if value.startswith("tests/graphics/") else [sys.executable, value]
        result = run(command, timeout=1200)
        results.append(result.as_dict())
        passed = passed and result.status == "passed"
    return {"status": "passed" if passed else "failed", "tests": results}, passed, False


def locate_godot() -> str | None:
    configured = os.environ.get("BAHRAIN_BRICK_GODOT")
    if configured and Path(configured).is_file():
        return str(Path(configured).resolve())
    return shutil.which("godot4") or shutil.which("godot")


def godot_validation() -> tuple[dict[str, Any], bool, bool]:
    if not (ROOT / "project.godot").is_file():
        return {"status": "unavailable", "reason": "project.godot is absent from the active filesystem checkout"}, False, True
    godot = locate_godot()
    if not godot:
        return {"status": "unavailable", "reason": "Godot executable is not installed or BAHRAIN_BRICK_GODOT is unset"}, False, True
    version = run([godot, "--version"], timeout=30)
    validation = run([godot, "--headless", "--path", str(ROOT), "--editor", "--import", "--quit", "--verbose"], timeout=1200)
    expected = "4.3.stable.official.77dcf97d8"
    version_ok = version.status == "passed" and version.stdout.strip() == expected
    passed = version_ok and validation.status == "passed"
    return {"status": "passed" if passed else "failed", "expected_version": expected, "version": version.as_dict(), "validation": validation.as_dict()}, passed, False


def relevant(paths: list[str]) -> tuple[dict[str, Any], bool]:
    commands: list[list[str]] = [[sys.executable, "tests/test_controlled_agent_environment.py"]]
    if any(path.endswith(".gd") for path in paths):
        for candidate in ("tests/test_karak_delivery_mission_contract.py", "tests/test_manama_souq_slice_contract.py"):
            if (ROOT / candidate).is_file():
                commands.append([sys.executable, candidate])
    if any(path.startswith((".claude/", "tools/agent_env/", ".mcp.json", "CLAUDE.md")) for path in paths):
        commands.append([sys.executable, "tools/agent_env/verify_environment.py", "config"])
    results = [run(command, timeout=1200).as_dict() for command in commands]
    return {"paths": paths, "results": results}, all(result["status"] == "passed" for result in results)


def newest_apk_evidence() -> tuple[dict[str, Any], bool, bool]:
    apks = sorted(
        [*ROOT.glob("build/**/*.apk"), *ROOT.glob("release/**/*.apk")],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not apks:
        return {"status": "unavailable", "reason": "no APK under build/ or release/"}, False, True
    target = apks[0]
    client = MCPClient(ROOT)
    try:
        client.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "evidence-hook", "version": "1"}})
        client.notify("notifications/initialized")
        response = client.request("tools/call", {"name": "collect_build_evidence", "arguments": {"artifact_path": str(target.relative_to(ROOT))}})
        payload = extract_tool_payload(response)
        return payload, payload.get("passed") is True, False
    finally:
        client.close()


def completion() -> tuple[dict[str, Any], bool]:
    config_report, config_ok = validate_config()
    test = run([sys.executable, "tests/test_controlled_agent_environment.py"], timeout=300)
    payload = {"config": config_report, "static_test": test.as_dict(), "passed": config_ok and test.status == "passed"}
    return payload, bool(payload["passed"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["config", "mcp-smoke", "baseline", "godot", "relevant", "changed", "completion", "evidence-newest", "inventory"])
    parser.add_argument("--path", action="append", default=[])
    args = parser.parse_args()

    if args.command in {"config", "inventory"}:
        report, passed = validate_config()
        return output({"status": "passed" if passed else "failed", **report}, exit_code=0 if passed else 1)
    if args.command == "mcp-smoke":
        report, passed = mcp_smoke()
        return output({"status": "passed" if passed else "failed", **report}, exit_code=0 if passed else 1)
    if args.command == "baseline":
        report, passed, unavailable = baseline()
        return output(report, exit_code=3 if unavailable else (0 if passed else 1))
    if args.command == "godot":
        report, passed, unavailable = godot_validation()
        return output(report, exit_code=3 if unavailable else (0 if passed else 1))
    if args.command in {"relevant", "changed"}:
        paths = list(args.path)
        if args.command == "changed" and not paths:
            git = shutil.which("git")
            if git and (ROOT / ".git").exists():
                result = run([git, "diff", "--name-only", "HEAD"], timeout=30)
                paths = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        report, passed = relevant(paths)
        return output({"status": "passed" if passed else "failed", **report}, exit_code=0 if passed else 1)
    if args.command == "completion":
        report, passed = completion()
        return output({"status": "passed" if passed else "failed", **report}, exit_code=0 if passed else 1)
    if args.command == "evidence-newest":
        report, passed, unavailable = newest_apk_evidence()
        return output(report, exit_code=3 if unavailable else (0 if passed else 1))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
