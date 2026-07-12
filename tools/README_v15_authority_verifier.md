# v15 Authority Verifier

Run from the repository root:

```bash
python tools/verify_v15_authority.py /path/to/brick_bahrain_v15.0.1-authority.bundle \
  --json-output authority-verification.json
```

Alternative source archive:

```bash
python tools/verify_v15_authority.py /path/to/brick_bahrain_v15.0.1-authority-source.zip
```

QA APK identity check:

```bash
python tools/verify_v15_authority.py /path/to/brick_bahrain_v15.0.1-audit-qa.apk
```

The tool is read-only. It verifies the recorded SHA-256 and size before deeper parsing. For the Git bundle, it also runs `git bundle verify`, clones into a temporary directory, checks the authority branch, exact commit, exact tree, clean worktree, and presence of one `project.godot` file.

Exit codes:

- `0`: all checks passed.
- `2`: verification failed.
- `3`: invocation, manifest, or environment error.

Run tests:

```bash
python -m unittest discover -s tools/tests -v
```
