from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np
from scipy.sparse import issparse
from scipy.sparse.linalg import eigsh

DOF_NAMES=("Ux","Uy","Uz","Rx","Ry","Rz")

@dataclass(slots=True)
class StabilityDiagnostic:
    zero_stiffness_dofs: list[str] = field(default_factory=list)
    near_mechanism_dofs: list[str] = field(default_factory=list)
    condition_estimate: float | None = None

    def as_text(self) -> str:
        lines=[]
        if self.zero_stiffness_dofs:
            lines.append("Zero-stiffness DOFs: "+", ".join(self.zero_stiffness_dofs[:12]))
        if self.near_mechanism_dofs:
            lines.append("Likely mechanism DOFs: "+", ".join(self.near_mechanism_dofs[:12]))
        if self.condition_estimate is not None:
            lines.append(f"Estimated stiffness condition number: {self.condition_estimate:.3e}")
        return "\n".join(lines) or "No specific unstable DOF could be isolated."


def _dof_label(global_dof: int, node_order: list[int]) -> str:
    node_index=global_dof//6
    component=global_dof%6
    node_id=node_order[node_index] if node_index < len(node_order) else node_index+1
    return f"N{node_id}.{DOF_NAMES[component]}"


def diagnose_reduced_stiffness(
    reduced_stiffness,
    free_dofs: np.ndarray,
    node_order: list[int],
    relative_tolerance: float = 1.0e-10,
) -> StabilityDiagnostic:
    """Identify zero diagonals and dominant DOFs in the softest eigenvector."""
    matrix=reduced_stiffness.tocsr() if issparse(reduced_stiffness) else np.asarray(reduced_stiffness)
    diagonal=np.asarray(matrix.diagonal() if issparse(matrix) else np.diag(matrix),dtype=float)
    scale=max(float(np.max(np.abs(diagonal))),1.0)
    zero=np.where(np.abs(diagonal)<=relative_tolerance*scale)[0]
    report=StabilityDiagnostic(
        zero_stiffness_dofs=[_dof_label(int(free_dofs[i]),node_order) for i in zero]
    )
    size=len(free_dofs)
    if size < 2:
        return report
    try:
        if issparse(matrix):
            small_vectors=eigsh(matrix,k=1,which="SM",return_eigenvectors=True)
            small=float(small_vectors[0][0])
            vector=np.asarray(small_vectors[1][:,0])
            large=float(eigsh(matrix,k=1,which="LM",return_eigenvectors=False)[0])
        else:
            eigenvalues,eigenvectors=np.linalg.eigh(matrix)
            order=np.argsort(np.abs(eigenvalues))
            small=float(eigenvalues[order[0]])
            vector=eigenvectors[:,order[0]]
            large=float(eigenvalues[np.argmax(np.abs(eigenvalues))])
        report.condition_estimate=abs(large)/max(abs(small),1.0e-30)
        magnitude=np.abs(vector)
        threshold=max(float(np.max(magnitude))*0.35,1.0e-12)
        dominant=np.where(magnitude>=threshold)[0]
        report.near_mechanism_dofs=[
            _dof_label(int(free_dofs[i]),node_order) for i in dominant
        ]
    except Exception:
        pass
    return report
