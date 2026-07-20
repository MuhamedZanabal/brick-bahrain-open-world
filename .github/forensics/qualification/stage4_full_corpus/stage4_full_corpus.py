#!/usr/bin/env python3
import hashlib
from pathlib import Path
_SOURCE_SHA256="4eee624fcc80d9788def5d04ae1379c5effe273da4eaf315bf2631742aa6a844"
_root=Path(__file__).resolve().parent
_source=b"".join(path.read_bytes() for path in sorted(_root.glob("source_*.pyfrag")))
if hashlib.sha256(_source).hexdigest()!=_SOURCE_SHA256:
    raise RuntimeError("Stage 4 analyzer source SHA-256 mismatch")
exec(compile(_source,__file__,"exec"))
