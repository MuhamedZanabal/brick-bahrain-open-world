from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

TOOLS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_DIR))

from audit_source_tree import audit_tree, render_markdown, threshold_met  # noqa: E402


class SourceTreeAuditTests(unittest.TestCase):
    def test_detects_debug_release_signing_and_missing_addon_license(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "addons" / "sample_plugin").mkdir(parents=True)
            (root / "addons" / "sample_plugin" / "plugin.gd").write_text("extends Node\n", encoding="utf-8")
            (root / "debug.keystore").write_bytes(b"synthetic")
            (root / "export_presets.cfg").write_text(
                "\n".join([
                    'keystore/debug="res://debug.keystore"',
                    'keystore/debug_password="android"',
                    'keystore/release="res://debug.keystore"',
                    'keystore/release_password="android"',
                ]),
                encoding="utf-8",
            )
            report = audit_tree(root)
            rules = {finding["rule_id"] for finding in report["findings"]}
            self.assertIn("SENSITIVE_FILE_COMMITTED", rules)
            self.assertIn("ANDROID_DEBUG_KEY_USED_FOR_RELEASE", rules)
            self.assertIn("ANDROID_SIGNING_PASSWORD_IN_CONFIG", rules)
            self.assertIn("THIRD_PARTY_LICENSE_EVIDENCE_MISSING", rules)
            self.assertTrue(threshold_met(report, "P0"))

    def test_detects_provider_secret_without_echoing_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            secret = "gh" + "p_" + ("A" * 36)
            (root / "config.txt").write_text(f"token={secret}\n", encoding="utf-8")
            report = audit_tree(root)
            markdown = render_markdown(report)
            self.assertIn("SECRET_GITHUB_TOKEN", markdown)
            self.assertNotIn(secret, markdown)
            self.assertIn("sha256:", markdown)

    def test_adjacent_license_satisfies_addon_evidence_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "LICENSE").write_text("Project license\n", encoding="utf-8")
            addon = root / "addons" / "licensed_plugin"
            addon.mkdir(parents=True)
            (addon / "LICENSE.md").write_text("MIT\n", encoding="utf-8")
            (addon / "plugin.gd").write_text("extends Node\n", encoding="utf-8")
            report = audit_tree(root)
            rules = {finding["rule_id"] for finding in report["findings"]}
            self.assertNotIn("ROOT_LICENSE_MISSING", rules)
            self.assertNotIn("THIRD_PARTY_LICENSE_EVIDENCE_MISSING", rules)


if __name__ == "__main__":
    unittest.main()
