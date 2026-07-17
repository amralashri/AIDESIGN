import numpy as np
from analysis.hover_results import frame_result_tip
from analysis.results import AnalysisResult,FrameResult
from core.units import UnitSystem
from model.project import ProjectModel

def test_frame_tip():
    model=ProjectModel.default()
    frame=model.add_frame((0,0,3.5),(5,0,3.5))
    end=np.zeros(12);end[5]=10;end[11]=-10
    result=AnalysisResult(
        "TEST",list(model.nodes),{nid:i for i,nid in enumerate(model.nodes)},
        np.zeros(12),np.zeros(12),
        {frame.id:FrameResult(frame.id,np.zeros(12),end,np.zeros(3),5.0)},{}
    )
    tip=frame_result_tip(model,result,UnitSystem(),frame.id,"Moment",0.5)
    assert tip is not None
    assert "Value" in tip.html()
