import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class BlenderScriptLauncherTests(unittest.TestCase):
    def test_launcher_adds_target_directory_and_preserves_arguments(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            (temp / "sibling.py").write_text("VALUE = 1405\n", encoding="utf-8")
            output = temp / "result.json"
            target = temp / "generator.py"
            target.write_text(
                "import json,sys\n"
                "from sibling import VALUE\n"
                "json.dump({'value': VALUE, 'args': sys.argv[1:]}, open(sys.argv[-1], 'w'))\n",
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["BAHRAIN_BRICK_BLENDER_SCRIPT"] = str(target)
            subprocess.run(
                [sys.executable, str(ROOT / "tools/asset_lab/blender_script_launcher.py"), "--", "--seed", "1405", str(output)],
                check=True,
                env=env,
            )
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["value"], 1405)
            self.assertEqual(result["args"][-3:], ["--seed", "1405", str(output)])


if __name__ == "__main__":
    unittest.main()
