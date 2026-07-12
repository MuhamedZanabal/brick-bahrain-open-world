# SOURCE RECOVERY HANDOFF

Generated: 2026-07-12 (Asia/Bahrain)

## Preferred input

`brick_bahrain_v15.0.1-authority.bundle`

Expected SHA-256:

```text
af928699cbc786083de77ba994eb357d54e2a9b4770268dc4971029067ca411b
```

## Alternative input

`brick_bahrain_v15.0.1-authority-source.zip`

Expected SHA-256:

```text
a009474ca5b556d4a3a9735bc742affd25acc3966d1b9f485303319e74313077
```

## Verification and clone commands

```bash
sha256sum brick_bahrain_v15.0.1-authority.bundle
# Must equal af928699cbc786083de77ba994eb357d54e2a9b4770268dc4971029067ca411b

mkdir -p /tmp/bb-bundle-verify.git
git init --bare /tmp/bb-bundle-verify.git
git -C /tmp/bb-bundle-verify.git bundle verify "$PWD/brick_bahrain_v15.0.1-authority.bundle"

git clone brick_bahrain_v15.0.1-authority.bundle brick-bahrain-v15.0.1
git -C brick-bahrain-v15.0.1 checkout audit/v15.0.1-authority
git -C brick-bahrain-v15.0.1 rev-parse HEAD
git -C brick-bahrain-v15.0.1 rev-parse 'HEAD^{tree}'
git -C brick-bahrain-v15.0.1 status --short
```

Expected:

```text
HEAD: 796b112802c83ce78f8233e9a215e97c39ca028e
TREE: 26bb58714fa7066c1fd887cd33456553f3739462
STATUS: empty
```

Preferred automated command:

```bash
python tools/verify_v15_authority.py brick_bahrain_v15.0.1-authority.bundle \
  --json-output authority-verification.json
```

## Remote branch procedure

Do not replace `main` directly. From the recovered repository:

```bash
git remote set-url origin https://github.com/MuhamedZanabal/brick-bahrain-open-world.git
git push -u origin audit/v15.0.1-authority
```

Then verify the remote commit through the connected GitHub tool before any merge or feature work.

## QA artifact required for device testing

```text
File: brick_bahrain_v15.0.1-audit-qa.apk
SHA-256: 1fbd907e7c287d42fa2a2b893967e8d5f033330342d0ba24d41d0cf3138a53f0
Size from prior provenance: 192,629,155 bytes
Signing: Android debug certificate
Use: controlled QA only
```
