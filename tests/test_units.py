from core.units import UnitSystem

def test_unit_conversion():
    units=UnitSystem()
    units.set_unit("length","mm")
    units.set_unit("moment","kip·ft")
    assert units.convert(2.0,"length")==2000.0
    assert abs(units.convert(10.0,"moment")-7.375621493)<1e-9
