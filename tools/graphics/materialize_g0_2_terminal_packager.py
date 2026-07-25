#!/usr/bin/env python3
from pathlib import Path
import base64
import gzip

root = Path(__file__).resolve().parent
payload = root / "package_g0_2_terminal.py.gz.b64"
target = root / "package_g0_2_terminal.py"
if not payload.is_file():
    raise SystemExit(f"missing terminal packager payload: {payload}")
target.write_bytes(gzip.decompress(base64.b64decode(payload.read_text().strip())))
target.chmod(0o755)
