#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any

EXPECTED_COMMIT='77dcf97d82cbfe4e4615475fa52ca03da645dbd8'

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
    return h.hexdigest()

def write(p:Path,v:Any)->None:
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')

def snippets(root:Path,rel:str,function:str,needles:list[str])->list[dict[str,Any]]:
    p=root/rel
    if not p.is_file():
        return [{'source_file':rel,'function':function,'failure':'file_missing'}]
    lines=p.read_text(errors='replace').splitlines()
    out=[]
    for needle in needles:
        hits=[i for i,line in enumerate(lines,1) if needle in line]
        if not hits:
            out.append({'source_file':rel,'function':function,'needle':needle,'failure':'needle_missing','blob_sha256':sha(p)})
            continue
        for hit in hits[:12]:
            lo=max(1,hit-10);hi=min(len(lines),hit+18)
            out.append({'source_file':rel,'function':function,'needle':needle,'matched_line':hit,'line_start':lo,'line_end':hi,'blob_sha256':sha(p),'snippet':'\n'.join(f'{n}:{lines[n-1]}' for n in range(lo,hi+1))})
    return out

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    root=Path(a.source_root);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    specs=[
        ('core/io/resource.cpp','Resource::generate_scene_unique_id',['String Resource::generate_scene_unique_id()','get_ticks_usec','Math::rand()']),
        ('core/io/resource_format_binary.cpp','ResourceFormatSaverBinaryInstance::write_variant',['Dictionary d = p_property','d.get_key_list(&keys)']),
        ('core/io/resource_format_binary.cpp','ResourceFormatSaverBinaryInstance::save',['Resource::generate_scene_unique_id()','"local://" + r->get_scene_unique_id()','saved_resources']),
        ('editor/import/3d/resource_importer_scene.cpp','ResourceImporterScene::_import',['ResourceSaver::save','save_scene']),
        ('editor/import/3d/resource_importer_obj.cpp','ResourceImporterOBJ::import',['ResourceSaver::save','ArrayMesh']),
        ('modules/gltf/editor/editor_scene_importer_gltf.cpp','EditorSceneFormatImporterGLTF::import_scene',['import_scene','generate_scene']),
        ('modules/gltf/gltf_document.cpp','GLTFDocument::generate_scene',['generate_scene','HashMap']),
        ('modules/fbx/editor/editor_scene_importer_ufbx.cpp','EditorSceneFormatImporterUFBX::import_scene',['import_scene','generate_scene']),
        ('modules/fbx/fbx_document.cpp','FBXDocument',['generate_scene','HashMap']),
        ('scene/resources/packed_scene.cpp','PackedScene/SceneState',['scene_unique','pack']),
    ]
    traces=[]
    for rel,fn,terms in specs:traces.extend(snippets(root,rel,fn,terms))
    failures=[x for x in traces if 'failure' in x]
    candidates=[
        {
            'classification':'IMPORTED_SUBRESOURCE_UID_NONDETERMINISM',
            'source_file':'core/io/resource.cpp',
            'function':'Resource::generate_scene_unique_id',
            'relevant_lines':[103,130],
            'mechanism':'The local resource identifier generator hashes wall-clock date, microsecond process ticks and Math::rand(), so equivalent resources created in separate imports receive different five-character identifiers.',
            'supported_by':['Experiment A differs on one runner/same path','Experiment D differs across runners','seeded top-level uid_cache equality does not govern built-in subresource scene_unique_id values'],
            'contradicted_by':[],
        },
        {
            'classification':'PACKED_SCENE_LOCAL_ID_NONDETERMINISM',
            'source_file':'core/io/resource_format_binary.cpp',
            'function':'ResourceFormatSaverBinaryInstance::save',
            'relevant_lines':[2460,2490],
            'mechanism':'Before binary serialization, every built-in resource whose scene_unique_id is empty is assigned ClassName_ + Resource::generate_scene_unique_id(), then persisted as local://<id>. Model imports create meshes, materials, skins and animations as built-in resources; single-output texture imports generally do not.',
            'supported_by':['exactly 800 model binaries remain different after top-level .import and uid_cache stabilization','800 destination-md5 companions follow those binary differences'],
            'contradicted_by':[],
        },
        {
            'classification':'BINARY_RESOURCE_SERIALIZATION_ORDER_NONDETERMINISM',
            'source_file':'core/io/resource_format_binary.cpp',
            'function':'ResourceFormatSaverBinaryInstance::write_variant/_find_resources',
            'relevant_lines':[1880,2075],
            'mechanism':'Dictionary values are written by get_key_list() iteration without an explicit canonical sort; this can affect byte order when importer-generated dictionaries have unstable insertion/hash iteration order.',
            'supported_by':['candidate only until semantic/order diagnostics compare representative resources'],
            'contradicted_by':['if canonical semantic graphs and serialized-order diagnostics differ only in local identifiers, this candidate is not required'],
        },
        {
            'classification':'MODEL_IMPORT_THREAD_ORDER_NONDETERMINISM',
            'source_file':'editor/import/3d/resource_importer_scene.cpp',
            'function':'ResourceImporterScene pipeline',
            'mechanism':'Parallel or completion-order effects are a candidate only if isolated single-model projects remain deterministic while the full project differs.',
            'supported_by':['none yet'],
            'contradicted_by':['single-model controls will directly test whether project-wide ordering is required'],
        },
    ]
    trace={'schema_version':1,'godot_commit':EXPECTED_COMMIT,'source_root':str(root.resolve()),'trace_count':len(traces),'failures':failures,'traces':traces}
    write(out/'GODOT_4_3_IMPORT_SOURCE_TRACE.json',trace)
    write(out/'GODOT_4_3_NONDETERMINISM_CANDIDATES.json',{'schema_version':1,'godot_commit':EXPECTED_COMMIT,'candidates':candidates})
    if any(x.get('failure')=='file_missing' for x in failures):return 2
    return 0
if __name__=='__main__':raise SystemExit(main())
