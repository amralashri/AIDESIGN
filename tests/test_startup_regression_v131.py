import ast
from pathlib import Path


def test_ribbon_has_no_executable_module_level_statements():
    root = Path(__file__).resolve().parents[1]
    tree = ast.parse((root / "ui" / "ribbon.py").read_text(encoding="utf-8"))
    allowed = (ast.Import, ast.ImportFrom, ast.ClassDef)
    bad = [node for node in tree.body if not isinstance(node, allowed)]
    assert not bad, f"Unexpected executable ribbon statements: {bad}"


def test_animation_and_code_buttons_belong_to_ribbon_init():
    root = Path(__file__).resolve().parents[1]
    tree = ast.parse((root / "ui" / "ribbon.py").read_text(encoding="utf-8"))
    ribbon = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "RibbonWidget"
    )
    init = next(
        node for node in ribbon.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assigned = {
        node.attr
        for node in ast.walk(init)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
    }
    required = {
        "animate_deformed_btn", "animate_mode_btn", "stop_animation_btn",
        "code_settings_btn", "code_summary_btn",
    }
    assert required <= assigned


def test_main_window_keeps_shortcut_and_display_methods():
    root = Path(__file__).resolve().parents[1]
    tree = ast.parse((root / "ui" / "main_window.py").read_text(encoding="utf-8"))
    cls = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "MainWindow"
    )
    methods = {
        node.name for node in cls.body if isinstance(node, ast.FunctionDef)
    }
    assert {"show_shortcuts", "_set_display_option"} <= methods
