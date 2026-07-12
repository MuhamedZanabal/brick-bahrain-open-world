extends SceneTree

func _initialize() -> void:
	var java_path := OS.get_environment("JAVA_HOME")
	var sdk_path := OS.get_environment("ANDROID_SDK_ROOT")
	if java_path.is_empty() or sdk_path.is_empty():
		push_error("JAVA_HOME or ANDROID_SDK_ROOT is empty")
		quit(2)
		return

	var settings: EditorSettings = EditorInterface.get_editor_settings()
	settings.set_setting("export/android/java_sdk_path", java_path)
	settings.set_setting("export/android/android_sdk_path", sdk_path)
	print("configured_java_sdk=", settings.get_setting("export/android/java_sdk_path"))
	print("configured_android_sdk=", settings.get_setting("export/android/android_sdk_path"))
	quit(0)
