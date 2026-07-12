# Flexible Toon Shader for Godot — Provenance Record

Evidence classification: VERIFIED upstream identity and license / INFERRED derivative-port mapping

## Upstream

- Repository: `CaptainProton42/FlexibleToonShaderGD`
- Author/license holder: John Wigg
- License: MIT
- Verified reference commit: `dacf9a41d697a26360af96cdbf6332589cd97ab7`
- Commit date: 2021-05-20
- Upstream README blob: `a6178a60acacaea0cc35c936996fd67cf3b3987e`
- Upstream LICENSE blob: `c4d5c2b58df509296a2abd065fa69164ce3170db`

The upstream README specifies installation under `addons/flexible_toon_shader`, including `FlexibleToonMaterial.tres`, `HatchToonMaterial.tres`, and the `example` directory. It explicitly states that the repository is licensed under MIT.

## Bundled Bahrain Bricks component

The connected v12/v1.4 source contains the same component directory, material names, example structure, parameter names, and shader algorithm structure. Its shader files use Godot 4 `.gdshader` syntax and `source_color` hints rather than the older Godot 3 `.shader` syntax, so the local files are not byte-identical to the verified 2021 upstream commit.

Disposition:

- Upstream origin and MIT license: VERIFIED.
- Exact author/date of the Godot 4 port modifications: BLOCKED / unknown.
- Applicability of the upstream MIT notice to the derivative shader code: INFERRED with strong evidence; preserve the MIT notice.
- Final release approval: requires this notice to be copied adjacent to the component in the exact recovered v15 authority tree and a reviewer to confirm that no additional third-party example assets impose separate attribution requirements.

## Special upstream notices

The upstream README separately notes CC-BY-4.0 attribution for a Godot Engine logo used in its example scene and MIT licensing for Godot Engine icons. The Bahrain Bricks addon inventory must be checked for those specific logo/icon files before they are shipped. The currently inventoried addon paths include cup assets and shader materials, but no proof should be inferred for unexamined binary assets.
