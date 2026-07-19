import re
import unittest
from pathlib import Path

GITHUB_ROOT = Path(__file__).parents[3]
WORKFLOW = GITHUB_ROOT / "workflows" / "godot-engine-qualification-stage4-full-corpus.yml"
SHARD_ACTION = GITHUB_ROOT / "actions" / "stage4-upload-shards" / "action.yml"


class Stage4WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.shards = SHARD_ACTION.read_text(encoding="utf-8")

    def test_exact_jobs_exist(self):
        for job in (
            "record_locator",
            "contracts",
            "prepare_authority",
            "prepare_sidecars",
            "import_d1",
            "import_d2",
            "compare_shards",
            "aggregate_stage4",
        ):
            self.assertRegex(self.text, rf"(?m)^  {job}:$")

    def test_exact_frozen_authorities(self):
        for value in (
            "5b4e2466ef84f3984f3bf336b31925d4d2e97a7f",
            "b12e1e012e256036e71066260a4c6392d26c3839",
            "ba937afa335170ccaa726297fc23712a44e3295689a86640e1c1dbe6165701ab",
            "e0cfa6604569c13e1d75b2439d6936b7e2423ad5ba3715f033200335e864bc4e",
            "6aa202e2298fa514bfdb2ba10fd66237cc2d15005cdb2d6316a57d847ece8eff",
            "4.4.1.stable.official.49a5bc7b6",
            "54215149d52efb1d653a3dec39d0993587bdf5daa2c56e787b5ee88417fb1339",
        ):
            self.assertIn(value, self.text)

    def test_exact_shard_matrix_and_bounded_parallelism(self):
        values = re.findall(r"(?m)^          - '(\d\d)'$", self.text)
        self.assertEqual(values, [f"{i:02d}" for i in range(40)])
        match = re.search(r"(?m)^      max-parallel: (\d+)$", self.text)
        self.assertIsNotNone(match)
        self.assertLessEqual(int(match.group(1)), 8)

    def test_independent_roots_and_runner_jobs(self):
        self.assertIn("/tmp/bahrain-stage4-d1/project", self.text)
        self.assertIn("/tmp/bahrain-stage4-d2-different-absolute-root/project", self.text)
        self.assertRegex(self.text, r"(?ms)^  import_d1:.*?runs-on: ubuntu-24.04")
        self.assertRegex(self.text, r"(?ms)^  import_d2:.*?runs-on: ubuntu-24.04")

    def test_exact_forty_shard_uploads_called_for_both_imports(self):
        self.assertEqual(self.text.count("uses: ./tooling/.github/actions/stage4-upload-shards"), 2)
        names = re.findall(r"(?m)^    - name: Upload shard (\d\d)$", self.shards)
        self.assertEqual(names, [f"{i:02d}" for i in range(40)])
        self.assertEqual(self.shards.count("uses: actions/upload-artifact@65462800fd760344b1a7b4382951275a0abb4808"), 40)
        self.assertEqual(self.shards.count("if: always()"), 40)
        self.assertEqual(self.shards.count("include-hidden-files: true"), 40)

    def test_every_main_upload_is_unconditional_and_pinned(self):
        blocks = self.text.split("uses: actions/upload-artifact@")
        self.assertEqual(len(blocks) - 1, 7)
        for block in blocks[1:]:
            self.assertIn("65462800fd760344b1a7b4382951275a0abb4808", block[:160])
        lines = self.text.splitlines()
        for index, line in enumerate(lines):
            if "uses: actions/upload-artifact@" in line:
                self.assertTrue(any("if: always()" in lines[j] for j in range(max(0, index - 3), index + 1)))

    def test_prohibitions(self):
        lowered = (self.text + self.shards).lower()
        for forbidden in (
            "4.5.2-stable",
            "4.6.3-stable",
            "--export-pack",
            "--export-debug",
            "--export-release",
            "gradle",
            "adb ",
            "android sdk",
            ".apk",
            ".aab",
        ):
            self.assertNotIn(forbidden, lowered)

    def test_only_workflow_path_triggers(self):
        self.assertIn("paths: [.github/workflows/godot-engine-qualification-stage4-full-corpus.yml]", self.text)


if __name__ == "__main__":
    unittest.main()
