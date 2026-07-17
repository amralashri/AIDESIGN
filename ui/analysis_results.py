from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from analysis.results import AnalysisResult
from model.project import ProjectModel


class AnalysisResultsDialog(QDialog):
    def __init__(
        self,
        project: ProjectModel,
        result: AnalysisResult,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Analysis Results - {result.case_name}")
        self.resize(1050, 650)

        layout = QVBoxLayout(self)
        summary = QLabel(
            f"Case: <b>{result.case_name}</b> &nbsp;&nbsp; "
            f"Maximum joint translation: "
            f"<b>{result.max_translation*1000.0:.6f} mm</b>"
        )
        layout.addWidget(summary)

        tabs = QTabWidget()
        tabs.addTab(self._joint_displacements(project, result), "Joint Displacements")
        tabs.addTab(self._joint_reactions(project, result), "Support Reactions")
        tabs.addTab(self._frame_forces(project, result), "Frame End Forces")
        layout.addWidget(tabs)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        layout.addLayout(buttons)

    @staticmethod
    def _make_table(headers: list[str], rows: list[list[str]]) -> QWidget:
        table = QTableWidget(len(rows), len(headers))
        table.setHorizontalHeaderLabels(headers)
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                table.setItem(
                    row_index, column_index,
                    QTableWidgetItem(value),
                )
        table.resizeColumnsToContents()
        return table

    def _joint_displacements(
        self,
        project: ProjectModel,
        result: AnalysisResult,
    ) -> QWidget:
        rows = []
        for node_id in result.node_order:
            u = result.node_displacement(node_id)
            rows.append([
                f"N{node_id}",
                *(f"{value*1000.0:.6f}" for value in u[:3]),
                *(f"{value:.8e}" for value in u[3:]),
            ])
        return self._make_table(
            ["Joint", "Ux mm", "Uy mm", "Uz mm", "Rx rad", "Ry rad", "Rz rad"],
            rows,
        )

    def _joint_reactions(
        self,
        project: ProjectModel,
        result: AnalysisResult,
    ) -> QWidget:
        rows = []
        for node_id in result.node_order:
            if not any(project.nodes[node_id].restraint):
                continue
            reaction = result.node_reaction(node_id)
            rows.append([
                f"N{node_id}",
                *(f"{value:.6f}" for value in reaction),
            ])
        return self._make_table(
            ["Joint", "Fx kN", "Fy kN", "Fz kN",
             "Mx kN.m", "My kN.m", "Mz kN.m"],
            rows,
        )

    def _frame_forces(
        self,
        project: ProjectModel,
        result: AnalysisResult,
    ) -> QWidget:
        rows = []
        for frame_id, frame_result in sorted(result.frame_results.items()):
            f = frame_result.local_end_forces
            rows.append([
                f"F{frame_id}",
                *(f"{value:.6f}" for value in f),
            ])
        headers = [
            "Frame",
            "Pi", "V2i", "V3i", "Ti", "M2i", "M3i",
            "Pj", "V2j", "V3j", "Tj", "M2j", "M3j",
        ]
        return self._make_table(headers, rows)
