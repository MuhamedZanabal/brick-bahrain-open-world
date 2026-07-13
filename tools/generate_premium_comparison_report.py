#!/usr/bin/env python3
"""Generate matched premium visual comparisons with fail-closed diagnostics."""
from __future__ import annotations

import argparse
import hashlib
import json
import traceback
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageStat

CAPTURE_NAMES = (
    "city_road",
    "waterfront",
    "building_area",
    "daylight",
    "player_character",
    "vehicle",
    "hud_walking",
    "hud_vehicle",
)
EXPECTED_SIZE = (1280, 720)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, label: str) -> Any:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"{label} JSON missing or empty: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        raise RuntimeError(f"{label} JSON invalid: {path}: {error}") from error


def load_rgb(path: Path, label: str) -> Image.Image:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"{label} image missing or empty: {path}")
    try:
        with Image.open(path) as source:
            source.load()
            image = source.convert("RGB")
    except Exception as error:
        raise RuntimeError(f"{label} image unreadable: {path}: {error}") from error
    if image.size != EXPECTED_SIZE:
        raise RuntimeError(
            f"{label} image dimensions mismatch: {path}: expected={EXPECTED_SIZE}, actual={image.size}"
        )
    return image


def image_stats(image: Image.Image) -> dict[str, float]:
    sample = image.resize((160, 90))
    pixels = list(sample.getdata())
    total = len(pixels)
    return {
        "mean_luminance": round(sum(ImageStat.Stat(sample).mean) / 3, 3),
        "near_white_ratio": round(
            sum(1 for red, green, blue in pixels if min(red, green, blue) > 246) / total,
            6,
        ),
        "near_black_ratio": round(
            sum(1 for red, green, blue in pixels if max(red, green, blue) < 12) / total,
            6,
        ),
    }


def generate(baseline: Path, premium: Path, report_path: Path) -> dict[str, Any]:
    before = baseline / "build/premium_visual_evidence/before"
    after = premium / "build/premium_visual_evidence/after"
    comparison_dir = premium / "build/premium_visual_evidence/comparisons"
    comparison_dir.mkdir(parents=True, exist_ok=True)

    baseline_runtime_path = before / "PREMIUM_WORLD_VISUAL_EVIDENCE.json"
    premium_runtime_path = after / "PREMIUM_WORLD_VISUAL_EVIDENCE.json"
    baseline_runtime = load_json(baseline_runtime_path, "baseline runtime")
    premium_runtime = load_json(premium_runtime_path, "premium runtime")

    metrics: list[dict[str, Any]] = []
    inputs: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []
    for name in CAPTURE_NAMES:
        before_path = before / f"{name}.png"
        after_path = after / f"{name}.png"
        before_image = load_rgb(before_path, f"baseline {name}")
        after_image = load_rgb(after_path, f"premium {name}")
        inputs.extend(
            [
                {
                    "role": "before",
                    "view": name,
                    "path": str(before_path),
                    "size_bytes": before_path.stat().st_size,
                    "sha256": sha256(before_path),
                },
                {
                    "role": "after",
                    "view": name,
                    "path": str(after_path),
                    "size_bytes": after_path.stat().st_size,
                    "sha256": sha256(after_path),
                },
            ]
        )

        combined = Image.new("RGB", (2560, 760), (18, 18, 22))
        combined.paste(before_image, (0, 40))
        combined.paste(after_image, (1280, 40))
        draw = ImageDraw.Draw(combined)
        draw.text((20, 12), f"BEFORE - v1.4.0.3 - {name}", fill="white")
        draw.text((1300, 12), f"AFTER - v1.4.0.4 - {name}", fill="white")
        output_path = comparison_dir / f"{name}_before_after.png"
        combined.save(output_path, format="PNG", optimize=True)
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise RuntimeError(f"comparison output missing or empty: {output_path}")
        with Image.open(output_path) as check:
            check.load()
            if check.size != (2560, 760):
                raise RuntimeError(
                    f"comparison output dimensions mismatch: {output_path}: actual={check.size}"
                )
        outputs.append(
            {
                "view": name,
                "path": str(output_path),
                "size_bytes": output_path.stat().st_size,
                "sha256": sha256(output_path),
            }
        )
        metrics.append(
            {"view": name, "before": image_stats(before_image), "after": image_stats(after_image)}
        )

    report = {
        "conclusion": "pass",
        "classification": "hosted GL Compatibility/software rendering; not physical Android performance",
        "expected_capture_count": len(CAPTURE_NAMES),
        "generated_comparison_count": len(outputs),
        "views": metrics,
        "inputs": inputs,
        "outputs": outputs,
        "baseline_runtime": baseline_runtime,
        "premium_runtime": premium_runtime,
        "baseline_runtime_sha256": sha256(baseline_runtime_path),
        "premium_runtime_sha256": sha256(premium_runtime_path),
        "physical_android_tested": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("premium", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--diagnostic", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = generate(args.baseline.resolve(), args.premium.resolve(), args.report.resolve())
    except Exception as error:
        diagnostic = {
            "conclusion": "fail",
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
            "baseline": str(args.baseline.resolve()),
            "premium": str(args.premium.resolve()),
        }
        args.diagnostic.parent.mkdir(parents=True, exist_ok=True)
        args.diagnostic.write_text(json.dumps(diagnostic, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({key: value for key, value in diagnostic.items() if key != "traceback"}, indent=2))
        raise
    args.diagnostic.parent.mkdir(parents=True, exist_ok=True)
    args.diagnostic.write_text(
        json.dumps(
            {
                "conclusion": "pass",
                "report": str(args.report.resolve()),
                "generated_comparison_count": report["generated_comparison_count"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"conclusion": "pass", "generated_comparison_count": report["generated_comparison_count"]},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
