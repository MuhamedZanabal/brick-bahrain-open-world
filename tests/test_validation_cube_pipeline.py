import json
import struct
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_glb(path: Path, *, bounds=(-0.5, 0.5), material_count=1):
    lo, hi = bounds
    document = {
        "asset": {"version": "2.0", "generator": "test"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": "bb_validation_cube_1m", "mesh": 0}],
        "meshes": [{"name": "bb_validation_cube_1m", "primitives": [{"attributes": {"POSITION": 0}, "indices": 1, "material": 0}]}],
        "materials": [{"name": "bb_validation_cube_material"}] * material_count,
        "accessors": [
            {"componentType": 5126, "count": 24, "type": "VEC3", "min": [lo, lo, lo], "max": [hi, hi, hi]},
            {"componentType": 5123, "count": 36, "type": "SCALAR"},
        ],
        "buffers": [{"byteLength": 0}],
    }
    payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
    payload += b" " * ((4 - len(payload) % 4) % 4)
    total = 12 + 8 + len(payload)
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, total) + struct.pack("<II", len(payload), 0x4E4F534A) + payload)


class ValidationCubePipelineTests(unittest.TestCase):
    def test_generator_contract_is_one_meter_deterministic_cube(self):
        source = (ROOT / "tools/asset_lab/generate_validation_cube.py").read_text(encoding="utf-8")
        for required in (
            "bb_validation_cube_1m",
            "size=1.0",
            "unit_settings.system = \"METRIC\"",
            "bpy.ops.wm.save_as_mainfile",
            "bpy.ops.export_scene.gltf",
            "export_format=\"GLB\"",
            "export_yup=True",
        ):
            self.assertIn(required, source)

    def test_valid_one_meter_cube_passes_independent_validation(self):
        from tools.asset_lab.validate_glb_asset import validate_glb

        with tempfile.TemporaryDirectory() as temp_dir:
            glb = Path(temp_dir) / "cube.glb"
            build_glb(glb)
            result = validate_glb(glb, expected_name="bb_validation_cube_1m", expected_size=1.0)
            self.assertTrue(result["passed"], result)
            self.assertEqual(result["triangle_count"], 12)
            self.assertEqual(result["mesh_count"], 1)
            self.assertEqual(result["material_count"], 1)

    def test_wrong_bounds_fail_independent_validation(self):
        from tools.asset_lab.validate_glb_asset import validate_glb

        with tempfile.TemporaryDirectory() as temp_dir:
            glb = Path(temp_dir) / "cube.glb"
            build_glb(glb, bounds=(-1.0, 1.0))
            result = validate_glb(glb, expected_name="bb_validation_cube_1m", expected_size=1.0)
            self.assertFalse(result["passed"])
            self.assertIn("bounds", result["failures"])

    def test_extra_material_fails_independent_validation(self):
        from tools.asset_lab.validate_glb_asset import validate_glb

        with tempfile.TemporaryDirectory() as temp_dir:
            glb = Path(temp_dir) / "cube.glb"
            build_glb(glb, material_count=2)
            result = validate_glb(glb, expected_name="bb_validation_cube_1m", expected_size=1.0)
            self.assertFalse(result["passed"])
            self.assertIn("material_count", result["failures"])


if __name__ == "__main__":
    unittest.main()
