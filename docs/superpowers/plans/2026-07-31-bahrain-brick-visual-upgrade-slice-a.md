# Bahrain Brick Visual Upgrade Slice A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current flat startup and menu flow with a reusable Bahrain Brick visual system, branded splash/loading screens, a reference-matched main menu, and a three-character selection flow that persists the selected character.

**Architecture:** Build the first visual-upgrade slice as native Godot 4.3 controls driven by a shared `BahrainTheme` factory. Keep interactive state in existing autoloads (`GameManager`, `SaveManager`) and use authored raster assets only for backgrounds, logos, and decorative art. Preserve the existing renderer settings and the frozen renderer-diagnostics evidence.

**Tech Stack:** Godot 4.3 GDScript, `.tscn` scenes, `StyleBoxFlat`, `GradientTexture2D`, Python `unittest` source-contract tests, GitHub Actions Android export.

## Global Constraints

- Work only on branch `work/bahrain-brick-reference-visual-upgrade`.
- Do not modify PR #63 renderer evidence, renderer selection, engine version, or R1 qualification conclusions.
- Keep `run/main_scene="res://scenes/splash_screen.tscn"`.
- Keep `renderer/rendering_method="gl_compatibility"` and `renderer/rendering_method.mobile="gl_compatibility"` unchanged in this slice.
- All user-facing layouts target 16:9 landscape but must use anchors and safe margins rather than fixed 1920×1080 placement.
- New interactive UI must be native Godot controls; raster images may not be used as invisible-hitbox substitutes.
- Existing single-player, multiplayer-host, multiplayer-client, mission-preview, and exit behavior must remain reachable.
- Character selection must persist through `SaveManager` before entering the world.
- Completion requires source-contract tests and Android export validation; generated mockup images are not runtime evidence.

---

## File Map

### Create

- `scripts/ui/bahrain_theme.gd` — shared palette, typography sizing, and `StyleBoxFlat` factories.
- `scripts/ui/safe_area_root.gd` — applies display-safe margins and emits a resized signal.
- `scripts/loading_screen.gd` — dedicated staged loading screen controller.
- `scenes/loading_screen.tscn` — world-loading transition scene.
- `tests/visual/test_visual_upgrade_slice_a.py` — deterministic source-contract tests for the first slice.

### Modify

- `scripts/splash_screen.gd` — branded studio splash and transition to loading/main flow.
- `scripts/main_menu.gd` — reference-matched menu using shared theme and responsive anchors.
- `scripts/character_select.gd` — three-role podium layout, persistence, and navigation.
- `scripts/game_manager.gd` — explicit menu/loading/character transition methods and stable role indices.
- `scripts/save_manager.gd` — versioned settings/character setters that do not overwrite in-memory state during save.
- `scenes/splash_screen.tscn` — attach safe-area root structure.
- `scenes/main_menu.tscn` — attach safe-area root structure.
- `scenes/character_select.tscn` — attach safe-area root structure.
- `project.godot` — add only new input actions if required by tests; renderer lines remain byte-for-byte unchanged.

---

### Task 1: Add Source-Contract Tests for the First Slice

**Files:**
- Create: `tests/visual/test_visual_upgrade_slice_a.py`

**Interfaces:**
- Consumes: repository text files only.
- Produces: a `unittest` suite that protects scene paths, renderer boundaries, reusable theme usage, navigation, and character persistence.

- [ ] **Step 1: Write the failing test file**

```python
#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class VisualUpgradeSliceATest(unittest.TestCase):
    def test_renderer_boundary_is_unchanged(self) -> None:
        project = read("project.godot")
        self.assertIn('run/main_scene="res://scenes/splash_screen.tscn"', project)
        self.assertIn('renderer/rendering_method="gl_compatibility"', project)
        self.assertIn('renderer/rendering_method.mobile="gl_compatibility"', project)

    def test_shared_theme_factory_exists(self) -> None:
        theme = read("scripts/ui/bahrain_theme.gd")
        for symbol in (
            "class_name BahrainTheme",
            "static func panel_style",
            "static func button_style",
            "static func title_size",
        ):
            self.assertIn(symbol, theme)

    def test_startup_flow_uses_real_scenes(self) -> None:
        splash = read("scripts/splash_screen.gd")
        loading = read("scripts/loading_screen.gd")
        manager = read("scripts/game_manager.gd")
        self.assertIn('res://scenes/loading_screen.tscn', splash)
        self.assertIn('res://scenes/main_menu.tscn', loading)
        self.assertIn("func show_character_select", manager)

    def test_main_menu_preserves_required_actions(self) -> None:
        menu = read("scripts/main_menu.gd")
        for label in (
            '"Play"',
            '"Character Select"',
            '"Multiplayer"',
            '"Missions"',
            '"Settings"',
            '"Credits"',
            '"Exit"',
        ):
            self.assertIn(label, menu)
        self.assertIn("BahrainTheme.button_style", menu)

    def test_character_roles_and_persistence_are_explicit(self) -> None:
        selection = read("scripts/character_select.gd")
        save_manager = read("scripts/save_manager.gd")
        for role in ('"Pearl Diver"', '"Street Racer"', '"Sky Pilot"'):
            self.assertIn(role, selection)
        self.assertIn("SaveManager.set_selected_character", selection)
        self.assertIn("func set_selected_character", save_manager)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
python3 -m unittest tests.visual.test_visual_upgrade_slice_a -v
```

Expected: failures for missing `scripts/ui/bahrain_theme.gd`, `scripts/loading_screen.gd`, `show_character_select`, and `set_selected_character`.

- [ ] **Step 3: Commit the failing test**

```bash
git add tests/visual/test_visual_upgrade_slice_a.py
git commit -m "test: define visual upgrade slice A contracts"
```

---

### Task 2: Create the Shared Bahrain UI Theme and Safe-Area Root

**Files:**
- Create: `scripts/ui/bahrain_theme.gd`
- Create: `scripts/ui/safe_area_root.gd`
- Test: `tests/visual/test_visual_upgrade_slice_a.py`

**Interfaces:**
- Produces: `BahrainTheme.panel_style(color: Color, border: Color, radius: int = 18) -> StyleBoxFlat`.
- Produces: `BahrainTheme.button_style(color: Color, pressed: bool = false) -> StyleBoxFlat`.
- Produces: `BahrainTheme.title_size(viewport_size: Vector2) -> int`.
- Produces: `SafeAreaRoot.safe_rect_changed(rect: Rect2)` and `get_safe_rect() -> Rect2`.

- [ ] **Step 1: Create `scripts/ui/bahrain_theme.gd`**

```gdscript
extends RefCounted
class_name BahrainTheme

const GOLD := Color("f4b91f")
const GOLD_LIGHT := Color("ffd968")
const PANEL := Color(0.025, 0.035, 0.05, 0.94)
const PANEL_SOFT := Color(0.04, 0.055, 0.075, 0.86)
const TEXT := Color("f7f7f2")
const TEXT_MUTED := Color("c7cbd1")
const GREEN := Color("55b53a")
const BLUE := Color("2877c7")
const PURPLE := Color("7d42c7")
const ORANGE := Color("ee941e")
const RED := Color("dc3e35")
const CYAN := Color("35a8bb")

static func panel_style(color: Color = PANEL, border: Color = GOLD, radius: int = 18) -> StyleBoxFlat:
    var style := StyleBoxFlat.new()
    style.bg_color = color
    style.border_color = border
    style.set_border_width_all(2)
    style.set_corner_radius_all(radius)
    style.shadow_color = Color(0, 0, 0, 0.55)
    style.shadow_size = 10
    style.content_margin_left = 22
    style.content_margin_right = 22
    style.content_margin_top = 16
    style.content_margin_bottom = 16
    return style

static func button_style(color: Color, pressed: bool = false) -> StyleBoxFlat:
    var style := StyleBoxFlat.new()
    style.bg_color = color.darkened(0.18) if pressed else color
    style.border_color = color.lightened(0.22)
    style.set_border_width_all(2)
    style.set_corner_radius_all(14)
    style.shadow_color = Color(0, 0, 0, 0.48)
    style.shadow_size = 7 if not pressed else 3
    style.content_margin_left = 24
    style.content_margin_right = 24
    style.content_margin_top = 13
    style.content_margin_bottom = 13
    return style

static func title_size(viewport_size: Vector2) -> int:
    return int(clamp(min(viewport_size.x / 1920.0, viewport_size.y / 1080.0) * 86.0, 42.0, 92.0))
```

- [ ] **Step 2: Create `scripts/ui/safe_area_root.gd`**

```gdscript
extends MarginContainer
class_name SafeAreaRoot

signal safe_rect_changed(rect: Rect2)

func _ready() -> void:
    get_viewport().size_changed.connect(_apply_safe_area)
    _apply_safe_area()

func get_safe_rect() -> Rect2:
    var viewport_rect := get_viewport().get_visible_rect()
    var safe := DisplayServer.get_display_safe_area()
    if safe.size == Vector2i.ZERO:
        return viewport_rect
    return Rect2(Vector2(safe.position), Vector2(safe.size))

func _apply_safe_area() -> void:
    var viewport_rect := get_viewport().get_visible_rect()
    var safe := get_safe_rect()
    add_theme_constant_override("margin_left", int(max(0.0, safe.position.x)))
    add_theme_constant_override("margin_top", int(max(0.0, safe.position.y)))
    add_theme_constant_override("margin_right", int(max(0.0, viewport_rect.size.x - safe.end.x)))
    add_theme_constant_override("margin_bottom", int(max(0.0, viewport_rect.size.y - safe.end.y)))
    safe_rect_changed.emit(safe)
```

- [ ] **Step 3: Run the focused tests**

```bash
python3 -m unittest tests.visual.test_visual_upgrade_slice_a.VisualUpgradeSliceATest.test_shared_theme_factory_exists -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add scripts/ui/bahrain_theme.gd scripts/ui/safe_area_root.gd tests/visual/test_visual_upgrade_slice_a.py
git commit -m "feat: add Bahrain visual theme foundation"
```

---

### Task 3: Make SaveManager Preserve and Persist Visual-Flow State

**Files:**
- Modify: `scripts/save_manager.gd`
- Modify: `scripts/game_manager.gd`
- Test: `tests/visual/test_visual_upgrade_slice_a.py`

**Interfaces:**
- Produces: `SaveManager.set_selected_character(index: int, flush: bool = true) -> void`.
- Produces: `SaveManager.get_settings() -> Dictionary`.
- Produces: `SaveManager.set_setting(key: String, value: Variant, flush: bool = true) -> void`.
- Produces: `GameManager.show_character_select() -> void`.
- Produces: `GameManager.show_main_menu() -> void`.

- [ ] **Step 1: Extend the save schema without recreating `save_data` on every save**

Replace the opening assignment in `save_game()` with schema-preserving initialization:

```gdscript
func _ensure_schema() -> void:
    var defaults := _default_save()
    for key in defaults:
        if not save_data.has(key):
            save_data[key] = defaults[key]
    if not save_data["player"].has("selected_character"):
        save_data["player"]["selected_character"] = 0
    if not save_data.has("settings"):
        save_data["settings"] = defaults["settings"]

func save_game() -> void:
    _ensure_schema()
    save_data["version"] = 3
    save_data["timestamp"] = Time.get_unix_time_from_system()
```

Add to `_default_save()`:

```gdscript
"settings": {
    "quality": "medium",
    "brightness": 0.8,
    "field_of_view": 75.0,
    "camera_shake": true,
    "auto_jump": true,
    "tutorial_hints": true,
},
```

Add setters:

```gdscript
func set_selected_character(index: int, flush: bool = true) -> void:
    _ensure_schema()
    save_data["player"]["selected_character"] = max(index, 0)
    if flush:
        save_game()

func get_settings() -> Dictionary:
    _ensure_schema()
    return save_data["settings"].duplicate(true)

func set_setting(key: String, value: Variant, flush: bool = true) -> void:
    _ensure_schema()
    save_data["settings"][key] = value
    if flush:
        save_game()
```

- [ ] **Step 2: Add explicit transition methods to `GameManager`**

```gdscript
const MAIN_MENU_SCENE := "res://scenes/main_menu.tscn"
const CHARACTER_SELECT_SCENE := "res://scenes/character_select.tscn"
const LOADING_SCENE := "res://scenes/loading_screen.tscn"
const WORLD_SCENE := "res://scenes/world.tscn"

func show_main_menu() -> void:
    transition_to(MAIN_MENU_SCENE)

func show_character_select() -> void:
    transition_to(CHARACTER_SELECT_SCENE)

func show_loading_screen() -> void:
    transition_to(LOADING_SCENE)

func enter_world() -> void:
    transition_to(WORLD_SCENE)
```

Update `start_singleplayer()`, `start_multiplayer_host()`, and `start_multiplayer_client()` to call `show_character_select()`.

- [ ] **Step 3: Run persistence and navigation contract tests**

```bash
python3 -m unittest \
  tests.visual.test_visual_upgrade_slice_a.VisualUpgradeSliceATest.test_startup_flow_uses_real_scenes \
  tests.visual.test_visual_upgrade_slice_a.VisualUpgradeSliceATest.test_character_roles_and_persistence_are_explicit -v
```

Expected: startup test still fails until Task 4; persistence symbols pass.

- [ ] **Step 4: Commit**

```bash
git add scripts/save_manager.gd scripts/game_manager.gd
git commit -m "feat: persist character and visual settings state"
```

---

### Task 4: Replace the Startup Flow with Branded Splash and Loading Scenes

**Files:**
- Modify: `scenes/splash_screen.tscn`
- Modify: `scripts/splash_screen.gd`
- Create: `scenes/loading_screen.tscn`
- Create: `scripts/loading_screen.gd`
- Test: `tests/visual/test_visual_upgrade_slice_a.py`

**Interfaces:**
- Splash transitions to `res://scenes/loading_screen.tscn` after a minimum display duration.
- Loading transitions to `res://scenes/main_menu.tscn` only after all staged milestones are complete.

- [ ] **Step 1: Replace the splash scene root with a safe-area-aware control**

```text
[gd_scene load_steps=3 format=3]

[ext_resource type="Script" path="res://scripts/splash_screen.gd" id="1"]
[ext_resource type="Script" path="res://scripts/ui/safe_area_root.gd" id="2"]

[node name="SplashScreen" type="Control"]
layout_mode = 3
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
script = ExtResource("1")

[node name="SafeArea" type="MarginContainer" parent="."]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
script = ExtResource("2")
```

- [ ] **Step 2: Rebuild `scripts/splash_screen.gd` around named nodes and tweened branding**

The controller must:

```gdscript
const NEXT_SCENE := "res://scenes/loading_screen.tscn"
const MIN_DISPLAY_SECONDS := 2.2

func _go_next() -> void:
    GameManager.transition_to(NEXT_SCENE)
```

It must load `res://assets/splash_screen.png` as an aspect-cover background, add a dark blue/black overlay, center the app crest, render `ZANABAL GAMING` and `Building legends, brick by brick`, and animate opacity/scale using a `Tween`. Touch/click may accelerate only after `MIN_DISPLAY_SECONDS`.

- [ ] **Step 3: Create `scenes/loading_screen.tscn`**

```text
[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://scripts/loading_screen.gd" id="1"]

[node name="LoadingScreen" type="Control"]
layout_mode = 3
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
script = ExtResource("1")
```

- [ ] **Step 4: Create `scripts/loading_screen.gd` with real milestones**

```gdscript
extends Control

const NEXT_SCENE := "res://scenes/main_menu.tscn"
const MILESTONES := [
    "Loading Bahrain skyline",
    "Preparing brick materials",
    "Connecting gameplay systems",
    "Finalizing menu",
]

var _index := 0
var _progress: ProgressBar
var _status: Label

func _ready() -> void:
    _build_ui()
    call_deferred("_advance")

func _advance() -> void:
    if _index >= MILESTONES.size():
        await get_tree().process_frame
        GameManager.transition_to(NEXT_SCENE)
        return
    _status.text = MILESTONES[_index]
    _progress.value = float(_index + 1) / float(MILESTONES.size()) * 100.0
    _index += 1
    await get_tree().create_timer(0.22).timeout
    _advance()
```

`_build_ui()` must use `BahrainTheme.panel_style`, a full-screen background, a large `BAHRAIN BRICK` title, gold `ProgressBar`, percentage label, and rotating tip label.

- [ ] **Step 5: Run startup-flow tests**

```bash
python3 -m unittest tests.visual.test_visual_upgrade_slice_a.VisualUpgradeSliceATest.test_startup_flow_uses_real_scenes -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scenes/splash_screen.tscn scripts/splash_screen.gd scenes/loading_screen.tscn scripts/loading_screen.gd
git commit -m "feat: add branded splash and loading flow"
```

---

### Task 5: Rebuild the Main Menu to Match the Reference Composition

**Files:**
- Modify: `scenes/main_menu.tscn`
- Modify: `scripts/main_menu.gd`
- Test: `tests/visual/test_visual_upgrade_slice_a.py`

**Interfaces:**
- `Play` calls `GameManager.start_singleplayer()`.
- `Character Select` calls `GameManager.show_character_select()`.
- `Multiplayer` opens a native mode chooser that calls host or client entry points.
- `Missions`, `Settings`, and `Credits` open native dialogs/panels.
- `Exit` quits the tree.

- [ ] **Step 1: Rebuild the scene with a safe-area root**

Use the same root pattern as Task 4 and attach `SafeAreaRoot` below `MainMenu`.

- [ ] **Step 2: Replace the current centered menu builder with a reference-matched anchored layout**

Required construction pattern:

```gdscript
func _create_menu_button(label: String, color: Color, icon_text: String) -> Button:
    var button := Button.new()
    button.text = "%s  %s" % [icon_text, label]
    button.custom_minimum_size = Vector2(330, 68)
    button.add_theme_font_size_override("font_size", 25)
    button.add_theme_stylebox_override("normal", BahrainTheme.button_style(color))
    button.add_theme_stylebox_override("hover", BahrainTheme.button_style(color.lightened(0.08)))
    button.add_theme_stylebox_override("pressed", BahrainTheme.button_style(color, true))
    return button
```

The rebuilt `_build_ui()` must create:

- aspect-cover background using `assets/splash_screen.png` until final authored menu art is committed;
- left hero/title region with `BAHRAIN` in white, `BRICK` in red, and `Open World Sandbox` on a black/gold plaque;
- right `VBoxContainer` with the seven required buttons;
- bottom-left profile panel showing crest, `BRICK BAHRAIN`, `Level 12`, progress, and `SaveManager.get_coins()`;
- bottom-right circular footer actions rendered as native buttons;
- a dark readability gradient that does not cover the whole image with uniform opacity.

- [ ] **Step 3: Wire every action explicitly**

```gdscript
play_button.pressed.connect(GameManager.start_singleplayer)
character_button.pressed.connect(GameManager.show_character_select)
multiplayer_button.pressed.connect(_show_multiplayer_dialog)
missions_button.pressed.connect(_show_mission_preview)
settings_button.pressed.connect(_show_settings_preview)
credits_button.pressed.connect(_show_credits)
exit_button.pressed.connect(get_tree().quit)
```

- [ ] **Step 4: Run menu tests**

```bash
python3 -m unittest tests.visual.test_visual_upgrade_slice_a.VisualUpgradeSliceATest.test_main_menu_preserves_required_actions -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scenes/main_menu.tscn scripts/main_menu.gd
git commit -m "feat: rebuild Bahrain Brick main menu"
```

---

### Task 6: Rebuild Character Select Around the Three Approved Roles

**Files:**
- Modify: `scenes/character_select.tscn`
- Modify: `scripts/character_select.gd`
- Modify: `scripts/game_manager.gd`
- Test: `tests/visual/test_visual_upgrade_slice_a.py`

**Interfaces:**
- Uses stable role indices from `GameManager`.
- Persists through `SaveManager.set_selected_character(index)`.
- `Play` persists then calls `GameManager.show_loading_screen()` or `GameManager.enter_world()` according to the final transition architecture.

- [ ] **Step 1: Add stable approved role data to `GameManager`**

```gdscript
const APPROVED_CHARACTER_INDICES := [3, 5, 4]

func get_approved_characters() -> Array[Dictionary]:
    var result: Array[Dictionary] = []
    for index in APPROVED_CHARACTER_INDICES:
        result.append(characters[index])
    return result
```

- [ ] **Step 2: Replace the six-button grid with three podium cards**

Use `GameManager.get_approved_characters()` and render exactly:

- `Pearl Diver` — blue podium, shell marker, underwater description.
- `Street Racer` — red podium, checkered marker, speed description.
- `Sky Pilot` — gold podium, aircraft marker, flight description.

Each card must be a native `Button` or `PanelContainer` with a selectable child button. Selected state uses a gold border and a 1.04 scale tween; unselected cards use their role color without a gold border.

- [ ] **Step 3: Restore prior selection and persist changes**

```gdscript
func _ready() -> void:
    GameManager.current_state = GameManager.GameState.CHARACTER_SELECT
    var saved_index := SaveManager.get_selected_character()
    selected_role = clamp(GameManager.APPROVED_CHARACTER_INDICES.find(saved_index), 0, 2)
    _build_ui()
    _select_role(selected_role)

func _select_role(role_index: int) -> void:
    selected_role = clamp(role_index, 0, 2)
    GameManager.selected_character_index = GameManager.APPROVED_CHARACTER_INDICES[selected_role]
    SaveManager.set_selected_character(GameManager.selected_character_index, false)
    _refresh_selection_state()

func _play_selected() -> void:
    SaveManager.set_selected_character(GameManager.selected_character_index, true)
    GameManager.enter_world()
```

- [ ] **Step 4: Keep 3D previews bounded**

Create one preview viewport per podium only if all three models fit the mobile memory budget. Otherwise use one shared `SubViewport` that updates when a podium is selected. The initial implementation must use one shared preview viewport to avoid three continuously updating 3D render targets.

- [ ] **Step 5: Run all slice tests**

```bash
python3 -m unittest tests.visual.test_visual_upgrade_slice_a -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add scenes/character_select.tscn scripts/character_select.gd scripts/game_manager.gd scripts/save_manager.gd
git commit -m "feat: add persistent three-role character selection"
```

---

### Task 7: Add Android Export Verification for Slice A

**Files:**
- Create: `tools/graphics/verify_visual_upgrade_slice_a.py`
- Modify: `.github/workflows/bahrain-brick-playable-mobile-apk-export.yml`
- Test: `tests/visual/test_visual_upgrade_slice_a.py`

**Interfaces:**
- Produces a nonzero exit code when the production scene, renderer boundary, required resources, or APK ZIP integrity is invalid.

- [ ] **Step 1: Create the verifier**

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path

REQUIRED = (
    "scenes/splash_screen.tscn",
    "scenes/loading_screen.tscn",
    "scenes/main_menu.tscn",
    "scenes/character_select.tscn",
    "scripts/ui/bahrain_theme.gd",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--apk", type=Path)
    args = parser.parse_args()

    project = (args.root / "project.godot").read_text(encoding="utf-8")
    assert 'run/main_scene="res://scenes/splash_screen.tscn"' in project
    assert 'renderer/rendering_method="gl_compatibility"' in project
    assert 'renderer/rendering_method.mobile="gl_compatibility"' in project
    for relative in REQUIRED:
        assert (args.root / relative).is_file(), relative

    if args.apk:
        assert args.apk.is_file() and args.apk.stat().st_size > 0
        with zipfile.ZipFile(args.apk) as archive:
            bad = archive.testzip()
            assert bad is None, bad
        print(hashlib.sha256(args.apk.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Add workflow verification after export**

```yaml
- name: Verify visual upgrade slice A
  run: |
    python3 tools/graphics/verify_visual_upgrade_slice_a.py \
      --root . \
      --apk "$OUTPUT_APK"
```

Use the workflow's existing APK environment variable; do not introduce a second export path.

- [ ] **Step 3: Run local source verification**

```bash
python3 tools/graphics/verify_visual_upgrade_slice_a.py --root .
python3 -m unittest tests.visual.test_visual_upgrade_slice_a -v
```

Expected: both commands exit 0.

- [ ] **Step 4: Commit**

```bash
git add tools/graphics/verify_visual_upgrade_slice_a.py .github/workflows/bahrain-brick-playable-mobile-apk-export.yml
git commit -m "ci: verify visual upgrade startup flow"
```

---

## Plan Self-Review

- Spec coverage for Slice A: shared visual system, safe-area behavior, splash, loading, main menu, character selection, persistence, Android source/export verification.
- Deferred to later plans: gameplay HUD rebuild, pause/settings implementation, world corridor art pass, material/lighting quality profiles, runtime screenshot comparison, physical-device qualification.
- Placeholder scan: no `TBD`, `TODO`, or unspecified implementation steps remain.
- Type consistency: `set_selected_character(index: int, flush: bool = true)`, `show_character_select()`, `show_main_menu()`, and `BahrainTheme` signatures are consistent across tasks.

## Completion Gate

Slice A is complete only when:

1. `python3 -m unittest tests.visual.test_visual_upgrade_slice_a -v` passes.
2. `python3 tools/graphics/verify_visual_upgrade_slice_a.py --root .` passes.
3. Android export succeeds through the existing playable workflow.
4. The exported APK is ZIP-clean and retains the production splash scene and frozen renderer configuration.
5. Runtime screenshots come from the implemented APK, not generated mockups.
