# Asset License Ledger Generator

`generate_asset_license_ledger.py` inventories candidate assets and third-party component files into the release-ledger schema required by issue BB-0004.

It is intentionally fail-safe:

- Third-party files without adjacent license evidence are `BLOCKED`.
- Unrecognized license text is `REVIEW_REQUIRED`.
- Project asset files are `PROJECT_PROVENANCE_REQUIRED` until ownership/source is completed manually.
- Only recognized adjacent license evidence can produce `VERIFIED_EVIDENCE`.

## Usage

```bash
python tools/generate_asset_license_ledger.py /path/to/source \
  --csv-out reports/ASSET_LICENSE_LEDGER.csv \
  --notices-out reports/THIRD_PARTY_NOTICES.md \
  --summary-out reports/asset_license_summary.json
```

Add `--fail-on-blocked` to make CI exit with code 2 when any third-party path lacks license evidence.

Generated fields:

`path`, `asset_name`, `component`, `creator_source`, `source_url`, `license`, `license_text_path`, `attribution_required`, `commercial_use`, `modification_allowed`, `redistribution_allowed`, `proof`, `status`, `replacement_required`.

The generated ledger is a review input, not legal approval. Creator/source URL and project-owned provenance usually require manual completion.
