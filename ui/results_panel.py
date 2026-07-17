from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QTabWidget, QVBoxLayout, QWidget,
)

from analysis.results import AnalysisResult
from model.project import ProjectModel
from core.units import UnitSystem


class ResultsPanel(QWidget):
    """Persistent results browser embedded in the main window."""

    result_mode_changed = __import__(
        "PySide6.QtCore", fromlist=["Signal"]
    ).Signal(str)

    MODES = [
        "None", "Deformed", "Moment", "Shear",
        "Axial", "Torsion", "Reactions",
        "Slab Mx", "Slab My", "Slab Mxy",
        "Slab Mmax", "Slab Mmin",
        "Slab Qx", "Slab Qy", "Slab Deflection",
        "Beam Rebar", "Slab Rebar X", "Slab Rebar Y",
        "Slab As X", "Slab As Y",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project: ProjectModel | None = None
        self.result: AnalysisResult | None = None
        self.unit_system=UnitSystem(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        header = QHBoxLayout()
        self.summary = QLabel("No analysis results.")
        header.addWidget(self.summary, 1)
        header.addWidget(QLabel("Display on model:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(self.MODES)
        self.mode_combo.currentTextChanged.connect(
            self.result_mode_changed.emit
        )
        header.addWidget(self.mode_combo)
        layout.addLayout(header)

        self.tabs = QTabWidget()
        self.displacement_table = self._table([
            "Joint", "Ux mm", "Uy mm", "Uz mm",
            "Rx rad", "Ry rad", "Rz rad",
        ])
        self.reaction_table = self._table([
            "Joint", "Fx kN", "Fy kN", "Fz kN",
            "Mx kN.m", "My kN.m", "Mz kN.m",
        ])
        self.force_table = self._table([
            "Frame",
            "Pi", "V2i", "V3i", "Ti", "M2i", "M3i",
            "Pj", "V2j", "V3j", "Tj", "M2j", "M3j",
        ])
        self.tabs.addTab(self.displacement_table, "Joint Displacements")
        self.tabs.addTab(self.reaction_table, "Support Reactions")
        self.area_table = self._table([
            "Area","Area m²","Nx","Ny","Nxy",
            "Mx","My","Mxy","Mmax","Mmin","Angle","Qx","Qy",
        ])
        self.tabs.addTab(self.force_table, "Frame End Forces")
        self.tabs.addTab(self.area_table, "Slab / Shell Resultants")
        layout.addWidget(self.tabs)

    def set_unit_system(self,unit_system):
        try:self.unit_system.changed.disconnect(self.refresh_units)
        except (TypeError,RuntimeError):pass
        self.unit_system=unit_system
        self.unit_system.changed.connect(self.refresh_units)
        self.refresh_units()

    def refresh_units(self):
        if self.project is not None and self.result is not None:
            self.set_results(self.project,self.result)

    @staticmethod
    def _table(headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        return table

    @staticmethod
    def _populate(table, rows):
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )
                table.setItem(row_index, column_index, item)
        table.resizeColumnsToContents()

    def clear_results(self):
        self.project = None
        self.result = None
        self.summary.setText("No analysis results.")
        for table in (
            self.displacement_table,
            self.reaction_table,
            self.force_table,
            self.area_table,
        ):
            table.setRowCount(0)
        self.mode_combo.setCurrentText("None")


    def set_results(self,project,result):
        self.project=project
        self.result=result
        u=self.unit_system
        self.summary.setText(
            f"Case: <b>{result.case_name}</b> &nbsp;&nbsp; "
            f"Maximum translation: <b>{u.displacement_component(result.max_translation)}</b>"
        )
        du,fu,mu,au=u.unit("displacement"),u.unit("force"),u.unit("moment"),u.unit("area")

        dr=[]
        for node_id in result.node_order:
            v=result.node_displacement(node_id)
            dr.append([f"N{node_id}",*(f"{u.convert(x,'displacement'):.6f}" for x in v[:3]),
                       *(f"{x:.8e}" for x in v[3:])])
        self.displacement_table.setHorizontalHeaderLabels(
            ["Joint",f"Ux {du}",f"Uy {du}",f"Uz {du}","Rx rad","Ry rad","Rz rad"]
        )
        self._populate(self.displacement_table,dr)

        rr=[]
        for node_id in result.node_order:
            if not any(project.nodes[node_id].restraint):continue
            v=result.node_reaction(node_id)
            rr.append([f"N{node_id}",*(f"{u.convert(x,'force'):.6f}" for x in v[:3]),
                       *(f"{u.convert(x,'moment'):.6f}" for x in v[3:])])
        self.reaction_table.setHorizontalHeaderLabels(
            ["Joint",f"Fx {fu}",f"Fy {fu}",f"Fz {fu}",f"Mx {mu}",f"My {mu}",f"Mz {mu}"]
        )
        self._populate(self.reaction_table,rr)

        fr=[]
        for frame_id,item in sorted(result.frame_results.items()):
            row=[f"F{frame_id}"]
            for i,x in enumerate(item.local_end_forces):
                q="moment" if i in (3,4,5,9,10,11) else "force"
                row.append(f"{u.convert(x,q):.6f}")
            fr.append(row)
        self.force_table.setHorizontalHeaderLabels(
            ["Frame",f"Pi {fu}",f"V2i {fu}",f"V3i {fu}",f"Ti {mu}",f"M2i {mu}",
             f"M3i {mu}",f"Pj {fu}",f"V2j {fu}",f"V3j {fu}",f"Tj {mu}",
             f"M2j {mu}",f"M3j {mu}"]
        )
        self._populate(self.force_table,fr)

        ar=[]
        for area_id,item in sorted(result.area_results.items()):
            r=item.resultants
            ar.append([f"A{area_id}",f"{u.convert(item.area,'area'):.4f}",
                       *(f"{u.convert(r[k],'force'):.6f}" for k in
                         ("Nx","Ny","Nxy","Mx","My","Mxy","Mmax","Mmin")),
                       f"{r.get('Mangle',0.0):.3f}",
                       *(f"{u.convert(r[k],'force'):.6f}" for k in ("Qx","Qy"))])
        self.area_table.setHorizontalHeaderLabels(
            ["Area",f"Area {au}",f"Nx {fu}/m",f"Ny {fu}/m",f"Nxy {fu}/m",
             f"Mx {fu}·m/m",f"My {fu}·m/m",f"Mxy {fu}·m/m",
             f"Mmax {fu}·m/m",f"Mmin {fu}·m/m","Angle deg",
             f"Qx {fu}/m",f"Qy {fu}/m"]
        )
        self._populate(self.area_table,ar)
