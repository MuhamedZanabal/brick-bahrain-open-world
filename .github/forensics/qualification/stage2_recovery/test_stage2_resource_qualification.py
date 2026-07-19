import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import stage2_resource_qualification as q


class Stage2QualificationTests(unittest.TestCase):
    def test_resource_pass_requires_every_byte_gate(self):
        state = q.decide_resource_result(
            authority_ok=True,
            d1_ok=True,
            d2_ok=True,
            imported_exists=True,
            imported_equal=True,
            destination_md5_equal=True,
            uid_cache_equal=True,
            path_sets_equal=True,
            timed_out=False,
            harness_error=None,
        )
        self.assertEqual(state, "PASS")

    def test_resource_difference_is_nondeterministic_only_after_complete_imports(self):
        state = q.decide_resource_result(
            authority_ok=True,
            d1_ok=True,
            d2_ok=True,
            imported_exists=True,
            imported_equal=False,
            destination_md5_equal=False,
            uid_cache_equal=True,
            path_sets_equal=True,
            timed_out=False,
            harness_error=None,
        )
        self.assertEqual(state, "NONDETERMINISTIC")

    def test_timeout_has_priority_over_difference(self):
        state = q.decide_resource_result(
            authority_ok=True,
            d1_ok=True,
            d2_ok=False,
            imported_exists=True,
            imported_equal=False,
            destination_md5_equal=False,
            uid_cache_equal=False,
            path_sets_equal=False,
            timed_out=True,
            harness_error=None,
        )
        self.assertEqual(state, "TIMEOUT")

    def test_engine_q6_has_priority_when_any_report_is_incomplete(self):
        reports = [q.synthetic_resource_report("PASS", selection_id=x) for x in q.RESOURCE_IDS[:7]]
        reports.append(q.synthetic_resource_report("TIMEOUT", selection_id=q.RESOURCE_IDS[7]))
        summary = q.aggregate_engine_reports("4.4.1-stable", reports, expected_ids=q.RESOURCE_IDS)
        self.assertEqual(summary["stage2_decision"], "FAIL_INSUFFICIENT_EVIDENCE")
        self.assertEqual(summary["classification"], "Q6")
        self.assertFalse(summary["stage3_eligible"])

    def test_engine_q1_requires_complete_evidence_and_a_real_byte_difference(self):
        reports = [q.synthetic_resource_report("PASS", selection_id=x) for x in q.RESOURCE_IDS]
        reports[3] = q.synthetic_resource_report("NONDETERMINISTIC", selection_id=q.RESOURCE_IDS[3])
        summary = q.aggregate_engine_reports("4.5.2-stable", reports, expected_ids=q.RESOURCE_IDS)
        self.assertEqual(summary["complete_reports"], 8)
        self.assertEqual(summary["differing_imported_binary_count"], 1)
        self.assertEqual(summary["classification"], "Q1")
        self.assertFalse(summary["stage3_eligible"])

    def test_engine_stage2_pass_requires_eight_unique_passes(self):
        reports = [q.synthetic_resource_report("PASS", selection_id=x) for x in q.RESOURCE_IDS]
        summary = q.aggregate_engine_reports("4.6.3-stable", reports, expected_ids=q.RESOURCE_IDS)
        self.assertEqual(summary["stage2_decision"], "PASS")
        self.assertEqual(summary["classification"], "STAGE2_PASS_PENDING_STAGE3")
        self.assertTrue(summary["stage3_eligible"])

    def test_bounded_binary_diagnostics_never_exceed_twenty_windows(self):
        left = bytes(range(128)) * 4
        right = bytearray(left)
        for index in range(0, len(right), 7):
            right[index] ^= 0xFF
        diagnostic = q.bounded_binary_difference(left, bytes(right), max_windows=20, radius=4)
        self.assertGreater(diagnostic["differing_byte_count"], 20)
        self.assertEqual(len(diagnostic["difference_windows"]), 20)
        self.assertEqual(diagnostic["first_differing_byte"], 0)

    def test_generated_inventory_excludes_editor_cache_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".godot/imported").mkdir(parents=True)
            (root / ".godot/editor").mkdir(parents=True)
            (root / ".godot/imported/model.scn").write_bytes(b"model")
            (root / ".godot/uid_cache.bin").write_bytes(b"uid")
            (root / ".godot/editor/layout.cfg").write_bytes(b"editor")
            rows = q.generated_inventory(root)
            paths = {row["path"] for row in rows["records"]}
            self.assertIn(".godot/imported/model.scn", paths)
            self.assertIn(".godot/uid_cache.bin", paths)
            self.assertNotIn(".godot/editor/layout.cfg", paths)

    def test_cancellation_audit_detects_exact_180_minute_job_timeout(self):
        job = {
            "id": 1,
            "started_at": "2026-07-18T22:47:14Z",
            "completed_at": "2026-07-19T01:47:14Z",
            "conclusion": "cancelled",
            "steps": [{
                "name": "Run Stage 1 source audit and Stage 2 eight-resource qualification",
                "started_at": "2026-07-18T22:48:00Z",
                "completed_at": "2026-07-19T01:47:14Z",
                "conclusion": "cancelled",
            }],
        }
        cause = q.classify_cancellation(job, configured_timeout_minutes=180, log_text="The operation was canceled.")
        self.assertEqual(cause["cause"], "JOB_TIMEOUT")
        self.assertEqual(cause["actual_job_duration_seconds"], 10800)
        self.assertFalse(cause["concurrency_cancellation"])

    def test_resource_command_completes_with_a_deterministic_fake_engine(self):
        import argparse
        import os
        import zipfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "corpus"
            logical = "assets/model.glb"
            source = corpus / "files" / logical
            source.parent.mkdir(parents=True)
            source.write_bytes(b"source-model")
            q.write_json(corpus / "CORPUS_AUTHORITY.json", {
                "resources": [{
                    "selection_id": "synthetic",
                    "source_type": "GLB",
                    "logical_source": logical,
                    "matrix_member": False,
                    "source_bytes": source.stat().st_size,
                    "source_sha256": q.sha256_file(source),
                    "source_md5": q.md5_file(source),
                    "dependencies": [],
                }]
            })
            engine = root / "engine"
            engine.mkdir()
            runtime_source = root / "Godot_fake"
            runtime_source.write_text(r"""#!/usr/bin/env python3
import hashlib, os, pathlib, sys
if '--version' in sys.argv:
    print('fake.stable.official.123')
    raise SystemExit(0)
project = pathlib.Path(sys.argv[sys.argv.index('--path') + 1])
source = next(project.rglob('*.glb'))
rel = source.relative_to(project).as_posix()
sidecar = project / (rel + '.import')
sidecar.parent.mkdir(parents=True, exist_ok=True)
sidecar.write_text('[remap]\npath=\"res://.godot/imported/model.scn\"\nsource_file=\"res://' + rel + '\"\n')
imported = project / '.godot/imported/model.scn'
imported.parent.mkdir(parents=True, exist_ok=True)
imported.write_bytes(b'deterministic-import')
md5 = imported.with_suffix('.md5')
md5.write_text('source_md5=\"' + hashlib.md5(source.read_bytes()).hexdigest() + '\"\ndest_md5=\"' + hashlib.md5(imported.read_bytes()).hexdigest() + '\"\n')
(project / '.godot/uid_cache.bin').write_bytes(b'uid-cache')
""")
            archive = engine / "Godot_vfake_linux.x86_64.zip"
            with zipfile.ZipFile(archive, 'w') as zf:
                zf.write(runtime_source, arcname='Godot_fake')
            (engine / 'SHA512-SUMS.txt').write_text(q.sha512_file(archive) + '  ' + archive.name + '\n')
            q.write_json(engine / 'ENGINE_PACKAGE_IDENTITY.json', {
                'binary_archive_filename': archive.name,
                'binary_archive_sha512': q.sha512_file(archive),
                'binary_archive_sha256': q.sha256_file(archive),
                'extracted_runtime_sha256': q.sha256_file(runtime_source),
                'runtime_identity': 'fake.stable.official.123',
                'source_commit': '123',
            })
            output = root / 'output'
            args = argparse.Namespace(
                version='fake-stable', selection_id='synthetic', engine_root=str(engine),
                corpus_root=str(corpus), timeout_seconds=10, work_root=str(root / 'work'), output=str(output)
            )
            self.assertEqual(q.resource_qualification(args), 0)
            report = q.read_json(output / 'RESOURCE_QUALIFICATION.json')
            self.assertEqual(report['candidate_resource_result'], 'PASS')
            self.assertTrue(report['imported_byte_equality'])
            self.assertTrue(report['destination_md5_equality'])


if __name__ == "__main__":
    unittest.main()
