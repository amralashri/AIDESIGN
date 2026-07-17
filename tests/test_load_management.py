from model.project import ProjectModel


def test_standard_combinations_reference_existing_patterns():
    model=ProjectModel.default()
    for combination in model.load_combinations.values():
        assert set(combination.factors).issubset(model.load_patterns)


def test_combination_factors_are_preserved_in_serialization(tmp_path):
    model=ProjectModel.default()
    path=tmp_path/"model.aidesign"
    model.save(path)
    loaded=ProjectModel.load(path)
    assert loaded.load_combinations["ULS 1.2D+1.6L"].factors == {
        "DEAD":1.2,"LIVE":1.6
    }
