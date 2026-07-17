from model.project import ProjectModel

def test_design_codes_are_saved_and_loaded(tmp_path):
    model=ProjectModel.default()
    model.design_codes.concrete_code="ACI 318-25"
    model.design_codes.importance_factor=1.25
    model.design_codes.concrete_phi_flexure=0.85
    path=tmp_path/"codes.aidesign"
    model.save(path)
    loaded=ProjectModel.load(path)
    assert loaded.design_codes.concrete_code=="ACI 318-25"
    assert loaded.design_codes.importance_factor==1.25
    assert loaded.design_codes.concrete_phi_flexure==0.85
