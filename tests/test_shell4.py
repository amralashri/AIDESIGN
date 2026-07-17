import numpy as np

from fem.shell4 import (
    shell4_local_stiffness,
    shell_local_geometry,
    shell_pressure_equivalent_local,
)


def rectangular_points():
    return np.array([
        [0.0,0.0,0.0],
        [4.0,0.0,0.0],
        [4.0,3.0,0.0],
        [0.0,3.0,0.0],
    ])


def test_shell_geometry_area_and_orientation():
    geometry=shell_local_geometry(rectangular_points())
    assert abs(geometry.area-12.0)<1e-12
    assert np.allclose(
        geometry.rotation@geometry.rotation.T,
        np.eye(3),atol=1e-12,
    )


def test_shell_stiffness_is_symmetric():
    geometry=shell_local_geometry(rectangular_points())
    stiffness=shell4_local_stiffness(
        25_000_000.0,0.20,0.20,geometry.local_xy
    )
    assert stiffness.shape==(24,24)
    assert np.allclose(
        stiffness,stiffness.T,rtol=1e-12,atol=1e-8
    )
    assert np.min(np.linalg.eigvalsh(stiffness))>-1e-5


def test_shell_uniform_pressure_total_force():
    load=shell_pressure_equivalent_local(-5.0,12.0)
    assert abs(load[2::6].sum()+60.0)<1e-12
