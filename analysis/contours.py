from __future__ import annotations

import numpy as np

from analysis.results import AnalysisResult
from fem.shell4 import shell_contour_samples
from model.project import ProjectModel


CONTOUR_KEYS = {
    "Slab Mx": "Mx",
    "Slab My": "My",
    "Slab Mxy": "Mxy",
    "Slab Qx": "Qx",
    "Slab Qy": "Qy",
    "Slab Deflection": "w",
}


def area_contour_samples(
    project: ProjectModel,
    result: AnalysisResult,
    area_id: int,
    mode: str,
    divisions: int = 7,
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
    output = []
    for sample in samples:
        global_point = (
            origin + sample["x"]*ex + sample["y"]*ey
        )
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
) -> tuple[float,float]:
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
    if abs(maximum-minimum) < 1.0e-12:
        delta = max(abs(maximum)*0.1, 1.0)
        minimum -= delta
        maximum += delta
    return minimum, maximum


def jet_rgb(value: float, minimum: float, maximum: float):
    ratio = (value-minimum)/max(maximum-minimum,1.0e-12)
    ratio = float(np.clip(ratio,0.0,1.0))
    stops = [
        (0.00,(0,40,180)),
        (0.25,(0,190,255)),
        (0.50,(40,210,80)),
        (0.75,(255,220,0)),
        (1.00,(210,0,0)),
    ]
    for (a,c1),(b,c2) in zip(stops[:-1],stops[1:]):
        if a <= ratio <= b:
            t=(ratio-a)/(b-a)
            return tuple(
                int(c1[i]+t*(c2[i]-c1[i])) for i in range(3)
            )
    return stops[-1][1]
