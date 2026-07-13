from pathlib import Path
import importlib.util
import json
import unittest

MODULE = Path(__file__).resolve().parents[1] / "apply_premium_validation_corrections.py"
spec = importlib.util.spec_from_file_location("premium_corrections", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class CorrectionStdoutSummaryTests(unittest.TestCase):
    def sample_report(self) -> dict:
        return {
            "conclusion": "pass",
            "protected_world_exit_actual_sha256": mod._post.PROTECTED_WORLD_EXIT_SHA256,
            "protected_world_exit_unchanged": True,
            "post_lifecycle_base_normalization": "normalized",
            "full_project_contract": True,
            "corrections": [
                {
                    "path": "scripts/world.gd",
                    "states": ["already_satisfied"],
                    "before_sha256": "a" * 64,
                    "after_sha256": "a" * 64,
                    "reasons": ["not printed"],
                }
            ],
            "generated_validation_resources": [
                {
                    "path": "tests/world_lifecycle_guard_test.gd",
                    "state": "generated",
                    "post_correction_state": "applied",
                    "sha256": "b" * 64,
                    "size_bytes": 123,
                    "reason": "not printed",
                }
            ],
            "post_lifecycle_teardown_guard": {
                "conclusion": "pass",
                "protected_world_exit_unchanged": True,
                "changes": [
                    {
                        "path": "scripts/world.gd",
                        "reason": "not printed",
                        "source": 'push_error("runtime text")',
                    }
                ],
            },
            "visual_evidence_shutdown_fix": {
                "conclusion": "pass",
                "path": "tests/premium_world_visual_evidence.gd",
                "state": "applied",
                "required": True,
                "before_sha256": "c" * 64,
                "after_sha256": "d" * 64,
                "size_bytes": 456,
                "source": 'push_error("Parse Error Compile Error")',
            },
            "transform_access_inventory": {
                "entry_count": 17,
                "file_count": 5,
                "entries": [
                    {
                        "text": 'push_error("Parse Error")',
                        "context": ["Compile Error", "Stack trace"],
                    }
                ],
                "source_snapshots": {
                    "tests/example.gd": 'push_error("Failed loading resource")'
                },
                "teardown_source_snapshots": {
                    "tests/example.gd": 'ERROR: Condition "!is_inside_tree()"'
                },
            },
            "diagnostic_sources": {
                "scripts/world.gd": 'push_error("Parse Error Compile Error")'
            },
        }

    def test_summary_keeps_only_scanner_safe_fields(self):
        summary = mod.compact_stdout_summary(self.sample_report())
        encoded = json.dumps(summary, sort_keys=True)
        for forbidden in (
            "diagnostic_sources",
            "source_snapshots",
            "teardown_source_snapshots",
            "entries",
            "push_error",
            "Parse Error",
            "Compile Error",
            "Stack trace",
            "Failed loading resource",
            "!is_inside_tree()",
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertEqual(summary["transform_access_inventory"]["entry_count"], 17)
        self.assertEqual(summary["transform_access_inventory"]["file_count"], 5)
        self.assertEqual(
            summary["transform_access_inventory"]["teardown_source_file_count"], 1
        )
        self.assertTrue(summary["protected_world_exit_unchanged"])

    def test_complete_report_remains_unchanged(self):
        report = self.sample_report()
        before = json.dumps(report, sort_keys=True)
        mod.compact_stdout_summary(report)
        self.assertEqual(before, json.dumps(report, sort_keys=True))
        self.assertIn("diagnostic_sources", report)
        self.assertIn("source_snapshots", report["transform_access_inventory"])


if __name__ == "__main__":
    unittest.main()
