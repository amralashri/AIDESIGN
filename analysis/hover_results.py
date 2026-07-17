from dataclasses import dataclass
import numpy as np
from analysis.postprocessing import dominant_curve
from fem.shell4 import shell_value_at_local_point

@dataclass(slots=True)
class ResultTip:
    title:str
    lines:list[str]
    def html(self):
        return f"<b>{self.title}</b><br>"+"<br>".join(self.lines)

def frame_result_tip(project,result,units,frame_id,mode,ratio):
    if frame_id not in result.frame_results:return None
    stations,values,component=dominant_curve(result,frame_id,mode)
    x=float(np.clip(ratio,0,1))*result.frame_results[frame_id].length
    value=float(np.interp(x,stations,values))
    formatted=units.moment_component(value) if mode in ("Moment","Torsion") else units.force_component(value)
    return ResultTip(f"Frame F{frame_id} — {mode}",[
        f"Component: {component}",f"Station: {units.format(x,'length')}",
        f"Value: <b>{formatted}</b>",f"Case: {result.case_name}"
    ])

def reaction_tip(result,units,node_id):
    r=result.node_reaction(node_id)
    return ResultTip(f"Joint N{node_id} — Reaction",[
        f"Fx: {units.force_component(r[0])}",f"Fy: {units.force_component(r[1])}",
        f"Fz: {units.force_component(r[2])}",f"Mx: {units.moment_component(r[3])}",
        f"My: {units.moment_component(r[4])}",f"Mz: {units.moment_component(r[5])}"
    ])

def displacement_tip(result,units,node_id):
    u=result.node_displacement(node_id)
    return ResultTip(f"Joint N{node_id} — Displacement",[
        f"Ux: {units.displacement_component(u[0])}",
        f"Uy: {units.displacement_component(u[1])}",
        f"Uz: {units.displacement_component(u[2])}"
    ])


def shell_tip(project,result,units,area_id,mode,x,y):
    if area_id not in result.area_results:
        return None
    key={"Slab Mx":"Mx","Slab My":"My","Slab Mxy":"Mxy",
         "Slab Mmax":"Mmax","Slab Mmin":"Mmin","Slab Qx":"Qx",
         "Slab Qy":"Qy","Slab Deflection":"w"}.get(mode)
    if not key:
        return None
    area=project.areas[area_id]
    ar=result.area_results[area_id]
    origin_node=project.nodes[area.nodes[0]]
    origin=np.array([origin_node.x,origin_node.y,origin_node.z],dtype=float)
    point=np.array([x,y,origin_node.z],dtype=float)
    relative=point-origin
    ex,ey,_=ar.rotation
    local_point=np.array([
        float(np.dot(relative,ex)),
        float(np.dot(relative,ey)),
    ])
    value=shell_value_at_local_point(
        ar.local_displacements,ar.elastic_modulus,
        ar.poisson_ratio,ar.thickness,ar.local_xy,
        local_point,key,
    )
    formatted=(
        units.displacement_component(value)
        if key=="w"
        else units.shell_result(key,value)
    )
    return ResultTip(f"Slab A{area_id} — {key}",[
        f"Value: <b>{formatted}</b>",
        f"X: {units.format(x,'length')}",
        f"Y: {units.format(y,'length')}",
        f"Case: {result.case_name}"
    ])
