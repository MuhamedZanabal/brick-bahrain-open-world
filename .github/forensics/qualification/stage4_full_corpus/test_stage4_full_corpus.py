import importlib.util,json,os,tempfile,unittest
from pathlib import Path
P=Path(__file__).with_name("stage4_full_corpus.py");s=importlib.util.spec_from_file_location("stage4",P);m=importlib.util.module_from_spec(s)
try:s.loader.exec_module(m)
except FileNotFoundError:m=None
class T(unittest.TestCase):
 def req(self):self.assertIsNotNone(m)
 def test_authorities(self):
  self.req();self.assertEqual(m.ENGINE_VERSION,"4.4.1-stable");self.assertEqual(m.MODEL_COUNTS,{"GLB":578,"GLTF":203,"FBX":18,"OBJ":1});self.assertEqual(m.MATRIX_MODEL_COUNT,436);self.assertEqual(len(m.MODEL_RESULT_VALUES),8)
 def test_shards(self):
  self.req();self.assertEqual(m.shard_bounds(0),(0,19));self.assertEqual(m.shard_bounds(39),(780,799));self.assertEqual([i for s in range(40) for i in range(*((lambda b:(b[0],b[1]+1))(m.shard_bounds(s))))],list(range(800)))
 def test_paths(self):
  self.req();self.assertEqual(m.normalize_relative_path("a/b.glb"),"a/b.glb")
  for x in ("../a","/a","a\\b","a/./b",""):
   with self.assertRaises(m.AuthorityError):m.normalize_relative_path(x)
 def test_matrix(self):
  self.req();v={"assets":[{"paths":{"balanced":["res://a.glb"],"high":["res://b.glb"],"low":["res://c.glb"]}}],"commercial":[{"path":"res://d.glb"}]};self.assertEqual(m.matrix_paths_from_manifest(v),{"a.glb","b.glb","c.glb","d.glb"})
 def test_deps(self):
  self.req()
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);(r/"m").mkdir();(r/"t").mkdir();p=r/"m/a.gltf";p.write_text(json.dumps({"buffers":[{"uri":"a.bin"}],"images":[{"uri":"../t/a.png"},{"uri":"data:x"}]}));(r/"m/a.bin").write_bytes(b"x");(r/"t/a.png").write_bytes(b"x");self.assertEqual(m.extract_dependencies(p,"m/a.gltf",r),["m/a.bin","t/a.png"])
 def test_sidecar(self):
  self.req();d=b'[remap]\nimporter="scene"\ntype="PackedScene"\nuid="uid://x"\npath="res://.godot/imported/a.scn"\n[deps]\nsource_file="res://a.glb"\ndest_files=["res://.godot/imported/a.scn"]\n[params]\nfoo=true\n';v=m.parse_import_sidecar(d);self.assertEqual(v["source_file"],"a.glb");self.assertEqual(v["imported_relative_path"],".godot/imported/a.scn")
 def test_diag(self):
  self.req();v=m.bounded_byte_diagnostic(b"abc123",b"abc999x");self.assertEqual(v["first_differing_byte_offset"],3);self.assertEqual(v["final_differing_byte_offset"],6)
 def test_umask(self):
  self.req();old=os.umask(0o027)
  try:
   with tempfile.TemporaryDirectory() as td:m.environment_snapshot(Path(td))
   seen=os.umask(0o027);os.umask(seen);self.assertEqual(seen,0o027)
  finally:os.umask(old)
 def test_compare(self):
  self.req()
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);a=r/"a";b=r/"b";a.write_bytes(b"x");b.write_bytes(b"x");x={"global_index":0,"logical_source_path":"a.glb","source_type":"GLB","matrix_member":False,"source_sha256":"1"*64,"authority_source_md5":"2"*32,"parsed_source_md5":"2"*32,"sidecar_sha256":"3"*64,"sidecar_authority_equal":True,"imported_sha256":m.sha256_file(a),"imported_byte_size":1,"imported_evidence_path":str(a),"destination_md5":"4"*32,"md5_companion_sha256":"5"*64};y=dict(x,imported_evidence_path=str(b));self.assertEqual(m.compare_model_records(x,y)["result"],"PASS");y["sidecar_authority_equal"]=False;self.assertEqual(m.compare_model_records(x,y)["result"],"SIDECAR_AUTHORITY_FAILURE")
 def test_inventory(self):
  self.req()
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);(r/"x").write_bytes(b"x");i=m.build_inventory(r);m.verify_inventory(r,i);(r/"x").write_bytes(b"y")
   with self.assertRaises(m.AuthorityError):m.verify_inventory(r,i)
 def test_aggregate(self):
  self.req();reports=[]
  for s in range(40):
   rows=[]
   for i in range(s*20,s*20+20):
    t="GLB" if i<578 else "GLTF" if i<781 else "FBX" if i<799 else "OBJ";rows.append({"global_index":i,"logical_source_path":str(i),"source_type":t,"matrix_member":i<436,"result":"PASS","imported_binary_equal":True,"destination_md5_equal":True,"source_md5_equal":True,"sidecar_equal":True,"md5_companion_equal":True})
   reports.append({"shard_index":s,"models":rows})
  imports={"D1":{"import_completed":True,"imported_model_count":800},"D2":{"import_completed":True,"imported_model_count":800}};self.assertEqual(m.aggregate_stage4(reports,imports)["classification"],"STAGE4_PASS_PENDING_STAGE5");reports[0]["models"][0].update(result="NONDETERMINISTIC",imported_binary_equal=False);self.assertEqual(m.aggregate_stage4(reports,imports)["classification"],"Q3")
if __name__=="__main__":unittest.main()
