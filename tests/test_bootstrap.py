from bootstrap import missing_packages


def test_missing_packages_returns_list():
    assert isinstance(missing_packages(), list)
