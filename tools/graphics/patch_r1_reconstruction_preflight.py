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
# temporary copy and then proves every production-source byte against the accepted G0.2
# shared-import inventory before injecting any R1 test harness.
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
  'production_source_equivalence_required':True,
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
python3 - \\
  "$REPO_ROOT/reports/graphics/g0_2/shared_import_equivalence.json" \\
  "$GAME" \\
  "$OUTPUT_ROOT/SOURCE_TREE_EQUIVALENCE.json" <<'PY'
from pathlib import Path
import hashlib, json, sys
authority_path=Path(sys.argv[1]); game=Path(sys.argv[2]); out=Path(sys.argv[3])
authority=json.loads(authority_path.read_text())
roots=authority.get('clone_identity',{}).get('roots',[])
if not roots:
    raise SystemExit('accepted shared-import file inventory unavailable')
excluded={
  'tests/graphics/android_renderer_evidence.gd',
  'tests/graphics/android_renderer_evidence.tscn',
}
expected={}
for item in roots[0].get('files',[]):
    rel=item['path']
    if rel.startswith('.godot/') or rel in excluded:
        continue
    expected[rel]={'bytes':int(item['bytes']),'sha256':item['sha256']}
actual={}
for path in sorted(p for p in game.rglob('*') if p.is_file()):
    data=path.read_bytes(); rel=path.relative_to(game).as_posix()
    actual[rel]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
missing=sorted(set(expected)-set(actual))
unexpected=sorted(set(actual)-set(expected))
mismatched={rel:{'expected':expected[rel],'actual':actual[rel]} for rel in sorted(set(expected)&set(actual)) if expected[rel]!=actual[rel]}
passed=not missing and not unexpected and not mismatched
value={
  'schema_version':1,
  'authority_path':'reports/graphics/g0_2/shared_import_equivalence.json',
  'authority_aggregate_sha256':authority.get('aggregate_sha256'),
  'excluded_import_or_g0_2_harness_paths':sorted(excluded),
  'expected_file_count':len(expected),
  'actual_file_count':len(actual),
  'missing_paths':missing,
  'unexpected_paths':unexpected,
  'mismatched_paths':mismatched,
  'passed':passed,
  'production_source_byte_equivalent':passed,
}
out.write_text(json.dumps(value,indent=2,sort_keys=True)+'\\n')
if not passed:
    raise SystemExit(json.dumps({'missing':len(missing),'unexpected':len(unexpected),'mismatched':len(mismatched)},sort_keys=True))
PY
'''


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def patch_runner(runner: Path, report: Path) -> dict[str, object]:
    before = runner.read_bytes()
    text = before.decode()
    if "SOURCE_TREE_EQUIVALENCE.json" in text and "R1_RECONSTRUCTION_ENVIRONMENT.json" in text:
        status = "already_patched"
        after = before
    else:
        if text.count(OLD_BLOCK) != 1:
            raise ValueError("original reconstruction block not found exactly once")
        text = text.replace(OLD_BLOCK, NEW_BLOCK).replace("all eight independent modes", "all nine independent modes")
        after = text.encode()
        runner.write_bytes(after)
        runner.chmod(0o755)
        status = "patched"
    if b"SOURCE_TREE_EQUIVALENCE.json" not in after or b"R1_ACTUAL_IMAGE_VERSION" not in after:
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
        "accepted_source_tree_equivalence_required": True,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(patch_runner(args.runner, args.report), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
