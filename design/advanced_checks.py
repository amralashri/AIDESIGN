from __future__ import annotations
from dataclasses import dataclass, field
from math import ceil, pi, sqrt
import numpy as np
from analysis.results import AnalysisResult
from design.concrete import design_concrete, ConcreteDesignResult
from model.project import ProjectModel

@dataclass(slots=True)
class BeamCheck:
    frame_id:int; shear_kn:float; stirrup_spacing_mm:float; torsion_knm:float; torsion_status:str
    development_length_mm:float; deflection_mm:float; limit_mm:float; status:str

@dataclass(slots=True)
class ColumnCheck:
    frame_id:int; axial_kn:float; moment_knm:float; ratio:float; required_as_mm2:float; bars:int; status:str

@dataclass(slots=True)
class SlabCheck:
    area_id:int; punching_ratio:float; punching_status:str; short_mm:float; long_mm:float; limit_mm:float
    service_status:str; top_x:str; top_y:str; bottom_x:str; bottom_y:str

@dataclass(slots=True)
class AdvancedDesignResult:
    base:ConcreteDesignResult
    beams:dict[int,BeamCheck]=field(default_factory=dict)
    columns:dict[int,ColumnCheck]=field(default_factory=dict)
    slabs:dict[int,SlabCheck]=field(default_factory=dict)
    warnings:list[str]=field(default_factory=list)

def _bar_area(db): return pi*db*db/4.0

def _stirrup_spacing(vu,b,d,fc=30.0,fy=420.0,db=10.0):
    dmm=max(d*1000-60,50); vc=0.17*sqrt(fc)*b*1000*dmm/1000
    vs=max(abs(vu)/0.75-vc,0); av=2*_bar_area(db)
    s=300.0 if vs<=1e-9 else av*fy*dmm/(vs*1000)
    return float(np.clip(s,75,300))

def _development(db=20.0,fy=420.0,fc=30.0): return max(300.0,0.90*db*fy/max(sqrt(fc),1e-9))

def _column_pm(pu,mu,b,h,fc=30.0,fy=420.0,db=20.0):
    ag=b*h*1e6; pcap=0.35*fc*ag/1000; pr=abs(pu)/max(pcap,1e-9)
    d=max(h-0.06,0.05); asmin=0.01*ag; asm=abs(mu)/max(0.9*fy*1000*0.8*d,1e-9)*1e6
    req=max(asmin,asm); bars=max(4,int(ceil(req/_bar_area(db)))); bars += bars%2
    mcap=bars*_bar_area(db)/1e6*fy*1000*0.8*d; ratio=pr+abs(mu)/max(mcap,1e-9)
    return req,bars,ratio,"OK" if ratio<=1 else "NG"

def _punching(project,result,aid,fc=30.0):
    area=project.areas[aid]; ar=result.area_results[aid]; d=max(ar.thickness-0.031,0.05)
    demand=max((abs(float(result.node_reaction(n)[2])) for n in area.nodes if any(project.nodes[n].restraint)),default=0.0)
    if demand<=1e-9: return 0.0,"N/A"
    u=4*(0.40+d); cap=0.75*0.33*sqrt(fc)*u*1000*d*1000/1000; r=demand/max(cap,1e-9)
    return r,"OK" if r<=1 else "NG"

def run_advanced_design(project:ProjectModel,result:AnalysisResult)->AdvancedDesignResult:
    base=design_concrete(project,result); out=AdvancedDesignResult(base)
    for fr in project.frames.values():
        if fr.id not in result.frame_results: continue
        sec=project.frame_sections.get(fr.section)
        if not sec: continue
        f=result.frame_results[fr.id].local_end_forces
        pu=max(abs(f[0]),abs(f[6])); vu=max(abs(f[1]),abs(f[2]),abs(f[7]),abs(f[8]))
        tu=max(abs(f[3]),abs(f[9])); mu=max(abs(f[4]),abs(f[5]),abs(f[10]),abs(f[11]))
        if fr.kind=="Column":
            req,bars,ratio,status=_column_pm(pu,mu,sec.width,sec.depth)
            out.columns[fr.id]=ColumnCheck(fr.id,pu,mu,ratio,req,bars,status); continue
        ni,nj=project.nodes[fr.i],project.nodes[fr.j]; L=sqrt((nj.x-ni.x)**2+(nj.y-ni.y)**2+(nj.z-ni.z)**2)
        u=result.node_displacement(fr.i)[:3]; v=result.node_displacement(fr.j)[:3]; df=float(np.linalg.norm(v-u)*1000); lim=L*1000/250
        out.beams[fr.id]=BeamCheck(fr.id,vu,_stirrup_spacing(vu,sec.width,sec.depth),tu,
            "DESIGN REQUIRED" if tu>0.25*max(mu,1e-9) else "MINIMUM",_development(),df,lim,"OK" if df<=lim else "NG")
    for area in project.areas.values():
        if area.id not in result.area_results or area.id not in base.slabs: continue
        ar=result.area_results[area.id]; bs=base.slabs[area.id]
        st=max(abs(ar.local_displacements[6*i+2])*1000 for i in range(4)); lt=2*st
        ns=[project.nodes[n] for n in area.nodes]; span=max(max(n.x for n in ns)-min(n.x for n in ns),max(n.y for n in ns)-min(n.y for n in ns)); lim=span*1000/250
        ratio,pstatus=_punching(project,result,area.id)
        out.slabs[area.id]=SlabCheck(area.id,ratio,pstatus,st,lt,lim,"OK" if lt<=lim else "NG",
            bs.label_x,bs.label_y,bs.label_x,bs.label_y)
    out.warnings=["Expanded preliminary checks only; not a certified code design.",
        "Punching assumes a 400 mm column and ignores opening reductions.",
        "Column P-M is simplified and not a full biaxial interaction surface.",
        "Seismic detailing, anchorage, crack width and long-term effects require project-specific review.",
        "Independent engineering verification is mandatory."]
    return out
