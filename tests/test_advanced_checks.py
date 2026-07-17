import numpy as np
from analysis.results import AnalysisResult, AreaResult, FrameResult
from design.advanced_checks import run_advanced_design
from model.project import ProjectModel


def test_advanced_checks_create_beam_column_and_slab_results():
    model=ProjectModel.default()
    beam=model.add_frame((0,0,3.5),(5,0,3.5),'Beam','B300x600')
    column=model.add_frame((0,0,0),(0,0,3.5),'Column','C400x400')
    area=model.add_rect_area((0,0,3.5),(5,5,3.5))
    fr={
        beam.id:FrameResult(beam.id,np.zeros(12),np.array([0,50,0,8,0,100,0,-50,0,-8,0,-100],float),np.zeros(3),5),
        column.id:FrameResult(column.id,np.zeros(12),np.array([500,0,0,0,50,40,-500,0,0,0,-50,-40],float),np.zeros(3),3.5),
    }
    ar=AreaResult(area.id,np.zeros(24),np.zeros(24),{'Nx':0,'Ny':0,'Nxy':0,'Mx':25,'My':18,'Mxy':0,'Qx':0,'Qy':0},25,
        np.array([[0,0],[5,0],[5,5],[0,5]],float),np.eye(3),25_000_000,0.2,0.2)
    node_ids=list(model.nodes)
    res=AnalysisResult('ULS',node_ids,{nid:i for i,nid in enumerate(node_ids)},np.zeros(6*len(node_ids)),np.zeros(6*len(node_ids)),fr,{area.id:ar})
    out=run_advanced_design(model,res)
    assert beam.id in out.beams
    assert column.id in out.columns
    assert area.id in out.slabs
    assert out.beams[beam.id].stirrup_spacing_mm>0
    assert out.columns[column.id].ratio>=0
