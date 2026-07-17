from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QFileDialog, QMessageBox
from model.project import ProjectModel
from ui.main_window import MainWindow


class AIDesignApplication(MainWindow):
    VERSION = "1.6.0"

    def __init__(self) -> None:
        self.settings = QSettings("AIDESIGN", "AIDESIGN")
        self.project_path: Path | None = None
        super().__init__(ProjectModel.default())
        self._connect_project_actions()
        self._restore_settings()
        self.update_title()

    def _connect_project_actions(self) -> None:
        self.action_new.triggered.connect(self.new_project)
        self.action_open.triggered.connect(self.open_project_dialog)
        self.action_save.triggered.connect(self.save_project)
        self.action_save_as.triggered.connect(self.save_project_as)
        self.action_exit.triggered.connect(self.close)
        self.ribbon.new_btn.clicked.connect(self.new_project)
        self.ribbon.open_btn.clicked.connect(self.open_project_dialog)
        self.ribbon.save_btn.clicked.connect(self.save_project)

    def update_title(self) -> None:
        name = self.project_path.stem if self.project_path else "Untitled"
        self.setWindowTitle(f"{name} - AIDESIGN {self.VERSION}")

    def new_project(self) -> None:
        if not self._confirm_discard():
            return
        self.project_path = None
        self.set_project(ProjectModel.default())
        self.update_title()
        self.log_message("New project created.")

    def open_project_dialog(self) -> None:
        if not self._confirm_discard():
            return
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open AIDESIGN Project", "",
            "AIDESIGN Project (*.aidesign);;JSON (*.json);;All Files (*)"
        )
        if not filename:
            return
        try:
            project = ProjectModel.load(filename)
        except Exception as exc:
            QMessageBox.critical(self, "Open Project", str(exc))
            return
        self.project_path = Path(filename)
        self.set_project(project)
        self.update_title()
        self.log_message(f"Opened: {filename}")

    def save_project(self) -> bool:
        if self.project_path is None:
            return self.save_project_as()
        try:
            self.project.save(self.project_path)
            self.project.dirty = False
            self.update_title()
            self.log_message(f"Saved: {self.project_path}")
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Save Project", str(exc))
            return False

    def save_project_as(self) -> bool:
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save AIDESIGN Project", "Untitled.aidesign",
            "AIDESIGN Project (*.aidesign)"
        )
        if not filename:
            return False
        if not filename.lower().endswith(".aidesign"):
            filename += ".aidesign"
        self.project_path = Path(filename)
        return self.save_project()

    def _confirm_discard(self) -> bool:
        if not self.project.dirty:
            return True
        answer = QMessageBox.question(
            self, "Unsaved Changes",
            "The project contains unsaved changes. Continue and discard them?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _restore_settings(self) -> None:
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)

    def closeEvent(self, event) -> None:  # noqa: N802
        if not self._confirm_discard():
            event.ignore()
            return
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        event.accept()
