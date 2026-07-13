#!/usr/bin/env python3
"""Deterministically assemble and execute the protected-compliant validation corrections."""
from __future__ import annotations

import hashlib
from pathlib import Path

EXPECTED_SOURCE_SHA256 = "8400e7b2a7fb32c61840b80af00cba3b2df8ee2e9c31e81c04f125963d2d369c"
PARTS = tuple(Path(__file__).with_name("premium_validation_v18_parts") / f"part_{index:02d}.pyfrag" for index in range(6))
missing = [path.as_posix() for path in PARTS if not path.is_file()]
if missing:
    raise RuntimeError(f"premium validation correction fragments missing: {missing}")
source = b"".join(path.read_bytes() for path in PARTS)
actual = hashlib.sha256(source).hexdigest()
if actual != EXPECTED_SOURCE_SHA256:
    raise RuntimeError(
        "premium validation correction source SHA-256 mismatch: "
        f"expected={EXPECTED_SOURCE_SHA256}, actual={actual}"
    )
exec(compile(source.decode("utf-8"), str(PARTS[0]), "exec"), globals())
