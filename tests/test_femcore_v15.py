import math
import numpy as np

from analysis.solver import LinearStaticSolver
from fem.frame3d import (
    local_consistent_mass_matrix,
    rigid_end_offset_matrix,
)
from model.entities import FrameSection, LoadPattern, Material, Story
from model.project import ProjectModel


def cantilever(length=3.0):
    model=ProjectModel()
    model.stories={1:Story(1,"Base",0.0,0.0),2:Story(2,"Top",3.0,3.0)}
    model.active_story_id=2
    model.materials={"Steel":Material(
        "Steel",elastic_modulus=200_000_000.0,
        poisson_ratio=0.30,density=0.0,
    )}
    model.frame_sections={"Test":FrameSection("Test","Steel",0.10,0.20)}
    model.area_sections={}
    model.load_patterns={"TEST":LoadPattern("TEST",0.0)}
    model.load_combinations={}
    frame=model.add_frame((0,0,0),(length,0,0),"Beam","Test")
    model.assign_restraint(frame.i,(True,True,True,True,True,True))
    model.add_joint_load(frame.j,"TEST",(0,0,-10,0,0,0))
    return model,frame


def test_rigid_offset_matrix_maps_rotation_to_face_translation():
    arm=rigid_end_offset_matrix(0.4,0.2)
    dof=np.zeros(12)
    dof[5]=1.0
    face=arm@dof
    assert math.isclose(face[1],0.4)
    dof=np.zeros(12)
    dof[11]=1.0
    face=arm@dof
    assert math.isclose(face[7],-0.2)


def test_rigid_i_zone_uses_shorter_deformable_cantilever_length():
    model,frame=cantilever(3.0)
    model.assign_frame_rigid_offsets(frame.id,0.5,0.0)
    result=LinearStaticSolver(model).solve("TEST")
    uz=result.node_displacement(frame.j)[2]
    section=model.frame_sections["Test"]
    E=model.materials["Steel"].elastic_modulus
    deformable=2.5
    expected=-10.0*deformable**3/(3.0*E*section.iy)
    assert math.isclose(uz,expected,rel_tol=1e-8,abs_tol=1e-12)


def test_consistent_mass_has_correct_rigid_body_translational_mass():
    mass_per_length=2.5
    length=4.0
    matrix=local_consistent_mass_matrix(mass_per_length,0.03,length)
    assert np.allclose(matrix,matrix.T,atol=1e-12)
    for component in range(3):
        rigid=np.zeros(12)
        rigid[component]=1.0
        rigid[6+component]=1.0
        total=float(rigid@matrix@rigid)
        assert math.isclose(total,mass_per_length*length,rel_tol=1e-12)
    assert np.min(np.linalg.eigvalsh(matrix)) >= -1e-10


def test_rigid_offsets_round_trip_in_project_file(tmp_path):
    model,frame=cantilever()
    model.assign_frame_rigid_offsets(frame.id,0.25,0.15)
    path=tmp_path/"offsets.aidesign"
    model.save(path)
    loaded=ProjectModel.load(path)
    item=loaded.frames[frame.id]
    assert item.rigid_offset_i==0.25
    assert item.rigid_offset_j==0.15
