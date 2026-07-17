from __future__ import annotations

import json
import numpy as np
from pathlib import Path
from typing import Iterable

from model.entities import (
    Area, AreaSection, Frame, FrameSection, JointLoad, LoadCombination,
    DesignCodeSettings, Diaphragm, LoadPattern, MassSource,
    Material, Node, Story, entity_dict,
)


class ProjectModel:
    FORMAT_VERSION = 2

    def __init__(self) -> None:
        self.x_grids: list[float] = [0.0, 5.0, 10.0, 15.0]
        self.y_grids: list[float] = [0.0, 5.0, 10.0, 15.0]
        self.stories: dict[int, Story] = {}
        self.materials: dict[str, Material] = {}
        self.frame_sections: dict[str, FrameSection] = {}
        self.area_sections: dict[str, AreaSection] = {}
        self.nodes: dict[int, Node] = {}
        self.frames: dict[int, Frame] = {}
        self.areas: dict[int, Area] = {}
        self.joint_loads: list[JointLoad] = []
        self.load_patterns: dict[str, LoadPattern] = {}
        self.load_combinations: dict[str, LoadCombination] = {}
        self.mass_source = MassSource()
        self.design_codes = DesignCodeSettings()
        self.diaphragms: dict[str, Diaphragm] = {}
        self.active_story_id: int = 2
        self.dirty = False
        self._next_node = 1
        self._next_frame = 1
        self._next_area = 1

    @classmethod
    def default(cls) -> "ProjectModel":
        model = cls()
        for story in [
            Story(1, "Base", 0.0, 0.0),
            Story(2, "Story 1", 3.5, 3.5),
            Story(3, "Story 2", 7.0, 3.5),
            Story(4, "Roof", 10.5, 3.5),
        ]:
            model.stories[story.id] = story

        model.materials["Concrete C30"] = Material("Concrete C30")
        model.frame_sections["B300x600"] = FrameSection(
            "B300x600", "Concrete C30", 0.30, 0.60
        )
        model.frame_sections["C400x400"] = FrameSection(
            "C400x400", "Concrete C30", 0.40, 0.40
        )
        model.area_sections["S200"] = AreaSection(
            "S200", "Concrete C30", 0.20
        )
        model.load_patterns["DEAD"] = LoadPattern("DEAD", 1.0)
        model.load_patterns["LIVE"] = LoadPattern("LIVE", 0.0)
        model.generate_standard_combinations()
        return model

    def generate_standard_combinations(self) -> None:
        self.load_combinations = {
            "ULS 1.4D": LoadCombination("ULS 1.4D", {"DEAD": 1.4}),
            "ULS 1.2D+1.6L": LoadCombination(
                "ULS 1.2D+1.6L", {"DEAD": 1.2, "LIVE": 1.6}
            ),
            "SLS D+L": LoadCombination("SLS D+L", {"DEAD": 1.0, "LIVE": 1.0}),
        }

    def grid_center(self) -> tuple[float,float,float]:
        x=(
            min(self.x_grids)+max(self.x_grids)
        )/2.0 if self.x_grids else 0.0
        y=(
            min(self.y_grids)+max(self.y_grids)
        )/2.0 if self.y_grids else 0.0
        z=(
            min(s.elevation for s in self.stories.values())
            + max(s.elevation for s in self.stories.values())
        )/2.0 if self.stories else 0.0
        return float(x),float(y),float(z)

    @property
    def active_story(self) -> Story:
        return self.stories[self.active_story_id]

    def ordered_stories(self) -> list[Story]:
        return sorted(self.stories.values(), key=lambda s: s.elevation)

    def story_by_name(self, name: str) -> Story | None:
        return next((s for s in self.stories.values() if s.name == name), None)

    def lower_story(self, story_id: int) -> Story | None:
        current = self.stories[story_id]
        lower = [s for s in self.stories.values() if s.elevation < current.elevation]
        return max(lower, key=lambda s: s.elevation, default=None)

    def find_node(self, x: float, y: float, z: float, tolerance: float = 1e-8) -> Node | None:
        for node in self.nodes.values():
            if (
                abs(node.x-x) <= tolerance
                and abs(node.y-y) <= tolerance
                and abs(node.z-z) <= tolerance
            ):
                return node
        return None

    def get_or_create_node(self, x: float, y: float, z: float) -> Node:
        existing = self.find_node(x, y, z)
        if existing:
            return existing
        node = Node(self._next_node, float(x), float(y), float(z))
        self.nodes[node.id] = node
        self._next_node += 1
        self.dirty = True
        return node

    def add_frame(
        self,
        p1: tuple[float,float,float],
        p2: tuple[float,float,float],
        kind: str = "Beam",
        section: str | None = None,
    ) -> Frame:
        if sum((a-b)**2 for a,b in zip(p1,p2)) <= 1e-16:
            raise ValueError("Frame length must be greater than zero.")
        ni = self.get_or_create_node(*p1)
        nj = self.get_or_create_node(*p2)
        for frame in self.frames.values():
            if {frame.i, frame.j} == {ni.id, nj.id}:
                return frame
        if section is None:
            section = "C400x400" if kind == "Column" else "B300x600"
        if section not in self.frame_sections:
            raise ValueError(f"Undefined frame section: {section}")
        frame = Frame(self._next_frame, ni.id, nj.id, kind, section)
        self.frames[frame.id] = frame
        self._next_frame += 1
        self.dirty = True
        return frame

    def add_column(self, x: float, y: float, story_id: int) -> Frame:
        top = self.stories[story_id]
        bottom = self.lower_story(story_id)
        if bottom is None:
            raise ValueError("The active story has no lower story.")
        return self.add_frame(
            (x,y,bottom.elevation), (x,y,top.elevation),
            "Column", "C400x400",
        )

    def add_rect_area(
        self,
        p1: tuple[float,float,float],
        p2: tuple[float,float,float],
    ) -> Area:
        x1,y1,z1 = p1
        x2,y2,z2 = p2
        if abs(z1-z2)>1e-8 or abs(x1-x2)<1e-8 or abs(y1-y2)<1e-8:
            raise ValueError(
                "Select opposite corners of a non-zero rectangle on one story."
            )
        coords = [
            (min(x1,x2),min(y1,y2),z1),
            (max(x1,x2),min(y1,y2),z1),
            (max(x1,x2),max(y1,y2),z1),
            (min(x1,x2),max(y1,y2),z1),
        ]
        node_ids = tuple(self.get_or_create_node(*p).id for p in coords)
        for area in self.areas.values():
            if set(area.nodes)==set(node_ids):
                return area
        area = Area(self._next_area,node_ids)
        self.areas[area.id] = area
        self._next_area += 1
        self.dirty = True
        return area


    def subdivide_area(
        self,
        area_id: int,
        divisions_x: int,
        divisions_y: int,
    ) -> list[int]:
        """
        Replace one four-node slab with a conforming Q4 mesh.

        The original area section and surface loads are copied to every
        generated element. Bilinear interpolation supports rectangular and
        general convex quadrilateral slabs.
        """
        if area_id not in self.areas:
            raise ValueError(f"Undefined area object: A{area_id}")
        nx=int(divisions_x)
        ny=int(divisions_y)
        if nx<1 or ny<1:
            raise ValueError("Mesh divisions must be at least 1 x 1.")
        if nx==1 and ny==1:
            return [area_id]

        original=self.areas[area_id]
        corners=[
            self.nodes[node_id] for node_id in original.nodes
        ]
        points=np.array([
            [node.x,node.y,node.z] for node in corners
        ],dtype=float)

        node_grid=[]
        for j in range(ny+1):
            eta=-1.0+2.0*j/ny
            row=[]
            for i in range(nx+1):
                xi=-1.0+2.0*i/nx
                shape=0.25*np.array([
                    (1-xi)*(1-eta),
                    (1+xi)*(1-eta),
                    (1+xi)*(1+eta),
                    (1-xi)*(1+eta),
                ])
                point=shape@points
                row.append(
                    self.get_or_create_node(
                        float(point[0]),float(point[1]),float(point[2])
                    ).id
                )
            node_grid.append(row)

        self.areas.pop(area_id)
        generated=[]
        for j in range(ny):
            for i in range(nx):
                node_ids=(
                    node_grid[j][i],
                    node_grid[j][i+1],
                    node_grid[j+1][i+1],
                    node_grid[j+1][i],
                )
                area=Area(
                    self._next_area,node_ids,original.kind,
                    original.section,dict(original.surface_loads),
                )
                self.areas[area.id]=area
                generated.append(area.id)
                self._next_area+=1
        self.dirty=True
        return generated

    def assign_frame_rigid_offsets(
        self, frame_id: int, offset_i: float, offset_j: float,
    ) -> None:
        if frame_id not in self.frames:
            raise ValueError(f"Undefined frame F{frame_id}.")
        frame=self.frames[frame_id]
        ni=self.nodes[frame.i]; nj=self.nodes[frame.j]
        length=((nj.x-ni.x)**2+(nj.y-ni.y)**2+(nj.z-ni.z)**2)**0.5
        oi=float(offset_i); oj=float(offset_j)
        if oi < 0.0 or oj < 0.0:
            raise ValueError("Rigid offsets cannot be negative.")
        if oi+oj >= length-1.0e-8:
            raise ValueError("Rigid offsets must leave a positive deformable length.")
        frame.rigid_offset_i=oi
        frame.rigid_offset_j=oj
        self.dirty=True

    def assign_frame_releases(
        self,
        frame_id: int,
        release_i: tuple[bool,bool,bool,bool,bool,bool],
        release_j: tuple[bool,bool,bool,bool,bool,bool],
    ) -> None:
        if frame_id not in self.frames:
            raise ValueError(f"Undefined frame F{frame_id}.")
        self.frames[frame_id].release_i = tuple(bool(x) for x in release_i)
        self.frames[frame_id].release_j = tuple(bool(x) for x in release_j)
        self.dirty = True

    def assign_diaphragm(
        self,
        name: str,
        node_ids: list[int],
        rigid_ux: bool = True,
        rigid_uy: bool = True,
        rigid_rz: bool = True,
    ) -> None:
        clean = sorted({int(node_id) for node_id in node_ids})
        if len(clean) < 2:
            raise ValueError("A diaphragm requires at least two joints.")
        missing = [node_id for node_id in clean if node_id not in self.nodes]
        if missing:
            raise ValueError(f"Undefined diaphragm joints: {missing}")
        self.diaphragms[name] = Diaphragm(
            name, clean, rigid_ux, rigid_uy, rigid_rz
        )
        self.dirty = True

    def remove_diaphragm(self, name: str) -> None:
        self.diaphragms.pop(name, None)
        self.dirty = True

    def assign_joint_mass(
        self,
        node_id: int,
        values: tuple[float,float,float,float,float,float],
    ) -> None:
        self.nodes[node_id].mass = tuple(float(v) for v in values)
        self.dirty = True

    def assign_restraint(
        self,
        node_id: int,
        restraint: tuple[bool,bool,bool,bool,bool,bool],
    ) -> None:
        node = self.nodes[node_id]
        node.restraint = tuple(bool(x) for x in restraint)
        self.dirty = True

    def assign_fixed_base(self) -> int:
        if not self.stories:
            return 0
        base_z = min(s.elevation for s in self.stories.values())
        count = 0
        for node in self.nodes.values():
            if abs(node.z-base_z) <= 1e-8:
                node.restraint = (True,True,True,True,True,True)
                count += 1
        self.dirty = True
        return count

    def assign_area_surface_load(
        self,
        area_id: int,
        pattern: str,
        downward_pressure: float,
    ) -> None:
        if pattern not in self.load_patterns:
            raise ValueError(f"Undefined load pattern: {pattern}")
        if area_id not in self.areas:
            raise ValueError(f"Undefined area object: A{area_id}")
        self.areas[area_id].surface_loads[pattern] = float(
            downward_pressure
        )
        self.dirty = True

    def assign_area_section(
        self,
        area_id: int,
        section_name: str,
    ) -> None:
        if section_name not in self.area_sections:
            raise ValueError(f"Undefined area section: {section_name}")
        self.areas[area_id].section = section_name
        self.dirty = True

    def assign_frame_udl(
        self,
        frame_id: int,
        pattern: str,
        global_vector: tuple[float,float,float],
    ) -> None:
        if pattern not in self.load_patterns:
            raise ValueError(f"Undefined load pattern: {pattern}")
        self.frames[frame_id].distributed_loads[pattern] = tuple(
            float(v) for v in global_vector
        )
        self.dirty = True

    def add_joint_load(
        self,
        node_id: int,
        pattern: str,
        values: tuple[float,float,float,float,float,float],
    ) -> None:
        if pattern not in self.load_patterns:
            raise ValueError(f"Undefined load pattern: {pattern}")
        self.joint_loads.append(
            JointLoad(node_id, pattern, tuple(float(v) for v in values))
        )
        self.dirty = True

    def delete_objects(
        self,
        frame_ids: Iterable[int],
        area_ids: Iterable[int],
    ) -> None:
        for fid in list(frame_ids):
            self.frames.pop(fid, None)
        for aid in list(area_ids):
            self.areas.pop(aid, None)
        used = set()
        for frame in self.frames.values():
            used.update([frame.i,frame.j])
        for area in self.areas.values():
            used.update(area.nodes)
        self.nodes = {nid:n for nid,n in self.nodes.items() if nid in used}
        self.joint_loads = [
            load for load in self.joint_loads if load.node_id in self.nodes
        ]
        self.dirty = True

    def to_dict(self) -> dict:
        return {
            "format_version": self.FORMAT_VERSION,
            "x_grids": self.x_grids,
            "y_grids": self.y_grids,
            "active_story_id": self.active_story_id,
            "stories": [entity_dict(x) for x in self.stories.values()],
            "materials": [entity_dict(x) for x in self.materials.values()],
            "frame_sections": [
                entity_dict(x) for x in self.frame_sections.values()
            ],
            "area_sections": [
                entity_dict(x) for x in self.area_sections.values()
            ],
            "nodes": [entity_dict(x) for x in self.nodes.values()],
            "frames": [entity_dict(x) for x in self.frames.values()],
            "areas": [entity_dict(x) for x in self.areas.values()],
            "joint_loads": [entity_dict(x) for x in self.joint_loads],
            "load_patterns": [
                entity_dict(x) for x in self.load_patterns.values()
            ],
            "load_combinations": [
                entity_dict(x) for x in self.load_combinations.values()
            ],
            "mass_source": entity_dict(self.mass_source),
            "design_codes": entity_dict(self.design_codes),
            "diaphragms": [
                entity_dict(item) for item in self.diaphragms.values()
            ],
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(self.to_dict(), indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> "ProjectModel":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        model = cls()
        model.x_grids = [float(x) for x in raw["x_grids"]]
        model.y_grids = [float(y) for y in raw["y_grids"]]
        model.stories = {
            int(x["id"]): Story(**x) for x in raw["stories"]
        }

        defaults = cls.default()
        model.materials = {
            x["name"]: Material(**x)
            for x in raw.get(
                "materials",
                [entity_dict(v) for v in defaults.materials.values()],
            )
        }
        model.frame_sections = {
            x["name"]: FrameSection(**x)
            for x in raw.get(
                "frame_sections",
                [entity_dict(v) for v in defaults.frame_sections.values()],
            )
        }
        model.area_sections = {
            x["name"]: AreaSection(**x)
            for x in raw.get(
                "area_sections",
                [entity_dict(v) for v in defaults.area_sections.values()],
            )
        }

        model.nodes = {
            int(x["id"]): Node(
                **{
                    **x,
                    "restraint": tuple(x.get("restraint", (False,)*6)),
                    "mass": tuple(x.get("mass", (0.0,)*6)),
                }
            )
            for x in raw.get("nodes",[])
        }
        model.frames = {
            int(x["id"]): Frame(**{
                **x,
                "release_i": tuple(x.get("release_i", (False,)*6)),
                "release_j": tuple(x.get("release_j", (False,)*6)),
                "rigid_offset_i": float(x.get("rigid_offset_i",0.0)),
                "rigid_offset_j": float(x.get("rigid_offset_j",0.0)),
            }) for x in raw.get("frames",[])
        }
        model.areas = {
            int(x["id"]): Area(**{**x,"nodes":tuple(x["nodes"])})
            for x in raw.get("areas",[])
        }
        model.joint_loads = [
            JointLoad(**{**x, "values":tuple(x["values"])})
            for x in raw.get("joint_loads",[])
        ]
        model.load_patterns = {
            x["name"]: LoadPattern(**x)
            for x in raw.get(
                "load_patterns",
                [entity_dict(v) for v in defaults.load_patterns.values()],
            )
        }
        model.mass_source = MassSource(
            **raw.get("mass_source", entity_dict(defaults.mass_source))
        )
        model.design_codes = DesignCodeSettings(
            **raw.get("design_codes", entity_dict(defaults.design_codes))
        )
        model.diaphragms = {
            item["name"]: Diaphragm(**item)
            for item in raw.get("diaphragms", [])
        }
        model.load_combinations = {
            x["name"]: LoadCombination(**x)
            for x in raw.get(
                "load_combinations",
                [entity_dict(v) for v in defaults.load_combinations.values()],
            )
        }

        model.active_story_id = int(
            raw.get("active_story_id", min(model.stories))
        )
        model._next_node = max(model.nodes,default=0)+1
        model._next_frame = max(model.frames,default=0)+1
        model._next_area = max(model.areas,default=0)+1
        model.dirty = False
        return model
