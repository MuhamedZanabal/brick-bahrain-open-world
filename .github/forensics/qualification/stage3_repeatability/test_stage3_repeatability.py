# Self-verifying compressed test payload.
import base64
import hashlib
import zlib
from pathlib import Path
_PAYLOAD_SHA256 = "92b6b075ebfd0482030b78649c52b9ee5e1c89fd0468c270f666a401c466ce35"
_encoded = (Path(__file__).resolve().parent / "test_repeatability_payload.b64").read_text(encoding="ascii").strip()
_source = zlib.decompress(base64.b64decode(_encoded))
if hashlib.sha256(_source).hexdigest() != _PAYLOAD_SHA256:
    raise RuntimeError("test payload SHA-256 mismatch")
exec(compile(_source, __file__, "exec"))
