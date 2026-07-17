from analysis.results import AnalysisResult, AreaResult, FrameResult
from design.concrete import design_concrete
from model.project import ProjectModel
import numpy as np


def test_preliminary_slab_design_produces_spacing():
    model=ProjectModel.default()
    area=model.add_rect_area((0,0,3.5),(5,5,3.5))
    area_result=AreaResult(
        area.id,np.zeros(24),np.zeros(24),
        {"Nx":0,"Ny":0,"Nxy":0,"Mx":25,"My":18,
         "Mxy":0,"Qx":0,"Qy":0},
        25.0,
        np.array([[0,0],[5,0],[5,5],[0,5]],dtype=float),
        np.eye(3),25_000_000.0,0.2,0.2,
    )
    result=AnalysisResult(
        "TEST",list(model.nodes),{
            nid:i for i,nid in enumerate(model.nodes)
        },np.zeros(24),np.zeros(24),{}, {area.id:area_result}
    )
    design=design_concrete(model,result)
    assert area.id in design.slabs
    assert 75 <= design.slabs[area.id].spacing_x_mm <= 300
