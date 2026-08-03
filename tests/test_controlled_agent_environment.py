#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tomllib
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
LEGACY_TERMS = ("cl" + "aude", "." + "cl" + "aude", "cl" + "aude_project_dir", ".mcp" + ".json")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ControlledCodexEnvironmentTests(unittest.TestCase):
    def test_required_files_parse_and_legacy_paths_are_absent(self) -> None:
        required = [
            "AGENTS.md",
            ".codex/config.toml",
            ".codex/hooks.json",
            ".codex/hooks/bahrain_brick_hook.py",
            "tools/agent_env/bahrain_brick_mcp.py",
            "tools/agent_env/blender_asset_validator.py",
            "tools/agent_env/verify_environment.py",
            ".github/workflows/controlled-agent-environment.yml",
        ]
        for relative in required:
            self.assertTrue((ROOT / relative).is_file(), relative)
        tomllib.loads((ROOT / ".codex/config.toml").read_text())
        json.loads((ROOT / ".codex/hooks.json").read_text())
        yaml_check = subprocess.run(
            ["ruby", "-e", 'require "yaml"; value=YAML.load_file(ARGV.fetch(0)); abort "workflow must be a mapping" unless value.is_a?(Hash)', ".github/workflows/controlled-agent-environment.yml"],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
        )
        self.assertEqual(0, yaml_check.returncode, yaml_check.stderr)
        self.assertFalse((ROOT / ("CL" + "AUDE.md")).exists())
        self.assertFalse((ROOT / ("." + "cl" + "aude")).exists())
        self.assertFalse((ROOT / (".mcp" + ".json")).exists())

    def test_skill_inventory_uses_codex_frontmatter(self) -> None:
        paths = list((ROOT / ".agents/skills").glob("*/SKILL.md"))
        self.assertEqual(EXPECTED_SKILLS, {path.parent.name for path in paths})
        for path in paths:
            text = path.read_text()
            self.assertTrue(text.startswith("---\n"))
            frontmatter = text[4:text.index("\n---\n", 4)]
            keys = {line.split(":", 1)[0] for line in frontmatter.splitlines() if line.strip()}
            self.assertEqual({"name", "description"}, keys, path)

    def test_agent_inventory_uses_codex_toml_and_parent_model(self) -> None:
        paths = list((ROOT / ".codex/agents").glob("*.toml"))
        self.assertEqual(EXPECTED_AGENTS, {path.stem for path in paths})
        for path in paths:
            data = tomllib.loads(path.read_text())
            self.assertEqual(path.stem, data["name"])
            self.assertTrue(data["description"])
            self.assertTrue(data["developer_instructions"])
            self.assertIn(data["sandbox_mode"], {"read-only", "workspace-write"})
            self.assertNotIn("model", data)

    def test_codex_config_is_least_privilege(self) -> None:
        config = tomllib.loads((ROOT / ".codex/config.toml").read_text())
        self.assertEqual("on-request", config["approval_policy"])
        self.assertEqual("workspace-write", config["sandbox_mode"])
        self.assertFalse(config["sandbox_workspace_write"]["network_access"])
        self.assertTrue(config["features"]["hooks"])
        self.assertTrue(config["agents"]["enabled"])
        self.assertEqual({"bahrain-brick-local"}, set(config["mcp_servers"]))
        server = config["mcp_servers"]["bahrain-brick-local"]
        self.assertEqual("bash", server["command"])
        self.assertEqual(
            ["-lc", 'ROOT=$(git rev-parse --show-toplevel) && exec python3 "$ROOT/tools/agent_env/bahrain_brick_mcp.py" --root "$ROOT"'],
            server["args"],
        )
        self.assertEqual(EXPECTED_TOOLS, server["enabled_tools"])
        self.assertFalse(server["supports_parallel_tool_calls"])
        self.assertEqual("prompt", server["default_tools_approval_mode"])
        self.assertEqual("auto", server["tools"]["godot_validate_project"]["approval_mode"])
        self.assertEqual("auto", server["tools"]["collect_build_evidence"]["approval_mode"])
        for name in ("godot_export_android_debug", "android_adb_smoke_test", "blender_validate_asset"):
            self.assertEqual("prompt", server["tools"][name]["approval_mode"])
        serialized = json.dumps(server).lower()
        for forbidden in ("http://", "https://", "token", "password", "keystore"):
            self.assertNotIn(forbidden, serialized)

    def test_hooks_cover_security_verification_and_completion(self) -> None:
        config = json.loads((ROOT / ".codex/hooks.json").read_text())
        self.assertEqual({"SessionStart", "PreToolUse", "PostToolUse", "Stop"}, set(config["hooks"]))
        hook_text = (ROOT / ".codex/hooks/bahrain_brick_hook.py").read_text()
        for token in ("git\\s+push", "git\\s+reset", "DROP", "TRUNCATE", "evidence-newest", "completion"):
            self.assertIn(token, hook_text)

    def test_mcp_exposes_only_typed_tools_and_confines_paths(self) -> None:
        module = load_module(ROOT / "tools/agent_env/bahrain_brick_mcp.py", "bahrain_brick_mcp_test")
        server = module.BahrainBrickTools(ROOT)
        self.assertEqual(EXPECTED_TOOLS, [tool["name"] for tool in server.list_tools()])
        with self.assertRaises(module.ValidationError):
            server._resolve("../outside", must_exist=False)
        with self.assertRaises(module.ValidationError):
            server._resolve_output("assets/not-approved.apk")
        with self.assertRaises(module.ValidationError):
            server._resolve("debug.keystore", must_exist=False)

    def test_direct_typed_cli_and_evidence_collection(self) -> None:
        build = ROOT / "build/controlled-codex-test"
        build.mkdir(parents=True, exist_ok=True)
        artifact = build / "fixture.apk"
        with zipfile.ZipFile(artifact, "w") as archive:
            archive.writestr("assets/project.binary", b"res://scenes/splash_screen.tscn")
        result = subprocess.run(
            [sys.executable, "tools/agent_env/bahrain_brick_mcp.py", "--root", ".", "--invoke", "collect_build_evidence", "--arguments-json", json.dumps({"artifact_path": str(artifact.relative_to(ROOT)), "output_path": "build/controlled-codex-test/evidence.json"})],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["passed"])
        self.assertFalse(payload["evidence"]["signing_material_accessed"])
        self.assertTrue(payload["evidence"]["zip_integrity"])

    def test_android_artifact_retention_is_split_and_evidence_complete(self) -> None:
        workflow = (ROOT / ".github/workflows/controlled-agent-environment.yml").read_text()
        markers = {
            "gl": "      - name: Upload GL APK\n",
            "mobile": "      - name: Upload Mobile APK\n",
            "evidence": "      - name: Upload Android evidence\n",
        }
        blocks: dict[str, str] = {}
        for name, marker in markers.items():
            self.assertEqual(1, workflow.count(marker), marker)
            blocks[name] = workflow.split(marker, 1)[1].split("\n      - name:", 1)[0]

        gl_apk = "build/controlled-codex/android/bahrain-brick-r1-physical-gl-arm64.apk"
        mobile_apk = "build/controlled-codex/android/bahrain-brick-playable-mobile-arm64.apk"
        self.assertIn(gl_apk, blocks["gl"])
        self.assertNotIn(mobile_apk, blocks["gl"])
        self.assertIn(mobile_apk, blocks["mobile"])
        self.assertNotIn(gl_apk, blocks["mobile"])
        self.assertNotIn(".apk", blocks["evidence"])
        self.assertNotIn("Upload Android attempt and evidence", workflow)

        required_evidence = (
            "build/controlled-codex/android/evidence/",
            "build/controlled-codex/android/export.log",
            "build/controlled-codex/android/import.log",
            "build/controlled-codex/android/export-gl.log",
            "build/controlled-codex/android/export-mobile.log",
            "build/controlled-codex/android/R1_PHYSICAL_DEVICE_APK_MANIFEST.json",
            "build/controlled-codex/android/APK_SHA256SUMS.txt",
            "build/controlled-codex/android/apk-signing.txt",
            "build/controlled-codex/android/SOURCE_TREE_EQUIVALENCE.json",
            "build/controlled-codex/android/GL_VARIANT_OVERRIDE.json",
            "build/controlled-codex/android/MOBILE_VARIANT_OVERRIDE.json",
            "build/controlled-codex/android/GODOT_VERSION.txt",
        )
        for path in required_evidence:
            self.assertIn(path, blocks["evidence"])
        for block in blocks.values():
            for prohibited in (
                "path: build/controlled-codex/android\n",
                "build/controlled-codex/android/reconstruction",
                "build/controlled-codex/android/gl-project",
                "build/controlled-codex/android/mobile-project",
                "build/controlled-codex/android/godot/",
                "build/controlled-codex/android/templates/",
            ):
                self.assertNotIn(prohibited, block)

    def test_apply_patch_paths_are_discovered_for_post_edit_verification(self) -> None:
        hook_module = load_module(ROOT / ".codex/hooks/bahrain_brick_hook.py", "bahrain_brick_hook_test")
        patch = "*** Begin Patch\n*** Update File: scripts/example.gd\n*** Add File: tests/example_test.py\n*** End Patch\n"
        self.assertEqual(
            ["scripts/example.gd", "tests/example_test.py"],
            hook_module.extract_edited_paths("apply_patch", {"command": patch}, {}),
        )

    def test_hook_blocks_destructive_git_and_external_mcp_writes(self) -> None:
        hook = ROOT / ".codex/hooks/bahrain_brick_hook.py"
        cases = [
            {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "git push --force origin main"}},
            {"hook_event_name": "PreToolUse", "tool_name": "mcp__community__delete_database", "tool_input": {"database": "prod"}},
        ]
        for payload in cases:
            result = subprocess.run([sys.executable, str(hook)], input=json.dumps(payload), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=ROOT, check=False)
            self.assertEqual(0, result.returncode, result.stderr)
            response = json.loads(result.stdout)
            self.assertEqual("deny", response["hookSpecificOutput"]["permissionDecision"])

    def test_no_embedded_secrets_or_legacy_provider_references(self) -> None:
        verifier = load_module(ROOT / "tools/agent_env/verify_environment.py", "bahrain_brick_verifier_test")
        paths = verifier.control_file_paths()
        self.assertEqual([], verifier.scan_secrets(paths))
        self.assertEqual([], verifier.provider_reference_findings(paths))
        for path in paths:
            if path.is_file():
                lowered = path.read_text(errors="replace").lower()
                for term in LEGACY_TERMS:
                    self.assertNotIn(term, lowered, path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
