import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("stage3_qualification.py")
spec = importlib.util.spec_from_file_location("stage3_qualification", MODULE_PATH)
stage3 = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(stage3)
except FileNotFoundError:
    stage3 = None


class Stage3QualificationTests(unittest.TestCase):
    def require_module(self):
        self.assertIsNotNone(stage3, "stage3_qualification.py must exist")

    def test_exact_authorized_matrix(self):
        self.require_module()
        self.assertEqual(stage3.ENGINES, ("4.4.1-stable", "4.5.2-stable"))
        self.assertEqual(
            tuple(item["selection_id"] for item in stage3.RESOURCES),
            (
                "glb_matrix_small",
                "glb_matrix_medium",
                "glb_matrix_large",
                "glb_non_matrix",
                "gltf_character",
                "gltf_environment",
                "fbx_character",
                "obj_single",
            ),
        )
        self.assertEqual(len(stage3.authority_matrix()), 16)
        self.assertEqual(len(stage3.c_side_matrix()), 32)
        self.assertNotIn("4.6.3-stable", json.dumps(stage3.authority_matrix()))

    def test_cell_values_are_exact(self):
        self.require_module()
        self.assertEqual(
            stage3.CELL_VALUES,
            {
                "PASS",
                "NONDETERMINISTIC",
                "IMPORT_FAILURE",
                "TIMEOUT",
                "HARNESS_FAILURE",
                "MISSING_EVIDENCE",
            },
        )

    def test_parse_sidecar_extracts_authority_fields(self):
        self.require_module()
        text = '''[remap]\n\nimporter="scene"\ntype="PackedScene"\nuid="uid://abc"\npath="res://.godot/imported/a.scn"\n\n[deps]\n\nsource_file="res://assets/a.glb"\ndest_files=["res://.godot/imported/a.scn"]\n\n[params]\n\nmeshes/generate_lods=true\n'''
        parsed = stage3.parse_import_sidecar(text)
        self.assertEqual(parsed["importer"], "scene")
        self.assertEqual(parsed["type"], "PackedScene")
        self.assertEqual(parsed["uid"], "uid://abc")
        self.assertEqual(parsed["source_file"], "assets/a.glb")
        self.assertEqual(parsed["imported_relative_path"], ".godot/imported/a.scn")
        self.assertEqual(parsed["dest_files"], [".godot/imported/a.scn"])
        self.assertEqual(len(parsed["parameters_sha256"]), 64)

    def test_intervals_overlap_requires_positive_overlap(self):
        self.require_module()
        self.assertTrue(stage3.intervals_overlap(1.0, 3.0, 2.0, 4.0))
        self.assertFalse(stage3.intervals_overlap(1.0, 2.0, 2.0, 3.0))
        self.assertFalse(stage3.intervals_overlap(3.0, 2.0, 1.0, 4.0))

    def test_bounded_difference_contains_required_diagnostics(self):
        self.require_module()
        diag = stage3.bounded_byte_diagnostic(b"abc123xyz", b"abc999xyzz")
        self.assertEqual(diag["first_differing_byte_offset"], 3)
        self.assertEqual(diag["final_differing_byte_offset"], 9)
        self.assertEqual(diag["differing_byte_position_count"], 4)
        self.assertGreaterEqual(diag["contiguous_range_count"], 2)
        self.assertLessEqual(len(diag["first_20_byte_windows"]), 20)
        self.assertEqual(diag["output_size_difference"], 1)
        self.assertIn("local_strings", diag)
        self.assertIn("uid_strings", diag)
        self.assertIn("resource_order_indications", diag)

    def test_compare_snapshots_distinguishes_nondeterminism_and_missing_evidence(self):
        self.require_module()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            left_file = root / "left.bin"
            right_file = root / "right.bin"
            left_file.write_bytes(b"same")
            right_file.write_bytes(b"same")
            base = {
                "imported_sha256": stage3.sha256_file(left_file),
                "imported_byte_size": 4,
                "destination_md5": "d" * 32,
                "generated_path_set": [".godot/imported/a.scn", ".godot/imported/a.md5"],
                "imported_evidence_path": str(left_file),
                "uid_cache_sha256": "u" * 64,
                "import_exit_code": 0,
                "timed_out": False,
                "watchdog_result": "COMPLETED",
            }
            other = dict(base, imported_evidence_path=str(right_file))
            result = stage3.compare_snapshots(base, other, require_uid=True)
            self.assertEqual(result["result"], "PASS")
            right_file.write_bytes(b"diff")
            other["imported_sha256"] = stage3.sha256_file(right_file)
            result = stage3.compare_snapshots(base, other, require_uid=True)
            self.assertEqual(result["result"], "NONDETERMINISTIC")
            result = stage3.compare_snapshots(base, {}, require_uid=True)
            self.assertEqual(result["result"], "MISSING_EVIDENCE")

    def test_engine_classification_boundaries(self):
        self.require_module()
        passing = []
        for resource in (item["selection_id"] for item in stage3.RESOURCES):
            passing.append(
                {
                    "engine_version": "4.4.1-stable",
                    "resource_selection_id": resource,
                    "experiments": {k: {"result": "PASS"} for k in "ABCD"},
                    "differing_imported_binary_count": 0,
                    "differing_destination_md5_count": 0,
                }
            )
        result = stage3.aggregate_engine_results("4.4.1-stable", passing)
        self.assertEqual(result["stage3_decision"], "PASS")
        self.assertEqual(result["classification"], "STAGE3_PASS_PENDING_STAGE4")
        passing[0]["experiments"]["B"] = {"result": "NONDETERMINISTIC"}
        passing[0]["differing_imported_binary_count"] = 1
        result = stage3.aggregate_engine_results("4.4.1-stable", passing)
        self.assertEqual(result["classification"], "Q2")
        passing[0]["differing_imported_binary_count"] = 0
        passing[0]["experiments"]["B"] = {"result": "TIMEOUT"}
        result = stage3.aggregate_engine_results("4.4.1-stable", passing)
        self.assertEqual(result["classification"], "Q6")

    def test_cross_version_preference_when_both_pass(self):
        self.require_module()
        engines = [
            {"engine_version": "4.4.1-stable", "classification": "STAGE3_PASS_PENDING_STAGE4"},
            {"engine_version": "4.5.2-stable", "classification": "STAGE3_PASS_PENDING_STAGE4"},
        ]
        result = stage3.aggregate_cross_version(engines, 123, "abc")
        self.assertEqual(result["stage4_eligible_versions"], ["4.4.1-stable", "4.5.2-stable"])
        self.assertEqual(result["preferred_first_stage4_candidate"], "4.4.1-stable")
        self.assertEqual(result["qualified_fallback_candidate"], "4.5.2-stable")
        self.assertEqual(result["gate4_status"], "FAIL")
        self.assertEqual(result["gate5_status"], "PASS_FOR_TWO_ORIGINAL_RETAINED_APKS_ONLY")

    def test_verify_and_materialize_authority(self):
        self.require_module()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            corpus = root / "corpus"
            resource = root / "resource"
            project = root / "project"
            source_rel = "assets/a.glb"
            dep_rel = "assets/a.bin"
            (corpus / "files/assets").mkdir(parents=True)
            (corpus / "files" / source_rel).write_bytes(b"source")
            (corpus / "files" / dep_rel).write_bytes(b"dep")
            authority = {
                "schema_version": 2,
                "resources": [
                    {
                        "selection_id": "glb_matrix_small",
                        "logical_source": source_rel,
                        "source_type": "GLB",
                        "source_bytes": 6,
                        "source_sha256": stage3.sha256_file(corpus / "files" / source_rel),
                        "source_md5": stage3.md5_file(corpus / "files" / source_rel),
                        "dependencies": [
                            {
                                "path": dep_rel,
                                "bytes": 3,
                                "sha256": stage3.sha256_file(corpus / "files" / dep_rel),
                                "md5": stage3.md5_file(corpus / "files" / dep_rel),
                            }
                        ],
                    }
                ],
            }
            (corpus / "CORPUS_AUTHORITY.json").write_text(json.dumps(authority))
            sidecar_rel = source_rel + ".import"
            sidecar_path = resource / "sidecar_authority" / sidecar_rel
            sidecar_path.parent.mkdir(parents=True)
            sidecar_path.write_text(
                '[remap]\n\nimporter="scene"\ntype="PackedScene"\nuid="uid://abc"\npath="res://.godot/imported/a.scn"\n\n[deps]\n\nsource_file="res://assets/a.glb"\ndest_files=["res://.godot/imported/a.scn"]\n\n[params]\n\nfoo=true\n'
            )
            report = {
                "candidate_resource_result": "PASS",
                "engine_version": "4.4.1-stable",
                "resource_selection_id": "glb_matrix_small",
                "logical_source_path": source_rel,
                "source_byte_size": 6,
                "source_sha256": authority["resources"][0]["source_sha256"],
                "source_md5": authority["resources"][0]["source_md5"],
                "frozen_pr_head": stage3.FROZEN_PR_HEAD,
                "sidecar_path": sidecar_rel,
                "sidecar_sha256": stage3.sha256_file(sidecar_path),
                "sidecar_size": sidecar_path.stat().st_size,
                "sidecar_authority_manifest": [
                    {"path": sidecar_rel, "sha256": stage3.sha256_file(sidecar_path), "size": sidecar_path.stat().st_size}
                ],
            }
            (resource / "RESOURCE_QUALIFICATION.json").write_text(json.dumps(report))
            verified = stage3.verify_authority("4.4.1-stable", "glb_matrix_small", corpus, resource)
            self.assertEqual(verified["sidecar"]["importer"], "scene")
            stage3.materialize_project(project, corpus, resource, verified)
            self.assertTrue((project / source_rel).is_file())
            self.assertTrue((project / dep_rel).is_file())
            self.assertTrue((project / sidecar_rel).is_file())
            self.assertFalse((project / ".godot").exists())
            self.assertTrue((project / "project.godot").is_file())


if __name__ == "__main__":
    unittest.main()
