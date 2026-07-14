#!/usr/bin/env python3
"""Launch an authority generator with its sibling modules importable in Blender."""

from __future__ import annotations

import os
from pathlib import Path
import runpy
import sys


def main() -> int:
    raw_target = os.environ.get("BAHRAIN_BRICK_BLENDER_SCRIPT", "")
    target = Path(raw_target).resolve()
    if not raw_target or target.suffix != ".py" or not target.is_file():
        raise SystemExit("BAHRAIN_BRICK_BLENDER_SCRIPT must identify an existing Python file")
    sys.path.insert(0, str(target.parent))
    runpy.run_path(str(target), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
