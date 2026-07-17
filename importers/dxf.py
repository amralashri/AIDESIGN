
from __future__ import annotations

from dataclasses import dataclass,field
from pathlib import Path

from model.project import ProjectModel


@dataclass(slots=True)
class DXFImportReport:
    beams:int=0
    slabs:int=0
    skipped:int=0
    warnings:list[str]=field(default_factory=list)


def import_dxf(
    project:ProjectModel,
    filename:str|Path,
    story_id:int,
    scale_to_m:float=1.0,
    import_closed_polylines_as_slabs:bool=True,
) -> DXFImportReport:
    try:
        import ezdxf
    except ImportError as exc:
        raise RuntimeError(
            "DXF import requires ezdxf. Run install.bat or "
            "py -m pip install ezdxf."
        ) from exc

    document=ezdxf.readfile(str(filename))
    modelspace=document.modelspace()
    z=project.stories[story_id].elevation
    report=DXFImportReport()

    def point(v):
        return (
            float(v[0])*scale_to_m,
            float(v[1])*scale_to_m,
            z,
        )

    for entity in modelspace:
        kind=entity.dxftype()
        try:
            if kind=="LINE":
                project.add_frame(
                    point(entity.dxf.start),
                    point(entity.dxf.end),
                    "Beam","B300x600",
                )
                report.beams+=1
            elif kind in ("LWPOLYLINE","POLYLINE"):
                if kind=="LWPOLYLINE":
                    vertices=[
                        (float(x)*scale_to_m,float(y)*scale_to_m,z)
                        for x,y,*_ in entity.get_points()
                    ]
                    closed=bool(entity.closed)
                else:
                    vertices=[
                        point(vertex.dxf.location)
                        for vertex in entity.vertices
                    ]
                    closed=bool(entity.is_closed)
                if len(vertices)<2:
                    report.skipped+=1
                    continue
                if closed and import_closed_polylines_as_slabs and len(vertices)==4:
                    nodes=tuple(
                        project.get_or_create_node(*v).id
                        for v in vertices
                    )
                    from model.entities import Area
                    area=Area(project._next_area,nodes)
                    project.areas[area.id]=area
                    project._next_area+=1
                    project.dirty=True
                    report.slabs+=1
                else:
                    pairs=list(zip(vertices,vertices[1:]))
                    if closed:
                        pairs.append((vertices[-1],vertices[0]))
                    for a,b in pairs:
                        project.add_frame(a,b,"Beam","B300x600")
                        report.beams+=1
            else:
                report.skipped+=1
        except Exception as exc:
            report.skipped+=1
            report.warnings.append(f"{kind}: {exc}")
    return report
