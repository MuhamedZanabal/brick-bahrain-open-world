#!/usr/bin/env python3
"""Validate and smoke-test the Bahrain Brick controlled Codex environment."""
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
import tomllib
from typing import Any, Iterable
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SKILLS = {"android-build-runtime-qa", "bahrain-world-fidelity", "blender-brick-asset-validation", "godot-gameplay-engineering", "multiplayer-authority-replication", "release-qualification"}
AGENTS = {"android-performance-qa", "godot-gameplay-engineer", "multiplayer-network-engineer", "release-auditor", "technical-artist"}
TOOLS = ["godot_validate_project", "godot_export_android_debug", "android_adb_smoke_test", "blender_validate_asset", "collect_build_evidence"]
HOOKS = {"SessionStart", "PreToolUse", "PostToolUse", "Stop"}
LEGACY_PATHS = ["CL" + "AUDE.md", "." + "cl" + "aude", ".mcp" + ".json"]
FORBIDDEN_TERMS = ("cl" + "aude", "." + "cl" + "aude", "cl" + "aude_project_dir", ".mcp" + ".json")
CONTROL_FILES = ["AGENTS.md", ".codex/config.toml", ".codex/hooks.json", ".codex/hooks/bahrain_brick_hook.py", "tools/agent_env/bahrain_brick_mcp.py", "tools/agent_env/blender_asset_validator.py", "tools/agent_env/verify_environment.py", "tests/test_controlled_agent_environment.py", ".github/workflows/controlled-agent-environment.yml"]
SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "openai_key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b"),
}

@dataclass
class Result:
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    elapsed_ms: int
    status: str
    def as_dict(self) -> dict[str, Any]:
        return self.__dict__

def run(command: list[str], timeout: int = 900, cwd: Path = ROOT) -> Result:
    started = time.monotonic()
    try:
        p = subprocess.run(command, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace", timeout=timeout, check=False)
        return Result(command, p.returncode, p.stdout[-20000:], p.stderr[-20000:], int((time.monotonic()-started)*1000), "passed" if p.returncode == 0 else "failed")
    except FileNotFoundError as exc:
        return Result(command, 127, "", str(exc), int((time.monotonic()-started)*1000), "unavailable")
    except subprocess.TimeoutExpired as exc:
        return Result(command, 124, exc.stdout or "", exc.stderr or "", int((time.monotonic()-started)*1000), "failed")

def control_file_paths() -> list[Path]:
    paths = [ROOT / p for p in CONTROL_FILES]
    paths += sorted((ROOT / ".agents/skills").glob("*/SKILL.md"))
    paths += sorted((ROOT / ".codex/agents").glob("*.toml"))
    return paths

def scan_secrets(paths: Iterable[Path]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for name, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(text):
                findings.append({"file": str(path.relative_to(ROOT)), "line": text.count("\n", 0, match.start()) + 1, "pattern": name})
    return findings

def provider_reference_findings(paths: Iterable[Path]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for term in FORBIDDEN_TERMS:
            if term in text:
                findings.append({"file": str(path.relative_to(ROOT)), "term": term})
    return findings

def skill_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError(f"invalid frontmatter: {path}")
    block = text[4:text.index("\n---\n", 4)]
    data: dict[str, str] = {}
    for line in block.splitlines():
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data

def validate_config() -> tuple[dict[str, Any], bool]:
    issues: list[str] = []
    for rel in CONTROL_FILES:
        if not (ROOT / rel).is_file(): issues.append(f"missing required file: {rel}")
    for rel in LEGACY_PATHS:
        if (ROOT / rel).exists(): issues.append(f"legacy provider path must be absent: {rel}")
    try: config = tomllib.loads((ROOT / ".codex/config.toml").read_text())
    except Exception as exc: config = {}; issues.append(f"invalid config TOML: {exc}")
    try: hooks = json.loads((ROOT / ".codex/hooks.json").read_text())
    except Exception as exc: hooks = {}; issues.append(f"invalid hooks JSON: {exc}")
    ruby = shutil.which("ruby")
    if ruby:
        result = run([ruby, "-e", 'require "yaml"; v=YAML.load_file(ARGV[0]); abort "not mapping" unless v.is_a?(Hash)', str(ROOT / ".github/workflows/controlled-agent-environment.yml")], 30)
        if result.exit_code: issues.append(f"invalid workflow YAML: {result.stderr or result.stdout}")
    skills = {}
    for path in sorted((ROOT / ".agents/skills").glob("*/SKILL.md")):
        try:
            data = skill_frontmatter(path)
            if set(data) != {"name", "description"}: issues.append(f"invalid skill keys: {path.relative_to(ROOT)}")
            skills[path.parent.name] = data
        except Exception as exc: issues.append(str(exc))
    agents = {}
    for path in sorted((ROOT / ".codex/agents").glob("*.toml")):
        try:
            data = tomllib.loads(path.read_text())
            if not all(data.get(k) for k in ("name", "description", "developer_instructions")): issues.append(f"missing agent fields: {path.relative_to(ROOT)}")
            if "model" in data: issues.append(f"agent pins model: {path.relative_to(ROOT)}")
            agents[path.stem] = data
        except Exception as exc: issues.append(f"invalid agent TOML {path.relative_to(ROOT)}: {exc}")
    if set(skills) != SKILLS: issues.append(f"skill inventory mismatch: {sorted(skills)}")
    if set(agents) != AGENTS: issues.append(f"agent inventory mismatch: {sorted(agents)}")
    if config.get("approval_policy") != "on-request": issues.append("approval_policy must be on-request")
    if config.get("sandbox_mode") != "workspace-write": issues.append("sandbox_mode must be workspace-write")
    if config.get("sandbox_workspace_write", {}).get("network_access") is not False: issues.append("sandbox network must be disabled")
    if config.get("features", {}).get("hooks") is not True: issues.append("hooks feature must be enabled")
    servers = config.get("mcp_servers", {})
    if set(servers) != {"bahrain-brick-local"}: issues.append(f"MCP inventory mismatch: {sorted(servers)}")
    server = servers.get("bahrain-brick-local", {})
    if server.get("enabled_tools") != TOOLS: issues.append("MCP enabled tools mismatch")
    if server.get("supports_parallel_tool_calls") is not False: issues.append("parallel MCP calls must be disabled")
    if set(hooks.get("hooks", {})) != HOOKS: issues.append("hook inventory mismatch")
    secrets = scan_secrets(control_file_paths())
    refs = provider_reference_findings(control_file_paths())
    if secrets: issues.append(f"secret findings: {len(secrets)}")
    if refs: issues.append(f"legacy provider reference findings: {len(refs)}")
    report = {"skills": sorted(skills), "agents": sorted(agents), "hooks": sorted(hooks.get("hooks", {})), "mcp_servers": sorted(servers), "mcp_tools": server.get("enabled_tools", []), "plugins": [], "secret_findings": secrets, "legacy_provider_findings": refs, "issues": issues}
    return report, not issues

def invoke(name: str, arguments: dict[str, Any]) -> Result:
    return run([sys.executable, "tools/agent_env/bahrain_brick_mcp.py", "--root", ".", "--invoke", name, "--arguments-json", json.dumps(arguments)], 1200)

def direct_smoke() -> tuple[dict[str, Any], bool]:
    root = ROOT / "build/codex-env-smoke"; root.mkdir(parents=True, exist_ok=True)
    artifact = root / "fixture.zip"
    project = root / "project"; project.mkdir(exist_ok=True); (project / "project.godot").write_text("[application]\nconfig/name=\"Codex Smoke\"\n", encoding="utf-8")
    with zipfile.ZipFile(artifact, "w") as z: z.writestr("assets/project.binary", b"res://scenes/splash_screen.tscn")
    listed = run([sys.executable, "tools/agent_env/bahrain_brick_mcp.py", "--root", ".", "--list-tools"], 30)
    calls = {
        "collect_build_evidence": invoke("collect_build_evidence", {"artifact_path": str(artifact.relative_to(ROOT)), "output_path": "build/codex-env-smoke/evidence.json"}),
        "godot_validate_project": invoke("godot_validate_project", {"project_path": str(project.relative_to(ROOT)), "timeout_seconds": 30}),
    }
    report = {"list": listed.as_dict(), "calls": {k:v.as_dict() for k,v in calls.items()}}
    expected = json.loads(listed.stdout).get("tools", []) if listed.exit_code == 0 else []
    ok = [t.get("name") for t in expected] == TOOLS and calls["collect_build_evidence"].exit_code == 0 and calls["godot_validate_project"].exit_code in {0,3}
    return report, ok

class MCPClient:
    def __init__(self):
        self.p = subprocess.Popen([sys.executable, "tools/agent_env/bahrain_brick_mcp.py", "--root", "."], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        self.i = 0
    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.i += 1; payload = {"jsonrpc":"2.0","id":self.i,"method":method}
        if params is not None: payload["params"] = params
        assert self.p.stdin and self.p.stdout
        self.p.stdin.write(json.dumps(payload)+"\n"); self.p.stdin.flush()
        return json.loads(self.p.stdout.readline())
    def close(self):
        if self.p.stdin: self.p.stdin.close()
        self.p.wait(timeout=5)

def mcp_smoke() -> tuple[dict[str, Any], bool]:
    client = MCPClient(); report: dict[str, Any] = {}
    try:
        report["initialize"] = client.request("initialize", {"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"verify","version":"1"}})
        report["list"] = client.request("tools/list", {})
        names = [t["name"] for t in report["list"].get("result", {}).get("tools", [])]
        ok = names == TOOLS
    finally: client.close()
    return report, ok

def baseline() -> tuple[dict[str, Any], bool, bool]:
    candidates = ["tests/test_karak_delivery_mission_contract.py", "tests/test_manama_souq_layout_contract.py", "tests/test_manama_souq_slice_contract.py", "tests/test_souq_population_contract.py", "tests/graphics/test_r1_playable_apk_export.py"]
    present = [p for p in candidates if (ROOT / p).is_file()]
    if not present: return {"status":"unavailable","reason":"representative tests absent"}, False, True
    results = []
    for p in present:
        cmd = [sys.executable, "-m", "unittest", p, "-v"] if "/graphics/" in p else [sys.executable, p]
        results.append(run(cmd, 1200).as_dict())
    return {"status":"passed" if all(r["exit_code"]==0 for r in results) else "failed", "tests":results}, all(r["exit_code"]==0 for r in results), False

def godot() -> tuple[dict[str, Any], bool, bool]:
    if not (ROOT / "project.godot").is_file(): return {"status":"unavailable","reason":"project.godot absent"}, False, True
    exe = os.environ.get("BAHRAIN_BRICK_GODOT") or shutil.which("godot4") or shutil.which("godot")
    if not exe: return {"status":"unavailable","reason":"Godot unavailable"}, False, True
    version = run([exe, "--version"], 30); validation = run([exe, "--headless", "--path", str(ROOT), "--editor", "--import", "--quit", "--verbose"], 1200)
    ok = version.stdout.strip() == "4.3.stable.official.77dcf97d8" and validation.exit_code == 0
    return {"status":"passed" if ok else "failed", "version":version.as_dict(), "validation":validation.as_dict()}, ok, False

def relevant(paths: list[str]) -> tuple[dict[str, Any], bool]:
    results = [run([sys.executable, "tests/test_controlled_agent_environment.py"], 300).as_dict()]
    if any(p.endswith(".gd") for p in paths) and (ROOT / "project.godot").is_file():
        report, ok, unavailable = godot(); return {"paths":paths,"results":results,"godot":report}, all(r["exit_code"]==0 for r in results) and (ok or unavailable)
    return {"paths":paths,"results":results}, all(r["exit_code"]==0 for r in results)

def evidence_newest() -> tuple[dict[str, Any], bool, bool]:
    apks = sorted([*ROOT.glob("build/**/*.apk"), *ROOT.glob("release/**/*.apk")], key=lambda p:p.stat().st_mtime, reverse=True)
    if not apks: return {"status":"unavailable","reason":"no APK under build/ or release/"}, False, True
    rel = str(apks[0].relative_to(ROOT)); result = invoke("collect_build_evidence", {"artifact_path":rel})
    return {"status":"passed" if result.exit_code==0 else "failed", "result":result.as_dict()}, result.exit_code==0, False

def completion() -> tuple[dict[str, Any], bool]:
    config, ok = validate_config(); test = run([sys.executable, "tests/test_controlled_agent_environment.py"], 300)
    return {"config":config,"static_test":test.as_dict(),"passed":ok and test.exit_code==0}, ok and test.exit_code==0

def emit(payload: dict[str, Any], code: int) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True)); return code

def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("command", choices=["config","inventory","direct-smoke","mcp-smoke","baseline","godot","relevant","changed","completion","evidence-newest"]); p.add_argument("--path", action="append", default=[]); a=p.parse_args()
    if a.command in {"config","inventory"}: report, ok=validate_config(); return emit({"status":"passed" if ok else "failed",**report},0 if ok else 1)
    if a.command=="direct-smoke": report,ok=direct_smoke(); return emit({"status":"passed" if ok else "failed",**report},0 if ok else 1)
    if a.command=="mcp-smoke": report,ok=mcp_smoke(); return emit({"status":"passed" if ok else "failed",**report},0 if ok else 1)
    if a.command=="baseline": report,ok,unavailable=baseline(); return emit(report,3 if unavailable else (0 if ok else 1))
    if a.command=="godot": report,ok,unavailable=godot(); return emit(report,3 if unavailable else (0 if ok else 1))
    if a.command in {"relevant","changed"}: report,ok=relevant(a.path); return emit({"status":"passed" if ok else "failed",**report},0 if ok else 1)
    if a.command=="completion": report,ok=completion(); return emit({"status":"passed" if ok else "failed",**report},0 if ok else 1)
    report,ok,unavailable=evidence_newest(); return emit(report,3 if unavailable else (0 if ok else 1))

if __name__ == "__main__": raise SystemExit(main())