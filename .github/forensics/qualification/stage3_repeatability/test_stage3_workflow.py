# Self-verifying compressed test payload.
import base64
import hashlib
import zlib
from pathlib import Path
_PAYLOAD_SHA256 = "9aa5d79c2428f619eb6984472838639f76179c74409fb0e644715eaa9b7bf2e3"
_encoded = (Path(__file__).resolve().parent / "test_workflow_payload.b64").read_text(encoding="ascii").strip()
_source = zlib.decompress(base64.b64decode(_encoded))
if hashlib.sha256(_source).hexdigest() != _PAYLOAD_SHA256:
    raise RuntimeError("test payload SHA-256 mismatch")
exec(compile(_source, __file__, "exec"))
