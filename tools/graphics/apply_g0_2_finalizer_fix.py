#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

FINALIZER = Path("tools/graphics/finalize_g0_2_android_evidence.py")
TEST = Path("tests/graphics/test_finalize_g0_2_android_evidence.py")

text = FINALIZER.read_text(encoding="utf-8")
text = text.replace(
    "from PIL import Image, ImageChops, ImageEnhance, ImageOps\n",
    "from PIL import Image, ImageChops, ImageEnhance, ImageOps, UnidentifiedImageError\n",
)
text = text.replace(
'''        try:\n            return cast(match.group(1))\n        except (TypeError, ValueError):\n            return match.group(1)\n''',
'''        captured = match.group(1) if match.lastindex else match.group(0)\n        try:\n            return cast(captured)\n        except (TypeError, ValueError):\n            return captured\n''',
)

old_image = '''def image_report(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"exists": path.is_file(), "valid_non_black": False}
    if not path.is_file():
        return result
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        gray = rgb.convert("L")
        pixels = list(gray.getdata())
        average = sum(pixels) / (len(pixels) * 255.0) if pixels else 0.0
        black_ratio = sum(1 for value in pixels if value <= 5) / len(pixels) if pixels else 1.0
        small = gray.resize((8, 8), Image.Resampling.LANCZOS)
        small_values = list(small.getdata())
        threshold = sum(small_values) / len(small_values)
        bits = "".join("1" if value >= threshold else "0" for value in small_values)
        phash = f"{int(bits, 2):016x}"
        result.update({
            "width": rgb.width,
            "height": rgb.height,
            "average_luminance": average,
            "black_pixel_ratio": black_ratio,
            "perceptual_hash": phash,
            "sha256": sha256(path),
            "valid_non_black": rgb.size == (1920, 1080) and average > 0.005 and black_ratio < 0.98,
        })
    return result
'''
new_image = '''def materialize_screenshot(source: Path, target: Path) -> bool:
    """Retain captured evidence or create an explicit non-evidence placeholder."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_file() and source.stat().st_size > 0:
        shutil.copy2(source, target)
        return True
    Image.new("RGB", (1920, 1080), "black").save(target)
    return False


def image_report(path: Path, *, source_evidence_present: bool | None = None) -> dict[str, Any]:
    output_present = path.is_file() and path.stat().st_size > 0
    evidence_present = output_present if source_evidence_present is None else bool(source_evidence_present)
    result: dict[str, Any] = {
        "exists": evidence_present,
        "source_evidence_present": evidence_present,
        "output_file_present": output_present,
        "placeholder": output_present and not evidence_present,
        "valid_non_black": False,
    }
    if not output_present:
        result["error"] = "missing_or_empty_png"
        return result
    try:
        with Image.open(path) as image:
            rgb = image.convert("RGB")
            gray = rgb.convert("L")
            pixels = list(gray.getdata())
            average = sum(pixels) / (len(pixels) * 255.0) if pixels else 0.0
            black_ratio = sum(1 for value in pixels if value <= 5) / len(pixels) if pixels else 1.0
            small = gray.resize((8, 8), Image.Resampling.LANCZOS)
            small_values = list(small.getdata())
            threshold = sum(small_values) / len(small_values) if small_values else 0.0
            bits = "".join("1" if value >= threshold else "0" for value in small_values)
            result.update({
                "width": rgb.width,
                "height": rgb.height,
                "average_luminance": average,
                "black_pixel_ratio": black_ratio,
                "perceptual_hash": f"{int(bits, 2):016x}" if bits else None,
                "sha256": sha256(path),
                "valid_non_black": evidence_present and rgb.size == (1920, 1080) and average > 0.005 and black_ratio < 0.98,
            })
    except (UnidentifiedImageError, OSError) as exc:
        result.update({"error": f"invalid_png:{exc}", "sha256": sha256(path)})
    return result
'''
if "def materialize_screenshot" not in text:
    if old_image not in text:
        raise SystemExit("image-report authority block not found")
    text = text.replace(old_image, new_image, 1)

old_copy = '''    for source_name, target_name in (
        ("state_machine.json", "state_machine.json"),
        ("logcat_full.txt", "logcat_full.txt"),
        ("logcat_critical.txt", "logcat_critical.txt"),
        ("screenshot.png", "screenshot.png"),
    ):
        source = raw_dir / source_name
        if source.is_file():
            shutil.copy2(source, out_dir / target_name)
        else:
            (out_dir / target_name).write_bytes(b"") if target_name.endswith(".png") else (out_dir / target_name).write_text("")
'''
new_copy = '''    for source_name, target_name in (
        ("state_machine.json", "state_machine.json"),
        ("logcat_full.txt", "logcat_full.txt"),
        ("logcat_critical.txt", "logcat_critical.txt"),
    ):
        source = raw_dir / source_name
        target = out_dir / target_name
        if source.is_file() and source.stat().st_size > 0:
            shutil.copy2(source, target)
        elif target_name == "logcat_critical.txt":
            target.write_text(
                "NOT_CAPTURED: candidate stopped before the critical-log-scan state; no absence-of-errors claim is made.\\n",
                encoding="utf-8",
            )
        else:
            target.write_text("NOT_CAPTURED: source evidence file is absent.\\n", encoding="utf-8")
    screenshot_source_present = materialize_screenshot(raw_dir / "screenshot.png", out_dir / "screenshot.png")
'''
if "screenshot_source_present = materialize_screenshot" not in text:
    if old_copy not in text:
        raise SystemExit("candidate-copy authority block not found")
    text = text.replace(old_copy, new_copy, 1)
text = text.replace(
    '    screenshot = image_report(out_dir / "screenshot.png")\n',
    '    screenshot = image_report(out_dir / "screenshot.png", source_evidence_present=screenshot_source_present)\n',
    1,
)

old_launch = '''    launch = parse_am_start(read_text(raw_dir / "am-start.txt"))
    liveness = read_json(raw_dir / "liveness.json", {})
    launch_start = int(liveness.get("launch_start_epoch_ms") or 0)
    visible = int(liveness.get("first_visible_window_epoch_ms") or 0)
    launch.update({
        "resolved_component": package_report["resolved_component"],
        "process_created": bool(liveness.get("initial_pid")),
        "initial_pid": liveness.get("initial_pid"),
        "final_pid": liveness.get("final_pid"),
        "process_remained_alive_60s": bool(liveness.get("process_remained_alive_60s")),
        "first_visible_window_time_ms": visible - launch_start if visible and launch_start else None,
    })
'''
new_launch = '''    launch = parse_am_start(read_text(raw_dir / "am-start.txt"))
    machine = read_json(raw_dir / "state_machine.json", {"states": []})
    states = state_map(machine)
    liveness = read_json(raw_dir / "liveness.json", {})
    launch_start = int(liveness.get("launch_start_epoch_ms") or 0)
    visible = int(liveness.get("first_visible_window_epoch_ms") or 0)
    launch.update({
        "resolved_component": package_report["resolved_component"],
        "process_created": is_pass(states, "PROCESS_CREATED"),
        "initial_pid": liveness.get("initial_pid") or (read_text(raw_dir / "pid-initial.txt").strip() or None),
        "final_pid": liveness.get("final_pid"),
        "process_remained_alive_60s": liveness.get("process_remained_alive_60s") if liveness else None,
        "window_became_visible": is_pass(states, "WINDOW_VISIBLE"),
        "first_visible_window_time_ms": visible - launch_start if visible and launch_start else None,
    })
'''
if "machine = read_json(raw_dir / \"state_machine.json\"" not in text:
    if old_launch not in text:
        raise SystemExit("launch-report authority block not found")
    text = text.replace(old_launch, new_launch, 1)
text = text.replace(
    '        "window_became_visible": state_map(read_json(raw_dir / "state_machine.json", {"states": []})).get("WINDOW_VISIBLE", {}).get("result") == "PASS",\n',
    '        "window_became_visible": launch["window_became_visible"],\n',
    1,
)

old_compare_sig = 'def compare_screenshots(gl_path: Path, mobile_path: Path, output_root: Path) -> dict[str, Any]:\n'
new_compare_sig = '''def compare_screenshots(
    gl_path: Path,
    mobile_path: Path,
    output_root: Path,
    *,
    gl_report: dict[str, Any] | None = None,
    mobile_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
'''
text = text.replace(old_compare_sig, new_compare_sig, 1)
text = text.replace(
    '        "gl": image_report(gl_path),\n        "mobile": image_report(mobile_path),\n',
    '        "gl": gl_report or image_report(gl_path),\n        "mobile": mobile_report or image_report(mobile_path),\n',
    1,
)
text = text.replace(
'''    if not gl_path.is_file() or not mobile_path.is_file():
        write_json(output_root / "screenshot_comparison.json", result)
        Image.new("RGB", (1920, 1080), "black").save(output_root / "screenshot_difference.png")
        Image.new("RGB", (3840, 1080), "black").save(output_root / "screenshot_side_by_side.png")
        return result
''',
'''    if not result["gl"].get("valid_non_black") or not result["mobile"].get("valid_non_black"):
        result.update({
            "comparison_performed": False,
            "comparison_reason": "both captured, valid, non-black screenshots are required",
        })
        write_json(output_root / "screenshot_comparison.json", result)
        Image.new("RGB", (1920, 1080), "black").save(output_root / "screenshot_difference.png")
        Image.new("RGB", (3840, 1080), "black").save(output_root / "screenshot_side_by_side.png")
        return result
''',
    1,
)
text = text.replace(
    '            "dimensions_equal": gl.size == mobile.size,\n',
    '            "dimensions_equal": gl.size == mobile.size,\n            "comparison_performed": True,\n',
    1,
)
text = text.replace(
'''    comparison = compare_screenshots(output_root / "gl_compatibility/screenshot.png", output_root / "mobile_vulkan/screenshot.png", output_root)
''',
'''    comparison = compare_screenshots(
        output_root / "gl_compatibility/screenshot.png",
        output_root / "mobile_vulkan/screenshot.png",
        output_root,
        gl_report=results["gl_compatibility"]["runtime"]["screenshot"],
        mobile_report=results["mobile_vulkan"]["runtime"]["screenshot"],
    )
''',
    1,
)
FINALIZER.write_text(text, encoding="utf-8")

TEST.write_text('''#!/usr/bin/env python3
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
        report=module.parse_am_start("Status: ok\\nActivity: com.example/.Main\\nTotalTime: 819\\nWaitTime: 828\\nComplete\\n")
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
''', encoding="utf-8")
