import math

from analysis.solver import LinearStaticSolver
from model.entities import FrameSection, Material, Story
from model.project import ProjectModel


def cantilever_project() -> ProjectModel:
    model = ProjectModel()
    model.stories = {
        1: Story(1, "Base", 0.0, 0.0),
        2: Story(2, "Top", 3.0, 3.0),
    }
    model.active_story_id = 2
    model.materials = {
        "Steel": Material(
            "Steel", elastic_modulus=200_000_000.0,
            poisson_ratio=0.30, density=0.0,
        )
    }
    model.frame_sections = {
        "Test": FrameSection(
            "Test", "Steel", width=0.10, depth=0.20,
        )
    }
    model.area_sections = {}
    model.load_patterns = {
        "TEST": __import__("model.entities", fromlist=["LoadPattern"]).LoadPattern(
            "TEST", 0.0
        )
    }
    model.load_combinations = {}

    frame = model.add_frame(
        (0.0,0.0,0.0), (3.0,0.0,0.0),
        kind="Beam", section="Test",
    )
    model.assign_restraint(
        frame.i, (True,True,True,True,True,True)
    )
    model.add_joint_load(
        frame.j, "TEST", (0.0,0.0,-10.0,0.0,0.0,0.0)
    )
    return model


def test_cantilever_tip_deflection():
    model = cantilever_project()
    result = LinearStaticSolver(model).solve("TEST")

    free_node = max(model.nodes)
    uz = result.node_displacement(free_node)[2]

    section = model.frame_sections["Test"]
    E = model.materials["Steel"].elastic_modulus
    L = 3.0
    P = 10.0
    expected = -P * L**3 / (3.0 * E * section.iy)

    assert math.isclose(uz, expected, rel_tol=1e-8, abs_tol=1e-12)


def test_cantilever_vertical_reaction():
    model = cantilever_project()
    result = LinearStaticSolver(model).solve("TEST")

    fixed_node = min(model.nodes)
    reaction = result.node_reaction(fixed_node)

    assert math.isclose(reaction[2], 10.0, rel_tol=1e-9, abs_tol=1e-9)
