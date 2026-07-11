extends Node
class_name RuntimeScreenshotCollector

var output_dir := "res://build/runtime_screenshots"
var records: Array[Dictionary] = []

func configure(directory: String) -> void:
    output_dir = directory
    DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(output_dir))

func capture(filename: String, settle_frames: int = 8) -> Dictionary:
    for _frame in range(maxi(settle_frames, 2)):
        await get_tree().process_frame
    await RenderingServer.frame_post_draw
    var viewport := get_viewport()
    if viewport == null or viewport.get_texture() == null:
        return _failure(filename, "viewport texture unavailable")
    var image := viewport.get_texture().get_image()
    if image == null or image.is_empty():
        return _failure(filename, "captured image is empty")
    if image.get_width() < 320 or image.get_height() < 180:
        return _failure(filename, "captured dimensions too small")
    var path := output_dir.path_join(filename)
    var error := image.save_png(path)
    if error != OK:
        return _failure(filename, "save_png code %d" % error)
    var bytes := FileAccess.get_file_as_bytes(path).size()
    if bytes <= 128:
        return _failure(filename, "PNG unexpectedly small")
    var row := {"filename": filename, "status": "captured", "path": ProjectSettings.globalize_path(path), "width": image.get_width(), "height": image.get_height(), "bytes": bytes}
    records.append(row)
    print("SCREENSHOT_OK %s %dx%d %d" % [filename, image.get_width(), image.get_height(), bytes])
    return row

func write_report(path: String) -> void:
    var file := FileAccess.open(path, FileAccess.WRITE)
    if file == null:
        push_error("Unable to write screenshot report")
        return
    file.store_string(JSON.stringify({"screenshots": records}, "  "))

func _failure(filename: String, reason: String) -> Dictionary:
    var row := {"filename": filename, "status": "unavailable", "reason": reason}
    records.append(row)
    push_error("SCREENSHOT_FAILED %s: %s" % [filename, reason])
    return row
