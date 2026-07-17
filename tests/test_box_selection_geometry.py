from graphics.selection import segment_intersects_rectangle

def test_segment_rectangle_crossing():
    rect=(10,10,40,30)
    assert segment_intersects_rectangle((0,20),(50,20),rect)
    assert not segment_intersects_rectangle((0,0),(5,5),rect)
