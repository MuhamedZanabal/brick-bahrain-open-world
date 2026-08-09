# Bahrain Brick Asset Lab

This directory is the editable/source-side half of the Phase 2 source/runtime boundary.

New production work uses these controlled roots:

- `source/` — editable source masters;
- `generators/` — deterministic Blender Python and supporting generator code;
- `references/` — licensed visual references and approved concept sheets;
- `materials/` — palette, trim, atlas, and texture sources;
- `exports/glb/` — validated runtime `.glb` exports only;
- `manifests/` — machine-readable source/generated metadata;
- `reports/` — durable audit, validation, and performance reports;
- `evidence/` — durable renders, screenshots, video, and logs;
- `quarantine/` — rejected or legally uncertain inputs that must never enter runtime production.

Legacy `reports/`, `reviews/`, `runtime/`, and `source_authority/` content is preserved. Phase 2 does not rename or delete legacy evidence. New runtime assets belong under `game/assets/bahrain/`.

Standard architecture check:

```bash
python3 tools/asset_lab/run_repository_checks.py --root .
```

The Phase 2 manifest validator allows the empty bootstrap state. As soon as manifests exist, an authoritative schema is mandatory; Phase 3 owns the schema and semantic rules.
