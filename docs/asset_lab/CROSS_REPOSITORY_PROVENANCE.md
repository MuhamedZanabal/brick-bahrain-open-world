# Bahrain Brick Asset Lab Cross-Repository Provenance

## Frozen game authority

- Repository: `MuhamedZanabal/brick-bahrain-open-world`
- Integration branch: `work/bahrain-brick-asset-lab-integration-v1`
- Integration base: `e26ec912db5c10d071a8e120010bdb5a9a136f17`
- Premium branch verification: identical to the integration base at authority establishment
- Preserved validation head: `83dd98013e75785c0101fa9501c461fc807cc342`
- Preserved validation PR: `#55`, open, draft and unmerged
- Preserved before-integration APK SHA-256: `7e32e81f005f300fca115e39f2962c9cac3c9835d34ac15d4bece2f86655bf65`

## Frozen Asset Lab authority

- Connected repository: `MuhamedZanabal/Bahrain_bricks_Assets`
- GitHub repository state at authority establishment: import-workflow scaffold only; expected production commit was not present on GitHub
- Verified source medium: complete Git bundle retrieved from connected Google Drive file ID `1SykBMg8fteOtnwsj-AlwNrLKZHOHZlhM`
- Durable source locator: `asset_lab/source_authority/BUNDLE_SOURCE.json`
- Bundle size: `623404` bytes
- Bundle SHA-256: `98e3964a1c84200c8d764116bc027678de0019fc6481ca41825ed606aa2a9c41`
- Production branch: `work/bahrain-brick-complete-asset-system-v1`
- Production head: `84ac94399262f71f29bf65dd553cd7729d87cce0`
- Complete history: yes
- Commit count: `21`
- Tracked files: `160`
- Manifest records: `98`

## Independent verification

- Git bundle verification: passed
- Bundle head verification: passed
- Unit tests: `16/16` passed
- Manifest validation: passed at `98` records
- Signing-material scan: passed
- Python compilation: passed
- Working tree after cleanup: clean
- Godot runtime: not run in source authority
- Android benchmark: not run in source authority
- Production GLBs in source authority: `0`

## Source checksum defect retained as evidence

The Asset Lab's checked-in `SHA256SUMS` is not valid for head `84ac943...`:

- `11` tracked files have stale hashes.
- `29` entries point to untracked Python bytecode.

The original file is preserved inside the immutable bundle. A separate head-accurate ledger was generated independently from all 160 files. This correction does not rewrite the Asset Lab repository or its history.

## ZIP status

The uploaded summary reports ZIP SHA-256 `080ca867fd22cdcffb7a8457c83927698766ee59c49e3c78e0fef503b22a20c8` and size `658587`, but the ZIP itself was not available through the connected Drive index. It is therefore **reported but not independently verified**. The complete Git bundle is independently verified and is the source authority used by the integration gate.

## Mutation boundaries

- PR `#55` remains untouched.
- The premium branch remains untouched.
- The verified APK remains untouched.
- The Asset repository import workflows were not executed because they contain force-push commands.
- No Asset repository history was rewritten.
