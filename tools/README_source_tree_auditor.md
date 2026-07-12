# Source Tree Security and License Auditor

`audit_source_tree.py` performs a deterministic, read-only pre-release scan of an extracted source tree.

## Checks

- Provider-specific API token patterns.
- Private-key headers.
- Explicit secret/password assignments.
- Committed `.jks`, `.keystore`, `.p12`, `.pfx`, `.pem`, `.key`, `.env`, and common private-key filenames.
- Godot Android export presets that reuse a debug keystore for release.
- Signing passwords stored in versioned export configuration.
- Missing root license/notice evidence.
- Missing adjacent license/notice evidence for component roots under `addons`, `plugins`, `third_party`, `third-party`, and `vendor`.

Suspected secret values are never written to reports. Findings include only a SHA-256-derived redacted fingerprint and length.

## Usage

```bash
python tools/audit_source_tree.py /path/to/source \
  --json-out reports/source_audit.json \
  --markdown-out reports/source_audit.md
```

To make CI fail when a threshold is reached:

```bash
python tools/audit_source_tree.py /path/to/source --fail-on P0
```

Exit codes:

- `0`: audit completed.
- `2`: audit completed and the selected failure threshold was met.
- `3`: invocation or environment error.

## Limitations

This is a high-signal release pre-audit, not a substitute for provider-side credential rotation, a complete SBOM, formal legal review, binary reverse engineering, or commercial secret-scanning services. Every P0/P1 finding requires human disposition.
