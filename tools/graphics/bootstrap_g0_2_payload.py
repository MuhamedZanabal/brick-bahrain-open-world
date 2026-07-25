#!/usr/bin/env python3
from pathlib import Path
import base64,gzip
root=Path(__file__).resolve().parent
payload=root/'g0_2_payload'
for stem,target in (
    ('runner',root/'run_g0_2_android_paired.sh'),
    ('finalizer',root/'finalize_g0_2_android_evidence.py'),
):
    encoded=''.join(path.read_text().strip() for path in sorted(payload.glob(f'{stem}.*.b64')))
    if not encoded:
        raise SystemExit(f'missing payload chunks for {stem}')
    target.write_bytes(gzip.decompress(base64.b64decode(encoded)))
    target.chmod(0o755)
