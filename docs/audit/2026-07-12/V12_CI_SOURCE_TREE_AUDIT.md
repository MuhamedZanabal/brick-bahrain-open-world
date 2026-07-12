# V12 CI SOURCE TREE AUDIT

Generated: 2026-07-12 (Asia/Bahrain)

## Evidence identity

- Repository: `MuhamedZanabal/brick-bahrain-open-world`
- Pull request: `#10` (draft)
- Head branch: `ops/v15-authority-recovery`
- Head commit: `5284d3f4abcdaf36c389baba090ac2ef4c9ded2f`
- Workflow: `Authority Recovery Checks`
- Workflow run: `29176502430`
- Job: `verify-tooling` / `86606522872`
- Workflow conclusion: `success`
- Audit artifact: `source-tree-preaudit` / `8255081655`
- Artifact SHA-256: `d0740472f357dfbc2de7a2d3b8e6e9909cd8c99fb694ed1ced0789eae6616488`
- JSON report SHA-256: `c7da8b72bec503c2e7b782b9310e9da4bccc35dd3d80f30ab06cbc87fe825a00`
- Markdown report SHA-256: `1965d66d4ff80de6a9859b2e4d8c941e2269cae4f0d11f6e75b9bce727eb22b8`

## CI execution result

Every workflow step completed successfully:

- Repository checkout.
- Python 3.13 setup.
- Python syntax validation.
- Authority-manifest JSON validation.
- Six regression tests.
- Full source-tree pre-audit generation.
- Evidence-artifact upload.

## Audit scope

The source-tree auditor scanned the complete checked-out draft-PR tree inherited from the connected v12 `main` baseline.

- Files scanned: **846**
- P0 findings: **4**
- P1 findings: **3**
- P2/P3/INFO findings: **0**

## P0 findings

1. `addons/flexible_toon_shader` has no adjacent license or notice evidence.
2. `debug.keystore` is committed to the source tree.
3. `export_presets.cfg` uses the same debug keystore for release signing.
4. `export_presets.cfg` stores a release signing password in versioned configuration. The report contains only a redacted fingerprint, never the value.

## P1 findings

1. No root project license or notice file was detected.
2. A debug signing password is stored in versioned configuration.
3. The release keystore path is stored in versioned configuration.

## Security interpretation

The provider-specific token and private-key content rules did not report a provider token or private-key header in the checked-out tree. This does not close the previously exposed third-party credential blocker because provider-side rotation and activity review remain required.

## Release decision

- Connected v12 production signing: **NO-GO**.
- Connected v12 public redistribution: **NO-GO** pending license evidence.
- v15.0.1 disposition: **BLOCKED** because the exact authority bytes remain unavailable.

## Required closure

1. Recover and verify the v15.0.1 authority bundle or source ZIP.
2. Run the same source-tree auditor against the verified authority tree with `--fail-on P0`.
3. Remove committed production/signing material from source.
4. Configure production signing exclusively through protected CI secrets.
5. Add complete license evidence and generate a third-party notices ledger.
6. Rotate the separately exposed third-party credential and verify that the old credential is invalid.
