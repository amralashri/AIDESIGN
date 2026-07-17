from __future__ import annotations
from PySide6.QtWidgets import QTableWidget,QTableWidgetItem,QHeaderView
from model.project import ProjectModel


class PropertyGrid(QTableWidget):
    def __init__(self,parent=None):
        super().__init__(0,2,parent); self.setHorizontalHeaderLabels(["Property","Value"]); self.verticalHeader().hide(); self.setAlternatingRowColors(True)
        self.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents); self.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
    def show_object(self,project:ProjectModel,kind:str|None,obj_id:int|None):
        rows=[]
        if kind=="Frame" and obj_id in project.frames:
            f=project.frames[obj_id]; ni=project.nodes[f.i]; nj=project.nodes[f.j]
            L=((nj.x-ni.x)**2+(nj.y-ni.y)**2+(nj.z-ni.z)**2)**0.5
            rows=[("Object","Frame"),("Label",f"F{f.id}"),("Type",f.kind),("Section",f.section),("I Node",f"N{f.i}"),("J Node",f"N{f.j}"),("Length",f"{L:.3f} m")]
        elif kind=="Area" and obj_id in project.areas:
            a=project.areas[obj_id]; rows=[("Object","Area"),("Label",f"A{a.id}"),("Type",a.kind),("Section",a.section),("Nodes",", ".join(f"N{x}" for x in a.nodes))]
        elif kind=="Story" and obj_id in project.stories:
            s=project.stories[obj_id]; rows=[("Object","Story"),("Name",s.name),("Elevation",f"{s.elevation:.3f} m"),("Height",f"{s.height:.3f} m")]
        self.setRowCount(len(rows))
        for r,(k,v) in enumerate(rows):
            self.setItem(r,0,QTableWidgetItem(k)); self.setItem(r,1,QTableWidgetItem(str(v)))
