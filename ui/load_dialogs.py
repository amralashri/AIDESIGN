from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QHBoxLayout, QInputDialog, QLabel, QListWidget,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout,
)

from model.entities import LoadCombination, LoadPattern
from model.project import ProjectModel


class LoadPatternDialog(QDialog):
    def __init__(self,project:ProjectModel,parent=None):
        super().__init__(parent)
        self.project=project
        self.setWindowTitle("Define Load Patterns")
        self.resize(520,350)
        layout=QVBoxLayout(self)
        self.table=QTableWidget(0,2)
        self.table.setHorizontalHeaderLabels(
            ["Pattern Name","Self Weight Multiplier"]
        )
        layout.addWidget(self.table)
        for pattern in project.load_patterns.values():
            self._append(pattern.name,pattern.self_weight_multiplier)
        buttons_row=QHBoxLayout()
        add=QPushButton("Add Pattern")
        delete=QPushButton("Delete Selected")
        add.clicked.connect(lambda:self._append("NEW",0.0))
        delete.clicked.connect(self._delete)
        buttons_row.addWidget(add)
        buttons_row.addWidget(delete)
        buttons_row.addStretch(1)
        layout.addLayout(buttons_row)
        buttons=QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _append(self,name,multiplier):
        row=self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row,0,QTableWidgetItem(str(name)))
        self.table.setItem(row,1,QTableWidgetItem(str(multiplier)))

    def _delete(self):
        rows=sorted(
            {item.row() for item in self.table.selectedItems()},
            reverse=True,
        )
        for row in rows:
            self.table.removeRow(row)

    def accept(self):
        try:
            patterns={}
            for row in range(self.table.rowCount()):
                name=self.table.item(row,0).text().strip().upper()
                multiplier=float(self.table.item(row,1).text())
                if not name:
                    raise ValueError("Load pattern name cannot be empty.")
                if name in patterns:
                    raise ValueError(f"Duplicate load pattern: {name}")
                patterns[name]=LoadPattern(name,multiplier)
            if not patterns:
                raise ValueError("At least one load pattern is required.")

            used={
                load.pattern for load in self.project.joint_loads
            }
            for frame in self.project.frames.values():
                used.update(frame.distributed_loads)
            missing=used-set(patterns)
            if missing:
                raise ValueError(
                    "Cannot remove patterns currently assigned to the model: "
                    + ", ".join(sorted(missing))
                )

            self.project.load_patterns=patterns
            self.project.load_combinations={
                name:combo
                for name,combo in self.project.load_combinations.items()
                if set(combo.factors).issubset(patterns)
            }
            self.project.dirty=True
        except Exception as exc:
            QMessageBox.warning(self,"Load Patterns",str(exc))
            return
        super().accept()


class LoadCombinationDialog(QDialog):
    def __init__(self,project:ProjectModel,parent=None):
        super().__init__(parent)
        self.project=project
        self.setWindowTitle("Define Load Combinations")
        self.resize(760,430)
        layout=QVBoxLayout(self)

        self.combo_list=QListWidget()
        layout.addWidget(QLabel(
            "Combination syntax: PATTERN=factor, PATTERN=factor"
        ))
        layout.addWidget(self.combo_list)

        for combination in project.load_combinations.values():
            expression=", ".join(
                f"{pattern}={factor:g}"
                for pattern,factor in combination.factors.items()
            )
            self.combo_list.addItem(
                f"{combination.name} | {expression}"
            )

        row=QHBoxLayout()
        add=QPushButton("Add")
        edit=QPushButton("Edit")
        delete=QPushButton("Delete")
        standards=QPushButton("Generate Standard ULS/SLS")
        add.clicked.connect(self._add)
        edit.clicked.connect(self._edit)
        delete.clicked.connect(self._delete)
        standards.clicked.connect(self._standards)
        for button in (add,edit,delete,standards):
            row.addWidget(button)
        row.addStretch(1)
        layout.addLayout(row)

        buttons=QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _parse(text:str) -> tuple[str,dict[str,float]]:
        if "|" not in text:
            raise ValueError("Use: Combination Name | DEAD=1.2, LIVE=1.6")
        name,expression=text.split("|",1)
        name=name.strip()
        factors={}
        for item in expression.split(","):
            if not item.strip():
                continue
            pattern,factor=item.split("=",1)
            factors[pattern.strip().upper()]=float(factor)
        if not name or not factors:
            raise ValueError("Combination name and factors are required.")
        return name,factors

    def _prompt(self,initial=""):
        text,ok=QInputDialog.getText(
            self,"Load Combination",
            "Name | PATTERN=factor, PATTERN=factor:",
            text=initial,
        )
        return text if ok else None

    def _add(self):
        text=self._prompt("New Combination | DEAD=1.0")
        if text:
            self.combo_list.addItem(text)

    def _edit(self):
        item=self.combo_list.currentItem()
        if item is None:
            return
        text=self._prompt(item.text())
        if text:
            item.setText(text)

    def _delete(self):
        row=self.combo_list.currentRow()
        if row>=0:
            self.combo_list.takeItem(row)

    def _standards(self):
        names=set(self.project.load_patterns)
        standards=[]
        if "DEAD" in names:
            standards.append("ULS 1.4D | DEAD=1.4")
        if {"DEAD","LIVE"}.issubset(names):
            standards.extend([
                "ULS 1.2D+1.6L | DEAD=1.2, LIVE=1.6",
                "SLS D+L | DEAD=1.0, LIVE=1.0",
            ])
        existing={
            item.text().split("|",1)[0].strip()
            for item in [
                self.combo_list.item(i)
                for i in range(self.combo_list.count())
            ]
        }
        for text in standards:
            if text.split("|",1)[0].strip() not in existing:
                self.combo_list.addItem(text)

    def accept(self):
        try:
            combinations={}
            for index in range(self.combo_list.count()):
                name,factors=self._parse(
                    self.combo_list.item(index).text()
                )
                unknown=set(factors)-set(self.project.load_patterns)
                if unknown:
                    raise ValueError(
                        f"{name}: undefined patterns "
                        + ", ".join(sorted(unknown))
                    )
                if name in combinations:
                    raise ValueError(f"Duplicate combination: {name}")
                combinations[name]=LoadCombination(name,factors)
            self.project.load_combinations=combinations
            self.project.dirty=True
        except Exception as exc:
            QMessageBox.warning(
                self,"Load Combinations",str(exc)
            )
            return
        super().accept()
