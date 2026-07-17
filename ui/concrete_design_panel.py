from __future__ import annotations

from PySide6.QtWidgets import (
    QLabel, QTableWidget, QTableWidgetItem, QTabWidget,
    QVBoxLayout, QWidget,
)

from design.concrete import ConcreteDesignResult


class ConcreteDesignPanel(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        layout=QVBoxLayout(self)
        self.notice=QLabel(
            "Run analysis, then run Preliminary Concrete Design."
        )
        self.notice.setWordWrap(True)
        layout.addWidget(self.notice)
        self.tabs=QTabWidget()
        self.beams=QTableWidget(0,6)
        self.beams.setHorizontalHeaderLabels([
            "Beam","Mu kN.m","As req mm²",
            "Bars","Diameter mm","Label",
        ])
        self.slabs=QTableWidget(0,9)
        self.slabs.setHorizontalHeaderLabels([
            "Slab","Mx","My","As X mm²/m","As Y mm²/m",
            "Spacing X","Spacing Y","Bar mm","Labels",
        ])
        self.tabs.addTab(self.beams,"Beam Reinforcement")
        self.tabs.addTab(self.slabs,"Slab Reinforcement")
        layout.addWidget(self.tabs)

    @staticmethod
    def _fill(table,rows):
        table.setRowCount(len(rows))
        for r,row in enumerate(rows):
            for c,value in enumerate(row):
                table.setItem(r,c,QTableWidgetItem(str(value)))
        table.resizeColumnsToContents()

    def clear_design(self):
        self.beams.setRowCount(0)
        self.slabs.setRowCount(0)
        self.notice.setText(
            "Run analysis, then run Preliminary Concrete Design."
        )

    def set_design(self,result:ConcreteDesignResult):
        beam_rows=[
            [
                f"F{x.frame_id}",
                f"{x.governing_moment_knm:.3f}",
                f"{x.required_area_mm2:.1f}",
                x.provided_bar_count,
                f"{x.bar_diameter_mm:g}",
                x.label,
            ]
            for x in result.beams.values()
        ]
        slab_rows=[
            [
                f"A{x.area_id}",
                f"{x.mx_knm_per_m:.3f}",
                f"{x.my_knm_per_m:.3f}",
                f"{x.as_x_mm2_per_m:.1f}",
                f"{x.as_y_mm2_per_m:.1f}",
                f"{x.spacing_x_mm:.0f} mm",
                f"{x.spacing_y_mm:.0f} mm",
                f"{x.bar_diameter_mm:g}",
                f"{x.label_x} / {x.label_y}",
            ]
            for x in result.slabs.values()
        ]
        self._fill(self.beams,beam_rows)
        self._fill(self.slabs,slab_rows)
        self.notice.setText(
            "<b>Preliminary design only.</b> "
            + " ".join(result.warnings)
        )
