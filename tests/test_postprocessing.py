import numpy as np

from analysis.postprocessing import frame_station_results
from analysis.results import AnalysisResult, FrameResult


def test_uniform_load_moment_curve_is_parabolic():
    length=6.0
    qz=-10.0
    # Fixed-end action vector for a fixed-fixed member under downward qz.
    local_load=np.zeros(3)
    local_load[2]=qz
    end=np.zeros(12)
    # Values chosen consistently with the recovery convention.
    end[2]=30.0
    end[4]=-30.0
    end[8]=30.0
    end[10]=30.0
    result=AnalysisResult(
        "TEST",[1,2],{1:0,2:1},
        np.zeros(12),np.zeros(12),
        {1:FrameResult(1,np.zeros(12),end,local_load,length)},
    )
    curves=frame_station_results(result,1,31)
    assert curves["M2"].shape==(31,)
    second=np.diff(curves["M2"],n=2)
    assert np.allclose(second,second[0],atol=1e-10)
