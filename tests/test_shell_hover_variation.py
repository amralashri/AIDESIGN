import numpy as np
from fem.shell4 import shell_local_geometry,shell_value_at_local_point

def test_shell_moment_value_varies_with_pointer_position():
    points=np.array([
        [0.,0.,0.],[4.,0.,0.],[4.,3.,0.],[0.,3.,0.]
    ])
    geometry=shell_local_geometry(points)
    u=np.zeros(24)
    # Bilinear rotation field producing a non-constant curvature.
    u[6*2+4]=0.01
    value_a=shell_value_at_local_point(
        u,25_000_000.0,0.2,0.2,geometry.local_xy,
        np.array([0.5,0.5]),"Mx"
    )
    value_b=shell_value_at_local_point(
        u,25_000_000.0,0.2,0.2,geometry.local_xy,
        np.array([3.5,2.5]),"Mx"
    )
    assert abs(value_a-value_b)>1e-8
