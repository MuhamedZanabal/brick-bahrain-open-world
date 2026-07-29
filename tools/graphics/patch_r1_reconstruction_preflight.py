#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

OLD_BLOCK = '''# Reconstruct the accepted source authority exactly once. R1 adds only a test harness before import.
rm -rf "$RECONSTRUCTION"
bash "$REPO_ROOT/tools/vertical_slice/reconstruct_manama_souq_composite.sh" \\
  A "$RECONSTRUCTION" "$REPO_ROOT/authority/manama_souq_composite_source.json" "$(git -C "$REPO_ROOT" rev-parse HEAD)"
test -f "$GAME/project.godot"
test -f "$GAME/export_presets.cfg"
'''

NEW_BLOCK = '''# Reconstruct the accepted source authority exactly once. The historical script pins an
# obsolete hosted-runner image, so R1 patches only that environment assertion in a
# temporary copy. The reconstruction's own checksum-pinned FINAL_TREE_MANIFEST is then
# re-verified byte-for-byte before any R1 test harness is injected or Godot import runs.
rm -rf "$RECONSTRUCTION"
RECONSTRUCTION_SCRIPT="$OUTPUT_ROOT/reconstruct_manama_souq_composite.r1.sh"
python3 - \\
  "$REPO_ROOT/tools/vertical_slice/reconstruct_manama_souq_composite.sh" \\
  "$RECONSTRUCTION_SCRIPT" \\
  "$OUTPUT_ROOT/R1_RECONSTRUCTION_ENVIRONMENT.json" <<'PY'
from pathlib import Path
import json, os, sys
source=Path(sys.argv[1]); target=Path(sys.argv[2]); report=Path(sys.argv[3])
text=source.read_text()
old='test "${ImageVersion:-}" = "20260714.240.1"'
new='test "${ImageVersion:-}" = "${R1_ACTUAL_IMAGE_VERSION:?R1 actual image version required}"'
if text.count(old) != 1:
    raise SystemExit('historical runner-image assertion not found exactly once')
target.write_text(text.replace(old,new))
target.chmod(0o755)
actual=os.environ.get('ImageVersion','')
value={
  'schema_version':1,
  'historical_expected_image_version':'20260714.240.1',
  'actual_image_version':actual,
  'temporary_script_path':target.name,
  'only_modified_assertion':'runner image version equality',
  'tool_and_dependency_version_assertions_retained':True,
  'reconstruction_final_tree_manifest_required':True,
  'production_source_modified':False,
}
report.write_text(json.dumps(value,indent=2,sort_keys=True)+'\\n')
if not actual:
    raise SystemExit('ImageVersion is unavailable')
PY
R1_ACTUAL_IMAGE_VERSION="${ImageVersion:-}" bash "$RECONSTRUCTION_SCRIPT" \\
  A "$RECONSTRUCTION" "$REPO_ROOT/authority/manama_souq_composite_source.json" "$(git -C "$REPO_ROOT" rev-parse HEAD)"
test -f "$GAME/project.godot"
test -f "$GAME/export_presets.cfg"
python3 "$REPO_ROOT/tools/graphics/patch_r1_reconstruction_preflight.py" \\
  --manifest "$RECONSTRUCTION/evidence/FINAL_TREE_MANIFEST.json" \\
  --game "$GAME" \\
  --output "$OUTPUT_ROOT/SOURCE_TREE_EQUIVALENCE.json"
'''


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_reconstruction_manifest(manifest_path: Path, game: Path, output: Path) -> dict[str, object]:
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    records = manifest.get("files")
    if not isinstance(records, list) or not records:
        raise ValueError("FINAL_TREE_MANIFEST.json does not contain a non-empty files list")

    expected: dict[str, dict[str, object]] = {}
    for item in records:
        rel = str(item["path"])
        expected[rel] = {
            "bytes": int(item["bytes"]),
            "sha256": str(item["sha256"]),
            "origin": str(item.get("origin", "")),
        }

    actual: dict[str, dict[str, object]] = {}
    for path in sorted(candidate for candidate in game.rglob("*") if candidate.is_file()):
        data = path.read_bytes()
        rel = path.relative_to(game).as_posix()
        actual[rel] = {"bytes": len(data), "sha256": sha256(data)}

    missing = sorted(set(expected) - set(actual))
    unexpected = sorted(set(actual) - set(expected))
    mismatched = {
        rel: {
            "expected": {"bytes": expected[rel]["bytes"], "sha256": expected[rel]["sha256"]},
            "actual": actual[rel],
        }
        for rel in sorted(set(expected) & set(actual))
        if actual[rel]["bytes"] != expected[rel]["bytes"]
        or actual[rel]["sha256"] != expected[rel]["sha256"]
    }
    passed = not missing and not unexpected and not mismatched
    value: dict[str, object] = {
        "schema_version": 1,
        "authority_class": "RECONSTRUCTION_FINAL_TREE_MANIFEST",
        "manifest_path": manifest_path.as_posix(),
        "manifest_sha256": sha256(manifest_bytes),
        "manifest_file_count": int(manifest.get("file_count", len(expected))),
        "manifest_total_bytes": int(
            manifest.get("total_bytes", sum(int(record["bytes"]) for record in expected.values()))
        ),
        "manifest_aggregate_tree_sha256": manifest.get("aggregate_tree_sha256"),
        "expected_file_count": len(expected),
        "actual_file_count": len(actual),
        "missing_paths": missing,
        "unexpected_paths": unexpected,
        "mismatched_paths": mismatched,
        "passed": passed,
        "production_source_byte_equivalent": passed,
        "import_or_qa_generated_files_in_scope": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    if not passed:
        raise ValueError(
            json.dumps(
                {"missing": len(missing), "unexpected": len(unexpected), "mismatched": len(mismatched)},
                sort_keys=True,
            )
        )
    return value


def patch_runner(runner: Path, report: Path) -> dict[str, object]:
    before = runner.read_bytes()
    text = before.decode()
    if "FINAL_TREE_MANIFEST.json" in text and "R1_RECONSTRUCTION_ENVIRONMENT.json" in text:
        status = "already_patched"
        after = before
    else:
        if text.count(OLD_BLOCK) != 1:
            raise ValueError("original reconstruction block not found exactly once")
        text = text.replace(OLD_BLOCK, NEW_BLOCK).replace(
            "all eight independent modes", "all nine independent modes"
        )
        after = text.encode()
        runner.write_bytes(after)
        runner.chmod(0o755)
        status = "patched"
    if b"FINAL_TREE_MANIFEST.json" not in after or b"R1_ACTUAL_IMAGE_VERSION" not in after:
        raise ValueError("patched runner preflight markers are incomplete")
    value = {
        "schema_version": 1,
        "status": status,
        "runner": runner.as_posix(),
        "before_sha256": sha256(before),
        "after_sha256": sha256(after),
        "changed": before != after,
        "only_runner_harness_modified": True,
        "production_source_modified": False,
        "reconstruction_environment_assertion_adjusted": True,
        "reconstruction_final_tree_equivalence_required": True,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--game", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.runner is not None or args.report is not None:
        if args.runner is None or args.report is None or any(
            value is not None for value in (args.manifest, args.game, args.output)
        ):
            parser.error(
                "--runner and --report must be supplied together and cannot be mixed with verification arguments"
            )
        result = patch_runner(args.runner, args.report)
    else:
        if any(value is None for value in (args.manifest, args.game, args.output)):
            parser.error("--manifest, --game, and --output are required for source verification")
        result = verify_reconstruction_manifest(args.manifest, args.game, args.output)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
