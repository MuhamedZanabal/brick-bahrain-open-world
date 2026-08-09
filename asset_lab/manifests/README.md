# Asset Manifests

Phase 3 makes this directory the authoritative machine-readable asset-contract root.

- `schema/asset-manifest.schema.json` — Draft 2020-12 structural schema.
- `assets/` — production manifests only. No production manifest is accepted unless schema and semantic validation both pass.
- `examples/valid/` — non-production schema fixtures that must validate.
- `examples/invalid/` — negative fixtures that must fail for the intended contract violation.
- `asset-index.json` — deterministic global index generated from validated production manifests.
- `NAMING_VERSIONING.md` — authoritative IDs, suffixes, filenames, versions, and legacy-alias policy.

The valid example is a contract fixture; its source/export paths are illustrative and do not claim those files are production assets. The current production `assets/` set is intentionally empty until a real asset clears its later production gates.

Standard checks:

```bash
python3 tools/asset_lab/validate_manifest_schema.py --root . --examples
python3 tools/asset_lab/run_repository_checks.py --root .
python3 tools/asset_lab/generate_asset_index.py --root .
```
