#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path

MAGIC = b"ECFG"
TYPE_STRING = 4
TARGET_KEY = "application/run/main_scene"
DIAGNOSTIC_SCENE = "res://tests/graphics/r1_renderer_runtime_debug.tscn"
PLAYABLE_SCENE = "res://scenes/splash_screen.tscn"
PROJECT_BINARY = "assets/project.binary"
SIGNATURE_SUFFIXES = (".SF", ".RSA", ".DSA", ".EC")


def u32(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError(f"truncated u32 at {offset}")
    return struct.unpack_from("<I", data, offset)[0], offset + 4


def pack_u32(value: int) -> bytes:
    return struct.pack("<I", value)


@dataclass(frozen=True)
class Entry:
    key: str
    variant: bytes


def parse_entries(data: bytes) -> list[Entry]:
    if data[:4] != MAGIC:
        raise ValueError("project.binary does not start with ECFG")
    count, offset = u32(data, 4)
    entries: list[Entry] = []
    for index in range(count):
        key_len, offset = u32(data, offset)
        end = offset + key_len
        if end > len(data):
            raise ValueError(f"truncated key {index}")
        key = data[offset:end].decode("utf-8")
        offset = end
        variant_len, offset = u32(data, offset)
        end = offset + variant_len
        if end > len(data):
            raise ValueError(f"truncated variant for {key}")
        entries.append(Entry(key, data[offset:end]))
        offset = end
    if offset != len(data):
        raise ValueError(f"unexpected trailing bytes: {len(data) - offset}")
    return entries


def encode_entries(entries: list[Entry]) -> bytes:
    out = bytearray(MAGIC)
    out += pack_u32(len(entries))
    for entry in entries:
        key = entry.key.encode("utf-8")
        out += pack_u32(len(key))
        out += key
        out += pack_u32(len(entry.variant))
        out += entry.variant
    return bytes(out)


def decode_string_variant(blob: bytes) -> str:
    value_type, offset = u32(blob, 0)
    if value_type != TYPE_STRING:
        raise ValueError(f"expected String variant type {TYPE_STRING}, got {value_type}")
    byte_len, offset = u32(blob, offset)
    end = offset + byte_len
    if end > len(blob):
        raise ValueError("truncated string variant")
    value = blob[offset:end].decode("utf-8")
    padding = blob[end:]
    expected_padding = (-byte_len) % 4
    if len(padding) != expected_padding or any(padding):
        raise ValueError("unexpected String variant padding")
    return value


def encode_string_variant(value: str) -> bytes:
    raw = value.encode("utf-8")
    return pack_u32(TYPE_STRING) + pack_u32(len(raw)) + raw + (b"\x00" * ((-len(raw)) % 4))


def patch_project_binary(data: bytes) -> bytes:
    entries = parse_entries(data)
    matches = [i for i, entry in enumerate(entries) if entry.key == TARGET_KEY]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {TARGET_KEY!r}, found {len(matches)}")
    index = matches[0]
    current = decode_string_variant(entries[index].variant)
    if current != DIAGNOSTIC_SCENE:
        raise ValueError(f"unexpected current main scene: {current!r}")
    before = entries[index]
    entries[index] = Entry(before.key, encode_string_variant(PLAYABLE_SCENE))
    output = encode_entries(entries)

    reparsed = parse_entries(output)
    original = parse_entries(data)
    if len(reparsed) != len(original):
        raise AssertionError("entry count changed")
    for i, (old, new) in enumerate(zip(original, reparsed)):
        if old.key != new.key:
            raise AssertionError(f"key changed at index {i}")
        if i != index and old.variant != new.variant:
            raise AssertionError(f"unrelated variant changed for {old.key}")
    if decode_string_variant(reparsed[index].variant) != PLAYABLE_SCENE:
        raise AssertionError("patched scene did not round-trip")
    if DIAGNOSTIC_SCENE.encode() in output:
        raise AssertionError("diagnostic scene path still present")
    if output.count(PLAYABLE_SCENE.encode()) != 1:
        raise AssertionError("playable scene path not present exactly once")
    return output


def is_v1_signature_entry(name: str) -> bool:
    upper = name.upper()
    if upper == "META-INF/MANIFEST.MF":
        return True
    if not upper.startswith("META-INF/"):
        return False
    return upper.endswith(SIGNATURE_SUFFIXES)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rewrite(source: Path, output: Path) -> dict:
    output.parent.mkdir(parents=True, exist_ok=True)
    input_count = 0
    output_count = 0
    removed_signatures: list[str] = []
    project_seen = 0

    with zipfile.ZipFile(source, "r") as src, zipfile.ZipFile(output, "w", allowZip64=True) as dst:
        for info in src.infolist():
            input_count += 1
            if is_v1_signature_entry(info.filename):
                removed_signatures.append(info.filename)
                continue
            data = src.read(info.filename)
            if info.filename == PROJECT_BINARY:
                project_seen += 1
                data = patch_project_binary(data)
            dst.writestr(info, data)
            output_count += 1

    if project_seen != 1:
        raise SystemExit(f"expected one {PROJECT_BINARY}, found {project_seen}")
    if not removed_signatures:
        raise SystemExit("no v1 signature entries were removed")

    with zipfile.ZipFile(output, "r") as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise SystemExit(f"rewritten APK ZIP integrity failed at {bad_member}")
        patched = archive.read(PROJECT_BINARY)
        names = set(archive.namelist())
    if DIAGNOSTIC_SCENE.encode() in patched:
        raise SystemExit("diagnostic main scene remains in rewritten APK")
    if patched.count(PLAYABLE_SCENE.encode()) != 1:
        raise SystemExit("production splash scene is not selected exactly once")
    if any(is_v1_signature_entry(name) for name in names):
        raise SystemExit("v1 signature entries remain in unsigned APK")

    return {
        "source_sha256": sha256(source),
        "source_size_bytes": source.stat().st_size,
        "unsigned_sha256": sha256(output),
        "unsigned_size_bytes": output.stat().st_size,
        "input_entry_count": input_count,
        "output_entry_count": output_count,
        "removed_v1_signature_entries": sorted(removed_signatures),
        "main_scene": PLAYABLE_SCENE,
        "diagnostic_main_scene_selected": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = rewrite(args.source, args.output)
    for key, value in report.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
