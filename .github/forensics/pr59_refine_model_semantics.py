#!/usr/bin/env python3
from __future__ import annotations
import argparse, collections, hashlib, json
from pathlib import Path
from typing import Any

def canonical(v:Any)->str:return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def digest(v:Any)->str:return hashlib.sha256(canonical(v).encode()).hexdigest()
def stable_identifier(x:dict[str,Any])->dict[str,Any]:
 return {'class':x.get('class'),'resource_name':x.get('resource_name'),'local_to_scene':x.get('local_to_scene')}
def node_projection(section:list[Any])->list[Any]:
 out=[]
 for scene in section:
  nodes=[]
  for n in scene.get('nodes',[]):
   nodes.append({'index':n.get('index'),'sibling_index':n.get('sibling_index'),'path':n.get('path'),'parent_path':n.get('parent_path'),'name':n.get('name'),'type':n.get('type'),'owner_path':n.get('owner_path'),'groups':sorted(n.get('groups',[])),'instance_placeholder':n.get('instance_placeholder'),'placeholder_path':n.get('placeholder_path'),'property_names':sorted(p.get('name') for p in n.get('properties',[]))})
  con=[]
  for c in scene.get('connections',[]):con.append({k:c.get(k) for k in ('source','signal','target','method','flags','unbinds')})
  con.sort(key=canonical)
  out.append({'node_count':scene.get('node_count'),'nodes':nodes,'connection_count':scene.get('connection_count'),'connections':con})
 return out
def multiset(section:list[Any])->collections.Counter[str]:return collections.Counter(canonical(x) for x in section)
def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();root=Path(a.input);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
 d1={r['selection_id']:r for r in json.loads((root/'D1_MODEL_SEMANTIC_GRAPH.json').read_text())['resources']};d2={r['selection_id']:r for r in json.loads((root/'D2_MODEL_SEMANTIC_GRAPH.json').read_text())['resources']};assert set(d1)==set(d2) and len(d1)==8
 rows=[];counts=collections.Counter();summary=collections.Counter()
 for sid in sorted(d1):
  x=d1[sid];y=d2[sid];fail=x.get('failures',[])+y.get('failures',[])
  ids1=x['sections']['identifiers'];ids2=y['sections']['identifiers'];stable1=[stable_identifier(z) for z in ids1];stable2=[stable_identifier(z) for z in ids2]
  identifier_multiset_equal=multiset(stable1)==multiset(stable2)
  identifiers_equal=ids1==ids2
  identifier_variance=identifier_multiset_equal and not identifiers_equal
  collection_order_variance=identifier_multiset_equal and stable1!=stable2
  content={}
  for sec in ('geometry','materials','animations','skeletons'):
   content[sec]={'equal_as_multiset':multiset(x['sections'][sec])==multiset(y['sections'][sec]),'d1_multiset_sha256':digest(sorted(canonical(z) for z in x['sections'][sec])),'d2_multiset_sha256':digest(sorted(canonical(z) for z in y['sections'][sec]))}
  node1=node_projection(x['sections']['nodes']);node2=node_projection(y['sections']['nodes']);node_equal=node1==node2
  float_equal=multiset(x['sections']['floats'])==multiset(y['sections']['floats'])
  explicit_order_equal=x['sections']['order']==y['sections']['order']
  actual=not all(v['equal_as_multiset'] for v in content.values()) or not node_equal or not float_equal
  if fail:classification='G';reasons=['diagnostic_failure']
  elif actual:
   classification='F' if identifier_variance or collection_order_variance else 'E';reasons=['actual_semantic_content_variance']
  elif identifier_variance and collection_order_variance:classification='F';reasons=['local_resource_identifier_variance','resource_collection_order_variance']
  elif identifier_variance:classification='A';reasons=['local_resource_identifier_variance_only']
  elif collection_order_variance:classification='D';reasons=['resource_collection_order_variance_only']
  else:classification='B';reasons=['binary_serialization_variance_with_identical_canonical_semantics']
  counts[classification]+=1
  summary['identifier_variance']+=int(identifier_variance);summary['collection_order_variance']+=int(collection_order_variance);summary['geometry_variance']+=int(not content['geometry']['equal_as_multiset']);summary['materials_variance']+=int(not content['materials']['equal_as_multiset']);summary['animations_variance']+=int(not content['animations']['equal_as_multiset']);summary['skeletons_variance']+=int(not content['skeletons']['equal_as_multiset']);summary['node_structure_variance']+=int(not node_equal);summary['float_multiset_variance']+=int(not float_equal);summary['explicit_order_section_variance']+=int(not explicit_order_equal)
  rows.append({'selection_id':sid,'logical_source':x['logical_source'],'source_type':x['source_type'],'classification':classification,'reasons':reasons,'identifier_variance':identifier_variance,'identifier_identity_multiset_equal':identifier_multiset_equal,'resource_collection_order_variance':collection_order_variance,'geometry_equal':content['geometry']['equal_as_multiset'],'materials_equal':content['materials']['equal_as_multiset'],'animations_equal_as_named_resource_multiset':content['animations']['equal_as_multiset'],'skeletons_equal':content['skeletons']['equal_as_multiset'],'node_hierarchy_and_property_schema_equal':node_equal,'float_multiset_equal':float_equal,'explicit_scene_order_section_equal':explicit_order_equal,'content_sections':content,'failures':fail})
 report={'schema_version':2,'classification_counts':dict(sorted(counts.items())),'summary_counts':dict(sorted(summary.items())),'resources':rows,'method':{'identifier_comparison':'All resource_path and scene_unique_id values retained in evidence; stable identity multiset uses class, resource_name, local_to_scene.','content_comparison':'Geometry, materials, animations, skeletons and lossless float records compared as multisets to distinguish semantic content from importer collection order.','node_comparison':'Exact node count, path, parent, name, type, owner, groups, placeholder state, property-name schema and connection structure; embedded resource values are evaluated in their dedicated semantic sections.','fail_closed':'Any diagnostic failure or semantic multiset mismatch is visible and cannot be classified A/B/D.'}}
 (out/'MODEL_SEMANTIC_COMPARISON_REFINED.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 assert counts=={'A':6,'B':1,'F':1},counts
 assert summary['geometry_variance']==summary['materials_variance']==summary['animations_variance']==summary['skeletons_variance']==summary['node_structure_variance']==0,summary
 return 0
if __name__=='__main__':raise SystemExit(main())
