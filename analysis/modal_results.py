from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(slots=True)
class ModeShape:
    number: int
    eigenvalue: float
    circular_frequency: float
    frequency_hz: float
    period_s: float
    vector: np.ndarray
    participation_x: float
    participation_y: float
    participation_z: float


@dataclass(slots=True)
class ModalAnalysisResult:
    node_order: list[int]
    node_index: dict[int,int]
    modes: list[ModeShape]
    mass_matrix_diagonal: np.ndarray
    free_dofs: np.ndarray

    def node_mode_displacement(
        self,
        mode_number: int,
        node_id: int,
    ) -> np.ndarray:
        mode = self.modes[mode_number-1]
        start = 6*self.node_index[node_id]
        return mode.vector[start:start+6].copy()
