#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import tempfile
import unittest
from pathlib import Path
MODULE_PATH=Path(__file__).resolve().parents[2]/"tools/graphics/finalize_g0_2_android_evidence.py"
spec=importlib.util.spec_from_file_location("g02_finalizer",MODULE_PATH)
module=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(module)
class FinalizerParserTest(unittest.TestCase):
    def test_complete_line_without_capture_group(self):
        report=module.parse_am_start("Status: ok\nActivity: com.example/.Main\nTotalTime: 819\nWaitTime: 828\nComplete\n")
        self.assertTrue(report["complete"])
        self.assertEqual(report["status"],"ok")
        self.assertEqual(report["total_time_ms"],819)
        self.assertEqual(report["wait_time_ms"],828)
    def test_missing_screenshot_is_explicit_placeholder(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            retained=module.materialize_screenshot(root/"missing.png",root/"screenshot.png")
            report=module.image_report(root/"screenshot.png",source_evidence_present=retained)
            self.assertFalse(retained)
            self.assertFalse(report["exists"])
            self.assertTrue(report["placeholder"])
            self.assertEqual((report["width"],report["height"]),(1920,1080))
            self.assertFalse(report["valid_non_black"])
    def test_comparison_refuses_placeholder(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); gl=root/"gl.png"; mobile=root/"mobile.png"
            module.Image.new("RGB",(1920,1080),"white").save(gl)
            module.Image.new("RGB",(1920,1080),"black").save(mobile)
            result=module.compare_screenshots(
                gl,mobile,root,
                gl_report=module.image_report(gl,source_evidence_present=True),
                mobile_report=module.image_report(mobile,source_evidence_present=False),
            )
            self.assertFalse(result["comparison_performed"])
            self.assertFalse(result["mobile"]["source_evidence_present"])
if __name__=="__main__": unittest.main()
