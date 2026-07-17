from __future__ import annotations

import numpy as np
from scipy.linalg import eigh
from scipy.sparse import coo_matrix

from analysis.model_check import check_model
from analysis.modal_results import ModalAnalysisResult, ModeShape
from fem.frame3d import (
    apply_end_releases, apply_rigid_end_offsets, local_axes,
    local_consistent_mass_matrix, local_stiffness_matrix,
    transformation_matrix,
)
from fem.shell4 import shell4_local_stiffness, shell_local_geometry, shell_transformation
from model.project import ProjectModel


GRAVITY = 9.80665


class ModalSolver:
    """
    Linear undamped eigenvalue analysis.

    Mass model:
    - explicit joint masses;
    - frame distributed translational mass lumped equally to both ends;
    - slab translational mass lumped equally to four corner joints;
    - optional load-derived mass from the configured mass source.

    Rotational masses are accepted only when explicitly assigned to joints.
    """

    def __init__(self, project: ProjectModel):
        self.project = project

    def solve(self, number_of_modes: int = 12) -> ModalAnalysisResult:
        report = check_model(self.project)
        if not report.is_valid:
            raise ValueError(report.as_text())

        node_order = sorted(self.project.nodes)
        node_index = {nid:i for i,nid in enumerate(node_order)}
        ndof = 6*len(node_order)

        rows=[]; cols=[]; values=[]
        mass_rows=[]; mass_cols=[]; mass_values=[]
        lumped_mass = np.zeros(ndof, dtype=float)

        # Explicit joint masses.
        for nid in node_order:
            base=6*node_index[nid]
            lumped_mass[base:base+6] += np.asarray(
                self.project.nodes[nid].mass, dtype=float
            )

        # Frame stiffness and mass.
        for frame in self.project.frames.values():
            ni=self.project.nodes[frame.i]
            nj=self.project.nodes[frame.j]
            pi=np.array([ni.x,ni.y,ni.z],dtype=float)
            pj=np.array([nj.x,nj.y,nj.z],dtype=float)
            total_length=float(np.linalg.norm(pj-pi))
            offset_i=float(frame.rigid_offset_i)
            offset_j=float(frame.rigid_offset_j)
            length=total_length-offset_i-offset_j
            if length <= 1.0e-8:
                raise ValueError(
                    f"Frame F{frame.id} rigid offsets leave no deformable length."
                )
            section=self.project.frame_sections[frame.section]
            material=self.project.materials[section.material]
            rotation=local_axes(pi,pj)
            transform=transformation_matrix(rotation)
            local_k=local_stiffness_matrix(
                material.elastic_modulus,
                material.shear_modulus,
                section.area,section.iy,section.iz,
                section.torsion_constant,length,
            )
            zero_load=np.zeros(12,dtype=float)
            local_k,_,_=apply_end_releases(
                local_k,zero_load,frame.release_i,frame.release_j
            )
            local_k,_,rigid_arm=apply_rigid_end_offsets(
                local_k,zero_load,offset_i,offset_j
            )
            global_k=transform.T@local_k@transform
            dofs=[]
            for nid in (frame.i,frame.j):
                start=6*node_index[nid]
                dofs.extend(range(start,start+6))
            dofs=np.asarray(dofs,dtype=int)
            rr,cc=np.meshgrid(dofs,dofs,indexing="ij")
            rows.extend(rr.ravel().tolist())
            cols.extend(cc.ravel().tolist())
            values.extend(global_k.ravel().tolist())

            if self.project.mass_source.include_element_self_mass:
                mass_per_length=(
                    section.area*material.density/GRAVITY
                )
                polar_area=section.iy+section.iz
                rotary_mass_per_length=(
                    material.density/GRAVITY*polar_area
                )
                local_m=local_consistent_mass_matrix(
                    mass_per_length,rotary_mass_per_length,length
                )
                local_m=rigid_arm.T@local_m@rigid_arm
                global_m=transform.T@local_m@transform
                mass_rows.extend(rr.ravel().tolist())
                mass_cols.extend(cc.ravel().tolist())
                mass_values.extend(global_m.ravel().tolist())

            # Load-derived mass from frame UDL.
            for pattern,factor in self.project.mass_source.load_pattern_factors.items():
                vector=frame.distributed_loads.get(pattern)
                if vector is None:
                    continue
                vertical=abs(float(vector[2]))*factor
                total_mass=vertical*length/GRAVITY
                for nid in (frame.i,frame.j):
                    base=6*node_index[nid]
                    lumped_mass[base:base+3] += total_mass/2.0

        # Shell stiffness and mass.
        for area in self.project.areas.values():
            section=self.project.area_sections[area.section]
            material=self.project.materials[section.material]
            points=np.array([
                [self.project.nodes[nid].x,
                 self.project.nodes[nid].y,
                 self.project.nodes[nid].z]
                for nid in area.nodes
            ],dtype=float)
            geometry=shell_local_geometry(points)
            transform=shell_transformation(geometry.rotation)
            local_k=shell4_local_stiffness(
                material.elastic_modulus,material.poisson_ratio,
                section.thickness,geometry.local_xy,
            )
            global_k=transform.T@local_k@transform
            dofs=[]
            for nid in area.nodes:
                start=6*node_index[nid]
                dofs.extend(range(start,start+6))
            dofs=np.asarray(dofs,dtype=int)
            rr,cc=np.meshgrid(dofs,dofs,indexing="ij")
            rows.extend(rr.ravel().tolist())
            cols.extend(cc.ravel().tolist())
            values.extend(global_k.ravel().tolist())

            total_mass=0.0
            if self.project.mass_source.include_element_self_mass:
                total_mass += (
                    geometry.area*section.thickness
                    * material.density/GRAVITY
                )
            for pattern,factor in self.project.mass_source.load_pattern_factors.items():
                pressure=area.surface_loads.get(pattern,0.0)
                total_mass += (
                    abs(float(pressure))*factor*geometry.area/GRAVITY
                )
            for nid in area.nodes:
                base=6*node_index[nid]
                lumped_mass[base:base+3] += total_mass/4.0

        stiffness=coo_matrix(
            (values,(rows,cols)),shape=(ndof,ndof)
        ).toarray()
        mass_matrix=coo_matrix(
            (mass_values,(mass_rows,mass_cols)),shape=(ndof,ndof)
        ).toarray()
        mass_matrix += np.diag(lumped_mass)
        mass_matrix=(mass_matrix+mass_matrix.T)/2.0

        restrained=[]
        for nid in node_order:
            base=6*node_index[nid]
            restrained.extend(
                base+i for i,fixed in enumerate(
                    self.project.nodes[nid].restraint
                ) if fixed
            )
        all_dofs=np.arange(ndof,dtype=int)
        free=np.setdiff1d(
            all_dofs,np.asarray(sorted(set(restrained)),dtype=int)
        )

        # Retain only free DOF with positive mass.
        positive=np.diag(mass_matrix)[free] > 1.0e-12
        dynamic_dofs=free[positive]
        if dynamic_dofs.size == 0:
            raise ValueError(
                "No positive dynamic mass is available. "
                "Define a mass source or assign joint masses."
            )

        k=stiffness[np.ix_(dynamic_dofs,dynamic_dofs)]
        m=mass_matrix[np.ix_(dynamic_dofs,dynamic_dofs)]

        count=min(number_of_modes,max(dynamic_dofs.size-1,1))
        eigvals,eigvecs=eigh(k,m,subset_by_index=[0,count-1])

        modes=[]
        directions=[]
        for axis in range(3):
            vector=np.zeros(dynamic_dofs.size)
            for local_index,dof in enumerate(dynamic_dofs):
                if dof%6==axis:
                    vector[local_index]=1.0
            directions.append(vector)

        for index,(eigenvalue,local_vector) in enumerate(
            zip(eigvals,eigvecs.T),start=1
        ):
            if eigenvalue <= 1.0e-10:
                continue
            # Mass normalization.
            modal_mass=float(local_vector.T@m@local_vector)
            local_vector=local_vector/np.sqrt(max(modal_mass,1e-18))
            full=np.zeros(ndof)
            full[dynamic_dofs]=local_vector
            omega=float(np.sqrt(eigenvalue))
            frequency=omega/(2.0*np.pi)
            period=1.0/frequency
            participation=[]
            for direction in directions:
                numerator=float(local_vector.T@m@direction)
                denominator=float(direction.T@m@direction)
                participation.append(
                    numerator/np.sqrt(max(denominator,1e-18))
                )
            modes.append(ModeShape(
                index,float(eigenvalue),omega,frequency,period,
                full,*participation
            ))

        if not modes:
            raise ValueError(
                "No positive vibration modes were found. "
                "Check restraints, stiffness and mass source."
            )
        return ModalAnalysisResult(
            node_order,node_index,modes,np.diag(mass_matrix),free
        )
