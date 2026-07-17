from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(slots=True)
class FrameResult:
    frame_id: int
    local_displacements: np.ndarray
    local_end_forces: np.ndarray
    local_uniform_load: np.ndarray
    length: float


@dataclass(slots=True)
class AreaResult:
    area_id: int
    local_displacements: np.ndarray
    local_nodal_forces: np.ndarray
    resultants: dict[str, float]
    area: float
    local_xy: np.ndarray
    rotation: np.ndarray
    elastic_modulus: float
    poisson_ratio: float
    thickness: float


@dataclass(slots=True)
class AnalysisResult:
    case_name: str
    node_order: list[int]
    node_index: dict[int, int]
    displacements: np.ndarray
    reactions: np.ndarray
    frame_results: dict[int, FrameResult]
    area_results: dict[int, AreaResult] = field(default_factory=dict)
    analysis_type: str = "Linear Static"
    iterations: int = 1
    convergence_error: float = 0.0

    def node_displacement(self, node_id: int) -> np.ndarray:
        start = 6 * self.node_index[node_id]
        return self.displacements[start:start+6].copy()

    def node_reaction(self, node_id: int) -> np.ndarray:
        start = 6 * self.node_index[node_id]
        return self.reactions[start:start+6].copy()

    @property
    def max_translation(self) -> float:
        if not self.node_order:
            return 0.0
        matrix = self.displacements.reshape((-1, 6))
        return float(np.max(np.linalg.norm(matrix[:, :3], axis=1)))
