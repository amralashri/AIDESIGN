from __future__ import annotations

from collections import defaultdict

import numpy as np

from analysis.results import AnalysisResult
from fem.shell4 import shape_functions, shell_contour_samples, shell_resultants_at
from model.project import ProjectModel


CONTOUR_KEYS = {
    "Slab Mx": "Mx",
    "Slab My": "My",
    "Slab Mxy": "Mxy",
    "Slab Mmax": "Mmax",
    "Slab Mmin": "Mmin",
    "Slab Qx": "Qx",
    "Slab Qy": "Qy",
    "Slab Deflection": "w",
}


def _corner_value(area_result, corner: int, key: str) -> float:
    xi_eta = ((-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0))
    xi, eta = xi_eta[corner]
    if key == "w":
        return float(area_result.local_displacements[6 * corner + 2])
    return float(shell_resultants_at(
        area_result.local_displacements,
        area_result.elastic_modulus,
        area_result.poisson_ratio,
        area_result.thickness,
        area_result.local_xy,
        xi,
        eta,
    )[key])


def smoothed_nodal_values(
    project: ProjectModel,
    result: AnalysisResult,
    mode: str,
) -> dict[int, float]:
    """Average compatible shell results at shared model joints."""
    key = CONTOUR_KEYS.get(mode)
    if key is None:
        return {}
    totals: dict[int, list[float]] = defaultdict(list)
    for area_id, area in project.areas.items():
        area_result = result.area_results.get(area_id)
        if area_result is None:
            continue
        for corner, node_id in enumerate(area.nodes):
            totals[node_id].append(_corner_value(area_result, corner, key))
    return {
        node_id: float(np.mean(values))
        for node_id, values in totals.items()
        if values
    }


def area_contour_samples(
    project: ProjectModel,
    result: AnalysisResult,
    area_id: int,
    mode: str,
    divisions: int = 7,
    smooth: bool = True,
) -> list[dict]:
    if area_id not in result.area_results:
        return []
    key = CONTOUR_KEYS.get(mode)
    if key is None:
        return []
    area_result = result.area_results[area_id]
    samples = shell_contour_samples(
        area_result.local_displacements,
        area_result.elastic_modulus,
        area_result.poisson_ratio,
        area_result.thickness,
        area_result.local_xy,
        divisions,
    )
    area = project.areas[area_id]
    origin_node = project.nodes[area.nodes[0]]
    origin = np.array(
        [origin_node.x, origin_node.y, origin_node.z], dtype=float
    )
    ex, ey, _ = area_result.rotation
    nodal = smoothed_nodal_values(project, result, mode) if smooth else {}
    corner_values = np.array([
        nodal.get(node_id, _corner_value(area_result, corner, key))
        for corner, node_id in enumerate(area.nodes)
    ], dtype=float)

    output = []
    for sample in samples:
        global_point = origin + sample["x"] * ex + sample["y"] * ey
        if smooth:
            n, _, _ = shape_functions(sample["xi"], sample["eta"])
            value = float(n @ corner_values)
        else:
            value = float(sample[key])
        if key == "w":
            value *= 1000.0
        output.append({
            **sample,
            "global": global_point,
            "value": value,
        })
    return output


def contour_range(
    project: ProjectModel,
    result: AnalysisResult,
    mode: str,
) -> tuple[float, float]:
    values = []
    for area_id in project.areas:
        values.extend(
            sample["value"]
            for sample in area_contour_samples(
                project, result, area_id, mode, 7
            )
        )
    if not values:
        return 0.0, 1.0
    minimum = float(min(values))
    maximum = float(max(values))
    if abs(maximum - minimum) < 1.0e-12:
        delta = max(abs(maximum) * 0.1, 1.0)
        minimum -= delta
        maximum += delta
    return minimum, maximum


def jet_rgb(value: float, minimum: float, maximum: float):
    ratio = (value - minimum) / max(maximum - minimum, 1.0e-12)
    ratio = float(np.clip(ratio, 0.0, 1.0))
    stops = [
        (0.00, (0, 40, 180)),
        (0.25, (0, 190, 255)),
        (0.50, (40, 210, 80)),
        (0.75, (255, 220, 0)),
        (1.00, (210, 0, 0)),
    ]
    for (a, c1), (b, c2) in zip(stops[:-1], stops[1:]):
        if a <= ratio <= b:
            t = (ratio - a) / (b - a)
            return tuple(int(c1[i] + t * (c2[i] - c1[i])) for i in range(3))
    return stops[-1][1]
