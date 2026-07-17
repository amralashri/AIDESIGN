from __future__ import annotations

from dataclasses import dataclass
import warnings

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import MatrixRankWarning, spsolve

from analysis.model_check import check_model
from analysis.results import AnalysisResult, AreaResult, FrameResult
from analysis.stability import diagnose_reduced_stiffness
from fem.frame3d import (
    apply_end_releases, apply_rigid_end_offsets,
    local_axes,
    local_geometric_stiffness,
    local_stiffness_matrix,
    transformation_matrix,
    uniform_load_equivalent_local,
)
from fem.shell4 import (
    shell4_local_stiffness,
    shell_center_resultants,
    shell_local_geometry,
    shell_pressure_equivalent_local,
    shell_transformation,
)
from model.project import ProjectModel


@dataclass(slots=True)
class ShellAssemblyData:
    dofs: np.ndarray
    transform: np.ndarray
    local_stiffness: np.ndarray
    local_equivalent_load: np.ndarray
    local_xy: np.ndarray
    rotation: np.ndarray
    area: float
    elastic_modulus: float
    poisson_ratio: float
    thickness: float


@dataclass(slots=True)
class ElementAssemblyData:
    dofs: np.ndarray
    transform: np.ndarray
    local_stiffness: np.ndarray
    local_equivalent_load: np.ndarray
    local_uniform_load: np.ndarray
    length: float
    released_dofs: np.ndarray
    rigid_arm: np.ndarray
    face_stiffness: np.ndarray
    face_equivalent_load: np.ndarray


class LinearStaticSolver:
    """
    Linear 3D frame + shell solver with optional geometric stiffness.

    Internal units:
      force = kN
      length = m
      moment = kN.m
    """

    def __init__(self, project: ProjectModel) -> None:
        self.project = project

    def _case_factors(self, case_name: str) -> dict[str,float]:
        if case_name in self.project.load_patterns:
            return {case_name:1.0}
        if case_name in self.project.load_combinations:
            return dict(
                self.project.load_combinations[case_name].factors
            )
        raise ValueError(
            f"Unknown load case or combination: {case_name}"
        )

    def solve(
        self,
        case_name: str,
        geometric_axial_forces: dict[int,float] | None = None,
        diaphragm_penalty_factor: float = 1.0e8,
    ) -> AnalysisResult:
        report=check_model(self.project)
        if not report.is_valid:
            raise ValueError(report.as_text())

        factors=self._case_factors(case_name)
        node_order=sorted(self.project.nodes)
        node_index={
            node_id:index for index,node_id in enumerate(node_order)
        }
        dof_count=6*len(node_order)

        rows=[]
        cols=[]
        values=[]
        force=np.zeros(dof_count,dtype=float)
        elements:dict[int,ElementAssemblyData]={}
        shells:dict[int,ShellAssemblyData]={}

        # ----------------------------------------------------
        # Frame elements
        # ----------------------------------------------------
        for frame in self.project.frames.values():
            node_i=self.project.nodes[frame.i]
            node_j=self.project.nodes[frame.j]
            point_i=np.array(
                [node_i.x,node_i.y,node_i.z],dtype=float
            )
            point_j=np.array(
                [node_j.x,node_j.y,node_j.z],dtype=float
            )
            total_length=float(np.linalg.norm(point_j-point_i))
            offset_i=float(frame.rigid_offset_i)
            offset_j=float(frame.rigid_offset_j)
            length=total_length-offset_i-offset_j
            if length <= 1.0e-8:
                raise ValueError(
                    f"Frame F{frame.id} rigid offsets leave no deformable length."
                )
            section=self.project.frame_sections[frame.section]
            material=self.project.materials[section.material]

            rotation=local_axes(point_i,point_j)
            transform=transformation_matrix(rotation)
            local_k=local_stiffness_matrix(
                material.elastic_modulus,
                material.shear_modulus,
                section.area,
                section.iy,
                section.iz,
                section.torsion_constant,
                length,
            )

            global_uniform=np.zeros(3,dtype=float)
            for pattern_name,factor in factors.items():
                assigned=frame.distributed_loads.get(pattern_name)
                if assigned is not None:
                    global_uniform += factor*np.asarray(
                        assigned,dtype=float
                    )
                pattern=self.project.load_patterns.get(pattern_name)
                if pattern and pattern.self_weight_multiplier:
                    self_weight=(
                        section.area*material.density
                        * pattern.self_weight_multiplier*factor
                    )
                    global_uniform += np.array(
                        [0.0,0.0,-self_weight],dtype=float
                    )

            local_uniform=rotation@global_uniform
            local_load=uniform_load_equivalent_local(
                local_uniform[0],
                local_uniform[1],
                local_uniform[2],
                length,
            )

            local_k,local_load,released=apply_end_releases(
                local_k,local_load,
                frame.release_i,frame.release_j,
            )
            face_stiffness=local_k.copy()
            face_equivalent_load=local_load.copy()
            local_k,local_load,rigid_arm=apply_rigid_end_offsets(
                local_k,local_load,offset_i,offset_j
            )

            if geometric_axial_forces is not None:
                compression=max(
                    0.0,
                    float(geometric_axial_forces.get(frame.id,0.0))
                )
                local_k=(
                    local_k
                    - local_geometric_stiffness(compression,length)
                )

            global_k=transform.T@local_k@transform
            dofs=[]
            for node_id in (frame.i,frame.j):
                start=6*node_index[node_id]
                dofs.extend(range(start,start+6))
            dofs=np.asarray(dofs,dtype=int)

            rr,cc=np.meshgrid(dofs,dofs,indexing="ij")
            rows.extend(rr.ravel().tolist())
            cols.extend(cc.ravel().tolist())
            values.extend(global_k.ravel().tolist())
            force[dofs] += transform.T@local_load

            elements[frame.id]=ElementAssemblyData(
                dofs,transform,local_k,local_load,
                local_uniform,length,released,rigid_arm,
                face_stiffness,face_equivalent_load,
            )

        # ----------------------------------------------------
        # Shell elements
        # ----------------------------------------------------
        for area_object in self.project.areas.values():
            section=self.project.area_sections[area_object.section]
            material=self.project.materials[section.material]
            node_ids=list(area_object.nodes)
            points=np.array([
                [
                    self.project.nodes[node_id].x,
                    self.project.nodes[node_id].y,
                    self.project.nodes[node_id].z,
                ]
                for node_id in node_ids
            ],dtype=float)

            geometry=shell_local_geometry(points)
            transform=shell_transformation(geometry.rotation)
            local_k=shell4_local_stiffness(
                material.elastic_modulus,
                material.poisson_ratio,
                section.thickness,
                geometry.local_xy,
            )
            global_k=transform.T@local_k@transform

            dofs=[]
            for node_id in node_ids:
                start=6*node_index[node_id]
                dofs.extend(range(start,start+6))
            dofs=np.asarray(dofs,dtype=int)

            rr,cc=np.meshgrid(dofs,dofs,indexing="ij")
            rows.extend(rr.ravel().tolist())
            cols.extend(cc.ravel().tolist())
            values.extend(global_k.ravel().tolist())

            global_pressure=np.zeros(3,dtype=float)
            for pattern_name,factor in factors.items():
                pressure=area_object.surface_loads.get(
                    pattern_name,0.0
                )
                global_pressure += np.array(
                    [0.0,0.0,-pressure*factor],dtype=float
                )
                pattern=self.project.load_patterns.get(pattern_name)
                if pattern and pattern.self_weight_multiplier:
                    self_weight=(
                        section.thickness*material.density
                        * pattern.self_weight_multiplier*factor
                    )
                    global_pressure += np.array(
                        [0.0,0.0,-self_weight],dtype=float
                    )

            local_pressure=geometry.rotation@global_pressure
            local_load=shell_pressure_equivalent_local(
                float(local_pressure[2]),geometry.area
            )
            force[dofs] += transform.T@local_load

            shells[area_object.id]=ShellAssemblyData(
                dofs=dofs,
                transform=transform,
                local_stiffness=local_k,
                local_equivalent_load=local_load,
                local_xy=geometry.local_xy,
                rotation=geometry.rotation,
                area=geometry.area,
                elastic_modulus=material.elastic_modulus,
                poisson_ratio=material.poisson_ratio,
                thickness=section.thickness,
            )

        # Joint loads.
        for joint_load in self.project.joint_loads:
            factor=factors.get(joint_load.pattern,0.0)
            if factor==0.0:
                continue
            start=6*node_index[joint_load.node_id]
            force[start:start+6] += (
                factor*np.asarray(joint_load.values,dtype=float)
            )

        # ----------------------------------------------------
        # Rigid diaphragm penalty constraints
        # ----------------------------------------------------
        if self.project.diaphragms:
            reference=max(
                max((abs(value) for value in values),default=1.0),
                1.0,
            )
            penalty=reference*diaphragm_penalty_factor
            for diaphragm in self.project.diaphragms.values():
                master=diaphragm.node_ids[0]
                master_base=6*node_index[master]
                components=[]
                if diaphragm.rigid_ux:
                    components.append(0)
                if diaphragm.rigid_uy:
                    components.append(1)
                if diaphragm.rigid_rz:
                    components.append(5)

                for slave in diaphragm.node_ids[1:]:
                    slave_base=6*node_index[slave]
                    for component in components:
                        a=master_base+component
                        b=slave_base+component
                        rows.extend([a,a,b,b])
                        cols.extend([a,b,a,b])
                        values.extend([
                            penalty,-penalty,-penalty,penalty
                        ])

        stiffness=coo_matrix(
            (values,(rows,cols)),
            shape=(dof_count,dof_count),
        ).tocsr()

        restrained=[]
        for node_id in node_order:
            start=6*node_index[node_id]
            restrained.extend(
                start+dof
                for dof,fixed in enumerate(
                    self.project.nodes[node_id].restraint
                )
                if fixed
            )

        all_dofs=np.arange(dof_count,dtype=int)
        fixed=np.asarray(sorted(set(restrained)),dtype=int)
        free=np.setdiff1d(all_dofs,fixed)
        if free.size==0:
            raise ValueError("No free degrees of freedom remain.")

        reduced_k=stiffness[free][:,free]
        reduced_f=force[free]

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "error",category=MatrixRankWarning
            )
            try:
                free_displacements=spsolve(
                    reduced_k,reduced_f
                )
            except (MatrixRankWarning,RuntimeError) as exc:
                diagnostic=diagnose_reduced_stiffness(
                    reduced_k,free,node_order
                )
                raise ValueError(
                    "The stiffness matrix is singular. Check supports, "
                    "connectivity, releases and diaphragm assignments.\n"
                    + diagnostic.as_text()
                ) from exc

        if not np.all(np.isfinite(free_displacements)):
            diagnostic=diagnose_reduced_stiffness(
                reduced_k,free,node_order
            )
            raise ValueError(
                "The solver produced non-finite displacements. "
                "The model is unstable or ill-conditioned.\n"
                + diagnostic.as_text()
            )

        displacements=np.zeros(dof_count,dtype=float)
        displacements[free]=free_displacements
        reactions=stiffness@displacements-force

        frame_results={}
        for frame_id,data in elements.items():
            local_joint_displacement=(
                data.transform@displacements[data.dofs]
            )
            local_displacement=data.rigid_arm@local_joint_displacement
            local_end_forces=(
                data.face_stiffness@local_displacement
                - data.face_equivalent_load
            )
            if data.released_dofs.size:
                local_end_forces[data.released_dofs]=0.0
            frame_results[frame_id]=FrameResult(
                frame_id,
                local_displacement,
                local_end_forces,
                data.local_uniform_load,
                data.length,
            )

        area_results={}
        for area_id,data in shells.items():
            local_displacement=(
                data.transform@displacements[data.dofs]
            )
            local_nodal_forces=(
                data.local_stiffness@local_displacement
                - data.local_equivalent_load
            )
            resultants=shell_center_resultants(
                local_displacement,
                data.elastic_modulus,
                data.poisson_ratio,
                data.thickness,
                data.local_xy,
            )
            area_results[area_id]=AreaResult(
                area_id=area_id,
                local_displacements=local_displacement,
                local_nodal_forces=local_nodal_forces,
                resultants=resultants,
                area=data.area,
                local_xy=data.local_xy,
                rotation=data.rotation,
                elastic_modulus=data.elastic_modulus,
                poisson_ratio=data.poisson_ratio,
                thickness=data.thickness,
            )

        return AnalysisResult(
            case_name,
            node_order,
            node_index,
            displacements,
            np.asarray(reactions),
            frame_results,
            area_results,
        )


class PDeltaSolver:
    """Iterative initial-stress P-Delta analysis."""

    def __init__(self,project:ProjectModel) -> None:
        self.project=project

    def solve(
        self,
        case_name:str,
        maximum_iterations:int=20,
        tolerance:float=1.0e-5,
    ) -> AnalysisResult:
        linear=LinearStaticSolver(self.project)
        result=linear.solve(case_name)
        previous=result.displacements.copy()

        for iteration in range(1,maximum_iterations+1):
            axial={}
            for frame_id,frame_result in result.frame_results.items():
                p_i=-float(frame_result.local_end_forces[0])
                p_j=float(frame_result.local_end_forces[6])
                axial[frame_id]=max(0.0,0.5*(p_i+p_j))

            updated=linear.solve(
                case_name,geometric_axial_forces=axial
            )
            denominator=max(
                float(np.linalg.norm(updated.displacements)),1.0e-12
            )
            error=float(
                np.linalg.norm(
                    updated.displacements-previous
                )/denominator
            )
            updated.analysis_type="P-Delta"
            updated.iterations=iteration
            updated.convergence_error=error

            if error<=tolerance:
                return updated

            previous=updated.displacements.copy()
            result=updated

        raise ValueError(
            f"P-Delta analysis did not converge in "
            f"{maximum_iterations} iterations. "
            f"Last relative error={error:.3e}."
        )
