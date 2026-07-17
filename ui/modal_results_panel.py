from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,QHBoxLayout,QLabel,QTableWidget,QTableWidgetItem,
    QVBoxLayout,QWidget,
)


class ModalResultsPanel(QWidget):
    mode_changed=Signal(int)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.result=None
        layout=QVBoxLayout(self)
        header=QHBoxLayout()
        self.summary=QLabel("No modal analysis results.")
        header.addWidget(self.summary,1)
        header.addWidget(QLabel("Display mode:"))
        self.mode_combo=QComboBox()
        self.mode_combo.currentIndexChanged.connect(
            lambda index:self.mode_changed.emit(index+1)
            if index>=0 else None
        )
        header.addWidget(self.mode_combo)
        layout.addLayout(header)
        self.table=QTableWidget(0,8)
        self.table.setHorizontalHeaderLabels([
            "Mode","Eigenvalue","ω rad/s","f Hz","T s",
            "Part X","Part Y","Part Z",
        ])
        layout.addWidget(self.table)

    def clear_results(self):
        self.result=None
        self.summary.setText("No modal analysis results.")
        self.mode_combo.clear()
        self.table.setRowCount(0)

    def set_results(self,result):
        self.result=result
        self.mode_combo.blockSignals(True)
        self.mode_combo.clear()
        self.mode_combo.addItems([
            f"Mode {mode.number} — T={mode.period_s:.4f}s"
            for mode in result.modes
        ])
        self.mode_combo.blockSignals(False)
        self.table.setRowCount(len(result.modes))
        for row,mode in enumerate(result.modes):
            values=[
                mode.number,f"{mode.eigenvalue:.6e}",
                f"{mode.circular_frequency:.6f}",
                f"{mode.frequency_hz:.6f}",
                f"{mode.period_s:.6f}",
                f"{mode.participation_x:.4f}",
                f"{mode.participation_y:.4f}",
                f"{mode.participation_z:.4f}",
            ]
            for column,value in enumerate(values):
                self.table.setItem(
                    row,column,QTableWidgetItem(str(value))
                )
        self.table.resizeColumnsToContents()
        self.summary.setText(
            f"{len(result.modes)} modes calculated. "
            f"Fundamental period = {result.modes[0].period_s:.6f} s"
        )
        if result.modes:
            self.mode_combo.setCurrentIndex(0)
