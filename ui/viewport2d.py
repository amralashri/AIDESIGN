from __future__ import annotations

import numpy as np
from math import floor, ceil, hypot
from PySide6.QtCore import QPointF,QRectF,Qt,Signal
from PySide6.QtGui import QColor,QMouseEvent,QPainter,QPainterPath,QPen,QBrush,QWheelEvent
from PySide6.QtWidgets import QToolTip,QWidget
from graphics.geometry import point_in_polygon, point_segment_distance
from graphics.snap import SnapEngine,SnapResult
from analysis.postprocessing import (
    automatic_deformation_scale, deformed_node_positions, dominant_curve,
)
from analysis.results import AnalysisResult
from analysis.contours import (
    area_contour_samples, contour_range, jet_rgb,
)
from design.concrete import ConcreteDesignResult
from model.project import ProjectModel
from core.units import UnitSystem
from analysis.hover_results import displacement_tip,frame_result_tip,reaction_tip,shell_tip


class PlanViewport(QWidget):
    cursor_world_changed=Signal(float,float,float,str)
    selection_changed=Signal(str,int)
    model_changed=Signal()

    def __init__(self,project:ProjectModel,parent=None):
        super().__init__(parent); self.project=project; self.setMouseTracking(True); self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.zoom=55.0; self.origin=QPointF(110.0, self.height()-100.0); self.mode="Select"; self.snap_enabled=True; self.ortho=False
        self.snap_engine=SnapEngine(14); self.hover_kind=None; self.hover_id=None; self.selected_frames=set(); self.selected_areas=set()
        self.drag_start=None; self.drag_current=None; self.pan_active=False; self.pan_last=None; self.current_snap=None
        self.analysis_result: AnalysisResult | None = None
        self.result_mode = "None"
        self.concrete_design_result: ConcreteDesignResult | None = None
        self.unit_system=UnitSystem(self)
        self._last_tip_key=None
        self.modal_result=None
        self.modal_mode_number=1
        self._initial_grid_fit=False
        self.show_node_labels=False
        self.show_frame_labels=True
        self.show_nodes=True
        self.selection_start_screen=None
        self.selection_current_screen=None
        self.selection_dragging=False
    def set_project(self,p):
        self.project=p
        self.analysis_result=None
        self.result_mode="None"
        self.modal_result=None
        self.clear_selection()
        self._initial_grid_fit=False
        self.show_node_labels=False
        self.show_frame_labels=True
        self.show_nodes=True
        self.selection_start_screen=None
        self.selection_current_screen=None
        self.selection_dragging=False
        self.fit_view()

    def showEvent(self,event):
        super().showEvent(event)
        if not self._initial_grid_fit:
            self._initial_grid_fit=True
            self.fit_view()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if not self._initial_grid_fit and self.isVisible():
            self._initial_grid_fit=True
            self.fit_view()

    def set_analysis_result(self,result):
        self.analysis_result=result
        self.update()

    def set_result_mode(self,mode):
        self.result_mode=mode
        self.update()

    def set_concrete_design_result(self,result):
        self.concrete_design_result=result
        self.update()
    def set_modal_result(self,result,mode_number=1):
        self.modal_result=result
        self.modal_mode_number=mode_number
        self.update()

    def set_unit_system(self,unit_system):
        self.unit_system=unit_system
        self.unit_system.changed.connect(self.update)
        self.update()
    def set_mode(self,mode): self.mode=mode; self.drag_start=None; self.drag_current=None; self.update()
    def clear_selection(self): self.selected_frames.clear(); self.selected_areas.clear(); self.hover_kind=self.hover_id=None; self.update()
    def world_to_screen(self,x,y): return QPointF(self.origin.x()+x*self.zoom,self.origin.y()-y*self.zoom)
    def screen_to_world(self,p): return ((p.x()-self.origin.x())/self.zoom,(self.origin.y()-p.y())/self.zoom)
    def active_z(self): return self.project.active_story.elevation
    def visible_endpoints(self):
        z=self.active_z(); result=[]
        for n in self.project.nodes.values():
            if abs(n.z-z)<1e-8: result.append((n.x,n.y))
        return result
    def visible_midpoints(self):
        z=self.active_z(); result=[]
        for f in self.project.frames.values():
            a=self.project.nodes[f.i]; b=self.project.nodes[f.j]
            if abs(a.z-z)<1e-8 and abs(b.z-z)<1e-8: result.append(((a.x+b.x)/2,(a.y+b.y)/2))
        return result
    def snap_world(self,x,y,modifiers=Qt.KeyboardModifier.NoModifier):
        if not self.snap_enabled: return x,y,None
        snap=self.snap_engine.find(x,y,self.zoom,self.project.x_grids,self.project.y_grids,self.visible_endpoints(),self.visible_midpoints())
        if snap: return snap.x,snap.y,snap
        return x,y,None
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.fillRect(self.rect(),QColor("#ffffff"))
        self._draw_minor_grid(p); self._draw_axis_grid(p); self._draw_areas(p); self._draw_frames(p); self._draw_results(p); self._draw_mode_shape(p); self._draw_nodes(p); self._draw_preview(p); self._draw_selection_window(p); self._draw_snap(p)
        p.setPen(QColor("#555")); p.drawText(
            10,20,
            f"Plan View - {self.project.active_story.name}   "
            f"Z={self.unit_system.format(self.active_z(),'length')}   Result: {self.result_mode}"
        )
    def _visible_world_bounds(self):
        x0,y1=self.screen_to_world(QPointF(0,0)); x1,y0=self.screen_to_world(QPointF(self.width(),self.height())); return min(x0,x1),max(x0,x1),min(y0,y1),max(y0,y1)
    def _draw_minor_grid(self,p):
        xmin,xmax,ymin,ymax=self._visible_world_bounds(); spacing=1.0
        while spacing*self.zoom<18: spacing*=2
        p.setPen(QPen(QColor("#eeeeee"),1))
        for i in range(floor(xmin/spacing),ceil(xmax/spacing)+1):
            x=self.world_to_screen(i*spacing,0).x(); p.drawLine(int(x),0,int(x),self.height())
        for j in range(floor(ymin/spacing),ceil(ymax/spacing)+1):
            y=self.world_to_screen(0,j*spacing).y(); p.drawLine(0,int(y),self.width(),int(y))
    def _draw_axis_grid(self,p):
        p.setPen(QPen(QColor("#9bbdd7"),1,Qt.PenStyle.DashLine)); ymin=min(self.project.y_grids)-1; ymax=max(self.project.y_grids)+1; xmin=min(self.project.x_grids)-1; xmax=max(self.project.x_grids)+1
        for i,x in enumerate(self.project.x_grids):
            a=self.world_to_screen(x,ymin); b=self.world_to_screen(x,ymax); p.drawLine(a,b); p.setPen(QColor("#245b83")); p.drawText(int(b.x()-4),int(b.y()-8),chr(65+i)); p.setPen(QPen(QColor("#9bbdd7"),1,Qt.PenStyle.DashLine))
        for i,y in enumerate(self.project.y_grids):
            a=self.world_to_screen(xmin,y); b=self.world_to_screen(xmax,y); p.drawLine(a,b); p.setPen(QColor("#245b83")); p.drawText(int(a.x()-18),int(a.y()+4),str(i+1)); p.setPen(QPen(QColor("#9bbdd7"),1,Qt.PenStyle.DashLine))
    def _draw_areas(self,p):
        z=self.active_z()
        for a in self.project.areas.values():
            pts=[self.project.nodes[n] for n in a.nodes]
            if not all(abs(n.z-z)<1e-8 for n in pts): continue
            path=QPainterPath(); q=[self.world_to_screen(n.x,n.y) for n in pts]; path.moveTo(q[0]); [path.lineTo(x) for x in q[1:]]; path.closeSubpath()
            selected=a.id in self.selected_areas; hover=self.hover_kind=="Area" and self.hover_id==a.id
            p.setPen(QPen(QColor("#ff8c00" if selected else "#2d6fa3"),3 if selected else 1)); p.setBrush(QBrush(QColor(180,220,245,150 if hover else 95))); p.drawPath(path)
            c=QPointF(sum(x.x() for x in q)/4,sum(x.y() for x in q)/4); p.setPen(QColor("#315b7d")); p.drawText(c,f"A{a.id}")
    def _draw_frames(self,p):
        z=self.active_z()
        for f in self.project.frames.values():
            a=self.project.nodes[f.i]; b=self.project.nodes[f.j]
            horizontal=abs(a.z-z)<1e-8 and abs(b.z-z)<1e-8; column=f.kind=="Column" and min(a.z,b.z)<z<=max(a.z,b.z)
            selected=f.id in self.selected_frames; hover=self.hover_kind=="Frame" and self.hover_id==f.id
            if horizontal:
                color="#ff8c00" if selected else ("#00a6b2" if f.kind=="Brace" else "#006dcc")
                pen=QPen(QColor(color),5 if selected else (4 if hover else 3)); pen.setCapStyle(Qt.PenCapStyle.RoundCap); p.setPen(pen); p.drawLine(self.world_to_screen(a.x,a.y),self.world_to_screen(b.x,b.y))
                if self.show_frame_labels:
                    mid=self.world_to_screen((a.x+b.x)/2,(a.y+b.y)/2)
                    p.setPen(QColor("#333"))
                    p.drawText(mid+QPointF(4,-4),f"F{f.id}")
            elif column:
                c=self.world_to_screen(a.x,a.y); size=max(7,int(.4*self.zoom)); p.setPen(QPen(QColor("#ff8c00" if selected else "#8e2ca8"),3 if selected else 1)); p.setBrush(QColor("#c84bd8")); p.drawRect(int(c.x()-size/2),int(c.y()-size/2),size,size)
    def _draw_results(self,p):
        if self.analysis_result is None or self.result_mode=="None":
            return
        z=self.active_z()

        if self.result_mode in ("Slab As X","Slab As Y"):
            self._draw_design_contours(p,z)
            return
        if self.result_mode.startswith("Slab ") and self.result_mode not in (
            "Slab Rebar X","Slab Rebar Y","Slab As X","Slab As Y"
        ):
            self._draw_slab_contours(p,z)
            return

        if self.result_mode in (
            "Beam Rebar","Slab Rebar X","Slab Rebar Y"
        ):
            self._draw_reinforcement(p,z)
            return

        if self.result_mode=="Deformed":
            scale=automatic_deformation_scale(
                self.project,self.analysis_result
            )
            positions=deformed_node_positions(
                self.project,self.analysis_result,scale
            )
            p.setPen(QPen(
                QColor("#d62728"),2,Qt.PenStyle.DashLine
            ))
            for frame in self.project.frames.values():
                ni=self.project.nodes[frame.i]
                nj=self.project.nodes[frame.j]
                if abs(ni.z-z)<1e-8 and abs(nj.z-z)<1e-8:
                    a=positions[frame.i]
                    b=positions[frame.j]
                    p.drawLine(
                        self.world_to_screen(a[0],a[1]),
                        self.world_to_screen(b[0],b[1]),
                    )
            return

        if self.result_mode=="Reactions":
            p.setPen(QPen(QColor("#008000"),2))
            for node_id,node in self.project.nodes.items():
                if abs(node.z-z)>1e-8 or not any(node.restraint):
                    continue
                reaction=self.analysis_result.node_reaction(node_id)
                base=self.world_to_screen(node.x,node.y)
                fx,fy,fz=reaction[:3]
                horizontal=max((fx*fx+fy*fy)**0.5,1e-12)
                arrow_scale=35.0/max(
                    horizontal,
                    max(abs(self.analysis_result.node_reaction(nid)[:2]).max()
                        if any(self.project.nodes[nid].restraint) else 0.0
                        for nid in self.analysis_result.node_order),
                    1e-12,
                )
                end=base+QPointF(
                    fx*arrow_scale,-fy*arrow_scale
                )
                p.drawLine(base,end)
                p.drawText(
                    base+QPointF(6,-8),
                    f"Rz={fz:.2f}",
                )
            return

        if self.result_mode not in (
            "Moment","Shear","Axial","Torsion"
        ):
            return

        visible=[]
        all_values=[]
        for frame in self.project.frames.values():
            ni=self.project.nodes[frame.i]
            nj=self.project.nodes[frame.j]
            if not (
                abs(ni.z-z)<1e-8
                and abs(nj.z-z)<1e-8
                and frame.id in self.analysis_result.frame_results
            ):
                continue
            stations,values,label=dominant_curve(
                self.analysis_result,
                frame.id,
                self.result_mode,
            )
            visible.append(
                (frame,ni,nj,stations,values,label)
            )
            all_values.extend(abs(value) for value in values)

        global_max=max(all_values,default=1.0)
        diagram_pixels=55.0
        color=QColor(
            "#d62728" if self.result_mode=="Moment"
            else "#2ca02c" if self.result_mode=="Shear"
            else "#9467bd"
        )

        for frame,ni,nj,stations,values,label in visible:
            dx=nj.x-ni.x
            dy=nj.y-ni.y
            length=max((dx*dx+dy*dy)**0.5,1e-12)
            nx=-dy/length
            ny=dx/length
            base=[]
            curve=[]
            for station,value in zip(stations,values):
                ratio=station/max(
                    self.analysis_result.frame_results[
                        frame.id
                    ].length,1e-12
                )
                x=ni.x+ratio*dx
                y=ni.y+ratio*dy
                base_point=self.world_to_screen(x,y)
                offset=value/global_max*diagram_pixels
                curve_point=base_point+QPointF(
                    nx*offset,-ny*offset
                )
                base.append(base_point)
                curve.append(curve_point)

            p.setPen(QPen(color,2))
            for index in range(len(curve)-1):
                p.drawLine(curve[index],curve[index+1])
            p.setPen(QPen(QColor(
                color.red(),color.green(),color.blue(),100
            ),1))
            for index in range(0,len(curve),5):
                p.drawLine(base[index],curve[index])

            peak=max(
                range(len(values)),
                key=lambda index:abs(values[index]),
            )
            p.setPen(QPen(color,1))
            p.drawText(
                curve[peak]+QPointF(4,-4),
                f"{values[peak]:.3f}",
            )

    def _draw_slab_contours(self,p,z):
        if self.analysis_result is None:
            return
        minimum,maximum=contour_range(
            self.project,self.analysis_result,self.result_mode
        )
        for area in self.project.areas.values():
            nodes=[self.project.nodes[nid] for nid in area.nodes]
            if not all(abs(node.z-z)<1e-8 for node in nodes):
                continue
            samples=area_contour_samples(
                self.project,self.analysis_result,
                area.id,self.result_mode,9
            )
            if not samples:
                continue
            # Colored sample cells.
            points=np.array([
                [s["global"][0],s["global"][1]] for s in samples
            ])
            divisions=int(round(len(samples)**0.5))
            for j in range(divisions-1):
                for i in range(divisions-1):
                    ids=[
                        j*divisions+i,
                        j*divisions+i+1,
                        (j+1)*divisions+i+1,
                        (j+1)*divisions+i,
                    ]
                    value=sum(samples[k]["value"] for k in ids)/4.0
                    rgb=jet_rgb(value,minimum,maximum)
                    polygon=QPolygonF([
                        self.world_to_screen(
                            points[k,0],points[k,1]
                        ) for k in ids
                    ])
                    p.setPen(QPen(QColor(*rgb),1))
                    p.setBrush(QColor(*rgb,190))
                    p.drawPolygon(polygon)

            # Contour isolines by quantized crossings on sample grid.
            levels=np.linspace(minimum,maximum,9)[1:-1]
            p.setPen(QPen(QColor(30,30,30,150),1))
            for level in levels:
                for j in range(divisions):
                    row=samples[j*divisions:(j+1)*divisions]
                    for a,b in zip(row[:-1],row[1:]):
                        if (a["value"]-level)*(b["value"]-level)<=0:
                            denom=b["value"]-a["value"]
                            t=0.5 if abs(denom)<1e-12 else (
                                level-a["value"]
                            )/denom
                            x=a["global"][0]+t*(
                                b["global"][0]-a["global"][0]
                            )
                            y=a["global"][1]+t*(
                                b["global"][1]-a["global"][1]
                            )
                            q=self.world_to_screen(x,y)
                            p.drawEllipse(q,1.5,1.5)

        self._draw_contour_legend(p,minimum,maximum)

    def _draw_contour_legend(self,p,minimum,maximum):
        x=self.width()-70
        top=55
        height=190
        steps=40
        for i in range(steps):
            ratio=i/(steps-1)
            value=maximum-ratio*(maximum-minimum)
            rgb=jet_rgb(value,minimum,maximum)
            p.fillRect(
                x,top+i*height/steps,20,height/steps+1,
                QColor(*rgb)
            )
        p.setPen(QColor("#222"))
        p.drawRect(x,top,20,height)
        p.drawText(x-5,top-6,f"{maximum:.3f}")
        p.drawText(x-5,top+height+16,f"{minimum:.3f}")
        p.drawText(x-30,top+height+34,self.result_mode)


    def _draw_design_contours(self,p,z):
        if self.concrete_design_result is None:
            return
        values=[]
        for design in self.concrete_design_result.slabs.values():
            values.append(
                design.as_x_mm2_per_m if self.result_mode=="Slab As X"
                else design.as_y_mm2_per_m
            )
        if not values:
            return
        minimum=min(values); maximum=max(values)
        if abs(maximum-minimum)<1e-9:
            minimum=0.0
            maximum=max(maximum,1.0)
        for area_id,design in self.concrete_design_result.slabs.items():
            area=self.project.areas.get(area_id)
            if area is None: continue
            nodes=[self.project.nodes[nid] for nid in area.nodes]
            if not all(abs(node.z-z)<1e-8 for node in nodes): continue
            value=(design.as_x_mm2_per_m if self.result_mode=="Slab As X"
                   else design.as_y_mm2_per_m)
            rgb=jet_rgb(value,minimum,maximum)
            polygon=QPolygonF([self.world_to_screen(n.x,n.y) for n in nodes])
            p.setPen(QPen(QColor(*rgb),1.5))
            p.setBrush(QColor(*rgb,195))
            p.drawPolygon(polygon)
            center=QPointF(
                sum(self.world_to_screen(n.x,n.y).x() for n in nodes)/4,
                sum(self.world_to_screen(n.x,n.y).y() for n in nodes)/4,
            )
            p.setPen(QColor("#111111"))
            p.drawText(center+QPointF(4,-4),f"As={value:.0f} mm²/m")
        self._draw_contour_legend(p,minimum,maximum)

    def _draw_reinforcement(self,p,z):
        if self.concrete_design_result is None:
            return
        if self.result_mode=="Beam Rebar":
            p.setPen(QPen(QColor("#b00020"),3))
            for frame_id,design in self.concrete_design_result.beams.items():
                frame=self.project.frames.get(frame_id)
                if frame is None:
                    continue
                ni=self.project.nodes[frame.i]
                nj=self.project.nodes[frame.j]
                if not (
                    abs(ni.z-z)<1e-8 and abs(nj.z-z)<1e-8
                ):
                    continue
                a=self.world_to_screen(ni.x,ni.y)
                b=self.world_to_screen(nj.x,nj.y)
                p.drawLine(a,b)
                p.drawText(
                    (a+b)/2+QPointF(5,-8),design.label
                )
            return

        p.setPen(QPen(QColor("#8b0000"),1.5))
        for area_id,design in self.concrete_design_result.slabs.items():
            area=self.project.areas.get(area_id)
            if area is None:
                continue
            nodes=[self.project.nodes[nid] for nid in area.nodes]
            if not all(abs(node.z-z)<1e-8 for node in nodes):
                continue
            xs=[n.x for n in nodes]
            ys=[n.y for n in nodes]
            xmin,xmax=min(xs),max(xs)
            ymin,ymax=min(ys),max(ys)
            if self.result_mode=="Slab Rebar X":
                spacing=max(design.spacing_x_mm/1000.0,0.05)
                y=ymin+spacing/2
                while y<ymax:
                    p.drawLine(
                        self.world_to_screen(xmin,y),
                        self.world_to_screen(xmax,y),
                    )
                    y+=spacing
                label=design.label_x
            else:
                spacing=max(design.spacing_y_mm/1000.0,0.05)
                x=xmin+spacing/2
                while x<xmax:
                    p.drawLine(
                        self.world_to_screen(x,ymin),
                        self.world_to_screen(x,ymax),
                    )
                    x+=spacing
                label=design.label_y
            center=self.world_to_screen(
                (xmin+xmax)/2,(ymin+ymax)/2
            )
            p.drawText(center+QPointF(5,-5),label)

    def _draw_mode_shape(self,p):
        if self.modal_result is None:
            return
        z=self.active_z()
        mode=self.modal_result.modes[self.modal_mode_number-1]
        values=[]
        for nid in self.modal_result.node_order:
            node=self.project.nodes[nid]
            if abs(node.z-z)<1e-8:
                values.append(
                    np.linalg.norm(mode.vector[
                        6*self.modal_result.node_index[nid]:
                        6*self.modal_result.node_index[nid]+3
                    ])
                )
        maximum=max(values,default=1.0)
        model_span=max(
            max(self.project.x_grids)-min(self.project.x_grids),
            max(self.project.y_grids)-min(self.project.y_grids),
            1.0,
        )
        scale=0.08*model_span/max(maximum,1e-12)
        p.setPen(QPen(QColor("#ff4500"),2,Qt.PenStyle.DashLine))
        for frame in self.project.frames.values():
            ni=self.project.nodes[frame.i]; nj=self.project.nodes[frame.j]
            if not(abs(ni.z-z)<1e-8 and abs(nj.z-z)<1e-8):
                continue
            ui=mode.vector[
                6*self.modal_result.node_index[frame.i]:
                6*self.modal_result.node_index[frame.i]+3
            ]
            uj=mode.vector[
                6*self.modal_result.node_index[frame.j]:
                6*self.modal_result.node_index[frame.j]+3
            ]
            a=self.world_to_screen(ni.x+scale*ui[0],ni.y+scale*ui[1])
            b=self.world_to_screen(nj.x+scale*uj[0],nj.y+scale*uj[1])
            p.drawLine(a,b)

    def _draw_nodes(self,p):
        if not self.show_nodes and not self.show_node_labels:
            return
        z=self.active_z()
        for n in self.project.nodes.values():
            if abs(n.z-z)<1e-8:
                c=self.world_to_screen(n.x,n.y)
                if self.show_nodes:
                    p.setBrush(QColor("#222"))
                    p.setPen(Qt.PenStyle.NoPen)
                    p.drawEllipse(c,2.5,2.5)
                if self.show_node_labels:
                    p.setPen(QColor("#5d4037"))
                    p.drawText(c+QPointF(5,-5),f"N{n.id}")
    def _draw_preview(self,p):
        if self.drag_start is None or self.drag_current is None: return
        a=self.world_to_screen(*self.drag_start); b=self.world_to_screen(*self.drag_current); p.setPen(QPen(QColor("#d62728"),2,Qt.PenStyle.DashLine)); p.setBrush(QColor(200,40,40,35))
        if self.mode in ("Beam","Slab"):
            if self.mode=="Beam": p.drawLine(a,b)
            else: p.drawRect(int(min(a.x(),b.x())),int(min(a.y(),b.y())),int(abs(a.x()-b.x())),int(abs(a.y()-b.y())))

    def _draw_selection_window(self,p):
        if (
            not self.selection_dragging
            or self.selection_start_screen is None
            or self.selection_current_screen is None
        ):
            return
        start=self.selection_start_screen
        current=self.selection_current_screen
        rectangle=QRectF(start,current).normalized()
        left_to_right=current.x()>=start.x()
        color=QColor("#1976d2" if left_to_right else "#2e7d32")
        p.setPen(QPen(color,1.5,Qt.PenStyle.DashLine))
        p.setBrush(QColor(
            color.red(),color.green(),color.blue(),35
        ))
        p.drawRect(rectangle)
        p.setPen(color)
        p.drawText(
            rectangle.topLeft()+QPointF(4,14),
            "Window" if left_to_right else "Crossing"
        )

    def _draw_snap(self,p):
        if not self.current_snap: return
        c=self.world_to_screen(self.current_snap.x,self.current_snap.y); p.setPen(QPen(QColor("#d00000"),1)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawRect(int(c.x()-5),int(c.y()-5),10,10); p.drawText(c+QPointF(8,-8),self.current_snap.kind)
    def mousePressEvent(self,e:QMouseEvent):
        if e.button()==Qt.MouseButton.MiddleButton: self.pan_active=True; self.pan_last=e.position(); self.setCursor(Qt.CursorShape.ClosedHandCursor); return
        if e.button()!=Qt.MouseButton.LeftButton: return
        x,y=self.screen_to_world(e.position()); x,y,s=self.snap_world(x,y,e.modifiers()); self.current_snap=s
        if self.mode in ("Beam","Slab"): self.drag_start=(x,y); self.drag_current=(x,y); self.update(); return
        if self.mode=="Select":
            self.selection_start_screen=e.position()
            self.selection_current_screen=e.position()
            self.selection_dragging=True
            self.setCursor(Qt.CursorShape.CrossCursor)
            self.update()
            return
        if self.mode=="Column":
            try: f=self.project.add_column(x,y,self.project.active_story_id); self.selected_frames={f.id}; self.selected_areas.clear(); self.selection_changed.emit("Frame",f.id); self.model_changed.emit()
            except ValueError: pass
            self.update(); return
        self._select_at(x,y,e.modifiers())
    def mouseMoveEvent(self,e:QMouseEvent):
        if self.pan_active and self.pan_last is not None:
            d=e.position()-self.pan_last; self.origin+=d; self.pan_last=e.position(); self.update(); return
        if self.selection_dragging:
            self.selection_current_screen=e.position()
            x,y=self.screen_to_world(e.position())
            self.cursor_world_changed.emit(x,y,self.active_z(),"Window")
            self.update()
            return
        x,y=self.screen_to_world(e.position()); x,y,s=self.snap_world(x,y,e.modifiers()); self.current_snap=s
        if self.drag_start is not None:
            if self.ortho or e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                dx=abs(x-self.drag_start[0]); dy=abs(y-self.drag_start[1]);
                if dx>=dy: y=self.drag_start[1]
                else: x=self.drag_start[0]
            self.drag_current=(x,y)
        else:
            self._update_hover(x,y)
            self._show_result_tip(e,x,y)
        self.cursor_world_changed.emit(x,y,self.active_z(),s.kind if s else "")
        self.update()

    def _nearest_visible_node(self,x,y,tol_px=10):
        tol=tol_px/max(self.zoom,1e-9); z=self.active_z()
        best=None; distance=tol
        for nid,node in self.project.nodes.items():
            if abs(node.z-z)>1e-8:continue
            d=hypot(x-node.x,y-node.y)
            if d<distance:best=nid;distance=d
        return best

    def _show_result_tip(self,e,x,y):
        if self.analysis_result is None or self.result_mode=="None":
            QToolTip.hideText();self._last_tip_key=None;return
        tip=None;key=None
        if self.result_mode in ("Moment","Shear","Axial","Torsion") and self.hover_kind=="Frame":
            f=self.project.frames[self.hover_id];a=self.project.nodes[f.i];b=self.project.nodes[f.j]
            dx,dy=b.x-a.x,b.y-a.y;den=dx*dx+dy*dy
            ratio=0 if den<=1e-12 else ((x-a.x)*dx+(y-a.y)*dy)/den
            tip=frame_result_tip(self.project,self.analysis_result,self.unit_system,f.id,self.result_mode,ratio)
            key=("f",f.id,self.result_mode,round(ratio,2))
        elif self.result_mode.startswith("Slab ") and self.hover_kind=="Area":
            tip=shell_tip(self.project,self.analysis_result,self.unit_system,self.hover_id,self.result_mode,x,y)
            key=("a",self.hover_id,self.result_mode,round(x,2),round(y,2))
        elif self.result_mode=="Reactions":
            nid=self._nearest_visible_node(x,y)
            if nid is not None and any(self.project.nodes[nid].restraint):
                tip=reaction_tip(self.analysis_result,self.unit_system,nid);key=("r",nid)
        elif self.result_mode=="Deformed":
            nid=self._nearest_visible_node(x,y)
            if nid is not None:
                tip=displacement_tip(self.analysis_result,self.unit_system,nid);key=("d",nid)
        if tip is None:
            QToolTip.hideText();self._last_tip_key=None;return
        if key!=self._last_tip_key:
            QToolTip.showText(e.globalPosition().toPoint(),tip.html(),self)
            self._last_tip_key=key

    def mouseReleaseEvent(self,e:QMouseEvent):
        if e.button()==Qt.MouseButton.MiddleButton:
            self.pan_active=False
            self.pan_last=None
            self.unsetCursor()
            return
        if e.button()==Qt.MouseButton.LeftButton and self.selection_dragging:
            self.selection_current_screen=e.position()
            start=self.selection_start_screen
            current=self.selection_current_screen
            self.selection_dragging=False
            self.selection_start_screen=None
            self.selection_current_screen=None
            self.unsetCursor()
            if start is not None and current is not None:
                if (current-start).manhattanLength()<5:
                    x,y=self.screen_to_world(current)
                    self._select_at(x,y,e.modifiers())
                else:
                    self._select_window(start,current,e.modifiers())
            self.update()
            return
        if e.button()!=Qt.MouseButton.LeftButton or self.drag_start is None:
            return
        x,y=self.screen_to_world(e.position()); x,y,s=self.snap_world(x,y,e.modifiers())
        if self.ortho or e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            if abs(x-self.drag_start[0])>=abs(y-self.drag_start[1]): y=self.drag_start[1]
            else: x=self.drag_start[0]
        z=self.active_z()
        try:
            if self.mode=="Beam":
                f=self.project.add_frame((self.drag_start[0],self.drag_start[1],z),(x,y,z)); self.selected_frames={f.id}; self.selected_areas.clear(); self.selection_changed.emit("Frame",f.id)
            elif self.mode=="Slab":
                a=self.project.add_rect_area((self.drag_start[0],self.drag_start[1],z),(x,y,z)); self.selected_areas={a.id}; self.selected_frames.clear(); self.selection_changed.emit("Area",a.id)
            self.model_changed.emit()
        except ValueError: pass
        self.drag_start=self.drag_current=None; self.update()
    def wheelEvent(self,e:QWheelEvent):
        before=self.screen_to_world(e.position()); factor=1.15 if e.angleDelta().y()>0 else 1/1.15; self.zoom=max(8,min(450,self.zoom*factor)); after=self.screen_to_world(e.position()); self.origin+=QPointF((after[0]-before[0])*self.zoom,-(after[1]-before[1])*self.zoom); self.update()
    def keyPressEvent(self,e):
        if e.key()==Qt.Key.Key_Escape:
            self.drag_start=self.drag_current=None
            self.selection_dragging=False
            self.selection_start_screen=None
            self.selection_current_screen=None
            self.unsetCursor()
            self.set_mode("Select")
        elif e.key()==Qt.Key.Key_Delete: self.delete_selected()
        else: super().keyPressEvent(e)


    @staticmethod
    def _segment_intersects_rectangle(a,b,rect):
        return segment_intersects_rectangle(
            (a.x(),a.y()),(b.x(),b.y()),
            (rect.left(),rect.top(),rect.right(),rect.bottom())
        )

    def _select_window(self,start,current,modifiers):
        rect=QRectF(start,current).normalized()
        crossing=current.x()<start.x()
        ctrl=bool(modifiers & Qt.KeyboardModifier.ControlModifier)
        if not ctrl:
            self.selected_frames.clear()
            self.selected_areas.clear()
        z=self.active_z()

        for frame in self.project.frames.values():
            ni=self.project.nodes[frame.i]
            nj=self.project.nodes[frame.j]
            horizontal=abs(ni.z-z)<1e-8 and abs(nj.z-z)<1e-8
            column=(
                frame.kind=="Column"
                and min(ni.z,nj.z)<z<=max(ni.z,nj.z)
            )
            if horizontal:
                a=self.world_to_screen(ni.x,ni.y)
                b=self.world_to_screen(nj.x,nj.y)
                selected=(
                    self._segment_intersects_rectangle(a,b,rect)
                    if crossing else rect.contains(a) and rect.contains(b)
                )
            elif column:
                point=self.world_to_screen(ni.x,ni.y)
                selected=rect.contains(point)
            else:
                selected=False
            if selected:
                self.selected_frames.add(frame.id)

        for area in self.project.areas.values():
            nodes=[self.project.nodes[nid] for nid in area.nodes]
            if not all(abs(node.z-z)<1e-8 for node in nodes):
                continue
            points=[self.world_to_screen(node.x,node.y) for node in nodes]
            if crossing:
                centre=rect.center()
                world_centre=self.screen_to_world(centre)
                selected=(
                    any(rect.contains(point) for point in points)
                    or any(
                        self._segment_intersects_rectangle(
                            points[i],points[(i+1)%len(points)],rect
                        )
                        for i in range(len(points))
                    )
                    or point_in_polygon(
                        world_centre[0],world_centre[1],
                        [(node.x,node.y) for node in nodes]
                    )
                )
            else:
                selected=all(rect.contains(point) for point in points)
            if selected:
                self.selected_areas.add(area.id)

        if self.selected_frames:
            self.selection_changed.emit(
                "Frame",next(iter(self.selected_frames))
            )
        elif self.selected_areas:
            self.selection_changed.emit(
                "Area",next(iter(self.selected_areas))
            )

    def select_all_visible(self):
        z=self.active_z()
        self.selected_frames.clear()
        self.selected_areas.clear()
        for frame in self.project.frames.values():
            ni=self.project.nodes[frame.i]
            nj=self.project.nodes[frame.j]
            horizontal=abs(ni.z-z)<1e-8 and abs(nj.z-z)<1e-8
            column=frame.kind=="Column" and min(ni.z,nj.z)<z<=max(ni.z,nj.z)
            if horizontal or column:
                self.selected_frames.add(frame.id)
        for area in self.project.areas.values():
            nodes=[self.project.nodes[nid] for nid in area.nodes]
            if all(abs(node.z-z)<1e-8 for node in nodes):
                self.selected_areas.add(area.id)
        self.update()

    def delete_selected(self):
        if self.selected_frames or self.selected_areas:
            self.project.delete_objects(self.selected_frames,self.selected_areas); self.clear_selection(); self.model_changed.emit()
    def _update_hover(self,x,y):
        self.hover_kind=self.hover_id=None; z=self.active_z(); tol=8/self.zoom
        for f in self.project.frames.values():
            a=self.project.nodes[f.i]; b=self.project.nodes[f.j]
            if abs(a.z-z)<1e-8 and abs(b.z-z)<1e-8 and point_segment_distance(x,y,a.x,a.y,b.x,b.y)<=tol: self.hover_kind="Frame"; self.hover_id=f.id; return
            if f.kind=="Column" and min(a.z,b.z)<z<=max(a.z,b.z) and hypot(x-a.x,y-a.y)<=tol: self.hover_kind="Frame"; self.hover_id=f.id; return
        for a in self.project.areas.values():
            pts=[self.project.nodes[n] for n in a.nodes]
            if all(abs(n.z-z)<1e-8 for n in pts) and point_in_polygon(x,y,[(n.x,n.y) for n in pts]): self.hover_kind="Area"; self.hover_id=a.id; return
    def _select_at(self,x,y,mods):
        self._update_hover(x,y); ctrl=bool(mods & Qt.KeyboardModifier.ControlModifier)
        if not ctrl: self.selected_frames.clear(); self.selected_areas.clear()
        if self.hover_kind=="Frame":
            if self.hover_id in self.selected_frames and ctrl: self.selected_frames.remove(self.hover_id)
            else: self.selected_frames.add(self.hover_id)
            self.selection_changed.emit("Frame",self.hover_id)
        elif self.hover_kind=="Area":
            if self.hover_id in self.selected_areas and ctrl: self.selected_areas.remove(self.hover_id)
            else: self.selected_areas.add(self.hover_id)
            self.selection_changed.emit("Area",self.hover_id)
        self.update()
    def fit_view(self):
        xs=self.project.x_grids or [0,10]; ys=self.project.y_grids or [0,10]; dx=max(max(xs)-min(xs),1); dy=max(max(ys)-min(ys),1)
        self.zoom=max(8,min((self.width()-160)/dx,(self.height()-140)/dy)); self.origin=QPointF(80-min(xs)*self.zoom,self.height()-70+min(ys)*self.zoom); self.update()
