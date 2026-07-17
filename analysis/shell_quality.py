from __future__ import annotations

from dataclasses import dataclass
from math import acos, degrees

import numpy as np

from fem.shell4 import derivatives_xy, shell_local_geometry
from model.project import ProjectModel


@dataclass(slots=True)
class ShellQualityResult:
    area_id: int
    area: float
    aspect_ratio: float
    minimum_angle_deg: float
    maximum_angle_deg: float
    skew_deg: float
    warpage_ratio: float
    jacobian_ratio: float
    quality_score: float
    status: str


def _edge_lengths(points: np.ndarray) -> np.ndarray:
    return np.array([
        np.linalg.norm(points[(i + 1) % 4] - points[i])
        for i in range(4)
    ], dtype=float)


def _corner_angles(points: np.ndarray) -> np.ndarray:
    values = []
    for i in range(4):
        previous = points[(i - 1) % 4] - points[i]
        following = points[(i + 1) % 4] - points[i]
        denominator = np.linalg.norm(previous) * np.linalg.norm(following)
        cosine = float(np.dot(previous, following) / max(denominator, 1.0e-15))
        values.append(degrees(acos(float(np.clip(cosine, -1.0, 1.0)))))
    return np.asarray(values, dtype=float)


def _warpage_ratio(points: np.ndarray) -> float:
    # Distance of node 4 from plane 1-2-3, normalized by the longest edge.
    normal = np.cross(points[1] - points[0], points[2] - points[0])
    norm = float(np.linalg.norm(normal))
    if norm <= 1.0e-15:
        return float("inf")
    distance = abs(float(np.dot(points[3] - points[0], normal / norm)))
    longest = float(np.max(_edge_lengths(points)))
    return distance / max(longest, 1.0e-15)


def evaluate_shell_quality(points: np.ndarray, area_id: int = 0) -> ShellQualityResult:
    points = np.asarray(points, dtype=float)
    geometry = shell_local_geometry(points)
    edges = _edge_lengths(points)
    aspect = float(np.max(edges) / max(np.min(edges), 1.0e-15))
    angles = _corner_angles(points)
    minimum_angle = float(np.min(angles))
    maximum_angle = float(np.max(angles))
    skew = float(np.max(np.abs(angles - 90.0)))
    warpage = _warpage_ratio(points)

    gauss = 1.0 / np.sqrt(3.0)
    determinants = []
    for xi in (-gauss, gauss):
        for eta in (-gauss, gauss):
            _, _, _, determinant = derivatives_xy(geometry.local_xy, xi, eta)
            determinants.append(float(determinant))
    jacobian_ratio = float(min(determinants) / max(max(determinants), 1.0e-15))

    # Dimensionless 0..1 score. A perfect rectangle receives 1.0.
    aspect_score = min(1.0, 1.0 / max(aspect, 1.0))
    skew_score = max(0.0, 1.0 - skew / 90.0)
    jacobian_score = float(np.clip(jacobian_ratio, 0.0, 1.0))
    warpage_score = max(0.0, 1.0 - min(warpage / 0.05, 1.0))
    score = float(
        0.30 * aspect_score
        + 0.30 * skew_score
        + 0.30 * jacobian_score
        + 0.10 * warpage_score
    )

    if jacobian_ratio <= 0.10 or minimum_angle < 20.0 or aspect > 10.0:
        status = "Poor"
    elif jacobian_ratio < 0.40 or minimum_angle < 35.0 or aspect > 5.0 or skew > 45.0:
        status = "Warning"
    else:
        status = "Good"

    return ShellQualityResult(
        area_id=area_id,
        area=geometry.area,
        aspect_ratio=aspect,
        minimum_angle_deg=minimum_angle,
        maximum_angle_deg=maximum_angle,
        skew_deg=skew,
        warpage_ratio=warpage,
        jacobian_ratio=jacobian_ratio,
        quality_score=score,
        status=status,
    )


def evaluate_project_shells(project: ProjectModel) -> list[ShellQualityResult]:
    results = []
    for area in project.areas.values():
        points = np.array([
            [project.nodes[nid].x, project.nodes[nid].y, project.nodes[nid].z]
            for nid in area.nodes
        ], dtype=float)
        results.append(evaluate_shell_quality(points, area.id))
    return results
