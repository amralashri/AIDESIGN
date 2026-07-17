import ast
from pathlib import Path

def methods(path,class_name):
    tree=ast.parse(Path(path).read_text(encoding="utf-8"))
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==class_name)
    return {n.name for n in cls.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}

def test_required_main_window_and_plan_methods_remain_in_classes():
    root=Path(__file__).resolve().parents[1]
    main=methods(root/"ui"/"main_window.py","MainWindow")
    plan=methods(root/"ui"/"viewport2d.py","PlanViewport")
    assert {"mesh_selected_slabs","import_dxf_dialog","_build_vertical_toolbar"}<=main
    assert {"delete_selected","fit_view","showEvent","mouseMoveEvent"}<=plan
