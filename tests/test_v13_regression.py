import ast
from pathlib import Path

def class_methods(path,name):
    tree=ast.parse(Path(path).read_text(encoding="utf-8"))
    cls=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name==name)
    return {node.name for node in cls.body if isinstance(node,ast.FunctionDef)}

def test_new_features_remain_inside_classes():
    root=Path(__file__).resolve().parents[1]
    plan=class_methods(root/"ui"/"viewport2d.py","PlanViewport")
    view3d=class_methods(root/"ui"/"viewport3d.py","Viewport3D")
    main=class_methods(root/"ui"/"main_window.py","MainWindow")
    assert {"_select_window","_draw_selection_window"}<=plan
    assert {"set_animation_state"}<=view3d
    assert {
        "start_deformed_animation","start_mode_animation",
        "stop_animation","edit_code_settings"
    }<=main
