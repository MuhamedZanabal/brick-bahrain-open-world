#!/usr/bin/env python3
import hashlib
from pathlib import Path
_SOURCE_SHA256="76d75db809d35b7ac99d0320827f9e302ab2d6704c90a0e2ac7c99131befe3d8"
_root=Path(__file__).resolve().parent
_source=b"".join(path.read_bytes() for path in sorted(_root.glob("source_*.pyfrag")))
if hashlib.sha256(_source).hexdigest()!=_SOURCE_SHA256:
    raise RuntimeError("Stage 4 analyzer source SHA-256 mismatch")
exec(compile(_source,__file__,"exec"))
