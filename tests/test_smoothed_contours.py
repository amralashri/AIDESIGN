import numpy as np

from analysis.contours import smoothed_nodal_values
from analysis.results import AnalysisResult, AreaResult
from model.project import ProjectModel


def test_shared_shell_node_is_averaged():
    model = ProjectModel.default()
    a1 = model.add_rect_area((0, 0, 3.5), (2, 2, 3.5))
    a2 = model.add_rect_area((2, 0, 3.5), (4, 2, 3.5))
    results = {}
    for area, rotation_value in ((a1, 0.001), (a2, 0.003)):
        u = np.zeros(24)
        u[4::6] = rotation_value
        results[area.id] = AreaResult(
            area.id, u, np.zeros(24),
            {"Nx": 0, "Ny": 0, "Nxy": 0, "Mx": 0, "My": 0, "Mxy": 0,
             "Mmax": 0, "Mmin": 0, "Mangle": 0, "Qx": 0, "Qy": 0},
            4.0, np.array([[0, 0], [2, 0], [2, 2], [0, 2]], dtype=float),
            np.eye(3), 25_000_000.0, 0.2, 0.2,
        )
    result = AnalysisResult(
        "TEST", list(model.nodes), {nid: i for i, nid in enumerate(model.nodes)},
        np.zeros(6 * len(model.nodes)), np.zeros(6 * len(model.nodes)), {}, results,
    )
    values = smoothed_nodal_values(model, result, "Slab Mx")
    shared = set(a1.nodes).intersection(a2.nodes)
    assert shared
    assert all(np.isfinite(values[nid]) for nid in shared)
