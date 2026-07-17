#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "vertical_slice" / "inventory_godot_android_apk_assets.py"
TARGET = ".godot/imported/example.glb-0123456789abcdef.scn"
SIDE = "models/example.glb.import"
LOGICAL = "models/example.glb"


def sidecar(*, path: str | None = TARGET, source_file: str | None = LOGICAL, dest_files: list[str] | None = None) -> str:
    lines = ["[remap]", 'importer="scene"', 'type="PackedScene"']
    if path is not None:
        lines.append(f'path="res://{path}"')
    lines.extend(["", "[deps]"])
    if source_file is not None:
        lines.append(f'source_file="res://{source_file}"')
    if dest_files is not None:
        encoded = ", ".join(f'"res://{item}"' for item in dest_files)
        lines.append(f"dest_files=[{encoded}]")
    return "\n".join(lines) + "\n"


class GlbImportSidecarInventoryTests(unittest.TestCase):
    def run_fixture(
        self,
        entries: list[tuple[str, bytes | str]],
        *,
        source_paths: tuple[str, ...] = (LOGICAL,),
    ) -> tuple[subprocess.CompletedProcess[str], dict]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            for relative in source_paths:
                target = source / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"source")
            apk = root / "fixture.apk"
            with zipfile.ZipFile(apk, "w") as archive:
                for name, payload in entries:
                    archive.writestr(name, payload)
            output = root / "inventory.json"
            result = subprocess.run(
                ["python3", str(TOOL), "--apk", str(apk), "--source-root", str(source), "--output", str(output)],
                text=True,
                capture_output=True,
                check=False,
            )
            value = json.loads(output.read_text(encoding="utf-8"))
            return result, value

    def test_exact_glb_import_sidecar_emits_one_verified_alias(self) -> None:
        result, value = self.run_fixture(
            [(f"assets/{SIDE}", sidecar(dest_files=[TARGET])), (f"assets/{TARGET}", b"scene")]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        aliases = [item for item in value["logical_aliases"] if item["logical_path"] == LOGICAL]
        self.assertEqual(len(aliases), 1)
        self.assertIn(LOGICAL, value["files"])
        self.assertEqual(value["validated_glb_alias_count"], 1)
        self.assertEqual(value["rejected_glb_sidecar_count"], 0)
        alias = aliases[0]
        self.assertEqual(alias["sidecar_path"], SIDE)
        self.assertEqual(alias["source_file"], LOGICAL)
        self.assertEqual(alias["declared_import_targets"], [TARGET])
        self.assertEqual(alias["verified_import_targets"], [TARGET])
        self.assertTrue(alias["source_verified"])
        self.assertTrue(alias["targets_verified"])

    def test_rejects_all_fail_closed_negative_fixtures(self) -> None:
        cases = {
            "target_absent": ([(f"assets/{SIDE}", sidecar(dest_files=[TARGET]))], (LOGICAL,), "missing_import_target"),
            "undeclared_target": ([(f"assets/{SIDE}", sidecar(path=None, dest_files=[])), (f"assets/{TARGET}", b"scene")], (LOGICAL,), "missing_declared_import_target"),
            "similar_basename": ([(f"assets/{SIDE}", sidecar(dest_files=[TARGET])), (f"assets/{TARGET}.similar", b"scene")], (LOGICAL,), "missing_import_target"),
            "source_disagrees": ([(f"assets/{SIDE}", sidecar(source_file="models/other.glb", dest_files=[TARGET])), (f"assets/{TARGET}", b"scene")], (LOGICAL, "models/other.glb"), "source_file_mismatch"),
            "source_absent": ([(f"assets/{SIDE}", sidecar(dest_files=[TARGET])), (f"assets/{TARGET}", b"scene")], (), "missing_source_file"),
            "sidecar_traversal": ([("assets/models/../example.glb.import", sidecar(dest_files=[TARGET])), (f"assets/{TARGET}", b"scene")], (LOGICAL,), "unsafe_apk_path"),
            "target_traversal": ([(f"assets/{SIDE}", sidecar(path=".godot/imported/../escape.scn", dest_files=[".godot/imported/../escape.scn"])), ("assets/.godot/escape.scn", b"scene")], (LOGICAL,), "unsafe_import_target"),
            "target_outside_imported": ([(f"assets/{SIDE}", sidecar(path="models/example.scn", dest_files=["models/example.scn"])), ("assets/models/example.scn", b"scene")], (LOGICAL,), "target_outside_godot_imported"),
            "malformed": ([(f"assets/{SIDE}", "[remap]\npath=res://bad\n[deps]\n"), (f"assets/{TARGET}", b"scene")], (LOGICAL,), "malformed_sidecar"),
            "path_dest_conflict": ([(f"assets/{SIDE}", sidecar(path=TARGET, dest_files=[".godot/imported/other.glb-deadbeef.scn"])), (f"assets/{TARGET}", b"scene"), ("assets/.godot/imported/other.glb-deadbeef.scn", b"scene")], (LOGICAL,), "conflicting_import_targets"),
            "source_case_differs": ([(f"assets/{SIDE}", sidecar(source_file="Models/example.glb", dest_files=[TARGET])), (f"assets/{TARGET}", b"scene")], (LOGICAL, "Models/example.glb"), "source_file_mismatch"),
            "target_case_differs": ([(f"assets/{SIDE}", sidecar(dest_files=[TARGET])), (f"assets/{TARGET.upper()}", b"scene")], (LOGICAL,), "missing_import_target"),
            "unrelated_same_base_scn": ([(f"assets/{SIDE}", sidecar(dest_files=[TARGET])), ("assets/models/example.scn", b"scene")], (LOGICAL,), "missing_import_target"),
            "multiple_one_missing": ([(f"assets/{SIDE}", sidecar(path=TARGET, dest_files=[TARGET, ".godot/imported/example-extra.scn"])), (f"assets/{TARGET}", b"scene")], (LOGICAL,), "missing_import_target"),
        }
        for name, (entries, source_paths, reason) in cases.items():
            with self.subTest(name=name):
                result, value = self.run_fixture(entries, source_paths=source_paths)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(LOGICAL, [item["logical_path"] for item in value.get("logical_aliases", [])])
                self.assertGreaterEqual(value.get("rejected_glb_sidecar_count", 0), 1)
                reasons = {failure for item in value.get("glb_import_rejections", []) for failure in item.get("validation_failures", [])}
                self.assertIn(reason, reasons)

    def test_duplicate_apk_paths_fail_closed(self) -> None:
        result, value = self.run_fixture(
            [(f"assets/{SIDE}", sidecar(dest_files=[TARGET])), (f"assets/{SIDE}", sidecar(dest_files=[TARGET])), (f"assets/{TARGET}", b"scene")]
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"assets/{SIDE}", value["duplicate_apk_paths"])
        self.assertNotIn(LOGICAL, [item["logical_path"] for item in value.get("logical_aliases", [])])


if __name__ == "__main__":
    unittest.main(verbosity=2)
