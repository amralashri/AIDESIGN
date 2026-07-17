import numpy as np

from analysis.shell_quality import evaluate_shell_quality


def test_square_shell_has_high_quality():
    points = np.array([
        [0.0, 0.0, 0.0],
        [4.0, 0.0, 0.0],
        [4.0, 4.0, 0.0],
        [0.0, 4.0, 0.0],
    ])
    result = evaluate_shell_quality(points, 1)
    assert result.status == "Good"
    assert result.aspect_ratio == 1.0
    assert result.jacobian_ratio > 0.99
    assert result.quality_score > 0.95


def test_high_aspect_shell_is_flagged():
    points = np.array([
        [0.0, 0.0, 0.0],
        [20.0, 0.0, 0.0],
        [20.0, 1.0, 0.0],
        [0.0, 1.0, 0.0],
    ])
    result = evaluate_shell_quality(points, 2)
    assert result.status == "Poor"
    assert result.aspect_ratio == 20.0
