from analysis.contours import jet_rgb


def test_contour_color_endpoints():
    assert jet_rgb(0.0,0.0,1.0)==(0,40,180)
    assert jet_rgb(1.0,0.0,1.0)==(210,0,0)
