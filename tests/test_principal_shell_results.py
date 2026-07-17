import numpy as np

from fem.shell4 import shell_resultants_at


def test_principal_moments_order_and_invariant():
    local_xy = np.array([
        [0.0, 0.0], [4.0, 0.0], [4.0, 3.0], [0.0, 3.0]
    ])
    displacement = np.zeros(24)
    displacement[4] = 0.001
    displacement[10] = 0.003
    displacement[16] = 0.006
    result = shell_resultants_at(
        displacement, 25_000_000.0, 0.2, 0.2, local_xy, 0.0, 0.0
    )
    assert result["Mmax"] >= result["Mmin"]
    assert np.isclose(result["Mmax"] + result["Mmin"], result["Mx"] + result["My"])
