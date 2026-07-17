import numpy as np

from graphics.camera3d import RevitOrbitCamera


def test_camera_basis_is_orthonormal():
    camera=RevitOrbitCamera()
    camera.set_isometric(20.0)
    for _ in range(20):
        camera.orbit(12.0,-7.0)
    right,up,forward=camera.basis()
    basis=np.vstack((right,up,forward))
    assert np.allclose(basis@basis.T,np.eye(3),atol=1e-10)


def test_camera_fit_produces_positive_distance():
    camera=RevitOrbitCamera()
    points=[
        np.array([0.0,0.0,0.0]),
        np.array([10.0,5.0,3.0]),
    ]
    camera.fit_points(points,1000/700)
    assert camera.distance>0.0
