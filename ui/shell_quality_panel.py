from __future__ import annotations

from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from analysis.shell_quality import evaluate_project_shells


class ShellQualityPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.summary = QLabel("No shell quality report.")
        layout.addWidget(self.summary)
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "Area", "Area m²", "Aspect", "Min Angle", "Max Angle",
            "Skew", "Warpage", "Jacobian", "Score", "Status",
        ])
        layout.addWidget(self.table)

    def refresh(self, project):
        results = evaluate_project_shells(project)
        self.table.setRowCount(len(results))
        poor = warning = 0
        for row, item in enumerate(results):
            if item.status == "Poor":
                poor += 1
            elif item.status == "Warning":
                warning += 1
            values = [
                f"A{item.area_id}", f"{item.area:.4f}", f"{item.aspect_ratio:.3f}",
                f"{item.minimum_angle_deg:.2f}°", f"{item.maximum_angle_deg:.2f}°",
                f"{item.skew_deg:.2f}°", f"{item.warpage_ratio:.6f}",
                f"{item.jacobian_ratio:.4f}", f"{item.quality_score:.3f}", item.status,
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()
        self.summary.setText(
            f"Shells: {len(results)} | Good: {len(results)-poor-warning} | "
            f"Warnings: {warning} | Poor: {poor}"
        )
