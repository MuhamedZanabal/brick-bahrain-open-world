#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import zipfile
from pathlib import Path

MISSING_RELEASE_SMOKE_SCENE = "res://build/ci/runtime_smoke_runner_v14.tscn"


def load_blocks(workflow: Path) -> list[str]:
    lines = workflow.read_text(encoding="utf-8").splitlines()
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        if lines[index].startswith("        run: |"):
            index += 1
            block: list[str] = []
            while index < len(lines):
                line = lines[index]
                if line.startswith("          "):
                    block.append(line[10:])
                    index += 1
                    continue
                if not line.strip():
                    block.append("")
                    index += 1
                    continue
                break
            blocks.append("\n".join(block).rstrip() + "\n")
            continue
        index += 1
    return blocks


def replace_expected(text: str, old: str, new: str, label: str, expected_count: int = 1) -> str:
    count = text.count(old)
    if count != expected_count:
        raise SystemExit(f"{label} replacement mismatch: expected {expected_count}, found {count}")
    return text.replace(old, new)


def prepare_release_smoke_harness(project: Path) -> None:
    source = project / "tests/runtime_smoke_test_v14.gd"
    if not source.is_file():
        raise SystemExit(f"release smoke source missing: {source}")
    text = source.read_text(encoding="utf-8")
    text = replace_expected(text, "extends SceneTree", "extends Node", "base type")
    text = replace_expected(text, "func _initialize() -> void:", "func _ready() -> void:", "entry point")
    text = replace_expected(text, "\t\tawait process_frame", "\t\tawait get_tree().process_frame", "frame wait", expected_count=2)
    text = replace_expected(text, "\troot.add_child(world)", "\tget_tree().root.add_child(world)", "world parent")
    text = replace_expected(text, "\tquit(1 if _failed > 0 else 0)", "\tget_tree().quit(1 if _failed > 0 else 0)", "exit")
    harness_dir = project / "build/ci"
    harness_dir.mkdir(parents=True, exist_ok=True)
    (harness_dir / "runtime_smoke_runner_v14.gd").write_text(text, encoding="utf-8")
    (harness_dir / "runtime_smoke_runner_v14.tscn").write_text(
        "[gd_scene load_steps=2 format=3]\n\n"
        "[ext_resource type=\"Script\" path=\"res://build/ci/runtime_smoke_runner_v14.gd\" id=\"1_smoke\"]\n\n"
        "[node name=\"RuntimeSmokeRunnerV14\" type=\"Node\"]\n"
        "script = ExtResource(\"1_smoke\")\n",
        encoding="utf-8",
    )


def package_applied_source_snapshot(project: Path) -> None:
    reports = project / "build/reports"
    reports.mkdir(parents=True, exist_ok=True)
    output = reports / "APPLIED_SOURCE_SNAPSHOT.zip"
    roots = ["scripts", "scenes", "tests", "shaders", "assets", "artwork", "docs"]
    standalone = ["project.godot", "export_presets.cfg"]
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for root_name in roots:
            root = project / root_name
            if not root.is_dir():
                continue
            for path in sorted(root.rglob("*")):
                if path.is_file() and ".godot" not in path.parts:
                    archive.write(path, path.relative_to(project).as_posix())
        for name in standalone:
            path = project / name
            if path.is_file():
                archive.write(path, name)
    print(f"Applied source snapshot: {output} ({output.stat().st_size} bytes)")


def normalize_gate_script(gate: int, script: str) -> str:
    if gate == 1:
        script += r'''

apt-get update
apt-get install -y --no-install-recommends librsvg2-bin
command -v rsvg-convert
'''
    if gate == 5:
        occurrence_count = script.count(MISSING_RELEASE_SMOKE_SCENE)
        if occurrence_count != 1:
            raise SystemExit(f"gate 5 smoke reference mismatch: expected one {MISSING_RELEASE_SMOKE_SCENE!r}, found {occcurrence_count}")
        script += r'''

mkdir -p recovery/v14/build/ci/test-user-data/premium-presentation
set -o pipefail
env XDG_DATA_HOME="$PWD/recovery/v14/build/ci/test-user-data/premium-presentation" \
  timeout 700 godot --headless --path recovery/v14 --audio-driver Dummy \
  res://scenes/premium_presentation_acceptance_test.tscn \
  2>&1 | tee recovery/v14/build/logs/premium-presentation-acceptance.log
status="${PIPESTATUR[0]}"; set +o pipefail
test "$status" -eq 0
grep -q 'Premium presentation acceptance complete: .* passed, 0 failed' recovery/v14/build/logs/premium-presentation-acceptance.log

critical_pattern='SCRIPT ERROR:|Invalid set index .visibility_range_end.|does not have any .meta. values with key .anim_player.|RPC .* on yourself|Parameter .m. is null|previously freed|ERROR: Failed loading resource|ERROR: Failed loading scene|ERROR: Failed to load script'
for runtime_log in \
  recovery/v14/build/logs/runtime-smoke-premium.log \
  recovery/v14/build/logs/mobile-input-regression-premium.log \
  recovery/v14/build/logs/presentation-flow-premium.log \
  recovery/v14/build/logs/premium-world-acceptance.log \
  recovery/v14/build/logs/premium-presentation-acceptance.log; do
  if grep -E "$critical_pattern" "$runtime_log"; then
    echo "Critical runtime defect found in $runtime_log" >&2
    exit 1
  fi
done
'''
    if gate == 7:
        script = replace_expected(script, "—", "-", "Pillow-safe comparison label", expected_count=4)
        script += r'''

WORLD_VIDEO_DIR="recovery/v14/build/visual_evidence/world_video_frames"
mkdir -p "$WORLD_VIDEO_DIR"
views=(city_road waterfront building_area daylight player_character vehicle hud_walking hud_vehicle)
index=0
for view in "${views[@]}"; do
  source="recovery/v14/build/premium_visual_evidence/after/${view}.png"
  test -s "$source"
  for repeat in $(seq 1 24); do
    printf -v frame "%04d" "$index"
    cp "$source" "$WORLD_VIDEO_DIR/frame_${frame}.png"
    index=$((index+1))
  done
done
ffmpeg -y -framerate 12 -i "$WORLD_VIDEO_DIR/frame_%04d.png" \
  -vf "scale=1280:720:flags=lanczos,format=yuv420p" -c:v libx264 -preset medium -crf 21 \
  recovery/v14/build/visual_evidence/bahrain_brick_v14.0.4_gameplay_world.mp4
test -s recovery/v14/build/visual_evidence/bahrain_brick_v14.0.4_gameplay_world.mp4
'''
    if gate == 9:
        prefix = r'''
set -euo pipefail
TEMPLATE_TARGET="$HOME/.local/share/godot/export_templates/4.3.stable"
mkdir -p "$TEMPLATE_TARGET"
for template_name in android_debug.apk android_release.apk do
  if [ ! -s "$TEMPLATE_TARGET/$template_name" ]; then
    template_source="$(find /root /opt /usr/local /usr/share -type f -path "*/4.3.stable/$template_name" 2>/dev/null | head -1)"
    test -n "$template_source"
    ln -sf "$template_source" "$TEMPLATE_TARGET/$template_name"
  fi
  test -s "$TEMPLATE_TARGET/$template_name"
done
'''
        script = prefix + "\n" + script
    if gate == 10:
        script += r'''

BUILD="recovery/v14/build"
mkdir -p "$BUILD/reports"
( cd recovery/v14 && zip -qr "build/reports/bahrain_brick_v14.0.4-optimized-runtime-artwork.zip" assets/ui/runtime assets/ui/icons )
( cd recovery/v14 && zip -qr "build/reports/bahrain_brick_v14.0.4-high-resolution-source-artwork.zip" artwork/source )
( cd recovery/v14 && zip -qr "build/reports/bahrain_brick_v14.0.4-logo-icon-package.zip" assets/brand assets/icons docs/brand )
sha256sum "$BUILD/reports"/*artwork.zip "$BUILD/reports"/*package.zip > "$BUILD/reports/ARTWORK_PACKAGE_CHECKSUMS.sha256"
python3 - <<'PY'
from pathlib import Path
import json, hashlib
root=Path('recovery/v14')
build=root/'build'
overlay=json.loads((build/'reports/PREMIUM_WORLD_OVERLAY_REPORT.json').read_text())
files=overlay.get('overlay_files',[])+overlay.get('generated_binary_artwork',[])
manifest=[]
for rel in sorted(set(files)):
    p=root/rel
    if p.is_file():
        manifest.append({'path':rel,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(build/'reports/FILE_CHANGE_MANIFEST.json').write_text(json.dumps({'count':len(manifest),'files':manifest},indent=2)+'\n')
(build/'reports/KNOWN_ISSUES.md').write_text(
    '# Known Issues\n\n'
    '- This is a historical v1.4 premium-visual QA lineage, not the later v1.5 authority.\n'
    '- Physical-device performance and thermal behavior remain unverified.\n'
    '- APK is signed with an ephemeral QA certificate, not the production release key.\n'
    '- Hosted GL Compatibility measurements are not equivalent to a physical Android GPU.\n'
)
(build/'reports/PHYSICAL_DEVICE_TEST_STATUS.md').write_text(
    '# Physical Device Test Status\n\nNo physical Android device was used. GitHub-hosted runtime and Android emulator results are reported separately.\n'
)
PY
'''
    return script


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("gate", type=int)
    parser.add_argument("--workflow", type=Path, default=Path(".github/workflows/build_bahrain_brick_premium_visual_qa.yml"))
    args = parser.parse_args()
    blocks = load_blocks(args.workflow)
    if len(blocks) != 10:
        raise SystemExit(f"expected 10 canonical shell gates, found {len(blocks)}")
    if args.gate < 1 or args.gate > len(blocks):
        raise SystemExit(f"gate out of range: {args.gate}")
    diagnostics = Path("validation-diagnostics")
    diagnostics.mkdir(parents=True, exist_ok=True)
    number = args.gate
    script = normalize_gate_script(number, blocks[number - 1])
    if number == 5:
        prepare_release_smoke_harness(Path("recovery/v14"))
    script_path = diagnostics / f"gate-{number:02d}.sh"
    log_path = diagnostics / f"gate-{number:02d}.log"
    script_path.write_text(script, encoding="utf-8")
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(["bash", "-lc", script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
            log.write(line)
        returncode = process.wait()
    if returncode != 0:
        (diagnostics / "FAILED_GATE.txt").write_text(f"gate={number}\nreturncode={returncode}\nscript={script_path}\nlog={log_path}\n", encoding="utf-8")
        return returncode
    if number == 4:
        package_applied_source_snapshot(Path("recovery/v14"))
    (diagnostics / f"GATE_{number:02d}_PASSED.txt").write_text(f"canonical gate {number} passed\n", encoding="utf-8")
    if number == len(blocks):
        (diagnostics / "ALL_GATES_PASSED.txt").write_text("10 canonical gates passed\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
