import numpy as np

from model.project import ProjectModel


def test_grid_center_uses_full_grid_extents():
    model=ProjectModel.default()
    model.x_grids=[0.0,6.0,18.0]
    model.y_grids=[-2.0,8.0]
    assert np.allclose(
        model.grid_center(),
        [9.0,3.0,5.25],
    )
