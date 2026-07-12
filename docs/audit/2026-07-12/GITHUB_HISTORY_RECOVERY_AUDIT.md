# GITHUB HISTORY RECOVERY AUDIT

Generated: 2026-07-12 (Asia/Bahrain)

## Objective

Search all connector-reachable GitHub branches, commits, and pull requests for a hidden or superseded v15/v15.0.1 source lineage before declaring remote authority recovery exhausted.

## Search terms

- `v15`
- `audit`
- `runtime`
- `landscape`
- `parser`

## Result

No branch name or commit-message result exposed the verified v15.0.1 authority commit:

```text
796b112802c83ce78f8233e9a215e97c39ca028e
```

No reachable branch or pull request contains the v15.0.1 authority tree:

```text
26bb58714fa7066c1fd887cd33456553f3739462
```

The only pull request matching `v15` is draft PR #10, which contains recovery tooling and explicitly does not contain the missing authority source.

## Historical branches recovered

Two v1.4-era branches remain reachable:

### `v14-runtime-verification`

- Head: `b03d9d14ba2c79ff44954d964b683099154f4305`
- Pull request: #1
- Ahead of `main`: 45 commits
- Scope: build/runtime verification tooling and delta-bootstrap files.
- Successful hosted run: `29142382089`
- Result: complete portable Godot 4.3 / Android API 34 / JDK 17 toolchain split into five unexpired artifacts.

### `v14-phone-apk`

- Head: `721e8c9df6cb8a4e142c18723a7fc72c27350159`
- Pull request: #2
- Ahead of `main`: 8 commits
- Scope: 17 base64 delta chunks plus Android build workflow.
- Exact decoded delta SHA-256: `7d1f637c83f32824dadf9d5b3a675184507707d3ddc2f557036d7afad1ac45a7`
- Exact decoded delta size: 76,132 bytes
- Delta members: 43
- Reconstruction: passed in historical run `29144364138`.
- Godot import: passed.
- Runtime smoke harness: failed because standalone `--script` compilation did not expose the `SaveManager` autoload symbol.
- Android export: skipped after the harness failure.

## Authority conclusion

- GitHub remote recovery of exact v15.0.1 authority: **EXHAUSTED / NOT FOUND**.
- v1.4 history: **RECOVERABLE AS A FALLBACK ONLY**.
- v1.4 must not replace or be relabeled as v15 authority.

## Executed follow-up

A dedicated workflow was added at `.github/workflows/recover_v14_source.yml` to:

1. Check out `v14-phone-apk`.
2. Verify and decode all 17 delta chunks.
3. Apply the already recorded Godot 4.3 parser corrections.
4. Remove embedded debug signing material from the distributed fallback package.
5. Run the source-tree security/license audit.
6. Generate an asset-license ledger.
7. Package a deterministic, parser-fixed, signing-sanitized v1.4 source ZIP.
8. Retain exact delta and provenance evidence.

The resulting source remains a historical recovery candidate, not current product authority.
