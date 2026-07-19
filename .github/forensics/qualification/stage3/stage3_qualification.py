#!/usr/bin/env python3
from pathlib import Path

_SOURCE_ROOT = Path(__file__).with_name("source")
_SOURCE = "".join(path.read_text(encoding="utf-8") for path in sorted(_SOURCE_ROOT.glob("part_*.pyfrag")))
exec(compile(_SOURCE, str(_SOURCE_ROOT / "stage3_qualification.py"), "exec"), globals(), globals())
