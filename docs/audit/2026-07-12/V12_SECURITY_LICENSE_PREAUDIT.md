# V12 SECURITY AND LICENSE PRE-AUDIT

Generated: 2026-07-12 (Asia/Bahrain)
Scope: connected GitHub `main` only; obsolete v12 baseline
Disposition: PARTIAL / NOT A V15 AUTHORITY AUDIT

## Verified findings

### BB-SEC-01 — Debug signing material is configured for release

`export_presets.cfg` contains:

- `keystore/debug="res://debug.keystore"`
- plaintext debug password and alias
- `keystore/release="res://debug.keystore"`
- the same plaintext password and alias in release fields
- `package/signed=true`

This configuration is unsuitable for a production release. It also makes release provenance ambiguous because the same debug identity is used for both build classes.

Severity: P0 for public production signing; P1 for controlled QA.

Required correction after authority recovery:

1. Remove release signing credentials from versioned project configuration.
2. Keep QA/debug and production signing identities separate.
3. Resolve production keystore path, alias, and passwords from protected CI secrets.
4. Record certificate fingerprint and signing provenance without recording secrets.
5. Add a CI check that fails when debug signing is selected for a production artifact.

### BB-LIC-01 — Third-party shader content is included without verified in-repository proof

The v12 initial commit includes content under `addons/flexible_toon_shader`, including shaders, materials, example meshes, and textures.

The GitHub contents API returned no file at these common proof locations:

- `/LICENSE`
- `/README.md`
- `/addons/flexible_toon_shader/LICENSE`
- `/addons/flexible_toon_shader/LICENSE.md`
- `/addons/flexible_toon_shader/README.md`
- `/addons/cartoon_3d_water/LICENSE`

This does not prove that no license evidence exists anywhere in the archive. It proves that release approval cannot rely on an assumed license or on the common locations checked.

Severity: P0 for public distribution until provenance is documented.

Required correction:

1. Enumerate every third-party asset and code path from the recovered v15 authority tree.
2. Preserve source URL, author, license text, version/date, and redistribution proof.
3. Generate `THIRD_PARTY_NOTICES.md` and an asset-license ledger.
4. Remove or replace every unknown, incompatible, or undocumented item.

## Inconclusive checks

GitHub indexed searches for generic strings such as `api_key`, `password`, and `debug.keystore` returned no results even though `export_presets.cfg` demonstrably contains signing fields. Therefore repository code-search results are not sufficient evidence of secret cleanliness.

A complete full-tree scan remains BLOCKED until either:

- the exact v15 authority source is recovered locally; or
- a GitHub Actions run checks out the complete tree and executes a scanner with reviewable output.

## Secret-rotation blocker

A third-party API credential was previously exposed outside the repository. Its value is intentionally omitted. Rotation and provider-side activity review remain operator actions and cannot be inferred from repository scanning.

## Release decision

- v12 production signing: NO-GO.
- v12 asset provenance: NO-GO.
- v15 security/license disposition: BLOCKED pending authority recovery.
