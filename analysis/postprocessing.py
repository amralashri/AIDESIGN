from __future__ import annotations

import numpy as np

from analysis.results import AnalysisResult
from model.project import ProjectModel


def frame_station_results(
    result: AnalysisResult,
    frame_id: int,
    station_count: int = 41,
) -> dict[str, np.ndarray]:
    """
    Recover continuous local internal-force curves from i-end equilibrium.

    Returned keys: x, P, V2, V3, T, M2, M3.
    """
    frame_result = result.frame_results[frame_id]
    length = frame_result.length
    x = np.linspace(0.0, length, station_count)
    end = frame_result.local_end_forces
    qx, qy, qz = frame_result.local_uniform_load

    # Internal section actions just to the right of the i-node.
    p0 = -end[0]
    v20 = -end[1]
    v30 = -end[2]
    t0 = -end[3]
    m20 = -end[4]
    m30 = -end[5]

    p = p0 - qx*x
    v2 = v20 - qy*x
    v3 = v30 - qz*x
    torsion = np.full_like(x, t0)

    # Equilibrium-consistent bending recovery.
    m2 = m20 + v30*x - 0.5*qz*x*x
    m3 = m30 + v20*x - 0.5*qy*x*x

    return {
        "x": x, "P": p, "V2": v2, "V3": v3,
        "T": torsion, "M2": m2, "M3": m3,
    }


def dominant_curve(
    result: AnalysisResult,
    frame_id: int,
    mode: str,
) -> tuple[np.ndarray, np.ndarray, str]:
    curves = frame_station_results(result, frame_id)
    if mode == "Moment":
        candidates = [("M2", curves["M2"]), ("M3", curves["M3"])]
        unit = "kN.m"
    elif mode == "Shear":
        candidates = [("V2", curves["V2"]), ("V3", curves["V3"])]
        unit = "kN"
    elif mode == "Axial":
        candidates = [("P", curves["P"])]
        unit = "kN"
    elif mode == "Torsion":
        candidates = [("T", curves["T"])]
        unit = "kN.m"
    else:
        raise ValueError(f"Unsupported result mode: {mode}")

    label, values = max(
        candidates,
        key=lambda item: float(np.max(np.abs(item[1]))),
    )
    return curves["x"], values, f"{label} ({unit})"


def deformed_node_positions(
    project: ProjectModel,
    result: AnalysisResult,
    scale_factor: float,
) -> dict[int, np.ndarray]:
    positions = {}
    for node_id, node in project.nodes.items():
        displacement = result.node_displacement(node_id)[:3]
        positions[node_id] = (
            np.array([node.x,node.y,node.z],dtype=float)
            + scale_factor*displacement
        )
    return positions


def automatic_deformation_scale(
    project: ProjectModel,
    result: AnalysisResult,
) -> float:
    if result.max_translation <= 1.0e-15:
        return 1.0
    coords = np.array(
        [[n.x,n.y,n.z] for n in project.nodes.values()],
        dtype=float,
    )
    model_size = max(float(np.ptp(coords, axis=0).max()), 1.0)
    return 0.08 * model_size / result.max_translation
