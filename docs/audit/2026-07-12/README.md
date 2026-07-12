# Bahrain Bricks v15 Authority Recovery

This directory records the non-destructive recovery checkpoint created on 2026-07-12.

## Current source authority

The connected `main` branch is the obsolete v12 baseline and must not receive v15 feature or stabilization changes.

The latest proven lineage is:

- Branch: `audit/v15.0.1-authority`
- Commit: `796b112802c83ce78f8233e9a215e97c39ca028e`
- Tree: `26bb58714fa7066c1fd887cd33456553f3739462`
- Engine: Godot 4.3 / GDScript

The authority bytes are not yet available in the connected repository. Recovery is tracked by issue `BB-0003`.

## Required sequence

1. Recover the exact Git bundle or authority source ZIP.
2. Run `python tools/verify_v15_authority.py <artifact>`.
3. Do not continue if any check fails.
4. Push the recovered branch under `audit/v15.0.1-authority`.
5. Verify the remote commit and tree before source changes.
6. Keep `main` unchanged until a reviewed migration/merge decision exists.

## Documents

- `INTERIM_PRODUCT_AUTHORITY.md`: constrained product contract while the original GDD is unavailable.
- `SOURCE_RECOVERY_HANDOFF.md`: exact artifact identities and manual recovery commands.
- `../../../tools/v15_authority_manifest.json`: machine-readable authority and artifact identity.
- `../../../tools/verify_v15_authority.py`: deterministic, read-only verifier.

## Release status

**NO-GO.** P0 blockers include authority recovery, asset provenance, and exposed-credential rotation.
