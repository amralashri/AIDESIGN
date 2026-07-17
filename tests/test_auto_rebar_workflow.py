import ast
from pathlib import Path


def test_display_reinforcement_auto_runs_design():
    root=Path(__file__).resolve().parents[1]
    text=(root/'ui'/'main_window.py').read_text(encoding='utf-8')
    assert 'run_concrete_design(show_notice=False)' in text
    assert 'Run Preliminary Concrete Design first.' not in text


def test_new_rebar_contour_modes_are_wired():
    root=Path(__file__).resolve().parents[1]
    for rel in ('ui/results_panel.py','ui/viewport2d.py','ui/viewport3d.py'):
        text=(root/rel).read_text(encoding='utf-8')
        assert 'Slab As X' in text
        assert 'Slab As Y' in text
