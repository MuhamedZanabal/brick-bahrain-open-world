#!/usr/bin/env python3
"""Audit a source tree for release-blocking secret, signing, and license risks.

The scanner is read-only. It never prints complete suspected secret values. Findings
contain only file paths, line numbers, rule identifiers, and redacted fingerprints.

Exit codes:
  0: audit completed (including when findings exist)
  2: audit completed and --fail-on threshold was met
  3: invocation/environment error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Iterator

TEXT_EXTENSIONS = {
    ".cfg", ".conf", ".env", ".gd", ".gdshader", ".gradle", ".ini", ".java",
    ".json", ".md", ".properties", ".py", ".sh", ".toml", ".tscn", ".tres",
    ".txt", ".xml", ".yaml", ".yml",
}

SKIP_DIRS = {
    ".git", ".godot", ".gradle", ".idea", ".mono", "__pycache__", "build",
    "dist", "node_modules",
}

SENSITIVE_FILE_PATTERNS = (
    re.compile(r"(^|/)(?:id_rsa|id_dsa|id_ecdsa|id_ed25519)$", re.I),
    re.compile(r"\.(?:jks|keystore|p12|pfx|pem|key)$", re.I),
    re.compile(r"(^|/)\.env(?:\.|$)", re.I),
)

# Patterns intentionally require provider-specific structure or explicit assignments.
SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("SECRET_GITHUB_TOKEN", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b"), "P0"),
    ("SECRET_OPENAI_KEY", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"), "P0"),
    ("SECRET_AWS_ACCESS_KEY", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"), "P0"),
    ("SECRET_PRIVATE_KEY", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "P0"),
    (
        "SECRET_EXPLICIT_ASSIGNMENT",
        re.compile(
            r"(?i)\b(?:api[_-]?key|client[_-]?secret|access[_-]?token|auth[_-]?token|password)\b"
            r"\s*[:=]\s*[\"']?([^\s\"']{12,})"
        ),
        "P1",
    ),
)

PLACEHOLDER_VALUES = {
    "android", "changeme", "change_me", "example", "placeholder", "replace_me",
    "test", "testing", "your_api_key", "your_token",
}

LICENSE_NAMES = {
    "license", "license.md", "license.txt", "copying", "copying.md", "copying.txt",
    "notice", "notice.md", "notice.txt", "third_party_notices.md", "third-party-notices.md",
}

THIRD_PARTY_ROOTS = ("addons", "plugins", "third_party", "third-party", "vendor")

SEVERITY_ORDER = {"INFO": 0, "P3": 1, "P2": 2, "P1": 3, "P0": 4}


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    path: str
    line: int | None
    message: str
    fingerprint: str | None = None


def redacted_fingerprint(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"sha256:{digest};len:{len(value)}"


def iter_files(root: Path) -> Iterator[Path]:
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        current_path = Path(current)
        for name in sorted(files):
            yield current_path / name


def is_probably_text(path: Path, max_bytes: int) -> bool:
    try:
        size = path.stat().st_size
    except OSError:
        return False
    if size > max_bytes:
        return False
    if path.suffix.lower() in TEXT_EXTENSIONS or path.name.lower() in LICENSE_NAMES:
        return True
    try:
        sample = path.read_bytes()[:4096]
    except OSError:
        return False
    return b"\x00" not in sample


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def scan_sensitive_filenames(root: Path, files: Iterable[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in files:
        rel = relative(path, root)
        if any(pattern.search(rel) for pattern in SENSITIVE_FILE_PATTERNS):
            severity = "P0" if path.suffix.lower() in {".jks", ".keystore", ".p12", ".pfx", ".pem", ".key"} else "P1"
            findings.append(Finding(
                "SENSITIVE_FILE_COMMITTED", severity, rel, None,
                "Sensitive credential/signing file type is present in the source tree.",
            ))
    return findings


def assignment_value(match: re.Match[str]) -> str:
    if match.lastindex:
        return match.group(match.lastindex) or match.group(0)
    return match.group(0)


def is_placeholder(value: str) -> bool:
    normalized = value.strip().strip('"\'').lower()
    return normalized in PLACEHOLDER_VALUES or normalized.startswith("${") or normalized.startswith("{{")


def scan_text_secrets(root: Path, files: Iterable[Path], max_bytes: int) -> list[Finding]:
    findings: list[Finding] = []
    for path in files:
        if not is_probably_text(path, max_bytes):
            continue
        rel = relative(path, root)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            for rule_id, pattern, severity in SECRET_PATTERNS:
                for match in pattern.finditer(line):
                    value = assignment_value(match)
                    if rule_id == "SECRET_EXPLICIT_ASSIGNMENT" and is_placeholder(value):
                        continue
                    findings.append(Finding(
                        rule_id, severity, rel, line_number,
                        "Potential secret material detected; value withheld.",
                        redacted_fingerprint(value),
                    ))
    return findings


def scan_android_signing(root: Path) -> list[Finding]:
    path = root / "export_presets.cfg"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    values: dict[str, tuple[str, int]] = {}
    for number, line in enumerate(lines, 1):
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = (value.strip().strip('"'), number)

    findings: list[Finding] = []
    release = values.get("keystore/release")
    debug = values.get("keystore/debug")
    if release and release[0]:
        findings.append(Finding(
            "ANDROID_RELEASE_KEYSTORE_IN_CONFIG", "P1", "export_presets.cfg", release[1],
            "Release keystore path is stored in versioned export configuration.",
        ))
    if release and debug and release[0] == debug[0]:
        findings.append(Finding(
            "ANDROID_DEBUG_KEY_USED_FOR_RELEASE", "P0", "export_presets.cfg", release[1],
            "Debug and release export profiles reference the same keystore.",
        ))
    for key in ("keystore/debug_password", "keystore/release_password"):
        item = values.get(key)
        if item and item[0]:
            severity = "P0" if key.endswith("release_password") else "P1"
            findings.append(Finding(
                "ANDROID_SIGNING_PASSWORD_IN_CONFIG", severity, "export_presets.cfg", item[1],
                f"{key} is stored in versioned export configuration; value withheld.",
                redacted_fingerprint(item[0]),
            ))
    return findings


def has_license_in(directory: Path) -> bool:
    try:
        return any(child.is_file() and child.name.lower() in LICENSE_NAMES for child in directory.iterdir())
    except OSError:
        return False


def scan_license_provenance(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    if not has_license_in(root):
        findings.append(Finding(
            "ROOT_LICENSE_MISSING", "P1", ".", None,
            "No root license/notice file was found.",
        ))

    for root_name in THIRD_PARTY_ROOTS:
        parent = root / root_name
        if not parent.is_dir():
            continue
        for child in sorted(p for p in parent.iterdir() if p.is_dir()):
            rel = relative(child, root)
            if not has_license_in(child):
                findings.append(Finding(
                    "THIRD_PARTY_LICENSE_EVIDENCE_MISSING", "P0", rel, None,
                    "Third-party component root has no adjacent license/notice file.",
                ))
    return findings


def audit_tree(root: Path, max_text_bytes: int = 2_000_000) -> dict[str, object]:
    root = root.resolve()
    files = list(iter_files(root))
    findings: list[Finding] = []
    findings.extend(scan_sensitive_filenames(root, files))
    findings.extend(scan_text_secrets(root, files, max_text_bytes))
    findings.extend(scan_android_signing(root))
    findings.extend(scan_license_provenance(root))
    findings = sorted(findings, key=lambda f: (-SEVERITY_ORDER[f.severity], f.path, f.line or 0, f.rule_id))

    counts = {severity: 0 for severity in SEVERITY_ORDER}
    for finding in findings:
        counts[finding.severity] += 1

    return {
        "schema_version": 1,
        "root": str(root),
        "files_scanned": len(files),
        "finding_counts": counts,
        "findings": [asdict(finding) for finding in findings],
    }


def render_markdown(report: dict[str, object]) -> str:
    counts = report["finding_counts"]
    lines = [
        "# Source Tree Audit",
        "",
        f"Files scanned: **{report['files_scanned']}**",
        "",
        "## Findings by severity",
        "",
        f"- P0: {counts['P0']}",
        f"- P1: {counts['P1']}",
        f"- P2: {counts['P2']}",
        f"- P3: {counts['P3']}",
        f"- INFO: {counts['INFO']}",
        "",
        "## Findings",
        "",
    ]
    findings = report["findings"]
    if not findings:
        lines.append("No findings.")
    for item in findings:
        location = item["path"]
        if item["line"]:
            location += f":{item['line']}"
        lines.extend([
            f"### {item['severity']} — {item['rule_id']}",
            "",
            f"- Location: `{location}`",
            f"- Finding: {item['message']}",
        ])
        if item["fingerprint"]:
            lines.append(f"- Redacted fingerprint: `{item['fingerprint']}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def threshold_met(report: dict[str, object], fail_on: str | None) -> bool:
    if not fail_on:
        return False
    threshold = SEVERITY_ORDER[fail_on]
    return any(SEVERITY_ORDER[item["severity"]] >= threshold for item in report["findings"])


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Source tree to audit")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    parser.add_argument("--max-text-bytes", type=int, default=2_000_000)
    parser.add_argument("--fail-on", choices=["P0", "P1", "P2", "P3", "INFO"])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if not args.root.is_dir():
        print(f"error: source root is not a directory: {args.root}", file=sys.stderr)
        return 3
    report = audit_tree(args.root, args.max_text_bytes)
    rendered = render_markdown(report)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(rendered, encoding="utf-8")
    if not args.json_out and not args.markdown_out:
        print(rendered, end="")
    return 2 if threshold_met(report, args.fail_on) else 0


if __name__ == "__main__":
    raise SystemExit(main())
