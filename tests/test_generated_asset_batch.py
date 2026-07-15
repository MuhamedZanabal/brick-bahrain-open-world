import csv
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.asset_lab.validate_generated_asset_batch import validate_batch


def build_glb(path: Path, asset_id: str, *, collision: bool = True, materials: int = 1):
    nodes = [{"name": f"{asset_id}_mesh", "mesh": 0}]
    meshes = [{"name": f"{asset_id}_mesh", "primitives": [{"attributes": {"POSITION": 0}, "indices": 1, "material": 0}]}]
    if collision:
        nodes.append({"name": f"{asset_id}_mesh_col_box_01", "mesh": 1})
        meshes.append({"name": f"{asset_id}_mesh_col_box_01", "primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]})
    document = {
        "asset": {"version": "2.0", "generator": "test"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": meshes,
        "materials": [{"name": f"material_{i}"} for i in range(materials)],
        "accessors": [
            {"componentType": 5126, "count": 24, "type": "VEC3", "min": [-0.5] * 3, "max": [0.5] * 3},
            {"componentType": 5123, "count": 36, "type": "SCALAR"},
        ],
        "buffers": [{"byteLength": 0}],
    }
    payload = json.dumps(document, separators=(",", ":")).encode()
    payload += b" " * ((4 - len(payload) % 4) % 4)
    total = 20 + len(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, total) + struct.pack("<II", len(payload), 0x4E4F534A) + payload)


class GeneratedAssetBatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.arch = self.root / "architecture"
        self.commercial = self.root / "commercial"
        self.manifest = self.root / "manifest.csv"
        rows = []
        for family, count in {"traditional": 14, "souq": 18, "waterfront": 16}.items():
            for index in range(count):
                asset_id = f"bh_{family}_asset_{index:02d}"
                rows.append({"asset_id": asset_id, "category": "architecture", "subcategory": family})
                for profile in ("low", "balanced", "high"):
                    for lod in (0, 1, 2):
                        build_glb(self.arch / profile / family / f"{asset_id}_lod{lod}.glb", asset_id, collision=lod == 0)
        for asset_id in sorted({
            "bh_cafe_storefront_karak_a_01",
            "bh_cafe_table_chair_set_a_01",
            "bh_supermarket_shelf_1m_01",
            "bh_supermarket_storefront_a_01",
        }):
            rows.append({"asset_id": asset_id, "category": "props", "subcategory": "commercial"})
            build_glb(self.commercial / f"{asset_id}.glb", asset_id)
        with self.manifest.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["asset_id", "category", "subcategory"])
            writer.writeheader(); writer.writerows(rows)

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_complete_batch_passes(self):
        result = validate_batch(self.arch, self.commercial, self.manifest)
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(result["architecture_derivatives"], 432)
        self.assertEqual(result["commercial_derivatives"], 4)
        self.assertEqual(result["validated_assets"], 436)
        self.assertEqual(result["collision_required_count"], result["collision_present_count"])

    def test_missing_lod_fails(self):
        next(self.arch.glob("low/traditional/*_lod2.glb")).unlink()
        result = validate_batch(self.arch, self.commercial, self.manifest)
        self.assertFalse(result["passed"])
        self.assertTrue(any(item.startswith("architecture_derivative_count") or item.startswith("lod_set") for item in result["failures"]))

    def test_missing_lod0_collision_fails(self):
        path = next(self.arch.glob("balanced/souq/*_lod0.glb"))
        asset_id = path.stem.removesuffix("_lod0")
        build_glb(path, asset_id, collision=False)
        result = validate_batch(self.arch, self.commercial, self.manifest)
        self.assertFalse(result["passed"])
        self.assertTrue(any("required_collision" in item for item in result["failures"]))

    def test_manifest_mismatch_fails(self):
        text = self.manifest.read_text(encoding="utf-8")
        self.manifest.write_text(text.replace("architecture,traditional", "props,traditional", 1), encoding="utf-8")
        result = validate_batch(self.arch, self.commercial, self.manifest)
        self.assertFalse(result["passed"])
        self.assertTrue(any(item.startswith("manifest_family_mismatch") for item in result["failures"]))


if __name__ == "__main__":
    unittest.main()
