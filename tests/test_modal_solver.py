from analysis.modal_solver import ModalSolver
from model.project import ProjectModel


def test_simple_frame_modal_analysis():
    model=ProjectModel.default()
    column=model.add_frame(
        (0,0,0),(0,0,3.5),"Column","C400x400"
    )
    beam=model.add_frame(
        (0,0,3.5),(5,0,3.5),"Beam","B300x600"
    )
    model.assign_restraint(
        column.i,(True,True,True,True,True,True)
    )
    model.assign_joint_mass(
        beam.j,(10.0,10.0,10.0,0.0,0.0,0.0)
    )
    result=ModalSolver(model).solve(3)
    assert result.modes
    assert result.modes[0].period_s>0.0
