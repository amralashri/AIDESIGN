import numpy as np
from fem.frame3d import local_geometric_stiffness

def test_geometric_stiffness_is_symmetric_and_scales_with_axial_force():
    k1=local_geometric_stiffness(100.0,3.0)
    k2=local_geometric_stiffness(200.0,3.0)
    assert np.allclose(k1,k1.T)
    assert np.allclose(k2,2.0*k1)
