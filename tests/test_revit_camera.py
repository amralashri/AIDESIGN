import numpy as np

from graphics.camera3d import RevitOrbitCamera


def test_default_isometric_keeps_global_z_up():
    camera=RevitOrbitCamera()
    camera.target=np.array([5.0,5.0,3.0])
    camera.set_isometric(20.0)
    right,up,forward=camera.basis()
    assert np.dot(up,np.array([0.0,0.0,1.0])) > 0.25
    assert camera.distance > 0.0


def test_orbit_does_not_flip_view():
    camera=RevitOrbitCamera()
    camera.set_isometric(20.0)
    for _ in range(200):
        camera.orbit(5.0,3.0)
    _,up,_=camera.basis()
    assert np.dot(up,np.array([0.0,0.0,1.0])) > 0.0


def test_pivot_changes_orbit_centre():
    camera=RevitOrbitCamera()
    camera.set_isometric(15.0)
    pivot=np.array([3.0,4.0,5.0])
    camera.set_pivot(pivot,False)
    assert np.allclose(camera.target,pivot)


def test_projection_places_target_at_screen_center():
    camera=RevitOrbitCamera()
    camera.target=np.array([2.0,3.0,4.0])
    camera.set_isometric(20.0)
    x,y,depth,visible=camera.project(camera.target,1000,800)
    assert visible
    assert abs(x-500.0)<1e-8
    assert abs(y-400.0)<1e-8
