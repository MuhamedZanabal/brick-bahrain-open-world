from pathlib import Path
import importlib.util,tempfile,unittest
MODULE=Path(__file__).resolve().parents[1]/'apply_premium_validation_corrections.py'
spec=importlib.util.spec_from_file_location('corrections',MODULE); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

class CorrectionTests(unittest.TestCase):
    def fixture(self,root:Path,npc_variant:str='with_default'):
        (root/'scripts').mkdir()
        variants={
            'with_default':'\t\t_anim_player = _model.get_meta("anim_player", null)\n',
            'without_default':'\t\t_anim_player = _model.get_meta("anim_player")\n',
            'typed_cast':'    _anim_player = _model.get_meta(&"anim_player") as AnimationPlayer\n',
        }
        (root/'scripts/npc_pedestrian.gd').write_text(variants[npc_variant])
        (root/'scripts/save_manager.gd').write_text('\tif player:\n\t\tsave_data["player"]["position"] = {\n')
        (root/'scripts/world.gd').write_text('\ttitle.text = "BRICK BAHRAIN"\n')
        (root/'export_presets.cfg').write_text('version/code=1\nversion/name="old"\n')
        (root/'project.godot').write_text('[application]\nconfig/name="Bahrain Brick"\n')
    def test_applies_exact_corrections_and_generates_missing_npc_scene(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fixture(root); report=mod.apply(root)
            self.assertEqual(report['conclusion'],'pass')
            self.assertIn('has_meta("anim_player")',(root/'scripts/npc_pedestrian.gd').read_text())
            self.assertIn('is_inside_tree()',(root/'scripts/save_manager.gd').read_text())
            self.assertIn('Bahrain Brick',(root/'scripts/world.gd').read_text())
            scene=root/'scenes/npc_pedestrian.tscn'
            self.assertTrue(scene.is_file())
            self.assertIn('res://scripts/npc_pedestrian.gd',scene.read_text())
            self.assertEqual(report['generated_runtime_resources'][0]['state'],'generated')
    def test_repairs_recovered_get_meta_variant_without_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fixture(root,'without_default'); mod.apply(root)
            body=(root/'scripts/npc_pedestrian.gd').read_text()
            self.assertIn('has_meta("anim_player")',body)
            self.assertNotIn('get_meta("anim_player")\n',body)
    def test_repairs_typed_string_name_variant(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fixture(root,'typed_cast'); mod.apply(root)
            body=(root/'scripts/npc_pedestrian.gd').read_text()
            self.assertIn('has_meta("anim_player")',body)
            self.assertIn('as AnimationPlayer',body)
    def test_is_idempotent_when_corrections_are_already_satisfied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fixture(root); mod.apply(root); report=mod.apply(root)
            self.assertTrue(all(item['states']==['already_satisfied'] for item in report['corrections']))
            self.assertEqual(report['generated_runtime_resources'][0]['state'],'already_satisfied')
    def test_incompatible_existing_npc_scene_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fixture(root); (root/'scenes').mkdir(); (root/'scenes/npc_pedestrian.tscn').write_text('invalid\n')
            with self.assertRaisesRegex(RuntimeError,'incompatible'):
                mod.apply(root)
    def test_test_source_may_name_obsolete_title_for_negative_assertion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fixture(root); tests=root/'tests'; tests.mkdir()
            (tests/'premium_test.gd').write_text('assert(not body.contains("BRICK BAHRAIN"))\n')
            report=mod.apply(root)
            self.assertEqual(report['obsolete_runtime_title_occurrences'],[])
    def test_runtime_stale_title_still_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fixture(root); (root/'scripts/other.gd').write_text('var title="Brick Bahrain"\n')
            with self.assertRaisesRegex(RuntimeError,'obsolete runtime title'):
                mod.apply(root)
    def test_fails_closed_when_expected_source_pattern_is_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fixture(root); (root/'scripts/world.gd').write_text('different\n')
            with self.assertRaises(RuntimeError): mod.apply(root)
if __name__=='__main__': unittest.main()
