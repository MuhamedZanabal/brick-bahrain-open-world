#!/usr/bin/env python3
import base64, hashlib, zlib
from pathlib import Path
_PAYLOAD_SHA256="76d75db809d35b7ac99d0320827f9e302ab2d6704c90a0e2ac7c99131befe3d8"
_root=Path(__file__).resolve().parent
_encoded="".join(p.read_text(encoding="ascii").strip() for p in sorted(_root.glob("payload_*.b64")))
_source=zlib.decompress(base64.b64decode(_encoded))
if hashlib.sha256(_source).hexdigest()!=_PAYLOAD_SHA256:
    raise RuntimeError("Stage 4 analyzer payload SHA-256 mismatch")
exec(compile(_source,__file__,"exec"))
