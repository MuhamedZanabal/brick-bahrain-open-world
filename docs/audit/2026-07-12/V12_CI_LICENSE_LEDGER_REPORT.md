# V12 CI ASSET LICENSE LEDGER REPORT

Generated: 2026-07-12 (Asia/Bahrain)

## Evidence identity

- Repository: `MuhamedZanabal/brick-bahrain-open-world`
- Pull request: `#10` (draft)
- Head branch: `ops/v15-authority-recovery`
- Head commit: `59012336ba191a7f0fd78262b157c723a584f2c8`
- Workflow run: `29176630547`
- Job: `verify-tooling` / `86606854096`
- Workflow conclusion: `success`
- Artifact: `asset-license-ledger` / `8255115790`
- Artifact SHA-256: `d383219d5ed584f6108eb37edeca252730e7efc6e21d9f1ceace67a26d9eca81`
- CSV SHA-256: `5510d5c254c05fa4a4584caf35c49568f300bf88453e6ec431a1a984370367c3`
- Summary SHA-256: `827f0a2f7f550b3c687c6b43d4d4c82e13933066495fd4504970416dfb0688d6`
- Notices SHA-256: `f883a550140f371b3b318a3540b505ba269453a159c3e42f722c614c07a1d085`

## CI result

All workflow steps passed, including:

- Ten tooling regression tests.
- Source-tree security/license pre-audit.
- Asset-license ledger generation.
- Upload of both evidence packages.

## Ledger result

- Candidate asset/component paths: **321**
- Third-party paths with status `BLOCKED`: **11**
- Project asset paths with status `PROJECT_PROVENANCE_REQUIRED`: **310**
- Paths with status `VERIFIED_EVIDENCE`: **0**

## Blocked third-party component

Every blocked path is under `addons/flexible_toon_shader`:

1. `FlexibleToonMaterial.tres`
2. `HatchToonMaterial.tres`
3. `example/CupMaterial.tres`
4. `example/CupMaterialHatch.tres`
5. `example/ExampleScene.tscn`
6. `example/cup.obj`
7. `example/cup_specular.png`
8. `example/cup_texture.png`
9. `flexible_toon.gdshader`
10. `hatch.png`
11. `hatch_toon.gdshader`

No adjacent license or notice evidence was available in the connected source tree. This does not prove the component lacks a valid upstream license; it proves the repository does not currently retain the evidence required for release approval.

## Project asset review load

The ledger identified 310 files under project asset roots. These remain review-required because filename presence cannot establish:

- Creator or owner.
- Original source URL.
- Commercial-use rights.
- Modification rights.
- Redistribution rights.
- Attribution obligations.

The CSV provides one unique row per candidate path and the exact fields required to complete provenance review.

## Third-party notices disposition

`V12_THIRD_PARTY_NOTICES.md` contains no approved components because the generator only includes components with recognized adjacent license evidence. It must not be populated from assumptions or memory.

## Release decision

- Connected v12 asset provenance: **NO-GO**.
- Exact v15.0.1 asset provenance: **BLOCKED** pending authority recovery.
- Issue #4 remains open until the ledger is regenerated against the verified v15 authority tree and all rows receive a documented disposition.
