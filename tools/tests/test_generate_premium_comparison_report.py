from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

MODULE = Path(__file__).resolve().parents[1] / "generate_premium_comparison_report.py"
spec = importlib.util.spec_from_file_location("comparison", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class ComparisonReportTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, Path]:
        baseline = root / "baseline"
        premium = root / "premium"
        before = baseline / "build/premium_visual_evidence/before"
        after = premium / "build/premium_visual_evidence/after"
        before.mkdir(parents=True)
        after.mkdir(parents=True)
        runtime = {"captures": [], "performance_summary": {"sample_count": 8}}
        (before / "PREMIUM_WORLD_VISUAL_EVIDENCE.json").write_text(json.dumps(runtime))
        (after / "PREMIUM_WORLD_VISUAL_EVIDENCE.json").write_text(json.dumps(runtime))
        for index, name in enumerate(mod.CAPTURE_NAMES):
            Image.new("RGB", mod.EXPECTED_SIZE, (index, index + 1, index + 2)).save(
                before / f"{name}.png"
            )
            Image.new("RGB", mod.EXPECTED_SIZE, (index + 3, index + 4, index + 5)).save(
                after / f"{name}.png"
            )
        return baseline, premium

    def test_generates_all_comparisons_and_report(self):
        with tempfile.TemporaryDirectory() as temp:
            baseline, premium = self.fixture(Path(temp))
            report_path = premium / "build/reports/report.json"
            report = mod.generate(baseline, premium, report_path)
            self.assertEqual(report["conclusion"], "pass")
            self.assertEqual(report["generated_comparison_count"], 8)
            self.assertEqual(len(report["inputs"]), 16)
            self.assertTrue(report_path.is_file())
            for name in mod.CAPTURE_NAMES:
                output = premium / f"build/premium_visual_evidence/comparisons/{name}_before_after.png"
                self.assertTrue(output.is_file())
                with Image.open(output) as image:
                    self.assertEqual(image.size, (2560, 760))

    def test_missing_baseline_image_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            baseline, premium = self.fixture(Path(temp))
            (baseline / "build/premium_visual_evidence/before/city_road.png").unlink()
            with self.assertRaisesRegex(RuntimeError, "baseline city_road image missing or empty"):
                mod.generate(baseline, premium, premium / "build/reports/report.json")

    def test_corrupt_premium_image_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            baseline, premium = self.fixture(Path(temp))
            target = premium / "build/premium_visual_evidence/after/waterfront.png"
            target.write_bytes(b"not a png")
            with self.assertRaisesRegex(RuntimeError, "premium waterfront image unreadable"):
                mod.generate(baseline, premium, premium / "build/reports/report.json")

    def test_dimension_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            baseline, premium = self.fixture(Path(temp))
            Image.new("RGB", (640, 360)).save(
                premium / "build/premium_visual_evidence/after/vehicle.png"
            )
            with self.assertRaisesRegex(RuntimeError, "premium vehicle image dimensions mismatch"):
                mod.generate(baseline, premium, premium / "build/reports/report.json")


if __name__ == "__main__":
    unittest.main()
