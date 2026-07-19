import tempfile
import unittest
from pathlib import Path

import stage2_resource_qualification as q


class Stage2SidecarAuthorityTests(unittest.TestCase):
    def test_sidecar_authority_retains_and_applies_all_source_adjacent_sidecars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            authority = root / "authority"
            (authority / "assets/textures").mkdir(parents=True)
            (authority / "assets/model.glb.import").write_text("model")
            (authority / "assets/textures/a.png.import").write_text("texture")
            evidence = root / "evidence"
            rows = q.retain_sidecar_authority(authority, evidence)
            self.assertEqual([row["path"] for row in rows], [
                "assets/model.glb.import",
                "assets/textures/a.png.import",
            ])
            project = root / "project"
            project.mkdir()
            q.apply_sidecar_authority(evidence, project)
            self.assertEqual((project / "assets/model.glb.import").read_text(), "model")
            self.assertEqual((project / "assets/textures/a.png.import").read_text(), "texture")


if __name__ == "__main__":
    unittest.main()
