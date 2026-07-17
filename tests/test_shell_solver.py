from analysis.solver import LinearStaticSolver
from model.project import ProjectModel


def test_supported_single_slab_solves_under_surface_load():
    model=ProjectModel.default()
    area=model.add_rect_area(
        (0.0,0.0,3.5),(5.0,5.0,3.5)
    )
    # Fix three corners; leave the fourth corner structurally active.
    for node_id in area.nodes[:3]:
        model.assign_restraint(
            node_id,(True,True,True,True,True,True)
        )
    model.assign_area_surface_load(area.id,"LIVE",5.0)
    result=LinearStaticSolver(model).solve("LIVE")
    assert area.id in result.area_results
    assert result.area_results[area.id].area>0.0
    assert result.max_translation>0.0
