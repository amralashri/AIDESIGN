from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import (
    QColor, QMouseEvent, QPainter, QPen, QPolygonF, QWheelEvent,
)
from PySide6.QtWidgets import QToolTip,QWidget

from analysis.postprocessing import (
    automatic_deformation_scale, deformed_node_positions, dominant_curve,
)
from analysis.results import AnalysisResult
from analysis.contours import (
    area_contour_samples, contour_range, jet_rgb,
)
from design.concrete import ConcreteDesignResult
from graphics.camera3d import RevitOrbitCamera
from model.project import ProjectModel
from graphics.geometry import point_in_polygon
from core.units import UnitSystem
from analysis.hover_results import frame_result_tip,shell_tip


class Viewport3D(QWidget):
    status_message = Signal(str)
    object_selected = Signal(str,int)

    def __init__(self, project: ProjectModel, parent=None):
        super().__init__(parent)
        self.project = project
        self.camera = RevitOrbitCamera()
        self.analysis_result: AnalysisResult | None = None
        self.result_mode = "None"
        self.show_base_grid = True
        self.show_axes = True
        self.show_pivot = True
        self.deformation_scale: float | None = None
        self.concrete_design_result: ConcreteDesignResult | None = None
        self.unit_system=UnitSystem(self)
        self._last_tip_key=None
        self.modal_result=None
        self.modal_mode_number=1
        self.animation_factor=1.0
        self.animation_target="None"

        self._drag_mode: str | None = None
        self._last_position: QPointF | None = None
        self._press_position: QPointF | None = None
        self._selected_frame: int | None = None
        self._selected_area: int | None = None

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.camera.target = self.grid_pivot()
        self.camera.set_isometric(20.0)
        self._initial_isometric_done = False

    def showEvent(self,event) -> None:
        super().showEvent(event)
        if not self._initial_isometric_done:
            self._initial_isometric_done=True
            self.view_isometric()

    def resizeEvent(self,event) -> None:
        super().resizeEvent(event)
        if not self._initial_isometric_done and self.isVisible():
            self._initial_isometric_done=True
            self.view_isometric()

    def set_project(self, project: ProjectModel) -> None:
        self.project = project
        self.analysis_result = None
        self.result_mode = "None"
        self._selected_frame = None
        self._selected_area = None
        self._initial_isometric_done=True
        self.view_isometric()

    def set_analysis_result(self, result: AnalysisResult | None) -> None:
        self.analysis_result = result
        self.update()

    def set_result_mode(self, mode: str) -> None:
        self.result_mode = mode
        self.update()

    def set_concrete_design_result(self,result) -> None:
        self.concrete_design_result=result
        self.update()

    def set_modal_result(self,result,mode_number=1):
        self.modal_result=result
        self.modal_mode_number=mode_number
        self.update()

    def set_animation_state(self,target,factor):
        self.animation_target=target
        self.animation_factor=float(factor)
        self.update()

    def set_unit_system(self,unit_system):
        self.unit_system=unit_system
        self.unit_system.changed.connect(self.update)
        self.update()

    def _model_points(self) -> list[np.ndarray]:
        points = [
            np.array([node.x,node.y,node.z],dtype=float)
            for node in self.project.nodes.values()
        ]
        if not points and self.project.stories:
            z0 = min(s.elevation for s in self.project.stories.values())
            z1 = max(s.elevation for s in self.project.stories.values())
            for x in self.project.x_grids:
                for y in self.project.y_grids:
                    points.extend([
                        np.array([x,y,z0],dtype=float),
                        np.array([x,y,z1],dtype=float),
                    ])
        return points

    def grid_pivot(self) -> np.ndarray:
        """Return the geometric centre of the grid and story extents."""
        return np.asarray(
            self.project.grid_center(),dtype=float
        )

    def project_point(self, point: np.ndarray) -> tuple[QPointF,float,bool]:
        x,y,depth,visible = self.camera.project(
            point,self.width(),self.height()
        )
        return QPointF(x,y),depth,visible

    def paintEvent(self,event) -> None:
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(),QColor("#ffffff"))

        if self.show_base_grid:
            self._draw_base_grid(painter)
        if self.result_mode in ("Slab As X","Slab As Y"):
            self._draw_design_contours(painter)
        elif self.result_mode.startswith("Slab ") and self.result_mode not in (
            "Slab Rebar X","Slab Rebar Y","Slab As X","Slab As Y"
        ):
            self._draw_slab_contours(painter)
        else:
            self._draw_areas(painter)
        self._draw_frames(painter)
        self._draw_results(painter)
        self._draw_mode_shape(painter)
        self._draw_reinforcement(painter)
        if self.show_pivot:
            self._draw_pivot(painter)
        if self.show_axes:
            self._draw_axis_triad(painter)

        painter.setPen(QColor("#444444"))
        painter.drawText(
            10,20,
            f"Perspective 3D | {self.result_mode} | "
            "LMB Orbit · MMB Pan · Wheel Zoom · Double-click Pivot",
        )
        painter.end()

    def _draw_base_grid(self,painter:QPainter) -> None:
        if not self.project.stories:
            return
        z=min(s.elevation for s in self.project.stories.values())
        painter.setPen(QPen(QColor("#d8e8f4"),1))
        for x in self.project.x_grids:
            p1,_,v1=self.project_point(np.array([
                x,min(self.project.y_grids),z
            ]))
            p2,_,v2=self.project_point(np.array([
                x,max(self.project.y_grids),z
            ]))
            if v1 or v2:
                painter.drawLine(p1,p2)
        for y in self.project.y_grids:
            p1,_,v1=self.project_point(np.array([
                min(self.project.x_grids),y,z
            ]))
            p2,_,v2=self.project_point(np.array([
                max(self.project.x_grids),y,z
            ]))
            if v1 or v2:
                painter.drawLine(p1,p2)

    def _draw_areas(self,painter:QPainter) -> None:
        draw_items=[]
        for area in self.project.areas.values():
            points3d=[
                np.array([
                    self.project.nodes[node_id].x,
                    self.project.nodes[node_id].y,
                    self.project.nodes[node_id].z,
                ],dtype=float)
                for node_id in area.nodes
            ]
            projected=[self.project_point(point) for point in points3d]
            if not any(item[2] for item in projected):
                continue
            depth=sum(item[1] for item in projected)/len(projected)
            draw_items.append((depth,area,[item[0] for item in projected]))
        for _,area,points in sorted(draw_items,key=lambda item:item[0],reverse=True):
            selected=area.id==self._selected_area
            painter.setPen(QPen(
                QColor("#ff8c00" if selected else "#4f81bd"),
                2 if selected else 1,
            ))
            painter.setBrush(QColor(
                255,180,60,90
            ) if selected else QColor(150,205,240,75))
            painter.drawPolygon(QPolygonF(points))

    def _frame_items(self,positions=None):
        items=[]
        for frame in self.project.frames.values():
            if positions is None:
                ni=self.project.nodes[frame.i]
                nj=self.project.nodes[frame.j]
                pi=np.array([ni.x,ni.y,ni.z],dtype=float)
                pj=np.array([nj.x,nj.y,nj.z],dtype=float)
            else:
                pi=positions[frame.i]
                pj=positions[frame.j]
            qi,di,vi=self.project_point(pi)
            qj,dj,vj=self.project_point(pj)
            if vi or vj:
                items.append(((di+dj)/2.0,frame,pi,pj,qi,qj))
        return sorted(items,key=lambda item:item[0],reverse=True)

    def _draw_frames(self,painter:QPainter) -> None:
        for _,frame,_,_,a,b in self._frame_items():
            selected=frame.id==self._selected_frame
            color = (
                "#ff8c00" if selected
                else "#9c27b0" if frame.kind=="Column"
                else "#00a6b2" if frame.kind=="Brace"
                else "#006dcc"
            )
            painter.setPen(QPen(
                QColor(color),4 if selected else 3
            ))
            painter.drawLine(a,b)

        if self.analysis_result and self.result_mode=="Deformed":
            scale=self.deformation_scale
            if scale is None:
                scale=automatic_deformation_scale(
                    self.project,self.analysis_result
                )
            factor=(
                self.animation_factor
                if self.animation_target=="Deformed" else 1.0
            )
            positions=deformed_node_positions(
                self.project,self.analysis_result,scale*factor
            )
            painter.setPen(QPen(
                QColor("#d62728"),2,Qt.PenStyle.DashLine
            ))
            for _,_,_,_,a,b in self._frame_items(positions):
                painter.drawLine(a,b)

    def _draw_results(self,painter:QPainter) -> None:
        if (
            self.analysis_result is None
            or self.result_mode not in ("Moment","Shear","Axial","Torsion")
        ):
            return

        curves={}
        absolute=[]
        for frame in self.project.frames.values():
            if frame.id not in self.analysis_result.frame_results:
                continue
            x,values,label=dominant_curve(
                self.analysis_result,frame.id,self.result_mode
            )
            curves[frame.id]=(x,values,label)
            absolute.extend(np.abs(values).tolist())
        maximum=max(absolute,default=1.0)
        points=self._model_points()
        size=1.0
        if points:
            array=np.vstack(points)
            size=max(float(np.ptp(array,axis=0).max()),1.0)
        scale=0.10*size/max(maximum,1.0e-12)
        color=QColor(
            "#d62728" if self.result_mode=="Moment"
            else "#2ca02c" if self.result_mode=="Shear"
            else "#9467bd"
        )

        for frame in self.project.frames.values():
            if frame.id not in curves:
                continue
            ni=self.project.nodes[frame.i]
            nj=self.project.nodes[frame.j]
            pi=np.array([ni.x,ni.y,ni.z],dtype=float)
            pj=np.array([nj.x,nj.y,nj.z],dtype=float)
            vector=pj-pi
            length=max(float(np.linalg.norm(vector)),1.0e-12)
            tangent=vector/length
            if abs(tangent[2])<0.90:
                normal=np.array([0.0,0.0,1.0])
            else:
                normal=np.array([1.0,0.0,0.0])

            x,values,label=curves[frame.id]
            base=np.array([
                pi+(station/length)*vector for station in x
            ])
            diagram=base+values[:,None]*scale*normal[None,:]
            projected_base=[self.project_point(p)[0] for p in base]
            projected_diag=[self.project_point(p)[0] for p in diagram]

            painter.setPen(QPen(color,2))
            for index in range(len(projected_diag)-1):
                painter.drawLine(
                    projected_diag[index],projected_diag[index+1]
                )
            painter.setPen(QPen(QColor(
                color.red(),color.green(),color.blue(),120
            ),1))
            for index in range(0,len(projected_diag),5):
                painter.drawLine(
                    projected_base[index],projected_diag[index]
                )
            peak=int(np.argmax(np.abs(values)))
            painter.setPen(QPen(color,1))
            painter.drawText(
                projected_diag[peak]+QPointF(4,-4),
                f"{values[peak]:.3f}",
            )

    def _draw_slab_contours(self,painter):
        if self.analysis_result is None:
            return
        minimum,maximum=contour_range(
            self.project,self.analysis_result,self.result_mode
        )
        for area in self.project.areas.values():
            samples=area_contour_samples(
                self.project,self.analysis_result,
                area.id,self.result_mode,9
            )
            if not samples:
                continue
            divisions=int(round(len(samples)**0.5))
            for j in range(divisions-1):
                for i in range(divisions-1):
                    ids=[
                        j*divisions+i,j*divisions+i+1,
                        (j+1)*divisions+i+1,
                        (j+1)*divisions+i,
                    ]
                    value=sum(samples[k]["value"] for k in ids)/4.0
                    rgb=jet_rgb(value,minimum,maximum)
                    points=[
                        self.project_point(
                            samples[k]["global"]
                        )[0] for k in ids
                    ]
                    painter.setPen(QPen(QColor(*rgb),1))
                    painter.setBrush(QColor(*rgb,205))
                    painter.drawPolygon(QPolygonF(points))
        self._draw_3d_legend(painter,minimum,maximum)

    def _draw_3d_legend(self,painter,minimum,maximum):
        x=self.width()-65
        top=50
        height=180
        for i in range(36):
            ratio=i/35.0
            value=maximum-ratio*(maximum-minimum)
            rgb=jet_rgb(value,minimum,maximum)
            painter.fillRect(
                x,int(top+i*height/36),18,
                int(height/36)+2,QColor(*rgb)
            )
        painter.setPen(QColor("#222"))
        painter.drawRect(x,top,18,height)
        painter.drawText(x-8,top-5,f"{maximum:.3f}")
        painter.drawText(x-8,top+height+15,f"{minimum:.3f}")


    def _draw_design_contours(self,painter):
        if self.concrete_design_result is None:
            return
        values=[
            (d.as_x_mm2_per_m if self.result_mode=="Slab As X" else d.as_y_mm2_per_m)
            for d in self.concrete_design_result.slabs.values()
        ]
        if not values: return
        minimum=min(values); maximum=max(values)
        if abs(maximum-minimum)<1e-9:
            minimum=0.0; maximum=max(maximum,1.0)
        for area_id,design in self.concrete_design_result.slabs.items():
            area=self.project.areas.get(area_id)
            if area is None: continue
            value=(design.as_x_mm2_per_m if self.result_mode=="Slab As X"
                   else design.as_y_mm2_per_m)
            rgb=jet_rgb(value,minimum,maximum)
            points=[]
            for nid in area.nodes:
                n=self.project.nodes[nid]
                point,_,visible=self.project_point(np.array([n.x,n.y,n.z+0.01]))
                points.append(point)
            painter.setPen(QPen(QColor(*rgb),1.5))
            painter.setBrush(QColor(*rgb,205))
            painter.drawPolygon(QPolygonF(points))
            center=QPointF(
                sum(q.x() for q in points)/len(points),
                sum(q.y() for q in points)/len(points),
            )
            painter.setPen(QColor("#111111"))
            painter.drawText(center+QPointF(4,-4),f"As={value:.0f}")
        self._draw_3d_legend(painter,minimum,maximum)

    def _draw_reinforcement(self,painter):
        if self.concrete_design_result is None:
            return
        painter.setPen(QPen(QColor("#b00020"),2))
        if self.result_mode=="Beam Rebar":
            for frame_id,design in self.concrete_design_result.beams.items():
                frame=self.project.frames.get(frame_id)
                if frame is None:
                    continue
                ni=self.project.nodes[frame.i]
                nj=self.project.nodes[frame.j]
                a,_,_=self.project_point(np.array([ni.x,ni.y,ni.z]))
                b,_,_=self.project_point(np.array([nj.x,nj.y,nj.z]))
                painter.drawLine(a,b)
                painter.drawText((a+b)/2+QPointF(4,-5),design.label)
        elif self.result_mode in ("Slab Rebar X","Slab Rebar Y"):
            for area_id,design in self.concrete_design_result.slabs.items():
                area=self.project.areas.get(area_id)
                if area is None:
                    continue
                nodes=[self.project.nodes[nid] for nid in area.nodes]
                xs=[n.x for n in nodes]; ys=[n.y for n in nodes]
                z=sum(n.z for n in nodes)/4.0+0.02
                xmin,xmax=min(xs),max(xs)
                ymin,ymax=min(ys),max(ys)
                if self.result_mode=="Slab Rebar X":
                    spacing=max(design.spacing_x_mm/1000.0,0.05)
                    y=ymin+spacing/2
                    while y<ymax:
                        a,_,_=self.project_point(np.array([xmin,y,z]))
                        b,_,_=self.project_point(np.array([xmax,y,z]))
                        painter.drawLine(a,b)
                        y+=spacing
                    label=design.label_x
                else:
                    spacing=max(design.spacing_y_mm/1000.0,0.05)
                    x=xmin+spacing/2
                    while x<xmax:
                        a,_,_=self.project_point(np.array([x,ymin,z]))
                        b,_,_=self.project_point(np.array([x,ymax,z]))
                        painter.drawLine(a,b)
                        x+=spacing
                    label=design.label_y
                center,_,_=self.project_point(np.array([
                    (xmin+xmax)/2,(ymin+ymax)/2,z
                ]))
                painter.drawText(center+QPointF(4,-5),label)

    def _draw_mode_shape(self,painter):
        if self.modal_result is None:
            return
        mode=self.modal_result.modes[self.modal_mode_number-1]
        maximum=max(
            np.linalg.norm(mode.vector[
                6*self.modal_result.node_index[nid]:
                6*self.modal_result.node_index[nid]+3
            ])
            for nid in self.modal_result.node_order
        )
        points=self._model_points()
        size=1.0
        if points:
            array=np.vstack(points)
            size=max(float(np.ptp(array,axis=0).max()),1.0)
        scale=0.10*size/max(maximum,1e-12)
        if self.animation_target=="Mode":
            scale*=self.animation_factor
        painter.setPen(QPen(
            QColor("#ff4500"),2,Qt.PenStyle.DashLine
        ))
        for frame in self.project.frames.values():
            ni=self.project.nodes[frame.i]
            nj=self.project.nodes[frame.j]
            ui=mode.vector[
                6*self.modal_result.node_index[frame.i]:
                6*self.modal_result.node_index[frame.i]+3
            ]
            uj=mode.vector[
                6*self.modal_result.node_index[frame.j]:
                6*self.modal_result.node_index[frame.j]+3
            ]
            pi=np.array([ni.x,ni.y,ni.z],dtype=float)+scale*ui
            pj=np.array([nj.x,nj.y,nj.z],dtype=float)+scale*uj
            a,_,_=self.project_point(pi)
            b,_,_=self.project_point(pj)
            painter.drawLine(a,b)

    def _draw_pivot(self,painter:QPainter) -> None:
        point,_,visible=self.project_point(self.camera.target)
        if not visible:
            return
        painter.setPen(QPen(QColor(60,60,60,110),1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(point,5,5)
        painter.drawLine(
            point+QPointF(-8,0),point+QPointF(8,0)
        )
        painter.drawLine(
            point+QPointF(0,-8),point+QPointF(0,8)
        )

    def _draw_axis_triad(self,painter:QPainter) -> None:
        origin=QPointF(65,self.height()-55)
        right,up,forward=self.camera.basis()
        # Screen components are projections onto camera right/up.
        axes=[
            (np.array([1.,0.,0.]),QColor("#e53935"),"X"),
            (np.array([0.,1.,0.]),QColor("#43a047"),"Y"),
            (np.array([0.,0.,1.]),QColor("#1e88e5"),"Z"),
        ]
        for world_axis,color,label in axes:
            dx=float(np.dot(world_axis,right))*34.0
            dy=-float(np.dot(world_axis,up))*34.0
            end=origin+QPointF(dx,dy)
            painter.setPen(QPen(color,2))
            painter.drawLine(origin,end)
            painter.drawText(end+QPointF(3,-3),label)

    @staticmethod
    def _distance_to_segment(
        point:QPointF,start:QPointF,end:QPointF
    ) -> float:
        px,py=point.x(),point.y()
        ax,ay=start.x(),start.y()
        bx,by=end.x(),end.y()
        dx,dy=bx-ax,by-ay
        length_sq=dx*dx+dy*dy
        if length_sq<=1.0e-12:
            return float(np.hypot(px-ax,py-ay))
        t=max(0.0,min(1.0,((px-ax)*dx+(py-ay)*dy)/length_sq))
        qx,qy=ax+t*dx,ay+t*dy
        return float(np.hypot(px-qx,py-qy))

    def _pick_frame(self,screen:QPointF,tolerance:float=10.0):
        best=None
        best_distance=tolerance
        best_depth=float("inf")
        for depth,frame,pi,pj,a,b in self._frame_items():
            distance=self._distance_to_segment(screen,a,b)
            if distance<best_distance or (
                abs(distance-best_distance)<1.0e-6 and depth<best_depth
            ):
                best=(frame,pi,pj)
                best_distance=distance
                best_depth=depth
        return best

    def _set_pivot_from_screen(self,screen:QPointF) -> None:
        picked=self._pick_frame(screen,14.0)
        if picked is not None:
            frame,pi,pj=picked
            # Use closest point on the actual 3D frame based on projected ratio.
            a,_,_=self.project_point(pi)
            b,_,_=self.project_point(pj)
            dx,dy=b.x()-a.x(),b.y()-a.y()
            denominator=dx*dx+dy*dy
            if denominator<=1.0e-12:
                t=0.5
            else:
                t=max(0.0,min(1.0,(
                    (screen.x()-a.x())*dx
                    +(screen.y()-a.y())*dy
                )/denominator))
            pivot=pi+t*(pj-pi)
            self.camera.set_pivot(pivot,True)
            self._selected_frame=frame.id
            self._selected_area=None
            self.object_selected.emit("Frame",frame.id)
            self.status_message.emit(
                f"3D pivot set on frame F{frame.id}"
            )
        else:
            # Empty-space double click returns pivot to grid centre.
            self.camera.set_pivot(self.grid_pivot(),False)
            self.status_message.emit("3D pivot reset to grid centre")
        self.update()

    def mousePressEvent(self,event:QMouseEvent) -> None:
        self._press_position=event.position()
        self._last_position=event.position()
        if event.button()==Qt.MouseButton.LeftButton:
            self._drag_mode="Orbit"
        elif event.button()==Qt.MouseButton.MiddleButton:
            self._drag_mode="Pan"
        elif event.button()==Qt.MouseButton.RightButton:
            self._drag_mode="Select"
        else:
            self._drag_mode=None
        if self._drag_mode:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self,event:QMouseEvent) -> None:
        if self._drag_mode is None or self._last_position is None:
            self._show_result_tip(event)
            return
        delta=event.position()-self._last_position
        self._last_position=event.position()
        if self._drag_mode=="Orbit":
            self.camera.orbit(delta.x(),delta.y())
        elif self._drag_mode=="Pan":
            self.camera.pan(
                delta.x(),delta.y(),self.height()
            )
        self.update()



    def _pick_area_world_point(self,screen_position):
        origin,direction=self.camera.ray_from_screen(
            screen_position.x(),screen_position.y(),
            self.width(),self.height()
        )
        best=None
        best_distance=float("inf")
        for area in self.project.areas.values():
            nodes=[self.project.nodes[nid] for nid in area.nodes]
            points=np.array([[n.x,n.y,n.z] for n in nodes],dtype=float)
            normal=np.cross(points[1]-points[0],points[3]-points[0])
            norm=float(np.linalg.norm(normal))
            if norm<=1e-12:continue
            normal/=norm
            denominator=float(np.dot(direction,normal))
            if abs(denominator)<=1e-10:continue
            distance=float(np.dot(points[0]-origin,normal)/denominator)
            if distance<0 or distance>=best_distance:continue
            hit=origin+distance*direction
            axis=int(np.argmax(np.abs(normal)))
            indices=[i for i in range(3) if i!=axis]
            polygon=[
                (float(point[indices[0]]),float(point[indices[1]]))
                for point in points
            ]
            query=(float(hit[indices[0]]),float(hit[indices[1]]))
            if point_in_polygon(query[0],query[1],polygon):
                best=(area.id,hit)
                best_distance=distance
        return best

    def _show_result_tip(self,event):
        if self.analysis_result is None or self.result_mode=="None":
            QToolTip.hideText()
            self._last_tip_key=None
            return
        tip=None
        key=None
        picked=self._pick_frame(event.position(),12.0)
        if picked and self.result_mode in ("Moment","Shear","Axial","Torsion"):
            frame,pi,pj=picked
            a,_,_=self.project_point(pi)
            b,_,_=self.project_point(pj)
            dx,dy=b.x()-a.x(),b.y()-a.y()
            denominator=dx*dx+dy*dy
            ratio=0.0 if denominator<=1e-12 else (
                ((event.position().x()-a.x())*dx
                 +(event.position().y()-a.y())*dy)/denominator
            )
            tip=frame_result_tip(
                self.project,self.analysis_result,self.unit_system,
                frame.id,self.result_mode,ratio
            )
            key=("f",frame.id,self.result_mode,round(ratio,3))
        if tip is None and self.result_mode.startswith("Slab "):
            picked_area=self._pick_area_world_point(event.position())
            if picked_area is not None:
                area_id,point=picked_area
                tip=shell_tip(
                    self.project,self.analysis_result,self.unit_system,
                    area_id,self.result_mode,
                    float(point[0]),float(point[1])
                )
                key=(
                    "a",area_id,self.result_mode,
                    round(float(point[0]),3),round(float(point[1]),3)
                )
        if tip is None:
            QToolTip.hideText()
            self._last_tip_key=None
            return
        if key!=self._last_tip_key:
            QToolTip.showText(
                event.globalPosition().toPoint(),tip.html(),self
            )
            self._last_tip_key=key

    def mouseReleaseEvent(self,event:QMouseEvent) -> None:
        if (
            self._drag_mode=="Select"
            and self._press_position is not None
            and (event.position()-self._press_position).manhattanLength()<4
        ):
            picked=self._pick_frame(event.position(),10.0)
            if picked:
                frame,_,_=picked
                self._selected_frame=frame.id
                self._selected_area=None
                self.object_selected.emit("Frame",frame.id)
        self._drag_mode=None
        self._last_position=None
        self._press_position=None
        self.unsetCursor()
        self.update()

    def mouseDoubleClickEvent(self,event:QMouseEvent) -> None:
        self._set_pivot_from_screen(event.position())

    def wheelEvent(self,event:QWheelEvent) -> None:
        steps=event.angleDelta().y()/120.0
        self.camera.zoom(steps)
        self.update()

    def reset_view(self) -> None:
        self.camera.target = self.grid_pivot()
        self.camera.set_isometric()
        self.fit_view(preserve_grid_pivot=True)

    def fit_view(self, preserve_grid_pivot: bool = True) -> None:
        pivot = self.grid_pivot() if preserve_grid_pivot else None
        self.camera.fit_points(
            self._model_points(),
            max(self.width()/max(self.height(),1),0.1),
        )
        if pivot is not None:
            old_direction = self.camera.eye-self.camera.target
            self.camera.target = pivot
            self.camera.eye = pivot+old_direction
        self.update()

    def view_isometric(self) -> None:
        self.camera.target = self.grid_pivot()
        self.camera.set_isometric()
        self.fit_view(True)

    def view_top(self) -> None:
        self.camera.target = self.grid_pivot()
        self.camera.set_top()
        self.fit_view(True)

    def view_front(self) -> None:
        self.camera.target = self.grid_pivot()
        self.camera.set_front()
        self.fit_view(True)

    def view_right(self) -> None:
        self.camera.target = self.grid_pivot()
        self.camera.set_right()
        self.fit_view(True)
