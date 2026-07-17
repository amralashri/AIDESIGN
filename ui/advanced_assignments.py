
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,QDialog,QDialogButtonBox,QDoubleSpinBox,QFormLayout,QGridLayout,
    QHBoxLayout,QInputDialog,QLabel,QLineEdit,QMessageBox,
    QPushButton,QVBoxLayout,
)

from model.project import ProjectModel


DOF_NAMES=("U1","U2","U3","R1","R2","R3")


class FrameReleaseDialog(QDialog):
    def __init__(self,project:ProjectModel,frame_ids:list[int],parent=None):
        super().__init__(parent)
        self.project=project
        self.frame_ids=frame_ids
        self.setWindowTitle("Assign Frame End Releases")
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"Selected frames: {len(frame_ids)}<br>"
            "Checked DOFs transfer no corresponding end force."
        ))
        grid=QGridLayout()
        grid.addWidget(QLabel("DOF"),0,0)
        grid.addWidget(QLabel("I End"),0,1)
        grid.addWidget(QLabel("J End"),0,2)
        self.i_checks=[]
        self.j_checks=[]
        for row,name in enumerate(DOF_NAMES,start=1):
            grid.addWidget(QLabel(name),row,0)
            ci=QCheckBox()
            cj=QCheckBox()
            grid.addWidget(ci,row,1)
            grid.addWidget(cj,row,2)
            self.i_checks.append(ci)
            self.j_checks.append(cj)
        layout.addLayout(grid)

        presets=QHBoxLayout()
        pin_i=QPushButton("Pin I")
        pin_j=QPushButton("Pin J")
        pin_both=QPushButton("Pin Both")
        clear=QPushButton("Clear")
        pin_i.clicked.connect(lambda:self._pin("i"))
        pin_j.clicked.connect(lambda:self._pin("j"))
        pin_both.clicked.connect(lambda:self._pin("both"))
        clear.clicked.connect(self._clear)
        for button in (pin_i,pin_j,pin_both,clear):
            presets.addWidget(button)
        layout.addLayout(presets)

        buttons=QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _pin(self,end):
        # Release local bending rotations R2/R3.
        if end in ("i","both"):
            self.i_checks[4].setChecked(True)
            self.i_checks[5].setChecked(True)
        if end in ("j","both"):
            self.j_checks[4].setChecked(True)
            self.j_checks[5].setChecked(True)

    def _clear(self):
        for check in self.i_checks+self.j_checks:
            check.setChecked(False)

    def accept(self):
        release_i=tuple(check.isChecked() for check in self.i_checks)
        release_j=tuple(check.isChecked() for check in self.j_checks)
        for frame_id in self.frame_ids:
            self.project.assign_frame_releases(
                frame_id,release_i,release_j
            )
        super().accept()


class DiaphragmDialog(QDialog):
    def __init__(self,project:ProjectModel,node_ids:list[int],parent=None):
        super().__init__(parent)
        self.project=project
        self.node_ids=node_ids
        self.setWindowTitle("Assign Rigid Diaphragm")
        layout=QFormLayout(self)
        self.name=QLineEdit("D1")
        self.ux=QCheckBox("Tie global Ux")
        self.uy=QCheckBox("Tie global Uy")
        self.rz=QCheckBox("Tie global Rz")
        self.ux.setChecked(True)
        self.uy.setChecked(True)
        self.rz.setChecked(True)
        layout.addRow("Diaphragm name:",self.name)
        layout.addRow(self.ux)
        layout.addRow(self.uy)
        layout.addRow(self.rz)
        layout.addRow(QLabel(f"Selected joints: {len(node_ids)}"))
        buttons=QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def accept(self):
        try:
            self.project.assign_diaphragm(
                self.name.text().strip() or "D1",
                self.node_ids,
                self.ux.isChecked(),
                self.uy.isChecked(),
                self.rz.isChecked(),
            )
        except Exception as exc:
            QMessageBox.warning(self,"Rigid Diaphragm",str(exc))
            return
        super().accept()


class RigidEndOffsetDialog(QDialog):
    def __init__(self,project:ProjectModel,frame_ids:list[int],parent=None):
        super().__init__(parent)
        self.project=project
        self.frame_ids=frame_ids
        self.setWindowTitle("Assign Rigid End Offsets")
        layout=QFormLayout(self)
        layout.addRow(QLabel(
            f"Selected frames: {len(frame_ids)}<br>"
            "Offsets are measured from the joint toward the member interior."
        ))
        self.offset_i=QDoubleSpinBox()
        self.offset_j=QDoubleSpinBox()
        for control in (self.offset_i,self.offset_j):
            control.setRange(0.0,1000.0)
            control.setDecimals(4)
            control.setSuffix(" m")
            control.setSingleStep(0.05)
        if len(frame_ids)==1:
            frame=project.frames[frame_ids[0]]
            self.offset_i.setValue(frame.rigid_offset_i)
            self.offset_j.setValue(frame.rigid_offset_j)
        layout.addRow("I-end offset:",self.offset_i)
        layout.addRow("J-end offset:",self.offset_j)
        buttons=QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def accept(self):
        try:
            for frame_id in self.frame_ids:
                self.project.assign_frame_rigid_offsets(
                    frame_id,self.offset_i.value(),self.offset_j.value()
                )
        except Exception as exc:
            QMessageBox.warning(self,"Rigid End Offsets",str(exc))
            return
        super().accept()
