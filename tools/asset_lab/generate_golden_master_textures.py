#!/usr/bin/env python3
"""Generate project-owned deterministic albedo textures for golden masters."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from golden_master_materials import MATERIAL_KEYS, PROFILE_SETTINGS, material_spec

DEFAULT_TEXTURE_SEED = 140500


def texture_plan(output_dir: Path, seed: int) -> dict[str, Any]:
    if seed != DEFAULT_TEXTURE_SEED:
        raise ValueError(f"golden-master textures require recorded seed {DEFAULT_TEXTURE_SEED}, received {seed}")
    outputs = []
    for profile, settings in PROFILE_SETTINGS.items():
        for material_key in MATERIAL_KEYS:
            outputs.append(
                {
                    "profile": profile,
                    "material_key": material_key,
                    "resolution": settings["texture_resolution"],
                    "seed": seed + int(hashlib.sha256(f"{profile}:{material_key}".encode()).hexdigest()[:8], 16),
                    "path": (output_dir / profile / f"{material_key}_albedo.png").as_posix(),
                }
            )
    outputs.sort(key=lambda record: record["path"])
    return {"seed": seed, "texture_count": len(outputs), "outputs": outputs}


def _stable_noise(material_key: str, x: int, y: int, seed: int) -> float:
    payload = f"{seed}:{material_key}:{x}:{y}".encode("utf-8")
    value = int(hashlib.sha256(payload).hexdigest()[:8], 16)
    return value / 0xFFFFFFFF


def pixel_rgb(material_key: str, x: int, y: int, size: int, seed: int) -> tuple[int, int, int]:
    if material_key not in MATERIAL_KEYS:
        raise KeyError(material_key)
    if size <= 0:
        raise ValueError("size must be positive")
    base = material_spec("balanced", material_key)["base_color"]
    noise = _stable_noise(material_key, x, y, seed) - 0.5
    wave = math.sin((x + 1) * 0.23 + (y + 1) * 0.11) * 0.5
    strength = {
        "sand_plaster": 0.075,
        "limestone": 0.060,
        "dark_timber": 0.095,
        "painted_metal": 0.025,
        "blue_glass": 0.040,
        "souq_gold": 0.070,
        "promenade_paving": 0.050,
        "signage_accent": 0.035,
    }[material_key]
    if material_key == "dark_timber":
        modulation = noise * 0.45 + wave * 0.55
    elif material_key == "blue_glass":
        modulation = noise * 0.25 + ((y / max(1, size - 1)) - 0.5) * 0.75
    else:
        modulation = noise * 0.8 + wave * 0.2
    return tuple(max(0, min(255, round((channel + modulation * strength) * 255))) for channel in base)


def _draw_material_pattern(image: Any, material_key: str, seed: int) -> None:
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    rng = random.Random(seed)
    if material_key == "dark_timber":
        spacing = max(8, width // 28)
        for x in range(0, width, spacing):
            drift = rng.randint(-2, 2)
            draw.line((x + drift, 0, x - drift, height), fill=(30, 12, 5, 85), width=max(1, width // 512))
            if x + spacing // 2 < width:
                draw.line((x + spacing // 2, 0, x + spacing // 2, height), fill=(105, 55, 20, 38), width=1)
    elif material_key in {"limestone", "promenade_paving"}:
        cell_w = max(32, width // (6 if material_key == "limestone" else 9))
        cell_h = max(24, height // (9 if material_key == "limestone" else 12))
        line = (60, 52, 42, 55) if material_key == "limestone" else (45, 45, 45, 70)
        for y in range(0, height, cell_h):
            offset = (cell_w // 2) if (y // cell_h) % 2 else 0
            draw.line((0, y, width, y), fill=line, width=max(1, width // 768))
            for x in range(-offset, width, cell_w):
                draw.line((x, y, x, min(height, y + cell_h)), fill=line, width=max(1, width // 768))
    elif material_key == "sand_plaster":
        count = max(120, width * height // 1800)
        for _ in range(count):
            x, y = rng.randrange(width), rng.randrange(height)
            r = max(1, width // 700)
            alpha = rng.randint(10, 32)
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(90, 68, 45, alpha))
    elif material_key == "painted_metal":
        for y in range(0, height, max(12, height // 48)):
            draw.line((0, y, width, y), fill=(255, 255, 255, 8), width=1)
    elif material_key == "blue_glass":
        band = max(12, width // 14)
        for x in range(0, width, band):
            draw.rectangle((x, 0, min(width, x + band // 3), height), fill=(130, 205, 220, 18))
    elif material_key == "souq_gold":
        count = max(180, width * height // 1200)
        for _ in range(count):
            x, y = rng.randrange(width), rng.randrange(height)
            shade = rng.choice([(255, 220, 90, 30), (75, 40, 5, 25)])
            draw.point((x, y), fill=shade)
    elif material_key == "signage_accent":
        stripe = max(12, height // 18)
        for y in range(0, height, stripe * 2):
            draw.rectangle((0, y, width, min(height, y + stripe)), fill=(255, 255, 255, 7))


def generate_textures(output_dir: Path, seed: int) -> dict[str, Any]:
    from PIL import Image

    plan = texture_plan(output_dir, seed)
    produced: list[dict[str, Any]] = []
    for record in plan["outputs"]:
        resolution = record["resolution"]
        sample_size = 64
        pixels = [
            pixel_rgb(record["material_key"], x, y, sample_size, record["seed"])
            for y in range(sample_size)
            for x in range(sample_size)
        ]
        sample = Image.new("RGB", (sample_size, sample_size))
        sample.putdata(pixels)
        image = sample.resize((resolution, resolution), resample=Image.Resampling.BICUBIC).convert("RGBA")
        _draw_material_pattern(image, record["material_key"], record["seed"])
        path = Path(record["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        image.convert("RGB").save(path, format="PNG", optimize=True)
        produced.append(
            {
                **record,
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return {"seed": seed, "texture_count": len(produced), "outputs": produced}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=DEFAULT_TEXTURE_SEED)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = generate_textures(args.output_dir, args.seed)
    if report["texture_count"] != 24:
        raise RuntimeError(f"expected 24 textures, generated {report['texture_count']}")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
