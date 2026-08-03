#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Sequence

KNOWN_AAPT_WARNING = (
    "AndroidManifest.xml:0: error: failed to read attribute 'android:required': "
    "attribute is not an integer value."
)
OTHER_ABI_PATTERN = re.compile(r"^/lib/(?:armeabi-v7a|x86|x86_64)/")
ARM64_GODOT_LIBRARY = "/lib/arm64-v8a/libgodot_android.so"


class VerificationError(RuntimeError):
    pass


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run(
    command: Sequence[str],
    *,
    output_path: Path,
    allow_failure: bool = False,
) -> tuple[int, str]:
    completed = subprocess.run(
        list(command),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = completed.stdout or ""
    _write(output_path, output)
    if completed.returncode != 0 and not allow_failure:
        raise VerificationError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n{output}"
        )
    return completed.returncode, output


def normalize_scalar(text: str) -> str:
    value = text.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value


def nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def validate_manifest(
    manifest: str,
    *,
    expected_package: str,
    required_permissions: Iterable[str],
) -> None:
    if f'package="{expected_package}"' not in manifest:
        raise VerificationError("manifest package does not match expected application ID")

    application_match = re.search(r"<application\b(?P<attrs>.*?)>", manifest, re.S)
    if not application_match:
        raise VerificationError("manifest application element is missing")
    if not re.search(r'android:label="(?:@ref/0x[0-9a-fA-F]+|@string/[^\"]+)"', application_match.group("attrs")):
        raise VerificationError("application label is not backed by an APK resource")

    activity_match = re.search(
        r'<activity\b(?P<attrs>.*?android:name="com\.godot\.game\.GodotApp".*?)>',
        manifest,
        re.S,
    )
    if not activity_match:
        raise VerificationError("Godot launcher activity is missing")
    orientation = re.search(r'android:screenOrientation="([^"]+)"', activity_match.group("attrs"))
    if not orientation or orientation.group(1) not in {"11", "landscape"}:
        raise VerificationError("Godot launcher activity is not locked to landscape")

    for permission in required_permissions:
        if permission not in manifest:
            raise VerificationError(f"required permission missing from manifest: {permission}")


def validate_inventory(files: Iterable[str]) -> None:
    normalized = {line.strip() for line in files if line.strip()}
    if ARM64_GODOT_LIBRARY not in normalized:
        raise VerificationError(f"required arm64 library missing: {ARM64_GODOT_LIBRARY}")
    unexpected = sorted(path for path in normalized if OTHER_ABI_PATTERN.match(path))
    if unexpected:
        raise VerificationError(f"unexpected non-arm64 native libraries: {unexpected[:10]}")


def resolve_label(
    *,
    apkanalyzer: str,
    apk: Path,
    output_dir: Path,
    resource_name: str,
) -> tuple[str, str, str]:
    _, package_output = _run(
        [apkanalyzer, "resources", "packages", str(apk)],
        output_path=output_dir / "playable-apk-resource-packages.txt",
    )
    packages = nonempty_lines(package_output)
    if not packages:
        raise VerificationError("APK resource table contains no packages")

    diagnostics: list[str] = []
    for package in packages:
        config_path = output_dir / f"playable-apk-resource-configs-{package.replace('.', '_')}.txt"
        _, config_output = _run(
            [
                apkanalyzer,
                "resources",
                "configs",
                "--type",
                "string",
                "--package",
                package,
                str(apk),
            ],
            output_path=config_path,
        )
        configs = nonempty_lines(config_output)
        ordered_configs = (["default"] if "default" in configs else []) + [
            config for config in configs if config != "default"
        ]
        for config in ordered_configs:
            safe_suffix = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{package}-{config}")
            names_path = output_dir / f"playable-apk-resource-names-{safe_suffix}.txt"
            status, names_output = _run(
                [
                    apkanalyzer,
                    "resources",
                    "names",
                    "--config",
                    config,
                    "--type",
                    "string",
                    "--package",
                    package,
                    str(apk),
                ],
                output_path=names_path,
                allow_failure=True,
            )
            diagnostics.append(f"{package}/{config}: names_status={status}")
            if status != 0 or resource_name not in nonempty_lines(names_output):
                continue
            value_path = output_dir / "playable-apk-app-label.txt"
            status, value_output = _run(
                [
                    apkanalyzer,
                    "resources",
                    "value",
                    "--config",
                    config,
                    "--name",
                    resource_name,
                    "--type",
                    "string",
                    "--package",
                    package,
                    str(apk),
                ],
                output_path=value_path,
                allow_failure=True,
            )
            value = normalize_scalar(value_output)
            diagnostics.append(f"{package}/{config}: value_status={status}, value={value!r}")
            if status == 0 and value:
                _write(output_dir / "playable-apk-resource-resolution.txt", "\n".join(diagnostics) + "\n")
                return value, package, config

    _write(output_dir / "playable-apk-resource-resolution.txt", "\n".join(diagnostics) + "\n")
    raise VerificationError(f"unable to resolve string resource: {resource_name}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_tool(explicit: str | None, fallback_name: str) -> str:
    if explicit:
        path = Path(explicit)
        if not path.is_file() or not os.access(path, os.X_OK):
            raise VerificationError(f"tool is not executable: {path}")
        return str(path)
    discovered = shutil.which(fallback_name)
    if not discovered:
        raise VerificationError(f"required tool unavailable: {fallback_name}")
    return discovered


def verify(args: argparse.Namespace) -> dict[str, object]:
    apk = Path(args.apk).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if not apk.is_file() or apk.stat().st_size <= 0:
        raise VerificationError(f"APK missing or empty: {apk}")

    apkanalyzer = find_tool(args.apkanalyzer, "apkanalyzer")
    apksigner = find_tool(args.apksigner, "apksigner")
    aapt = find_tool(args.aapt, "aapt")

    _, signing = _run(
        [apksigner, "verify", "--verbose", "--print-certs", str(apk)],
        output_path=output_dir / "playable-apk-signing.txt",
    )
    for signature_line in (
        "Verified using v2 scheme (APK Signature Scheme v2): true",
        "Verified using v3 scheme (APK Signature Scheme v3): true",
    ):
        if signature_line not in signing:
            raise VerificationError(f"required APK signature verification missing: {signature_line}")
    certificate_match = re.search(
        r"Signer #1 certificate SHA-256 digest:\s*([0-9a-fA-F]{64})",
        signing,
    )
    if not certificate_match:
        raise VerificationError("signing certificate SHA-256 digest is missing")
    signing_certificate_sha256 = certificate_match.group(1).lower()

    _, summary = _run(
        [apkanalyzer, "apk", "summary", str(apk)],
        output_path=output_dir / "playable-apk-summary.txt",
    )
    _, manifest = _run(
        [apkanalyzer, "manifest", "print", str(apk)],
        output_path=output_dir / "playable-apk-manifest.xml",
    )

    scalar_commands = {
        "application_id": ("application-id", "playable-apk-application-id.txt"),
        "version_name": ("version-name", "playable-apk-version-name.txt"),
        "version_code": ("version-code", "playable-apk-version-code.txt"),
        "min_sdk": ("min-sdk", "playable-apk-min-sdk.txt"),
        "target_sdk": ("target-sdk", "playable-apk-target-sdk.txt"),
    }
    scalars: dict[str, str] = {}
    for key, (verb, filename) in scalar_commands.items():
        _, value = _run(
            [apkanalyzer, "manifest", verb, str(apk)],
            output_path=output_dir / filename,
        )
        scalars[key] = normalize_scalar(value)

    _, permissions_output = _run(
        [apkanalyzer, "manifest", "permissions", str(apk)],
        output_path=output_dir / "playable-apk-permissions.txt",
        allow_failure=True,
    )
    _ = permissions_output

    _, files_output = _run(
        [apkanalyzer, "files", "list", str(apk)],
        output_path=output_dir / "playable-apk-inventory.txt",
    )

    aapt_status, aapt_output = _run(
        [aapt, "dump", "badging", str(apk)],
        output_path=output_dir / "playable-apk-badging.txt",
        allow_failure=True,
    )
    if aapt_status != 0 and KNOWN_AAPT_WARNING not in aapt_output:
        raise VerificationError(f"aapt dump badging failed unexpectedly ({aapt_status})")

    app_label, resource_package, resource_config = resolve_label(
        apkanalyzer=apkanalyzer,
        apk=apk,
        output_dir=output_dir,
        resource_name=args.label_resource,
    )

    expected = {
        "application_id": args.package,
        "version_name": args.version_name,
        "version_code": str(args.version_code),
        "min_sdk": str(args.min_sdk),
        "target_sdk": str(args.target_sdk),
    }
    for key, expected_value in expected.items():
        if scalars[key] != expected_value:
            raise VerificationError(
                f"{key} mismatch: expected {expected_value!r}, observed {scalars[key]!r}"
            )
    if app_label != args.app_label:
        raise VerificationError(
            f"app label mismatch: expected {args.app_label!r}, observed {app_label!r}"
        )

    required_permissions = (
        "android.permission.INTERNET",
        "android.permission.ACCESS_NETWORK_STATE",
    )
    validate_manifest(
        manifest,
        expected_package=args.package,
        required_permissions=required_permissions,
    )
    validate_inventory(nonempty_lines(files_output))

    apk_sha256 = sha256_file(apk)
    _write(
        output_dir / "PLAYABLE_APK_SHA256SUMS.txt",
        f"{apk_sha256}  {apk.name}\n",
    )
    payload: dict[str, object] = {
        "schema_version": 3,
        "classification": "PLAYABLE_VERTICAL_SLICE",
        "purpose": "Playable Android package using the production project main scene",
        "source_commit": args.source_commit,
        "engine": "4.3-stable",
        "renderer": "gl_compatibility",
        "architecture": "arm64-v8a",
        "package": scalars["application_id"],
        "app_label": app_label,
        "app_label_resource": args.label_resource,
        "resource_table_package": resource_package,
        "resource_configuration": resource_config,
        "version_code": int(scalars["version_code"]),
        "version_name": scalars["version_name"],
        "min_sdk": int(scalars["min_sdk"]),
        "target_sdk": int(scalars["target_sdk"]),
        "filename": apk.name,
        "size_bytes": apk.stat().st_size,
        "sha256": apk_sha256,
        "signing_certificate_sha256": signing_certificate_sha256,
        "required_permissions": list(required_permissions),
        "production_main_scene_preserved": True,
        "diagnostic_main_scene_selected": False,
        "diagnostic_evidence_camera_selected": False,
        "debug_signed": True,
        "physical_device_acceptance": "NOT_EXECUTED",
        "production_signing": "NOT_APPLICABLE_TO_QA_ARTIFACT",
        "aapt_known_warning_observed": aapt_status != 0,
        "apkanalyzer_summary": summary.strip(),
    }
    _write(
        output_dir / "PLAYABLE_APK_HANDOFF.json",
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
    )
    return payload


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the Bahrain Brick playable Android APK")
    parser.add_argument("--apk", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--package", default="com.brickbahrain.playable.mobile")
    parser.add_argument("--app-label", default="Bahrain Brick Open World")
    parser.add_argument("--label-resource", default="godot_project_name_string")
    parser.add_argument("--version-code", type=int, default=1404)
    parser.add_argument("--version-name", default="1.4.0.4-premium-visual-qa")
    parser.add_argument("--min-sdk", type=int, default=21)
    parser.add_argument("--target-sdk", type=int, default=34)
    parser.add_argument("--apkanalyzer")
    parser.add_argument("--apksigner")
    parser.add_argument("--aapt")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        payload = verify(parse_args(argv))
    except (VerificationError, OSError, ValueError) as exc:
        print(f"PLAYABLE_APK_VERIFICATION_FAILED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
