import numpy as np
from fem.frame3d import (
    apply_end_releases,local_stiffness_matrix,
    uniform_load_equivalent_local,
)

def test_pinned_end_release_zeroes_released_end_moments():
    k=local_stiffness_matrix(
        25_000_000.0,10_416_666.7,
        0.18,0.0054,0.00135,0.002,6.0
    )
    load=uniform_load_equivalent_local(0.0,0.0,-10.0,6.0)
    release_i=(False,False,False,False,True,True)
    release_j=(False,False,False,False,True,True)
    kc,fc,released=apply_end_releases(
        k,load,release_i,release_j
    )
    assert set(released)=={4,5,10,11}
    assert np.allclose(fc[released],0.0)
    assert np.allclose(kc,kc.T)
