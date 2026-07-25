#!/usr/bin/env python3
from pathlib import Path

test = Path("tests/graphics/test_g0_2_android_renderer_qualification_contract.py")
text = test.read_text()
old = '''        self.assertIn("types: [opened]", text)
        self.assertNotIn("synchronize", text)
'''
new = '''        self.assertIn("types: [opened, synchronize]", text)
        self.assertIn("paths:\\n      - .github/workflows/bahrain-brick-g0-2-android-paired.yml", text)
'''
if old not in text:
    raise SystemExit("expected one-shot workflow assertions not found")
test.write_text(text.replace(old, new, 1))
