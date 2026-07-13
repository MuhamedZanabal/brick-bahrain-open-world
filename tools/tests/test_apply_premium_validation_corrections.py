from pathlib import Path
import importlib.util,tempfile,unittest
MODULE=Path(__file__).resolve().parents[1]/'apply_premium_validation_corrections.py'
spec=importlib.util.spec_from_file_location('corrections',MODULE); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

class CorrectionTests(unittest.TestCase):
    def fixture(self,root:Path,npc_variant:str='with_default',save_condition:str='if player:',save_shape:str='direct',world_guarded:bool=False):
        (root/'scripts').mkdir()
        variants={
            'with_default':'\t\t_anim_player = _model.get_meta("anim_player", null)\n',
            'without_default':'\t\t_anim_player = _model.get_meta("anim_player")\n',
            'typed_cast':'    _anim_player = _model.get_meta(&"anim_player") as AnimationPlayer\n',
            'recovered_variable':'\t\t_animation_player = _model.get_meta("anim_player", null) as AnimationPlayer\n',
        }
        (root/'scripts/npc_pedestrian.gd').write_text(variants[npc_variant])
        if save_shape == 'direct':
            save_source=(
                '\t%s\n' % save_condition
                + '\t\tsave_data["player"]["position"] = {\n'
                + '\t\t\t"x": player.global_position.x,\n'
                + '\t\t\t"y": player.global_position.y,\n'
                + '\t\t\t"z": player.global_position.z,\n'
                + '\t\t}\n'
            )
        elif save_shape == 'staged':
            save_source=(
                '\tvar position: Vector3 = Vector3.ZERO\n'
                + '\t%s\n' % save_condition
                + '\t\tposition = player.global_position\n'
                + '\tsave_data["player"]["position"] = _vector_to_dict(position)\n'
            )
        else:
            raise AssertionError(save_shape)
        (root/'scripts/save_manager.gd').write_text(save_source)
        guard = 'if player and player is Node3D and player.is_inside_tree():' if world_guarded else 'if player and player is Node3D:'
        (root/'scripts/world.gd').write_text(
            '\t\ttitle.text = "BRICK BAHRAIN"\n\n'
            + 'func _exit_tree() -> void:\n'
            + '\tif GameManager.current_state == GameManager.GameState.IN_WORLD:\n'
            + '\t\t' + guard + '\n'
            + '\t\t\tSaveManager.set_position((player as Node3D).global_position)\n'
            + '\t\tSaveManager.save_game("world exit")\n'
        )
        (root/'scripts/npc_manager.gd').write_text('const NPC_SCENE = preload("res://scenes/npc_pedestrian.tscn")\n')
        (root/'export_presets.cfg').write_text('version/code=1\nversion/name="old"\n')
        (root/'project.godot').write_text('[application]\nconfig/name="Bahrain Brick"\n')
    def test_applies_exact_corrections_and_generates_missing_npc_scene(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fixture(root); report=mod.apply(root)
            self.assertEqual(report['conclusion'],'pass')
            self.assertIn('has_meta("anim_player")',(root/'scripts/npc_pedestrian.gd').read_text())
            self.assertIn('is_inside_tree()',(root/'scripts/save_manager.gd').read_text())
            world=(root/'scripts/world.gd').read_text()
            self.assertIn('Bahrain Brick',world)
            self.assertIn('player is Node3D and player.is_inside_tree()',world)
            scene=root/'scenes/npc_pedestrian.tscn'
            self.assertTrue(scene.is_file())
            self.assertEqual(scene.read_text(),mod.NPC_SCENE_CONTENT)
            self.assertEqual(report['generated_runtime_resources'][0]['state'],'generated')
            self.assertIn('scripts/save_manager.gd',report['diagnostic_sources'])
            self.assertIn('scenes/npc_pedestrian.tscn',report['diagnostic_sources'])
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
            self.assertIn('_anim_player =',body)
            self.assertIn('has_meta("anim_player")',body)
            self.assertIn('as AnimationPlayer',body)
    def test_repairs_actual_recovered_animation_player_variable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fixture(root,'recovered_variable'); mod.apply(root)
            body=(root/'scripts/npc_pedestrian.gd').read_text()
            self.assertIn('_animation_player =',body)
            self.assertIn('has_meta("anim_player")',body)
            self.assertIn('as AnimationPlayer',body)
            self.assertNotIn('\n\t\t_anim_player =',body)
    def test_adds_tree_guard_to_direct_position_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fixture(root,save_condition='if is_instance_valid(player):'); mod.apply(root)
            body=(root/'scripts/save_manager.gd').read_text()
            self.assertIn('if is_instance_valid(player) and player.is_inside_tree():',body)
    def test_adds_tree_guard_to_recovered_staged_position_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fixture(root,save_condition='if is_instance_valid(player):',save_shape='staged'); mod.apply(root)
            body=(root/'scripts/save_manager.gd').read_text()
            self.assertIn('if is_instance_valid(player) and player.is_inside_tree():',body)
            self.assertIn('position = player.global_position',body)
            self.assertIn('_vector_to_dict(position)',body)
    def test_world_exit_guard_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fixture(root,world_guarded=True); report=mod.apply(root)
            world_result=next(item for item in report['corrections'] if item['path']=='scripts/world.gd')
            self.assertEqual(world_result['states'][1],'already_satisfied')
    def test_save_guard_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fixture(root,save_condition='if player and player.is_inside_tree():',save_shape='staged'); report=mod.apply(root)
            save_result=next(item for item in report['corrections'] if item['path']=='scripts/save_manager.gd')
            self.assertEqual(save_result['states'],['already_satisfied'])
    def test_is_idempotent_when_corrections_are_already_satisfied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fixture(root,'recovered_variable'); mod.apply(root); report=mod.apply(root)
            self.assertTrue(all(all(state=='already_satisfied' for state in item['states']) for item in report['corrections']))
            self.assertEqual(report['generated_runtime_resources'][0]['state'],'already_satisfied')
    def test_compatible_noncanonical_npc_scene_is_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fixture(root); (root/'scenes').mkdir()
            (root/'scenes/npc_pedestrian.tscn').write_text(mod.NPC_SCENE_CONTENT + 'metadata/test_only = true\n')
            report=mod.apply(root)
            self.assertEqual((root/'scenes/npc_pedestrian.tscn').read_text(),mod.NPC_SCENE_CONTENT)
            self.assertEqual(report['generated_runtime_resources'][0]['state'],'replaced')
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
