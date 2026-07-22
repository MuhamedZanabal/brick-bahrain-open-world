# Bahrain Brick Graphics Licence and Provenance Ledger

Status: **ACTIVE G0 GATE**  
Recorded: 2026-07-22

## Policy

No asset may enter a production scene, atlas, theme, package, promotional capture, or Android export unless this ledger records its origin, rights, permitted use, modification status, and repository identity.

The Bahrain Brick graphics program must use an original proprietary construction-toy visual identity. Reference concept screens are art-direction inputs only and are prohibited as production assets.

## Hard Prohibitions

The project must not ship:

- copied minifigure proportions or recognisable protected toy-character trade dress;
- third-party toy logos, stud markings, connector geometry, faces, hands, silhouettes, vehicle designs, or packaging identity;
- reference-image pixels, crops, paint-overs, traced geometry, or extracted textures as final assets;
- unlicensed fonts, textures, models, music, logos, icons, photographs, or sound effects;
- downloaded icon packs mixed into the proprietary icon family without explicit licence and visual-authority approval;
- assets whose source, author, licence, or commercial-use status cannot be proven.

## Required Record Fields

Every new asset record must include:

| Field | Requirement |
|---|---|
| Asset ID | Stable Bahrain Brick identifier. |
| Repository path | Exact final source path. |
| Category | UI, font, icon, logo, texture, model, animation, shader, audio, reference, or tool output. |
| Creator / source | Person, studio, vendor, generator, or internal tool. |
| Creation date | ISO date. |
| Licence | Exact licence name or internal work-for-hire ownership statement. |
| Commercial use | Allowed / prohibited / conditional. |
| Modification rights | Allowed / prohibited / conditional. |
| Attribution | Exact required attribution or `none`. |
| Source locator | Contract, invoice, licence file, source repository, or immutable archive locator. |
| Source checksum | SHA-256 of the received source package or file. |
| Derivative process | Material modifications, conversion, retopology, baking, atlas generation, or compression. |
| Final checksum | SHA-256 of the repository production asset. |
| Reviewer | Accountable reviewer. |
| State | PROPOSED, REVIEWING, APPROVED, REJECTED, REVOKED. |
| Notes / restrictions | Territory, platform, seat, redistribution, attribution, model-release, or trademark limits. |

## Existing Authorities

| Record | Source / authority | SHA-256 | State | Use boundary |
|---|---|---|---|---|
| Validated 436-GLB asset archive | Existing release authority via frozen composite contract | `76964c58c283cacaee137152189727d678aa83230d7211dc6a15aa9af9d4a67a` | APPROVED_AS_EXISTING_AUTHORITY | May be consumed only through the validated manifest and profile rules. No regeneration or silent replacement. |
| Historical source archive | Existing release authority via frozen composite contract | `5c4d8ac4497eda7752058424062a74a97c1f6f5e0c9a1ff393abac2a2c7c828a` | APPROVED_AS_RECONSTRUCTION_INPUT | Reconstruction input only; does not automatically approve every embedded third-party asset for new use. |
| Uploaded Bahrain Brick concept screens | User-provided aspirational references | not ingested | REFERENCE_ONLY | Composition, colour, readability and perceived-polish direction only. Never exported or used as source pixels. |

## Font Gate

Before GFX-025 or GFX-026 can complete, each font family must have:

1. complete licence text stored or referenced by immutable locator;
2. commercial game embedding rights;
3. Android redistribution rights;
4. desktop redistribution rights where applicable;
5. Arabic glyph coverage evidence for the interface family;
6. exact font-file checksums;
7. attribution and modification obligations recorded;
8. no use in repository or screenshots before approval.

## Originality Review Gate

Characters, bricks, connectors, vehicles, UI artwork, logos, icons, and facial systems require an originality review that records:

- design source and author;
- comparison against prohibited third-party trade dress;
- proprietary proportion and connector decisions;
- rejected similarities and corrective changes;
- final model/sprite/vector checksums;
- reviewer and approval date.

## Initial New-Asset Register

No new graphics asset batch has been approved or ingested in G0.

| Asset ID | Path | Category | Source | Licence | State | Notes |
|---|---|---|---|---|---|---|
| BB-GFX-PENDING | TBD | TBD | TBD | TBD | PROPOSED | Placeholder only. It must be replaced by one record per asset; it grants no usage rights. |

## Gate Enforcement

- G0 sets `large_asset_ingestion_allowed` to `false`.
- A missing ledger record is a build/review blocker, not a documentation warning.
- Revoked or rejected assets must be removed from source, generated derivatives, atlases, caches, screenshots, and packages.
- Licence evidence must survive repository handoff and release archival.
