from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


DOFRestraint = tuple[bool, bool, bool, bool, bool, bool]


@dataclass(slots=True)
class Story:
    id: int
    name: str
    elevation: float
    height: float


@dataclass(slots=True)
class Material:
    name: str
    elastic_modulus: float = 25_000_000.0   # kN/m²
    poisson_ratio: float = 0.20
    density: float = 25.0                   # kN/m³
    thermal_coefficient: float = 1.0e-5

    @property
    def shear_modulus(self) -> float:
        return self.elastic_modulus / (2.0 * (1.0 + self.poisson_ratio))


@dataclass(slots=True)
class FrameSection:
    name: str
    material: str
    width: float
    depth: float

    @property
    def area(self) -> float:
        return self.width * self.depth

    @property
    def iy(self) -> float:
        # Local y bending uses depth along local z.
        return self.width * self.depth**3 / 12.0

    @property
    def iz(self) -> float:
        return self.depth * self.width**3 / 12.0

    @property
    def torsion_constant(self) -> float:
        a = max(self.width, self.depth)
        b = min(self.width, self.depth)
        beta = b / a
        return a * b**3 * (1.0/3.0 - 0.21*beta*(1.0 - beta**4/12.0))


@dataclass(slots=True)
class AreaSection:
    name: str
    material: str
    thickness: float
    formulation: str = "Shell-Thin"


@dataclass(slots=True)
class Node:
    id: int
    x: float
    y: float
    z: float
    restraint: DOFRestraint = (False, False, False, False, False, False)
    mass: tuple[float,float,float,float,float,float] = (
        0.0,0.0,0.0,0.0,0.0,0.0
    )


@dataclass(slots=True)
class Frame:
    id: int
    i: int
    j: int
    kind: Literal["Beam", "Column", "Brace"] = "Beam"
    section: str = "B300x600"
    distributed_loads: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    release_i: DOFRestraint = (False, False, False, False, False, False)
    release_j: DOFRestraint = (False, False, False, False, False, False)
    rigid_offset_i: float = 0.0
    rigid_offset_j: float = 0.0


@dataclass(slots=True)
class Area:
    id: int
    nodes: tuple[int, int, int, int]
    kind: Literal["Slab", "Wall"] = "Slab"
    section: str = "S200"
    surface_loads: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class JointLoad:
    node_id: int
    pattern: str
    values: tuple[float, float, float, float, float, float]


@dataclass(slots=True)
class LoadPattern:
    name: str
    self_weight_multiplier: float = 0.0


@dataclass(slots=True)
class LoadCombination:
    name: str
    factors: dict[str, float]


def entity_dict(obj) -> dict:
    data = asdict(obj)
    if isinstance(obj, (Area, Node, JointLoad)):
        if "nodes" in data:
            data["nodes"] = list(data["nodes"])
        if "restraint" in data:
            data["restraint"] = list(data["restraint"])
        if "values" in data:
            data["values"] = list(data["values"])
    return data


@dataclass(slots=True)
class MassSource:
    include_element_self_mass: bool = True
    load_pattern_factors: dict[str, float] = field(
        default_factory=lambda: {"DEAD": 1.0, "LIVE": 0.25}
    )


@dataclass(slots=True)
class DesignCodeSettings:
    concrete_code: str = "SBC 304 / ACI 318-19"
    loading_code: str = "SBC 301"
    steel_code: str = "SBC 306 / AISC 360"
    seismic_code: str = "SBC 301"
    wind_code: str = "SBC 301"
    importance_factor: float = 1.0
    concrete_phi_flexure: float = 0.90
    concrete_phi_shear: float = 0.75
    steel_resistance_method: str = "LRFD"
    notes: str = "Project-specific code review required."


@dataclass(slots=True)
class Diaphragm:
    name: str
    node_ids: list[int] = field(default_factory=list)
    rigid_ux: bool = True
    rigid_uy: bool = True
    rigid_rz: bool = True
