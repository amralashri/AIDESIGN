import numpy as np

from fem.frame3d import (
    local_stiffness_matrix,
    transformation_matrix,
)


def test_local_stiffness_is_symmetric():
    matrix = local_stiffness_matrix(
        200_000_000.0, 76_923_076.923,
        0.02, 8.0e-5, 4.0e-5, 1.0e-5, 4.0,
    )
    assert matrix.shape == (12, 12)
    assert np.allclose(matrix, matrix.T, rtol=1e-12, atol=1e-9)


def test_transformation_is_orthogonal_by_blocks():
    rotation = np.eye(3)
    transform = transformation_matrix(rotation)
    assert np.allclose(transform.T @ transform, np.eye(12))
