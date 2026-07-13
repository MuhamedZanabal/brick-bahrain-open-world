from pathlib import Path
import importlib.util,tempfile,unittest
MODULE=Path(__file__).resolve().parents[1]/'apply_premium_validation_corrections.py'
spec=importlib.util.spec_from_file_location('corrections',MODULE); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

class CorrectionTests(unittest.TestCase):
    def fixture(self,root:Path):
        (root/'scripts').mkdir()
        (root/'scripts/npc_pedestrian.gd').write_text('\t\t_anim_player = _model.get_meta("anim_player", null)\n')
        (root/'scripts/save_manager.gd').write_text('\tif player:\n\t\tsave_data["player"]["position"] = {\n')
        (root/'scripts/world.gd').write_text('\ttitle.text = "BRICK BAHRAIN"\n')
        (root/'export_presets.cfg').write_text('version/code=1\nversion/name="old"\n')
    def test_applies_exact_corrections_and_removes_stale_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fixture(root); report=mod.apply(root)
            self.assertEqual(report['conclusion'],'pass')
            self.assertIn('has_meta("anim_player")',(root/'scripts/npc_pedestrian.gd').read_text())
            self.assertIn('is_inside_tree()',(root/'scripts/save_manager.gd').read_text())
            self.assertIn('Bahrain Brick',(root/'scripts/world.gd').read_text())
    def test_fails_closed_when_expected_source_pattern_is_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fixture(root); (root/'scripts/world.gd').write_text('different\n')
            with self.assertRaises(RuntimeError): mod.apply(root)
if __name__=='__main__': unittest.main()
