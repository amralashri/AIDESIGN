import ast
from pathlib import Path


def _class_methods(path: Path, class_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    return {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}


def test_shell_quality_ui_is_wired_inside_main_window():
    root = Path(__file__).resolve().parents[1]
    methods = _class_methods(root / "ui" / "main_window.py", "MainWindow")
    assert "show_shell_quality" in methods
    ribbon = (root / "ui" / "ribbon.py").read_text(encoding="utf-8")
    assert "shell_quality_btn" in ribbon
    assert "contour_mmax_btn" in ribbon
    assert "contour_mmin_btn" in ribbon
