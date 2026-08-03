#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
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
EXPECTED_TOOLS = [
    "godot_validate_project",
    "godot_export_android_debug",
    "android_adb_smoke_test",
    "blender_validate_asset",
    "collect_build_evidence",
]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ControlledAgentEnvironmentTests(unittest.TestCase):
    def test_required_files_and_json(self) -> None:
        required = [
            "CLAUDE.md",
            ".claude/settings.json",
            ".mcp.json",
            ".claude/hooks/bahrain_brick_hook.py",
            "tools/agent_env/bahrain_brick_mcp.py",
            "tools/agent_env/blender_asset_validator.py",
            "tools/agent_env/verify_environment.py",
            ".github/workflows/controlled-agent-environment.yml",
        ]
        for relative in required:
            self.assertTrue((ROOT / relative).is_file(), relative)
        json.loads((ROOT / ".claude/settings.json").read_text())
        json.loads((ROOT / ".mcp.json").read_text())

    def test_skill_and_agent_inventory(self) -> None:
        skills = {path.parent.name for path in (ROOT / ".claude/skills").glob("*/SKILL.md")}
        agents = {path.stem for path in (ROOT / ".claude/agents").glob("*.md")}
        self.assertEqual(EXPECTED_SKILLS, skills)
        self.assertEqual(EXPECTED_AGENTS, agents)
        for path in (ROOT / ".claude/agents").glob("*.md"):
            text = path.read_text()
            self.assertIn("isolation: worktree", text)
            self.assertIn("tools:", text)

    def test_permissions_and_hooks_are_least_privilege(self) -> None:
        settings = json.loads((ROOT / ".claude/settings.json").read_text())
        self.assertEqual({}, settings["enabledPlugins"])
        self.assertEqual({"SessionStart", "PreToolUse", "PostToolUse", "Stop"}, set(settings["hooks"]))
        deny = settings["permissions"]["deny"]
        for rule in (
            "Bash(git push --force*)",
            "Bash(git reset --hard*)",
            "Bash(git clean -f*)",
            "Bash(rm -rf *)",
            "Read(./**/*.keystore)",
        ):
            self.assertIn(rule, deny)
        self.assertEqual([], settings["allowedHttpHookUrls"])

    def test_exact_single_local_mcp(self) -> None:
        config = json.loads((ROOT / ".mcp.json").read_text())
        self.assertEqual({"bahrain-brick-local"}, set(config["mcpServers"]))
        server = config["mcpServers"]["bahrain-brick-local"]
        self.assertEqual("python3", server["command"])
        serialized = json.dumps(server).lower()
        for forbidden in ("http://", "https://", "token", "password", "keystore"):
            self.assertNotIn(forbidden, serialized)

    def test_mcp_exposes_only_typed_tools_and_confines_paths(self) -> None:
        module = load_module(ROOT / "tools/agent_env/bahrain_brick_mcp.py", "bahrain_brick_mcp_test")
        server = module.BahrainBrickMCP(ROOT)
        self.assertEqual(EXPECTED_TOOLS, [tool["name"] for tool in server.list_tools()])
        with self.assertRaises(module.ValidationError):
            server._resolve("../outside", must_exist=False)
        with self.assertRaises(module.ValidationError):
            server._resolve_output("assets/not-approved.apk")
        with self.assertRaises(module.ValidationError):
            server._resolve("debug.keystore", must_exist=False)

    def test_evidence_collection_does_not_require_signing_keys(self) -> None:
        module = load_module(ROOT / "tools/agent_env/bahrain_brick_mcp.py", "bahrain_brick_mcp_evidence_test")
        server = module.BahrainBrickMCP(ROOT)
        build = ROOT / "build/controlled-agent-test"
        build.mkdir(parents=True, exist_ok=True)
        artifact = build / "fixture.apk"
        with zipfile.ZipFile(artifact, "w") as archive:
            archive.writestr("assets/project.binary", b"res://scenes/splash_screen.tscn")
        result = server.collect_build_evidence(
            {
                "artifact_path": str(artifact.relative_to(ROOT)),
                "output_path": "build/controlled-agent-test/evidence.json",
            }
        )
        self.assertTrue(result["passed"])
        self.assertFalse(result["evidence"]["signing_material_accessed"])
        self.assertTrue(result["evidence"]["zip_integrity"])

    def test_hook_blocks_destructive_git_and_external_mcp_writes(self) -> None:
        hook = ROOT / ".claude/hooks/bahrain_brick_hook.py"
        cases = [
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "git push --force origin main"},
            },
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "mcp__community__delete_database",
                "tool_input": {"database": "prod"},
            },
        ]
        for payload in cases:
            result = subprocess.run(
                [sys.executable, str(hook)],
                input=json.dumps(payload),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=ROOT,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            response = json.loads(result.stdout)
            self.assertEqual("deny", response["hookSpecificOutput"]["permissionDecision"])

    def test_no_embedded_strong_secret_patterns(self) -> None:
        verifier = load_module(ROOT / "tools/agent_env/verify_environment.py", "bahrain_brick_verifier_secret_test")
        paths = verifier.control_file_paths()
        self.assertEqual([], verifier.scan_secrets(paths))


if __name__ == "__main__":
    unittest.main(verbosity=2)
