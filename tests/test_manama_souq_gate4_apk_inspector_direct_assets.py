#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
GATE4 = ROOT / ".github" / "workflows" / "manama-souq-gate4-android-export.yml"
APK_TOOL = ROOT / "tools" / "vertical_slice" / "manama_souq_apk_evidence.py"

REQUIRED_RESOURCES = (
    "scenes/manama_souq_vertical_slice.tscn",
    "scripts/manama_souq_vertical_slice.gd",
    "scripts/karak_delivery_mission.gd",
    "scenes/karak_delivery_hud.tscn",
    "scripts/karak_delivery_hud.gd",
    "scripts/souq_population_controller.gd",
    "scripts/brick_factory.gd",
    "scripts/touch_input.gd",
    "asset_lab/runtime/manama_souq_layout_v1.json",
)
MATRIX_PATHS = tuple(f"asset_lab/generated/matrix/asset_{index:03d}.glb" for index in range(436))


def compiled_path(logical: str) -> str:
    suffix = PurePosixPath(logical).suffix
    return {
        ".tscn": str(PurePosixPath(logical).with_suffix(".scn")),
        ".gd": str(PurePosixPath(logical).with_suffix(".gdc")),
    }.get(suffix, logical)


class InspectorFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.source = root / "source"
        self.report = root / "reports"
        self.apk = root / "fixture.apk"
        self.inventory = root / "APK_PROJECT_ASSETS.json"
        self.badging = root / "APK_BADGING.txt"
        self.manifest = root / "APK_MANIFEST_XMLTREE.txt"
        self.signing = root / "APK_SIGNING.txt"
        self.source.mkdir(parents=True)
        self._create_source()
        self.raw_files, self.aliases = self._build_packaging()
        self.write_apk()
        self.write_inventory()
        self.badging.write_text(
            "\n".join(
                (
                    "package: name='com.brickbahrain.openworld' versionCode='1' versionName='1.0.0'",
                    "sdkVersion:'21'",
                    "targetSdkVersion:'34'",
                    "application-label:'Zanabal Gaming'",
                    "launchable-activity: name='org.godotengine.godot.GodotApp'",
                    "application-debuggable",
                    "uses-permission: name='android.permission.INTERNET'",
                    "uses-permission: name='android.permission.ACCESS_NETWORK_STATE'",
                    "native-code: 'armeabi-v7a' 'arm64-v8a' 'x86_64'",
                )
            )
            + "\n",
            encoding="utf-8",
        )
        self.manifest.write_text(
            "A: android:screenOrientation(0x0101001e)=(type 0x10)0x5\n"
            "A: android:debuggable(0x0101000f)=(type 0x12)0xffffffff\n",
            encoding="utf-8",
        )
        self.write_signing(valid=True, qa=True)

    def _create_source(self) -> None:
        for relative in REQUIRED_RESOURCES + MATRIX_PATHS:
            target = self.source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"source")
        manifest = self.source / "asset_lab/runtime/full_asset_matrix_manifest.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(
            json.dumps({"assets": [f"res://{path}" for path in MATRIX_PATHS]}, indent=2) + "\n",
            encoding="utf-8",
        )

    def _build_packaging(self) -> tuple[set[str], list[dict[str, object]]]:
        raw: set[str] = set()
        aliases: list[dict[str, object]] = []
        for logical in REQUIRED_RESOURCES:
            packaged = compiled_path(logical)
            raw.add(packaged)
            if packaged != logical:
                aliases.append(
                    {
                        "logical_path": logical,
                        "packaged_path": packaged,
                        "reason": "Godot compiled resource",
                        "target_verified": True,
                    }
                )
        for index, logical in enumerate(MATRIX_PATHS):
            remap = f"{logical}.remap"
            target = f".godot/imported/{PurePosixPath(logical).name}-{index:03d}.scn"
            raw.update((remap, target))
            aliases.append(
                {
                    "logical_path": logical,
                    "packaged_path": remap,
                    "remap_target": target,
                    "reason": "Godot imported-resource remap",
                    "source_verified": True,
                    "target_verified": True,
                }
            )
        return raw, aliases

    def write_apk(
        self,
        *,
        extra_entries: list[tuple[str, bytes]] | None = None,
        omitted_assets: set[str] | None = None,
    ) -> None:
        omitted_assets = omitted_assets or set()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.apk, "w") as archive:
                for path in (
                    "AndroidManifest.xml",
                    "resources.arsc",
                    "classes.dex",
                    "lib/arm64-v8a/libgodot_android.so",
                ):
                    archive.writestr(path, b"critical")
                alias_by_packaged = {str(item["packaged_path"]): item for item in self.aliases}
                for relative in sorted(self.raw_files - omitted_assets):
                    alias = alias_by_packaged.get(relative)
                    if alias and alias.get("remap_target"):
                        payload = f'[remap]\npath="res://{alias["remap_target"]}"\n'.encode()
                    else:
                        payload = b"project-resource"
                    archive.writestr(f"assets/{relative}", payload)
                for name, payload in extra_entries or []:
                    archive.writestr(name, payload)

    def write_inventory(
        self,
        *,
        files: set[str] | None = None,
        raw_files: set[str] | None = None,
        aliases: list[dict[str, object]] | None = None,
        passed: bool = True,
        remap_failures: list[dict[str, object]] | None = None,
    ) -> None:
        raw_files = set(self.raw_files if raw_files is None else raw_files)
        aliases = list(self.aliases if aliases is None else aliases)
        logical_files = set(raw_files)
        logical_files.update(str(item["logical_path"]) for item in aliases)
        if files is not None:
            logical_files = set(files)
        value = {
            "passed": passed,
            "packaging": "godot-4.3-default-android-apk-assets",
            "pck_required": False,
            "raw_asset_count": len(raw_files),
            "logical_file_count": len(logical_files),
            "files": sorted(logical_files),
            "raw_files": sorted(raw_files),
            "logical_aliases": aliases,
            "remap_count": sum(1 for item in aliases if item.get("remap_target")),
            "remap_targets_verified": not remap_failures,
            "remap_failures": remap_failures or [],
            "compatibility_note": (
                "Normalized logical project-resource inventory; not proof of a physical PCK archive entry."
            ),
        }
        self.inventory.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def remove_logical_resource(self, logical: str) -> None:
        aliases = [dict(item) for item in self.aliases]
        matching = [item for item in aliases if item.get("logical_path") == logical]
        raw_files = set(self.raw_files)
        omitted: set[str] = set()
        if matching:
            for item in matching:
                packaged = str(item["packaged_path"])
                raw_files.discard(packaged)
                omitted.add(packaged)
                target = item.get("remap_target")
                if target:
                    raw_files.discard(str(target))
                    omitted.add(str(target))
            aliases = [item for item in aliases if item.get("logical_path") != logical]
        else:
            raw_files.discard(logical)
            omitted.add(logical)
        self.write_apk(omitted_assets=omitted)
        self.write_inventory(raw_files=raw_files, aliases=aliases)

    def write_signing(self, *, valid: bool, qa: bool) -> None:
        verified = "true" if valid else "false"
        subject = "CN=Android Debug,O=Android" if qa else "CN=Production,O=Example"
        marker = "" if valid else "DOES NOT VERIFY\n"
        self.signing.write_text(
            marker
            + f"Verified using v1 scheme (JAR signing): {verified}\n"
            + f"Verified using v2 scheme (APK Signature Scheme v2): {verified}\n"
            + f"Verified using v3 scheme (APK Signature Scheme v3): {verified}\n"
            + "Verified using v4 scheme (APK Signature Scheme v4): false\n"
            + "Signer #1 certificate SHA-256 digest: 11:22:33:44\n"
            + f"Signer #1 certificate DN: {subject}\n",
            encoding="utf-8",
        )

    def inspect(self) -> tuple[subprocess.CompletedProcess[str], dict[str, object], dict[str, object], dict[str, object]]:
        result = subprocess.run(
            [
                "python3",
                str(APK_TOOL),
                "inspect",
                "--apk",
                str(self.apk),
                "--report-dir",
                str(self.report),
                "--source-root",
                str(self.source),
                "--badging",
                str(self.badging),
                "--manifest-xml",
                str(self.manifest),
                "--signing",
                str(self.signing),
                "--pck-inventory",
                str(self.inventory),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        archive = json.loads((self.report / "APK_ARCHIVE_REPORT.json").read_text())
        packaged = json.loads((self.report / "PACKAGED_VERTICAL_SLICE_RESOURCES.json").read_text())
        record = json.loads((self.report / "APK_EXPORT_RECORD.json").read_text())
        return result, archive, packaged, record


class ManamaSouqGate4ApkInspectorDirectAssetsTests(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory[str], InspectorFixture]:
        temporary = tempfile.TemporaryDirectory()
        return temporary, InspectorFixture(Path(temporary.name))

    def test_valid_direct_assets_layout_without_standalone_pck_passes(self) -> None:
        temporary, fixture = self.fixture()
        with temporary:
            result, archive, packaged, record = fixture.inspect()
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertTrue(record["passed"])
            self.assertTrue(record["apk"]["signing"]["v1"])
            self.assertTrue(archive["direct_assets_layout"])
            self.assertEqual(archive["standalone_pck_paths"], [])
            self.assertNotIn("missing Godot PCK payload", archive["failures"])
            self.assertTrue(packaged["project_asset_inventory"]["valid"])

    def test_empty_project_asset_inventory_fails_closed(self) -> None:
        temporary, fixture = self.fixture()
        with temporary:
            fixture.write_inventory(files=set(), raw_files=set(), aliases=[])
            result, _, packaged, _ = fixture.inspect()
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(packaged["passed"])
            self.assertIn("empty normalized project-resource inventory", packaged["failures"])

    def test_missing_required_souq_resource_fails(self) -> None:
        temporary, fixture = self.fixture()
        with temporary:
            missing = "scenes/manama_souq_vertical_slice.tscn"
            fixture.remove_logical_resource(missing)
            result, _, packaged, _ = fixture.inspect()
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(packaged["required_vertical_slice_resources"][missing])

    def test_missing_karak_mission_or_hud_resource_fails(self) -> None:
        for missing in ("scripts/karak_delivery_mission.gd", "scenes/karak_delivery_hud.tscn"):
            with self.subTest(missing=missing):
                temporary, fixture = self.fixture()
                with temporary:
                    fixture.remove_logical_resource(missing)
                    result, _, packaged, _ = fixture.inspect()
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(packaged["required_vertical_slice_resources"][missing])

    def test_declared_remap_target_absence_fails(self) -> None:
        temporary, fixture = self.fixture()
        with temporary:
            alias = next(item for item in fixture.aliases if item.get("remap_target"))
            missing_target = str(alias["remap_target"])
            broken_aliases = [dict(item) for item in fixture.aliases]
            broken = next(item for item in broken_aliases if item.get("remap_target") == missing_target)
            broken["target_verified"] = False
            raw_files = set(fixture.raw_files)
            raw_files.remove(missing_target)
            fixture.write_apk(omitted_assets={missing_target})
            fixture.write_inventory(
                raw_files=raw_files,
                aliases=broken_aliases,
                passed=False,
                remap_failures=[{"remap_target": missing_target, "target_verified": False}],
            )
            result, _, packaged, _ = fixture.inspect()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unverified or missing remap target", packaged["failures"])

    def test_missing_declared_matrix_asset_fails(self) -> None:
        temporary, fixture = self.fixture()
        with temporary:
            missing = MATRIX_PATHS[-1]
            fixture.remove_logical_resource(missing)
            result, _, packaged, _ = fixture.inspect()
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(packaged["full_asset_matrix_manifest_glb_count"], 436)
            self.assertEqual(packaged["full_asset_matrix_packaged_count"], 435)
            self.assertEqual(packaged["full_asset_matrix_missing"], [missing])

    def test_physical_pck_is_detected_but_optional(self) -> None:
        temporary, fixture = self.fixture()
        with temporary:
            fixture.write_apk(extra_entries=[("assets/optional.pck", b"GDPCpayload")])
            result, archive, _, _ = fixture.inspect()
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(archive["standalone_pck_paths"], ["assets/optional.pck"])

    def test_duplicate_unsafe_and_nested_apk_paths_still_fail(self) -> None:
        cases = {
            "duplicate": [("classes.dex", b"duplicate")],
            "unsafe": [("assets/../escape.txt", b"unsafe")],
            "nested": [("assets/nested.apk", b"nested")],
        }
        for name, entries in cases.items():
            with self.subTest(name=name):
                temporary, fixture = self.fixture()
                with temporary:
                    fixture.write_apk(extra_entries=entries)
                    result, archive, _, _ = fixture.inspect()
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(archive["passed"])

    def test_signing_verification_and_qa_identity_are_mandatory(self) -> None:
        for valid, qa in ((False, True), (True, False)):
            with self.subTest(valid=valid, qa=qa):
                temporary, fixture = self.fixture()
                with temporary:
                    fixture.write_signing(valid=valid, qa=qa)
                    result, _, _, record = fixture.inspect()
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(record["passed"])

    def test_workflow_retains_two_independent_exports_and_fail_closed_comparison(self) -> None:
        workflow = GATE4.read_text(encoding="utf-8")
        self.assertIn("export_primary:", workflow)
        self.assertIn("export_secondary:", workflow)
        self.assertIn("needs: [export_primary, export_secondary]", workflow)
        self.assertNotIn("always() && needs.export_primary", workflow)
        self.assertNotIn("continue-on-error: true", workflow)


if __name__ == "__main__":
    unittest.main(verbosity=2)
