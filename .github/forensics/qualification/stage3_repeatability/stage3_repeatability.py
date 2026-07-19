#!/usr/bin/env python3
# Self-verifying compressed Stage 3 analyzer payload.
import base64
import hashlib
import zlib
from pathlib import Path

_PAYLOAD_SHA256 = "fbed7e3276816502ac9af15f3e3a3b5a7840f81ae71066671b2873421ce97214"
_root = Path(__file__).resolve().parent
_encoded = "".join(path.read_text(encoding="ascii").strip() for path in sorted(_root.glob("payload_*.b64")))
_source = zlib.decompress(base64.b64decode(_encoded))
if hashlib.sha256(_source).hexdigest() != _PAYLOAD_SHA256:
    raise RuntimeError("Stage 3 analyzer payload SHA-256 mismatch")
exec(compile(_source, __file__, "exec"))
