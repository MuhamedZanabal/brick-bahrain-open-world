"""Deterministically assemble the v18 correction-tool regression tests."""
from __future__ import annotations

import hashlib
from pathlib import Path

EXPECTED_SOURCE_SHA256 = "c4641fee88ab9403b80b069593a7fd7c938f79e74cd8dd3894c63fe2ff3df604"
PARTS = tuple(Path(__file__).with_name("premium_validation_v18_test_parts") / f"part_{index:02d}.pyfrag" for index in range(5))
missing = [path.as_posix() for path in PARTS if not path.is_file()]
if missing:
    raise RuntimeError(f"premium validation test fragments missing: {missing}")
source = b"".join(path.read_bytes() for path in PARTS)
actual = hashlib.sha256(source).hexdigest()
if actual != EXPECTED_SOURCE_SHA256:
    raise RuntimeError(
        "premium validation test source SHA-256 mismatch: "
        f"expected={EXPECTED_SOURCE_SHA256}, actual={actual}"
    )
exec(compile(source.decode("utf-8"), str(PARTS[0]), "exec"), globals())
