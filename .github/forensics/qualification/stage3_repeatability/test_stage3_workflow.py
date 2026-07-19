# Self-verifying compressed test payload.
import base64
import hashlib
import zlib
from pathlib import Path
_PAYLOAD_SHA256 = "ef5c24e4f1e7106e8399b11fcdbeab5deabb3cd55f01346de1168eecabfc4eb8"
_encoded = (Path(__file__).resolve().parent / "test_workflow_payload.b64").read_text(encoding="ascii").strip()
_source = zlib.decompress(base64.b64decode(_encoded))
if hashlib.sha256(_source).hexdigest() != _PAYLOAD_SHA256:
    raise RuntimeError("test payload SHA-256 mismatch")
exec(compile(_source, __file__, "exec"))
