#!/usr/bin/env python3
"""Fail if presentation integration changes the accepted mobile-control baseline."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

FILE_HASHES = {
    'scripts/virtual_joystick.gd': '917fde4ffac3cf6f224d6761b26443ad3ffe66a913c56b0f11570058584f166e',
    'scripts/touch_input.gd': 'd9ff063d02140fdcd330a26f967982b929896b742d53d36678ad70608ba5591d',
    'scripts/player_controller.gd': '79f18a1950c9d0819e36ff102615eda2ed6796ba74daece9c7c2631c3e348366',
    'tests/mobile_input_pipeline_test.gd': 'c4d6c5d8fab9197259cd82ea02f76da4d906a1283e242b92e9a2892bf1c790bf',
    'scenes/mobile_input_pipeline_test.tscn': '29c3bba4dabf57c3f52f6d31c9de935bfaf45c3b96eae877b390c9dcf633d527',
    'tests/mobile_input_visual_evidence.gd': 'eb363e0ea7ce3c14b67e3c6d18be5f034c437f9841715582fa84b074301d4b78',
    'scenes/mobile_input_visual_evidence.tscn': 'c456c26db3f2e6d15a4de300c976613c6717aa6a1006c0b23c3b68dba20fbb1b',
}
FUNCTION_HASHES = {
    ('scripts/hud.gd', '_exit_tree'): '4b7dad0209c99ba9d6f119377446655f31ac7565446198d106f8034fbd0d8d87',
    ('scripts/hud.gd', '_build_touch_controls'): 'af46af6c6542fe8ad32ebb59ffe5d21f98c533011417832d61204cb6b76e1cbd',
    ('scripts/hud.gd', '_build_action_bar'): 'b55caddc0650cc63bb66db0d5b0b6a8eba998e63bb9cbfefd92e47f027bde353',
    ('scripts/hud.gd', '_round_action'): '399608f79b174f31596dfe4d50cee77fb27dfb6830e1a96cd4648bd7bed352ce',
    ('scripts/hud.gd', '_refresh_all'): 'edb9d3a666f6fe198dfa27e2d2b674603f83b7febd26e8d2d8fa0e8ed934dea3',
    ('scripts/world.gd', '_exit_tree'): 'fa19607a0388e58ff970bacc77139b736e33b827d8682d5859ee2fd62c90a5bc',
    ('scripts/world.gd', '_spawn_player'): '5d97ef3556dafa21f8e934fc4b6802e4957c2c4e3790a3c28289dfcfd05e0e05',
}
INPUT_SECTION_SHA256 = 'ffb79530e51ae22bb7664c98c73204079ecdaa6c53edcdd9b8aad16b9e4b22ad'
REQUIRED_SNIPPETS = {
    'scripts/hud.gd': [
        'root.mouse_filter = Control.MOUSE_FILTER_IGNORE',
        'joystick.name = "MovementJoystick"',
        '_walking_controls.visible = true',
        '_vehicle_controls.visible = false',
        '_walking_controls.visible = not in_vehicle',
        '_vehicle_controls.visible = in_vehicle',
    ],
    'scripts/world.gd': ['TouchInput.reset_all()'],
    'scripts/player_controller.gd': [
        'var touch_vector: Vector2 = TouchInput.movement',
        'move_and_slide()',
        '"is_local": is_local',
    ],
}


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def function_block(text: str, name: str) -> str:
    match = re.search(rf'(?ms)^func {re.escape(name)}\b.*?(?=^func |\Z)', text)
    if not match:
        raise RuntimeError(f'missing function: {name}')
    return match.group(0).rstrip() + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--json-out', type=Path, required=True)
    parser.add_argument('--markdown-out', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()

    results: list[dict[str, object]] = []
    failures: list[str] = []
    for relative, expected in FILE_HASHES.items():
        path = root / relative
        actual = digest_bytes(path.read_bytes()) if path.is_file() else 'MISSING'
        passed = actual == expected
        results.append({'kind': 'file', 'target': relative, 'expected': expected, 'actual': actual, 'pass': passed})
        if not passed:
            failures.append(relative)

    for (relative, name), expected in FUNCTION_HASHES.items():
        path = root / relative
        try:
            actual = digest_bytes(function_block(path.read_text(encoding='utf-8'), name).encode('utf-8'))
        except Exception as error:
            actual = f'ERROR: {error}'
        passed = actual == expected
        target = f'{relative}::{name}'
        results.append({'kind': 'function', 'target': target, 'expected': expected, 'actual': actual, 'pass': passed})
        if not passed:
            failures.append(target)

    project = (root / 'project.godot').read_text(encoding='utf-8')
    section = re.search(r'(?ms)^\[input\]\n.*?(?=^\[|\Z)', project)
    actual_input = digest_bytes((section.group(0).rstrip() + '\n').encode('utf-8')) if section else 'MISSING'
    input_pass = actual_input == INPUT_SECTION_SHA256
    results.append({'kind': 'section', 'target': 'project.godot::[input]', 'expected': INPUT_SECTION_SHA256, 'actual': actual_input, 'pass': input_pass})
    if not input_pass:
        failures.append('project.godot::[input]')

    for relative, snippets in REQUIRED_SNIPPETS.items():
        text = (root / relative).read_text(encoding='utf-8')
        for snippet in snippets:
            passed = snippet in text
            results.append({'kind': 'snippet', 'target': f'{relative}: {snippet}', 'pass': passed})
            if not passed:
                failures.append(f'{relative}: {snippet}')

    report = {
        'evidence_class': 'VERIFIED' if not failures else 'FAILED',
        'frozen_controls_commit': 'c5548465627942a2889a0bd09f8979c3a29fbcdd',
        'checks': len(results),
        'failures': failures,
        'results': results,
    }
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    lines = [
        '# Frozen Controls Verification', '',
        f"- Baseline commit: `{report['frozen_controls_commit']}`",
        f"- Checks: {len(results)}",
        f"- Failures: {len(failures)}", '',
        '| Check | Result |', '|---|---|',
    ]
    for item in results:
        lines.append(f"| `{item['target']}` | {'PASS' if item['pass'] else 'FAIL'} |")
    args.markdown_out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'checks': len(results), 'failures': failures}, indent=2))
    return 0 if not failures else 2


if __name__ == '__main__':
    raise SystemExit(main())
