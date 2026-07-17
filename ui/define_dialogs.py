from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QHBoxLayout,
    QInputDialog, QLabel, QListWidget, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from model.entities import AreaSection, FrameSection, Material, Story
from model.project import ProjectModel


class GridDialog(QDialog):
    def __init__(self, project: ProjectModel, parent=None):
        super().__init__(parent)
        self.project=project
        self.setWindowTitle("Define Grid System")
        layout=QFormLayout(self)
        self.x_list=QListWidget()
        self.y_list=QListWidget()
        for value in project.x_grids:
            self.x_list.addItem(str(value))
        for value in project.y_grids:
            self.y_list.addItem(str(value))
        layout.addRow("X grid coordinates:",self.x_list)
        layout.addRow("Y grid coordinates:",self.y_list)
        add_x=QPushButton("Add X")
        add_y=QPushButton("Add Y")
        delete_x=QPushButton("Delete selected X")
        delete_y=QPushButton("Delete selected Y")
        add_x.clicked.connect(lambda:self._add(self.x_list,"X coordinate"))
        add_y.clicked.connect(lambda:self._add(self.y_list,"Y coordinate"))
        delete_x.clicked.connect(lambda:self._delete(self.x_list))
        delete_y.clicked.connect(lambda:self._delete(self.y_list))
        row=QHBoxLayout()
        for button in (add_x,delete_x,add_y,delete_y):
            row.addWidget(button)
        layout.addRow(row)
        buttons=QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _add(self,widget,title):
        value,ok=QInputDialog.getDouble(self,title,title,0.0,-1e6,1e6,4)
        if ok:
            widget.addItem(str(value))

    @staticmethod
    def _delete(widget):
        for item in widget.selectedItems():
            widget.takeItem(widget.row(item))

    def accept(self):
        try:
            xs=sorted({float(self.x_list.item(i).text()) for i in range(self.x_list.count())})
            ys=sorted({float(self.y_list.item(i).text()) for i in range(self.y_list.count())})
            if len(xs)<2 or len(ys)<2:
                raise ValueError("At least two X and two Y grid lines are required.")
            self.project.x_grids=xs
            self.project.y_grids=ys
            self.project.dirty=True
        except Exception as exc:
            QMessageBox.warning(self,"Grid System",str(exc))
            return
        super().accept()


class StoryDialog(QDialog):
    def __init__(self,project:ProjectModel,parent=None):
        super().__init__(parent)
        self.project=project
        self.setWindowTitle("Define Story Data")
        self.resize(520,360)
        layout=QVBoxLayout(self)
        self.table=QTableWidget(0,3)
        self.table.setHorizontalHeaderLabels(["Name","Elevation m","Height m"])
        layout.addWidget(self.table)
        for story in project.ordered_stories():
            self._append(story.name,story.elevation,story.height)
        row=QHBoxLayout()
        add=QPushButton("Add Story")
        delete=QPushButton("Delete Selected")
        add.clicked.connect(lambda:self._append("New Story",0.0,3.5))
        delete.clicked.connect(self._delete)
        row.addWidget(add); row.addWidget(delete); row.addStretch(1)
        layout.addLayout(row)
        buttons=QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _append(self,name,elevation,height):
        row=self.table.rowCount()
        self.table.insertRow(row)
        for col,value in enumerate((name,elevation,height)):
            self.table.setItem(row,col,QTableWidgetItem(str(value)))

    def _delete(self):
        rows=sorted({item.row() for item in self.table.selectedItems()},reverse=True)
        for row in rows:
            self.table.removeRow(row)

    def accept(self):
        try:
            stories=[]
            for row in range(self.table.rowCount()):
                name=self.table.item(row,0).text().strip()
                elevation=float(self.table.item(row,1).text())
                height=float(self.table.item(row,2).text())
                if not name:
                    raise ValueError("Story names cannot be empty.")
                stories.append((name,elevation,height))
            stories.sort(key=lambda item:item[1])
            if not stories:
                raise ValueError("At least one story is required.")
            self.project.stories={
                index+1:Story(index+1,name,elevation,height)
                for index,(name,elevation,height) in enumerate(stories)
            }
            if self.project.active_story_id not in self.project.stories:
                self.project.active_story_id=max(self.project.stories)
            self.project.dirty=True
        except Exception as exc:
            QMessageBox.warning(self,"Story Data",str(exc))
            return
        super().accept()


class MaterialDialog(QDialog):
    def __init__(self,project:ProjectModel,parent=None):
        super().__init__(parent)
        self.project=project
        self.setWindowTitle("Define Materials")
        self.resize(700,370)
        layout=QVBoxLayout(self)
        self.table=QTableWidget(0,5)
        self.table.setHorizontalHeaderLabels(
            ["Name","E kN/m²","Poisson","Density kN/m³","Thermal /°C"]
        )
        layout.addWidget(self.table)
        for material in project.materials.values():
            self._append(
                material.name,material.elastic_modulus,
                material.poisson_ratio,material.density,
                material.thermal_coefficient,
            )
        add=QPushButton("Add Material")
        add.clicked.connect(
            lambda:self._append("New Material",25_000_000,0.20,25.0,1e-5)
        )
        layout.addWidget(add)
        buttons=QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _append(self,*values):
        row=self.table.rowCount()
        self.table.insertRow(row)
        for col,value in enumerate(values):
            self.table.setItem(row,col,QTableWidgetItem(str(value)))

    def accept(self):
        try:
            materials={}
            for row in range(self.table.rowCount()):
                values=[self.table.item(row,col).text() for col in range(5)]
                material=Material(
                    values[0].strip(),float(values[1]),float(values[2]),
                    float(values[3]),float(values[4]),
                )
                if not material.name:
                    raise ValueError("Material name cannot be empty.")
                materials[material.name]=material
            if not materials:
                raise ValueError("At least one material is required.")
            self.project.materials=materials
            self.project.dirty=True
        except Exception as exc:
            QMessageBox.warning(self,"Materials",str(exc))
            return
        super().accept()


class FrameSectionDialog(QDialog):
    def __init__(self,project:ProjectModel,parent=None):
        super().__init__(parent)
        self.project=project
        self.setWindowTitle("Define Frame Sections")
        self.resize(620,360)
        layout=QVBoxLayout(self)
        self.table=QTableWidget(0,4)
        self.table.setHorizontalHeaderLabels(
            ["Name","Material","Width m","Depth m"]
        )
        layout.addWidget(self.table)
        for section in project.frame_sections.values():
            self._append(
                section.name,section.material,
                section.width,section.depth,
            )
        add=QPushButton("Add Section")
        add.clicked.connect(
            lambda:self._append(
                "New Section",next(iter(project.materials)),0.30,0.60
            )
        )
        layout.addWidget(add)
        buttons=QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _append(self,*values):
        row=self.table.rowCount()
        self.table.insertRow(row)
        for col,value in enumerate(values):
            self.table.setItem(row,col,QTableWidgetItem(str(value)))

    def accept(self):
        try:
            sections={}
            for row in range(self.table.rowCount()):
                name=self.table.item(row,0).text().strip()
                material=self.table.item(row,1).text().strip()
                width=float(self.table.item(row,2).text())
                depth=float(self.table.item(row,3).text())
                if material not in self.project.materials:
                    raise ValueError(
                        f"Undefined material '{material}' in section '{name}'."
                    )
                if width<=0 or depth<=0:
                    raise ValueError("Section dimensions must be positive.")
                sections[name]=FrameSection(
                    name,material,width,depth
                )
            if not sections:
                raise ValueError("At least one frame section is required.")
            self.project.frame_sections=sections
            self.project.dirty=True
        except Exception as exc:
            QMessageBox.warning(self,"Frame Sections",str(exc))
            return
        super().accept()


class SlabSectionDialog(QDialog):
    def __init__(self,project:ProjectModel,parent=None):
        super().__init__(parent)
        self.project=project
        self.setWindowTitle("Define Slab / Shell Sections")
        self.resize(650,360)
        layout=QVBoxLayout(self)
        self.table=QTableWidget(0,4)
        self.table.setHorizontalHeaderLabels(
            ["Name","Material","Thickness m","Formulation"]
        )
        layout.addWidget(self.table)
        for section in project.area_sections.values():
            self._append(
                section.name,section.material,
                section.thickness,section.formulation,
            )
        add=QPushButton("Add Slab Section")
        add.clicked.connect(
            lambda:self._append(
                "New Slab",
                next(iter(project.materials)),
                0.20,
                "Mindlin-Q4",
            )
        )
        layout.addWidget(add)
        buttons=QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _append(self,*values):
        row=self.table.rowCount()
        self.table.insertRow(row)
        for column,value in enumerate(values):
            self.table.setItem(
                row,column,QTableWidgetItem(str(value))
            )

    def accept(self):
        try:
            sections={}
            for row in range(self.table.rowCount()):
                name=self.table.item(row,0).text().strip()
                material=self.table.item(row,1).text().strip()
                thickness=float(self.table.item(row,2).text())
                formulation=self.table.item(row,3).text().strip()
                if not name:
                    raise ValueError("Slab section name cannot be empty.")
                if material not in self.project.materials:
                    raise ValueError(
                        f"Undefined material '{material}' "
                        f"in slab section '{name}'."
                    )
                if thickness<=0:
                    raise ValueError(
                        "Slab thickness must be positive."
                    )
                sections[name]=AreaSection(
                    name,material,thickness,
                    formulation or "Mindlin-Q4",
                )
            if not sections:
                raise ValueError(
                    "At least one slab section is required."
                )
            used={area.section for area in self.project.areas.values()}
            missing=used-set(sections)
            if missing:
                raise ValueError(
                    "Cannot remove slab sections currently in use: "
                    + ", ".join(sorted(missing))
                )
            self.project.area_sections=sections
            self.project.dirty=True
        except Exception as exc:
            QMessageBox.warning(
                self,"Slab Sections",str(exc)
            )
            return
        super().accept()
