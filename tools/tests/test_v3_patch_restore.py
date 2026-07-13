from pathlib import Path
import hashlib,importlib.util,tempfile,unittest
MODULE=Path(__file__).resolve().parents[1]/'v3_patch_restore.py'
spec=importlib.util.spec_from_file_location('restore',MODULE); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
class PatchRestorationTests(unittest.TestCase):
 def test_extracts_added_file_with_final_newline(self):
  patch=b'diff --git a/a.txt b/a.txt\nnew file mode 100644\n--- /dev/null\n+++ b/a.txt\n@@ -0,0 +1,2 @@\n+one\n+two\n'
  self.assertEqual(mod.extract_new_file(patch,'a.txt'),b'one\ntwo\n')
 def test_restores_only_manifested_new_file_with_exact_hash(self):
  patch=b'diff --git a/a.txt b/a.txt\nnew file mode 100644\n--- /dev/null\n+++ b/a.txt\n@@ -0,0 +1 @@\n+one\n'
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp); expected={'a.txt':hashlib.sha256(b'one\n').hexdigest()}
   restored=mod.restore_missing_new_files(root,patch,expected,{'a.txt'})
   self.assertEqual(restored,['a.txt']); self.assertEqual((root/'a.txt').read_bytes(),b'one\n')
 def test_rejects_reconstructed_content_hash_mismatch(self):
  patch=b'diff --git a/a.txt b/a.txt\nnew file mode 100644\n--- /dev/null\n+++ b/a.txt\n@@ -0,0 +1 @@\n+one\n'
  with tempfile.TemporaryDirectory() as tmp:
   with self.assertRaises(RuntimeError): mod.restore_missing_new_files(Path(tmp),patch,{'a.txt':'0'*64},{'a.txt'})
 def test_isolated_apply_stays_inside_nested_project(self):
  patch=b'diff --git a/project.godot b/project.godot\n--- a/project.godot\n+++ b/project.godot\n@@ -1 +1 @@\n-old\n+new\n'
  with tempfile.TemporaryDirectory() as tmp:
   repo=Path(tmp); __import__('subprocess').run(['git','init','-q'],cwd=repo,check=True)
   nested=repo/'recovery/v14'; nested.mkdir(parents=True); (nested/'project.godot').write_text('old\n')
   (repo/'project.godot').write_text('root\n')
   mod.apply_patch_isolated(nested,patch)
   self.assertEqual((nested/'project.godot').read_text(),'new\n')
   self.assertEqual((repo/'project.godot').read_text(),'root\n')
if __name__=='__main__': unittest.main()
