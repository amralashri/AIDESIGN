from model.project import ProjectModel

def test_diaphragm_saved_and_loaded(tmp_path):
    model=ProjectModel.default()
    n1=model.get_or_create_node(0,0,3.5)
    n2=model.get_or_create_node(5,0,3.5)
    model.assign_diaphragm("D1",[n1.id,n2.id])
    path=tmp_path/"d.aidesign"
    model.save(path)
    loaded=ProjectModel.load(path)
    assert loaded.diaphragms["D1"].node_ids==[n1.id,n2.id]
    assert loaded.diaphragms["D1"].rigid_ux
