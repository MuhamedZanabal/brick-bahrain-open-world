#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path


def apply_patch_isolated(project: Path, patch: bytes) -> None:
    project = project.resolve()
    env = os.environ.copy()
    env["GIT_CEILING_DIRECTORIES"] = str(project.parent.resolve())
    with tempfile.NamedTemporaryFile(prefix="bahrain-brick-v3-", suffix=".patch") as handle:
        handle.write(patch)
        handle.flush()
        subprocess.run(
            ["git", "apply", "--check", "--unsafe-paths", handle.name],
            cwd=project,
            env=env,
            check=True,
        )
        subprocess.run(
            ["git", "apply", "--unsafe-paths", "--whitespace=nowarn", handle.name],
            cwd=project,
            env=env,
            check=True,
        )


def extract_new_file(patch:bytes,relative:str)->bytes:
    text=patch.decode('utf-8')
    marker=f'diff --git a/{relative} b/{relative}'
    start=text.find(marker)
    if start<0: raise RuntimeError(f'new-file patch section missing: {relative}')
    end=text.find('\ndiff --git a/',start+1)
    section=text[start:] if end<0 else text[start:end]
    if '\nnew file mode ' not in section or '\n--- /dev/null\n' not in section:
        raise RuntimeError(f'patch section is not an added file: {relative}')
    lines=section.splitlines(); in_hunk=False; output=[]; no_newline=False
    for line in lines:
        if line.startswith('@@ '): in_hunk=True; continue
        if not in_hunk: continue
        if line=='\\ No newline at end of file': no_newline=True; continue
        if line.startswith('+') and not line.startswith('+++'): output.append(line[1:])
        elif line.startswith((' ','-')): raise RuntimeError(f'unexpected non-addition in new-file patch: {relative}')
    if not output and '@@ -0,0 +0,0 @@' not in section: raise RuntimeError(f'no added content found for {relative}')
    data='\n'.join(output).encode('utf-8')
    if output and not no_newline: data+=b'\n'
    return data


def restore_missing_new_files(project:Path,patch:bytes,expected:dict[str,str],new_paths:set[str])->list[str]:
    restored=[]
    for relative,digest in sorted(expected.items()):
        target=project/relative
        if target.is_file(): continue
        if relative not in new_paths: raise RuntimeError(f'missing non-new-file output cannot be reconstructed: {relative}')
        data=extract_new_file(patch,relative); actual=hashlib.sha256(data).hexdigest()
        if actual!=digest: raise RuntimeError(f'reconstructed hash mismatch for {relative}: expected {digest}, got {actual}')
        target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data); restored.append(relative)
    return restored
