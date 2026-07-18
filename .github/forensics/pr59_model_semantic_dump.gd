extends SceneTree

var _seen: Dictionary = {}
var _next_ref := 0
var _failures: Array = []
var _skipped: Array = []
var _sections := {
    "nodes": [],
    "geometry": [],
    "materials": [],
    "animations": [],
    "skeletons": [],
    "identifiers": [],
    "floats": [],
    "order": [],
}

func _initialize() -> void:
    call_deferred("_run")

func _sha_bytes(data: PackedByteArray) -> String:
    var context := HashingContext.new()
    context.start(HashingContext.HASH_SHA256)
    context.update(data)
    return context.finish().hex_encode()

func _sha_text(text: String) -> String:
    return _sha_bytes(text.to_utf8_buffer())

func _bytes_record(value: Variant) -> Dictionary:
    var data: PackedByteArray = var_to_bytes(value)
    return {"bytes": data.size(), "sha256": _sha_bytes(data), "hex": data.hex_encode() if data.size() <= 64 else null}

func _float_record(value: float) -> Dictionary:
    var rec := {"type": "float", "text": String.num(value, 17), "encoding": _bytes_record(value)}
    _sections["floats"].append(rec)
    return rec

func _sort_dict_entries(value: Dictionary, context: String) -> Array:
    var rows: Array = []
    for key in value.keys():
        var ck: Variant = _canon(key, context + ".key")
        rows.append({"key": ck, "value": _canon(value[key], context + ".value"), "sort": JSON.stringify(ck)})
    rows.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return String(a["sort"]) < String(b["sort"]))
    for row in rows:
        row.erase("sort")
    return rows

func _canon(value: Variant, context: String = "") -> Variant:
    var t := typeof(value)
    match t:
        TYPE_NIL:
            return {"type": "nil"}
        TYPE_BOOL:
            return {"type": "bool", "value": value}
        TYPE_INT:
            return {"type": "int", "value": value}
        TYPE_FLOAT:
            return _float_record(value)
        TYPE_STRING, TYPE_STRING_NAME, TYPE_NODE_PATH:
            return {"type": type_string(t), "value": str(value)}
        TYPE_VECTOR2, TYPE_VECTOR2I, TYPE_RECT2, TYPE_RECT2I, TYPE_VECTOR3, TYPE_VECTOR3I, TYPE_TRANSFORM2D, TYPE_VECTOR4, TYPE_VECTOR4I, TYPE_PLANE, TYPE_QUATERNION, TYPE_AABB, TYPE_BASIS, TYPE_TRANSFORM3D, TYPE_PROJECTION, TYPE_COLOR:
            return {"type": type_string(t), "text": str(value), "encoding": _bytes_record(value)}
        TYPE_ARRAY:
            var out: Array = []
            for i in range(value.size()):
                out.append(_canon(value[i], context + "[%d]" % i))
            return {"type": "Array", "typed_builtin": value.get_typed_builtin(), "values": out}
        TYPE_DICTIONARY:
            return {"type": "Dictionary", "entries": _sort_dict_entries(value, context)}
        TYPE_PACKED_BYTE_ARRAY, TYPE_PACKED_INT32_ARRAY, TYPE_PACKED_INT64_ARRAY, TYPE_PACKED_FLOAT32_ARRAY, TYPE_PACKED_FLOAT64_ARRAY, TYPE_PACKED_STRING_ARRAY, TYPE_PACKED_VECTOR2_ARRAY, TYPE_PACKED_VECTOR3_ARRAY, TYPE_PACKED_COLOR_ARRAY, TYPE_PACKED_VECTOR4_ARRAY:
            return {"type": type_string(t), "size": value.size(), "encoding": _bytes_record(value)}
        TYPE_OBJECT:
            if value == null:
                return {"type": "Object", "value": null}
            if value is Resource:
                return _resource(value, context)
            _skipped.append({"context": context, "class": value.get_class(), "reason": "Non-Resource Object has process-local identity and is not a serializable resource value."})
            return {"type": "Object", "class": value.get_class(), "skipped": true}
        _:
            _failures.append({"context": context, "reason": "Unhandled Variant type", "type": type_string(t)})
            return {"type": type_string(t), "failure": true}

func _resource(res: Resource, context: String) -> Dictionary:
    var iid := res.get_instance_id()
    if _seen.has(iid):
        return {"type": "ResourceRef", "ref": _seen[iid]}
    var token := "r%06d" % _next_ref
    _next_ref += 1
    _seen[iid] = token
    var ident := {
        "ref": token,
        "class": res.get_class(),
        "resource_path": res.resource_path,
        "resource_name": res.resource_name,
        "scene_unique_id": res.resource_scene_unique_id,
        "local_to_scene": res.resource_local_to_scene,
    }
    _sections["identifiers"].append(ident)
    var result := {"type": "Resource", "identity": ident}
    if res is PackedScene:
        result["packed_scene"] = _packed_scene(res, context)
    elif res is Mesh:
        result["mesh"] = _mesh(res, context)
    elif res is Material:
        result["material"] = _storage_properties(res, context + ".material")
        _sections["materials"].append({"identity": ident, "properties": result["material"]})
    elif res is Animation:
        result["animation"] = _animation(res, context)
    elif res is AnimationLibrary:
        result["animation_library"] = _animation_library(res, context)
    elif res is Skin:
        result["skin"] = _skin(res, context)
    else:
        result["properties"] = _storage_properties(res, context + ".resource")
    return result

func _storage_properties(obj: Object, context: String) -> Array:
    var props: Array = obj.get_property_list()
    props.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return String(a.get("name", "")) < String(b.get("name", "")))
    var rows: Array = []
    for prop in props:
        var usage := int(prop.get("usage", 0))
        if (usage & PROPERTY_USAGE_STORAGE) == 0:
            continue
        var name := String(prop.get("name", ""))
        if name in ["resource_path", "resource_name", "resource_local_to_scene", "resource_scene_unique_id"]:
            continue
        var value: Variant = obj.get(name)
        rows.append({"name": name, "type": int(prop.get("type", TYPE_NIL)), "usage": usage, "value": _canon(value, context + "." + name)})
    return rows

func _packed_scene(scene: PackedScene, context: String) -> Dictionary:
    var state := scene.get_state()
    var nodes: Array = []
    for i in range(state.get_node_count()):
        var props: Array = []
        for j in range(state.get_node_property_count(i)):
            props.append({"name": str(state.get_node_property_name(i, j)), "value": _canon(state.get_node_property_value(i, j), context + ".node[%d].property[%d]" % [i, j])})
        props.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return String(a["name"]) < String(b["name"]))
        var groups: Array = Array(state.get_node_groups(i))
        groups.sort()
        var node := {
            "index": i,
            "sibling_index": state.get_node_index(i),
            "path": str(state.get_node_path(i)),
            "parent_path": str(state.get_node_path(i, true)),
            "name": str(state.get_node_name(i)),
            "type": str(state.get_node_type(i)),
            "owner_path": str(state.get_node_owner_path(i)),
            "groups": groups,
            "instance_placeholder": state.is_node_instance_placeholder(i),
            "placeholder_path": state.get_node_instance_placeholder(i),
            "instance": _canon(state.get_node_instance(i), context + ".node[%d].instance" % i),
            "properties": props,
        }
        nodes.append(node)
    var connections: Array = []
    for i in range(state.get_connection_count()):
        connections.append({
            "source": str(state.get_connection_source(i)),
            "signal": str(state.get_connection_signal(i)),
            "target": str(state.get_connection_target(i)),
            "method": str(state.get_connection_method(i)),
            "flags": state.get_connection_flags(i),
            "unbinds": state.get_connection_unbinds(i),
            "binds": _canon(state.get_connection_binds(i), context + ".connection[%d].binds" % i),
        })
    connections.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return JSON.stringify(a) < JSON.stringify(b))
    var structure := {"node_count": nodes.size(), "nodes": nodes, "connection_count": connections.size(), "connections": connections}
    _sections["nodes"].append(structure)
    _sections["order"].append({"node_paths_in_serialized_order": nodes.map(func(x): return x["path"]), "connection_order": connections})
    _skipped.append({"context": context, "property": "editable_instance_state", "reason": "Godot 4.3 SceneState exposes instance and placeholder metadata but no editable-instance accessor; omission is explicit."})
    var instantiated := scene.instantiate(PackedScene.GEN_EDIT_STATE_DISABLED)
    if instantiated != null:
        structure["instantiated_diagnostics"] = _walk_node(instantiated, instantiated, context + ".instance")
        instantiated.free()
    else:
        _failures.append({"context": context, "reason": "PackedScene.instantiate returned null"})
    return structure

func _walk_node(root: Node, node: Node, context: String) -> Dictionary:
    var row := {"path": "." if node == root else str(root.get_path_to(node)), "class": node.get_class(), "children": []}
    if node is Skeleton3D:
        var bones: Array = []
        for i in range(node.get_bone_count()):
            bones.append({"index": i, "name": node.get_bone_name(i), "parent": node.get_bone_parent(i), "rest": _canon(node.get_bone_rest(i), context + ".bone[%d].rest" % i), "pose_position": _canon(node.get_bone_pose_position(i), context + ".bone[%d].position" % i), "pose_rotation": _canon(node.get_bone_pose_rotation(i), context + ".bone[%d].rotation" % i), "pose_scale": _canon(node.get_bone_pose_scale(i), context + ".bone[%d].scale" % i)})
        row["skeleton"] = bones
        _sections["skeletons"].append({"node_path": row["path"], "bones": bones})
    if node is MeshInstance3D:
        row["mesh"] = _canon(node.mesh, context + ".mesh")
        var overrides: Array = []
        for i in range(node.get_surface_override_material_count()):
            overrides.append(_canon(node.get_surface_override_material(i), context + ".override[%d]" % i))
        row["surface_overrides"] = overrides
    if node is AnimationPlayer:
        var libs: Array = []
        var names: Array = Array(node.get_animation_library_list())
        names.sort()
        for name in names:
            libs.append({"name": str(name), "library": _canon(node.get_animation_library(name), context + ".animation_library." + str(name))})
        row["animation_libraries"] = libs
    for child in node.get_children(true):
        row["children"].append(_walk_node(root, child, context + ".child"))
    return row

func _mesh(mesh: Mesh, context: String) -> Dictionary:
    var surfaces: Array = []
    for i in range(mesh.get_surface_count()):
        var arrays := mesh.surface_get_arrays(i)
        var arr_records: Array = []
        for j in range(arrays.size()):
            var value = arrays[j]
            arr_records.append({"array_index": j, "is_null": value == null, "count": value.size() if value != null and value is Array or value is PackedByteArray or value is PackedInt32Array or value is PackedInt64Array or value is PackedFloat32Array or value is PackedFloat64Array or value is PackedVector2Array or value is PackedVector3Array or value is PackedColorArray or value is PackedVector4Array else null, "canonical": _canon(value, context + ".surface[%d].array[%d]" % [i, j])})
        var blends: Array = []
        var blend_arrays: Array = mesh.surface_get_blend_shape_arrays(i)
        for b in range(blend_arrays.size()):
            blends.append({"name": str(mesh.get_blend_shape_name(b)), "arrays": _canon(blend_arrays[b], context + ".surface[%d].blend[%d]" % [i, b])})
        var surface := {
            "index": i,
            "primitive": mesh.surface_get_primitive_type(i),
            "format": mesh.surface_get_format(i),
            "arrays": arr_records,
            "blend_shapes": blends,
            "material": _canon(mesh.surface_get_material(i), context + ".surface[%d].material" % i),
            "lods": _canon(mesh.surface_get_lods(i), context + ".surface[%d].lods" % i),
        }
        surfaces.append(surface)
    var result := {"class": mesh.get_class(), "surface_count": mesh.get_surface_count(), "blend_shape_count": mesh.get_blend_shape_count(), "blend_shape_mode": mesh.get_blend_shape_mode(), "aabb": _canon(mesh.get_aabb(), context + ".aabb"), "surfaces": surfaces}
    _sections["geometry"].append(result)
    _sections["order"].append({"mesh_surface_order": surfaces.map(func(x): return x["index"])})
    return result

func _animation_library(lib: AnimationLibrary, context: String) -> Dictionary:
    var names: Array = Array(lib.get_animation_list())
    names.sort()
    var rows: Array = []
    for name in names:
        rows.append({"name": str(name), "animation": _canon(lib.get_animation(name), context + "." + str(name))})
    return {"animations": rows}

func _animation(anim: Animation, context: String) -> Dictionary:
    var tracks: Array = []
    for i in range(anim.get_track_count()):
        var keys: Array = []
        for k in range(anim.track_get_key_count(i)):
            keys.append({"index": k, "time": _canon(anim.track_get_key_time(i, k), context + ".track[%d].key[%d].time" % [i, k]), "value": _canon(anim.track_get_key_value(i, k), context + ".track[%d].key[%d].value" % [i, k]), "transition": _canon(anim.track_get_key_transition(i, k), context + ".track[%d].key[%d].transition" % [i, k])})
        tracks.append({"index": i, "type": anim.track_get_type(i), "path": str(anim.track_get_path(i)), "interpolation": anim.track_get_interpolation_type(i), "loop_wrap": anim.track_get_interpolation_loop_wrap(i), "enabled": anim.track_is_enabled(i), "key_count": keys.size(), "keys": keys})
    var result := {"length": _canon(anim.length, context + ".length"), "loop_mode": anim.loop_mode, "step": _canon(anim.step, context + ".step"), "track_count": tracks.size(), "tracks": tracks}
    _sections["animations"].append(result)
    _sections["order"].append({"animation_track_paths": tracks.map(func(x): return x["path"])})
    return result

func _skin(skin: Skin, context: String) -> Dictionary:
    var binds: Array = []
    for i in range(skin.get_bind_count()):
        binds.append({"index": i, "bone": skin.get_bind_bone(i), "name": str(skin.get_bind_name(i)), "pose": _canon(skin.get_bind_pose(i), context + ".bind[%d]" % i)})
    var result := {"bind_count": binds.size(), "binds": binds}
    _sections["skeletons"].append(result)
    return result

func _reset_state() -> void:
    _seen.clear()
    _next_ref = 0
    _failures.clear()
    _skipped.clear()
    for key in _sections.keys():
        _sections[key] = []

func _run() -> void:
    var args := OS.get_cmdline_user_args()
    if args.size() != 2:
        push_error("expected selection manifest and output path")
        quit(2)
        return
    var selection_text := FileAccess.get_file_as_string(args[0])
    var selection = JSON.parse_string(selection_text)
    if typeof(selection) != TYPE_DICTIONARY:
        push_error("invalid selection JSON")
        quit(3)
        return
    var output := {"godot_version": Engine.get_version_info(), "resources": []}
    for item in selection["resources"]:
        _reset_state()
        var target := "res://" + String(item["target_path"])
        var res := ResourceLoader.load(target, "", ResourceLoader.CACHE_MODE_IGNORE)
        if res == null:
            _failures.append({"target": target, "reason": "ResourceLoader.load returned null"})
        var graph = _resource(res, String(item["selection_id"])) if res != null else null
        var section_hashes := {}
        for key in _sections.keys():
            section_hashes[key] = _sha_text(JSON.stringify(_sections[key]))
        output["resources"].append({
            "selection_id": item["selection_id"],
            "logical_source": item["logical_source"],
            "source_type": item["source_type"],
            "target_path": item["target_path"],
            "graph": graph,
            "sections": _sections.duplicate(true),
            "section_sha256": section_hashes,
            "failures": _failures.duplicate(true),
            "skipped_properties": _skipped.duplicate(true),
        })
    var file := FileAccess.open(args[1], FileAccess.WRITE)
    if file == null:
        push_error("failed to open semantic output")
        quit(4)
        return
    file.store_string(JSON.stringify(output, "  "))
    file.close()
    for item in output["resources"]:
        if not item["failures"].is_empty():
            push_error("semantic diagnostic failures: " + JSON.stringify(item["failures"]))
            quit(5)
            return
    quit(0)
