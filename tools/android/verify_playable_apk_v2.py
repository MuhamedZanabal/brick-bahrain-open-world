#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Sequence

MODULE_PATH = Path(__file__).with_name("verify_playable_apk.py")
EXACT_AAPT_WARNING = (
    "AndroidManifest.xml:0: error: failed to read attribute 'android:required': "
    "attribute is not an integer value"
)


def load_verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_playable_apk_base", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load verifier: {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.KNOWN_AAPT_WARNING = EXACT_AAPT_WARNING
    return module


def main(argv: Sequence[str] | None = None) -> int:
    return int(load_verifier().main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
