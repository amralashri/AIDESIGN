from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QTabWidget,
    QToolButton, QVBoxLayout, QWidget,
)


class RibbonButton(QToolButton):
    def __init__(
        self,
        symbol: str,
        title: str,
        tooltip: str = "",
        checkable: bool = False,
        compact: bool = False,
    ):
        super().__init__()
        self.setText(symbol or title)
        self.setToolTip(tooltip or title)
        self.setCheckable(checkable)
        self.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextUnderIcon
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if compact:
            self.setMinimumSize(42, 36)
        else:
            self.setMinimumSize(48, 44)
        self.setStyleSheet("""
            QToolButton {
                border: 1px solid transparent;
                border-radius: 7px;
                padding: 2px 4px;
                background: transparent;
                color: #263238;
                font-size: 13pt;
            }
            QToolButton:hover {
                background: #e8f3fb;
                border-color: #9cc9e7;
            }
            QToolButton:pressed {
                background: #d4e9f7;
            }
            QToolButton:checked {
                background: #d9ecfa;
                border-color: #4d9fd3;
                color: #075985;
                font-weight: 600;
            }
        """)


class RibbonGroup(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("RibbonGroup")
        self.setStyleSheet("""
            QFrame#RibbonGroup {
                background: #ffffff;
                border: 1px solid #d7e0e7;
                border-radius: 8px;
            }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 3, 4, 2)
        outer.setSpacing(3)

        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(4)
        self.grid.setVerticalSpacing(3)
        outer.addLayout(self.grid, 1)

        label = QLabel(title)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            "color:#607d8b;font-size:8pt;font-weight:600;"
        )
        outer.addWidget(label)

        self._column = 0

    def add_button(
        self,
        title: str,
        symbol: str = "",
        tooltip: str = "",
        checkable: bool = False,
        row_span: int = 2,
    ):
        button = RibbonButton(
            symbol, title, tooltip, checkable,
            compact=(row_span == 1),
        )
        self.grid.addWidget(
            button, 0, self._column, row_span, 1
        )
        self._column += 1
        return button


class RibbonPage(QWidget):
    def __init__(self):
        super().__init__()
        self.row = QHBoxLayout(self)
        self.row.setContentsMargins(4, 3, 4, 3)
        self.row.setSpacing(4)
        self.row.setAlignment(Qt.AlignmentFlag.AlignLeft)

    def group(self, title: str):
        group = RibbonGroup(title)
        self.row.addWidget(group)
        return group


class RibbonWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDocumentMode(True)
        self.setMaximumHeight(96)
        self.setStyleSheet("""
            QTabWidget::pane {
                border: 0;
                background: #f4f7f9;
            }
            QTabBar::tab {
                background: #edf2f5;
                color: #455a64;
                padding: 7px 18px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #075985;
                border-bottom: 2px solid #2196f3;
            }
            QTabBar::tab:hover {
                background: #e2eef6;
            }
        """)

        home = RibbonPage()
        draw = RibbonPage()
        define = RibbonPage()
        assign = RibbonPage()
        analyze = RibbonPage()
        display = RibbonPage()
        design = RibbonPage()
        codes = RibbonPage()
        for page, name in [
            (home, "Home"),
            (draw, "Draw"),
            (define, "Define"),
            (assign, "Assign"),
            (analyze, "Analyze"),
            (display, "Display"),
            (design, "Design"),
            (codes, "Codes"),
        ]:
            self.addTab(page, name)

        # HOME: deliberately organized as the main working row.
        project = home.group("Project")
        self.new_btn = project.add_button("New", "＋")
        self.open_btn = project.add_button("Open", "⌂")
        self.save_btn = project.add_button("Save", "▣")

        modify = home.group("Modify")
        self.select_btn = modify.add_button(
            "Select", "↖", checkable=True
        )
        self.delete_btn = modify.add_button("Delete", "×")
        self.select_btn.setChecked(True)

        model = home.group("Create Model")
        self.beam_btn = model.add_button(
            "Beam", "╱", checkable=True
        )
        self.column_btn = model.add_button(
            "Column", "■", checkable=True
        )
        self.slab_btn = model.add_button(
            "Slab", "▰", checkable=True
        )

        analysis = home.group("Analysis")
        self.check_btn = analysis.add_button("Check", "✓")
        self.run_btn = analysis.add_button("Run", "▶")

        view = home.group("View")
        self.fit_btn = view.add_button("Fit", "⛶")
        self.reset3d_btn = view.add_button("Isometric", "◇")

        # DRAW
        objects = draw.group("Structural Objects")
        # Reuse same logical controls via additional buttons in draw tab.
        self.draw_beam_btn = objects.add_button(
            "Beam", "╱", checkable=True
        )
        self.draw_column_btn = objects.add_button(
            "Column", "■", checkable=True
        )
        self.draw_slab_btn = objects.add_button(
            "Slab", "▰", checkable=True
        )

        aids = draw.group("Drawing Aids")
        self.snap_btn = aids.add_button(
            "Snap", "⌖", checkable=True
        )
        self.snap_btn.setChecked(True)
        self.ortho_btn = aids.add_button(
            "Ortho", "⊥", checkable=True
        )

        # DEFINE
        data = define.group("Model Data")
        self.grid_btn = data.add_button("Grids", "#")
        self.story_btn = data.add_button("Stories", "≡")
        self.material_btn = data.add_button("Materials", "◆")
        self.section_btn = data.add_button("Frames", "▭")
        self.slabsection_btn = data.add_button("Slabs", "▰")

        loads = define.group("Loads")
        self.pattern_btn = loads.add_button("Patterns", "↓")
        self.combo_btn = loads.add_button("Combinations", "Σ")

        # ASSIGN
        assignments = assign.group("Assignments")
        self.support_btn = assignments.add_button("Fixed Base", "⌂")
        self.load_btn = assignments.add_button("Frame UDL", "⇩")
        self.area_load_btn = assignments.add_button("Slab Load", "⇊")
        self.release_btn = assignments.add_button("Releases", "○")
        self.offset_btn = assignments.add_button("Rigid Offsets", "⇥")
        self.diaphragm_btn = assignments.add_button("Diaphragm", "D")

        # ANALYZE
        analysis_tab = analyze.group("Model Analysis")
        self.analyze_check_btn = analysis_tab.add_button("Check", "✓")
        self.analyze_run_btn = analysis_tab.add_button("Run", "▶")
        self.pdelta_btn = analysis_tab.add_button("P-Delta", "PΔ")
        self.shell_quality_btn = analysis_tab.add_button("Shell Quality", "Q4")

        # DISPLAY
        results = display.group("Analysis Results")
        self.deformed_btn = results.add_button("Deformed", "〰")
        self.moment_btn = results.add_button("Moment", "⌒")
        self.shear_btn = results.add_button("Shear", "⟋")


        # Additional display modes.
        contours = display.group("Slab Contours")
        self.contour_mx_btn = contours.add_button("Mx", "▨")
        self.contour_my_btn = contours.add_button("My", "▨")
        self.contour_mmax_btn = contours.add_button("Mmax", "M+")
        self.contour_mmin_btn = contours.add_button("Mmin", "M−")
        self.contour_qx_btn = contours.add_button("Qx", "▧")
        self.contour_def_btn = contours.add_button("Deflection", "◫")

        concrete = design.group("Concrete Design")
        self.concrete_design_btn = concrete.add_button(
            "Run Design", "RC"
        )
        self.advanced_design_btn = concrete.add_button(
            "Advanced Checks", "✓RC"
        )
        self.beam_rebar_btn = concrete.add_button(
            "Beam Rebar", "≣"
        )
        self.slab_rebar_x_btn = concrete.add_button(
            "Slab Rebar X", "════"
        )
        self.slab_rebar_y_btn = concrete.add_button(
            "Slab Rebar Y", "||||"
        )
        self.slab_as_x_btn = concrete.add_button(
            "As X Contour", "AsX"
        )
        self.slab_as_y_btn = concrete.add_button(
            "As Y Contour", "AsY"
        )


        modal_group = analyze.group("Dynamic Analysis")
        self.modal_run_btn = modal_group.add_button("Modal", "≈")
        self.mode_shape_btn = modal_group.add_button("Mode Shape", "∿")


        animation = display.group("Animation")
        self.animate_deformed_btn = animation.add_button(
            "Animate Deformed", "▶〰"
        )
        self.animate_mode_btn = animation.add_button(
            "Animate Mode", "▶∿"
        )
        self.stop_animation_btn = animation.add_button(
            "Stop", "■"
        )

        standards = codes.group("Codes & Standards")
        self.code_settings_btn = standards.add_button(
            "Project Codes", "§"
        )
        self.code_summary_btn = standards.add_button(
            "Code Summary", "CODE"
        )
