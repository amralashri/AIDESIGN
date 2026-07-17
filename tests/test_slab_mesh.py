from model.project import ProjectModel

def test_area_subdivision_creates_conforming_mesh_and_copies_loads():
    model=ProjectModel.default()
    area=model.add_rect_area((0,0,3.5),(6,4,3.5))
    model.assign_area_surface_load(area.id,"LIVE",5.0)
    generated=model.subdivide_area(area.id,3,2)
    assert len(generated)==6
    assert area.id not in model.areas
    assert len(model.nodes)==12
    assert all(
        model.areas[aid].surface_loads["LIVE"]==5.0
        for aid in generated
    )
    assert all(
        model.areas[aid].section=="S200"
        for aid in generated
    )
