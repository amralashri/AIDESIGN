
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,QDialog,QDialogButtonBox,QDoubleSpinBox,
    QFormLayout,QLabel,QLineEdit,QTextEdit,QVBoxLayout,QWidget,
)

from model.project import ProjectModel


class CodeSettingsWidget(QWidget):
    def __init__(self,project:ProjectModel,parent=None):
        super().__init__(parent)
        self.project=project
        layout=QFormLayout(self)

        self.concrete=QComboBox()
        self.concrete.addItems([
            "SBC 304 / ACI 318-19",
            "ACI 318-19",
            "ACI 318-25",
            "Eurocode 2",
            "BS 8110 (Legacy)",
        ])
        self.loading=QComboBox()
        self.loading.addItems([
            "SBC 301","ASCE 7-22","ASCE 7-16","Eurocode 1"
        ])
        self.steel=QComboBox()
        self.steel.addItems([
            "SBC 306 / AISC 360",
            "AISC 360-22","AISC 360-16","Eurocode 3"
        ])
        self.seismic=QComboBox()
        self.seismic.addItems([
            "SBC 301","ASCE 7-22","ASCE 7-16","Eurocode 8"
        ])
        self.wind=QComboBox()
        self.wind.addItems([
            "SBC 301","ASCE 7-22","ASCE 7-16","Eurocode 1"
        ])
        self.importance=QDoubleSpinBox()
        self.importance.setRange(0.5,2.0)
        self.importance.setDecimals(3)
        self.phi_flexure=QDoubleSpinBox()
        self.phi_flexure.setRange(0.1,1.0)
        self.phi_flexure.setDecimals(3)
        self.phi_shear=QDoubleSpinBox()
        self.phi_shear.setRange(0.1,1.0)
        self.phi_shear.setDecimals(3)
        self.steel_method=QComboBox()
        self.steel_method.addItems(["LRFD","ASD"])
        self.notes=QTextEdit()
        self.notes.setMaximumHeight(80)

        layout.addRow("Concrete design:",self.concrete)
        layout.addRow("Loading:",self.loading)
        layout.addRow("Steel design:",self.steel)
        layout.addRow("Seismic:",self.seismic)
        layout.addRow("Wind:",self.wind)
        layout.addRow("Importance factor:",self.importance)
        layout.addRow("φ flexure:",self.phi_flexure)
        layout.addRow("φ shear:",self.phi_shear)
        layout.addRow("Steel method:",self.steel_method)
        layout.addRow("Project notes:",self.notes)
        self.load_from_project()

    def load_from_project(self):
        c=self.project.design_codes
        self.concrete.setCurrentText(c.concrete_code)
        self.loading.setCurrentText(c.loading_code)
        self.steel.setCurrentText(c.steel_code)
        self.seismic.setCurrentText(c.seismic_code)
        self.wind.setCurrentText(c.wind_code)
        self.importance.setValue(c.importance_factor)
        self.phi_flexure.setValue(c.concrete_phi_flexure)
        self.phi_shear.setValue(c.concrete_phi_shear)
        self.steel_method.setCurrentText(c.steel_resistance_method)
        self.notes.setPlainText(c.notes)

    def apply_to_project(self):
        c=self.project.design_codes
        c.concrete_code=self.concrete.currentText()
        c.loading_code=self.loading.currentText()
        c.steel_code=self.steel.currentText()
        c.seismic_code=self.seismic.currentText()
        c.wind_code=self.wind.currentText()
        c.importance_factor=self.importance.value()
        c.concrete_phi_flexure=self.phi_flexure.value()
        c.concrete_phi_shear=self.phi_shear.value()
        c.steel_resistance_method=self.steel_method.currentText()
        c.notes=self.notes.toPlainText().strip()
        self.project.dirty=True


class CodeSettingsDialog(QDialog):
    def __init__(self,project,parent=None):
        super().__init__(parent)
        self.setWindowTitle("Codes and Standards")
        self.resize(540,520)
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel(
            "<b>Project Design Codes</b><br>"
            "These selections are saved with the model and used by "
            "design modules where implemented."
        ))
        self.editor=CodeSettingsWidget(project,self)
        layout.addWidget(self.editor)
        buttons=QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        self.editor.apply_to_project()
        super().accept()
