#!/usr/bin/env python3
from pathlib import Path

runner = Path("tools/graphics/run_g0_2_android_paired.sh")
text = runner.read_text()
old = '  local out="$OUTPUT_ROOT/$key" state_file="$out/state_machine.json"\n'
new = '  local out="$OUTPUT_ROOT/$key"\n  local state_file="$out/state_machine.json"\n'
if old not in text:
    raise SystemExit("expected unbound-local declaration not found")
runner.write_text(text.replace(old, new, 1))

test = Path("tests/graphics/test_g0_2_android_renderer_qualification_contract.py")
text = test.read_text()
needle = '        self.assertIn("DIAGNOSTIC_ONLY_NOT_PHYSICAL_DEVICE_ACCEPTANCE", text)\n'
addition = (
    needle
    + "        self.assertNotIn('local out=\"$OUTPUT_ROOT/$key\" state_file=\"$out/state_machine.json\"', text)\n"
    + "        self.assertIn('local state_file=\"$out/state_machine.json\"', text)\n"
)
if "self.assertNotIn('local out=" not in text:
    if needle not in text:
        raise SystemExit("runner contract insertion point not found")
    text = text.replace(needle, addition, 1)
test.write_text(text)
