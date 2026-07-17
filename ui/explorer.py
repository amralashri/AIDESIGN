from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTreeWidget,QTreeWidgetItem
from model.project import ProjectModel


class ModelExplorer(QTreeWidget):
    object_requested=Signal(str,int)
    def __init__(self,parent=None):
        super().__init__(parent); self.setHeaderHidden(True); self.itemDoubleClicked.connect(self._open)
    def set_project(self,project:ProjectModel):
        self.clear(); root=QTreeWidgetItem(["Model"]); root.setExpanded(True); self.addTopLevelItem(root)
        stories=QTreeWidgetItem(["Stories"]); stories.setExpanded(True); root.addChild(stories)
        for s in reversed(project.ordered_stories()):
            item=QTreeWidgetItem([f"{s.name}  ({s.elevation:.3f} m)"]); item.setData(0,32,("Story",s.id)); stories.addChild(item)
        objects=QTreeWidgetItem(["Structural Objects"]); objects.setExpanded(True); root.addChild(objects)
        frames=QTreeWidgetItem([f"Frames ({len(project.frames)})"]); objects.addChild(frames)
        for f in project.frames.values():
            item=QTreeWidgetItem([f"F{f.id}  {f.kind}"]); item.setData(0,32,("Frame",f.id)); frames.addChild(item)
        areas=QTreeWidgetItem([f"Areas ({len(project.areas)})"]); objects.addChild(areas)
        for a in project.areas.values():
            item=QTreeWidgetItem([f"A{a.id}  {a.kind}"]); item.setData(0,32,("Area",a.id)); areas.addChild(item)
        defs=QTreeWidgetItem(["Definitions"]); root.addChild(defs)
        for text in ["Materials","Frame Sections","Slab Sections","Load Patterns","Load Combinations"]: defs.addChild(QTreeWidgetItem([text]))
    def _open(self,item,column):
        data=item.data(0,32)
        if isinstance(data,tuple): self.object_requested.emit(data[0],int(data[1]))
