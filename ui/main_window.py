from __future__ import annotations

from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (
    QComboBox, QDockWidget, QFileDialog, QInputDialog, QLabel,
    QMainWindow, QMessageBox, QSplitter, QStatusBar, QTextEdit,
    QToolBar, QToolButton, QVBoxLayout, QWidget,
)

from analysis.model_check import check_model
from analysis.solver import LinearStaticSolver,PDeltaSolver
from model.project import ProjectModel
from ui.define_dialogs import (
    FrameSectionDialog, GridDialog, MaterialDialog,
    SlabSectionDialog, StoryDialog,
)
from ui.load_dialogs import LoadCombinationDialog, LoadPatternDialog
from ui.results_panel import ResultsPanel
from ui.concrete_design_panel import ConcreteDesignPanel
from ui.advanced_design_panel import AdvancedDesignPanel
from design.advanced_checks import run_advanced_design
from design.concrete import ConcreteDesignSettings,design_concrete
from ui.explorer import ModelExplorer
from ui.properties import PropertyGrid
from ui.ribbon import RibbonWidget
from ui.theme import LIGHT_STYLESHEET
from ui.viewport2d import PlanViewport
from ui.viewport3d import Viewport3D
from core.units import UnitSystem
from ui.unit_status import UnitStatusWidget
from analysis.modal_solver import ModalSolver
from ui.modal_results_panel import ModalResultsPanel
from ui.code_settings import CodeSettingsDialog,CodeSettingsWidget
from ui.advanced_assignments import (
    DiaphragmDialog,FrameReleaseDialog,RigidEndOffsetDialog,
)
from importers.dxf import import_dxf


class MainWindow(QMainWindow):
    def __init__(self, project: ProjectModel):
        super().__init__()
        self.project=project
        self.analysis_result=None
        self.concrete_design_result=None
        self.advanced_design_result=None
        self.unit_system=UnitSystem(self)
        self.modal_result=None
        self.animation_timer=QTimer(self)
        self.animation_timer.setInterval(40)
        self.animation_angle=0.0
        self.animation_target="None"
        self.animation_speed=1.0
        self.setStyleSheet(LIGHT_STYLESHEET)
        self.resize(1600,900)
        self.setDockOptions(
            QMainWindow.DockOption.AllowNestedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
            | QMainWindow.DockOption.AnimatedDocks
        )
        self._build_actions()
        self._build_menu()
        self._build_ribbon()
        self._build_story_toolbar()
        self._build_central()
        self._build_vertical_toolbar()
        self._build_docks()
        self._build_code_dock()
        self._build_status()
        self._wire()
        self.refresh_model()

    def _build_actions(self):
        self.action_new=QAction("New",self)
        self.action_new.setShortcut(QKeySequence.StandardKey.New)
        self.action_open=QAction("Open...",self)
        self.action_open.setShortcut(QKeySequence.StandardKey.Open)
        self.action_save=QAction("Save",self)
        self.action_save.setShortcut(QKeySequence.StandardKey.Save)
        self.action_save_as=QAction("Save As...",self)
        self.action_import_dxf=QAction("Import DXF...",self)
        self.action_import_dxf.setShortcut(QKeySequence("Ctrl+Shift+D"))
        self.action_exit=QAction("Exit",self)

        self.action_select=QAction("Select",self,checkable=True)
        self.action_select.setShortcut(QKeySequence("V"))
        self.action_beam=QAction("Draw Beam",self,checkable=True)
        self.action_beam.setShortcut(QKeySequence("B"))
        self.action_column=QAction("Draw Column",self,checkable=True)
        self.action_column.setShortcut(QKeySequence("C"))
        self.action_slab=QAction("Draw Slab",self,checkable=True)
        self.action_slab.setShortcut(QKeySequence("S"))
        self.action_mesh_slab=QAction("Divide / Mesh Selected Slab...",self)
        self.action_mesh_slab.setShortcut(QKeySequence("M"))
        self.mode_group=QActionGroup(self)
        self.mode_group.setExclusive(True)
        for action in (
            self.action_select,self.action_beam,
            self.action_column,self.action_slab,
        ):
            self.mode_group.addAction(action)
        self.action_select.setChecked(True)

        self.action_delete=QAction("Delete Selected",self)
        self.action_delete.setShortcut(QKeySequence.StandardKey.Delete)
        self.action_select_all=QAction("Select All Visible",self)
        self.action_select_all.setShortcut(QKeySequence.StandardKey.SelectAll)
        self.action_clear_selection=QAction("Clear Selection",self)
        self.action_clear_selection.setShortcut(QKeySequence("Shift+Esc"))

        self.action_grids=QAction("Grid Systems...",self)
        self.action_grids.setShortcut(QKeySequence("Ctrl+G"))
        self.action_stories=QAction("Story Data...",self)
        self.action_materials=QAction("Materials...",self)
        self.action_sections=QAction("Frame Sections...",self)
        self.action_sections.setShortcut(QKeySequence("Ctrl+Shift+F"))
        self.action_slab_sections=QAction("Slab Sections...",self)
        self.action_load_patterns=QAction("Load Patterns...",self)
        self.action_load_combinations=QAction("Load Combinations...",self)

        self.action_fixed_base=QAction("Assign Fixed Base",self)
        self.action_frame_udl=QAction("Assign Frame UDL...",self)
        self.action_area_load=QAction("Assign Slab Load...",self)
        self.action_frame_releases=QAction(
            "Assign Frame End Releases...",self
        )
        self.action_diaphragm=QAction(
            "Assign Rigid Diaphragm...",self
        )
        self.action_rigid_offsets=QAction(
            "Assign Rigid End Offsets...",self
        )

        self.action_check=QAction("Check Model",self)
        self.action_check.setShortcut(QKeySequence("F6"))
        self.action_run=QAction("Run Analysis",self)
        self.action_pdelta=QAction("Run P-Delta Analysis...",self)
        self.action_run.setShortcut(QKeySequence("F5"))

        self.action_none=QAction("Undeformed Model",self)
        self.action_deformed=QAction("Deformed Shape",self)
        self.action_deformed.setShortcut(QKeySequence("F10"))
        self.action_moment=QAction("Moment Diagrams",self)
        self.action_moment.setShortcut(QKeySequence("F8"))
        self.action_shear=QAction("Shear Diagrams",self)
        self.action_shear.setShortcut(QKeySequence("F9"))
        self.action_axial=QAction("Axial Force",self)
        self.action_torsion=QAction("Torsion",self)
        self.action_reactions=QAction("Support Reactions",self)
        self.result_group=QActionGroup(self)
        self.result_group.setExclusive(True)
        for action in (
            self.action_none,self.action_deformed,self.action_moment,
            self.action_shear,self.action_axial,
            self.action_torsion,self.action_reactions,
        ):
            action.setCheckable(True)
            self.result_group.addAction(action)
        self.action_none.setChecked(True)

        self.action_fit_plan=QAction("Fit Plan View",self)
        self.action_fit_plan.setShortcut(QKeySequence("F4"))
        self.action_fit_3d=QAction("Fit 3D View",self)
        self.action_iso=QAction("3D Isometric",self)
        self.action_iso.setShortcut(QKeySequence("Ctrl+I"))
        self.action_top=QAction("3D Top",self)
        self.action_top.setShortcut(QKeySequence("Ctrl+1"))
        self.action_front=QAction("3D Front",self)
        self.action_front.setShortcut(QKeySequence("Ctrl+2"))
        self.action_right=QAction("3D Right",self)
        self.action_right.setShortcut(QKeySequence("Ctrl+3"))
        self.action_reset_layout=QAction("Reset Dock Layout",self)
        self.action_show_node_labels=QAction("Show Node Labels",self,checkable=True)
        self.action_show_frame_labels=QAction("Show Frame Labels",self,checkable=True)
        self.action_show_frame_labels.setChecked(True)
        self.action_show_nodes=QAction("Show Nodes",self,checkable=True)
        self.action_show_nodes.setChecked(True)
        self.action_show_3d_grid=QAction("Show 3D Base Grid",self,checkable=True)
        self.action_show_3d_grid.setChecked(True)
        self.action_show_3d_axes=QAction("Show 3D Axes",self,checkable=True)
        self.action_show_3d_axes.setChecked(True)
        self.action_show_3d_pivot=QAction("Show 3D Pivot",self,checkable=True)
        self.action_show_3d_pivot.setChecked(True)

        self.action_concrete_design=QAction(
            "Run Preliminary Concrete Design",self
        )
        self.action_advanced_design=QAction("Run Advanced Concrete Checks",self)
        self.action_beam_rebar=QAction("Show Beam Reinforcement",self)
        self.action_slab_rebar_x=QAction("Show Slab Reinforcement X",self)
        self.action_slab_rebar_y=QAction("Show Slab Reinforcement Y",self)
        self.action_slab_as_x=QAction("Slab Required Steel As X",self)
        self.action_slab_as_y=QAction("Slab Required Steel As Y",self)
        self.action_modal=QAction("Run Modal Analysis...",self)
        self.action_modal.setShortcut(QKeySequence("F7"))
        self.action_mode_shape=QAction("Show Mode Shape",self)
        self.action_animate_deformed=QAction(
            "Start Deformed Shape Animation",self
        )
        self.action_animate_deformed.setShortcut(QKeySequence("Ctrl+F10"))
        self.action_animate_mode=QAction(
            "Start Mode Shape Animation",self
        )
        self.action_stop_animation=QAction("Stop Animation",self)
        self.action_stop_animation.setShortcut(QKeySequence("Shift+F10"))
        self.action_code_settings=QAction(
            "Project Codes and Standards...",self
        )
        self.action_code_settings.setShortcut(QKeySequence("Ctrl+Shift+C"))
        self.action_code_summary=QAction(
            "Show Code Summary",self
        )
        self.action_shortcuts=QAction("Keyboard Shortcuts...",self)
        self.action_shortcuts.setShortcut(QKeySequence("Ctrl+/"))
        self.action_about=QAction("About AIDESIGN",self)

    def _build_menu(self):
        menu=self.menuBar()

        file_menu=menu.addMenu("&File")
        file_menu.addActions([
            self.action_new,self.action_open,
            self.action_save,self.action_save_as,
        ])
        file_menu.addSeparator()
        file_menu.addAction(self.action_import_dxf)
        file_menu.addSeparator()
        file_menu.addAction(self.action_exit)

        edit_menu=menu.addMenu("&Edit")
        edit_menu.addAction(self.action_delete)

        view_menu=menu.addMenu("&View")
        view_menu.addActions([
            self.action_fit_plan,self.action_fit_3d,
            self.action_iso,self.action_top,
            self.action_front,self.action_right,
        ])
        view_menu.addSeparator()
        display_options=view_menu.addMenu("Display Options")
        display_options.addActions([
            self.action_show_nodes,self.action_show_node_labels,
            self.action_show_frame_labels,self.action_show_3d_grid,
            self.action_show_3d_axes,self.action_show_3d_pivot,
        ])
        view_menu.addSeparator()
        view_menu.addAction(self.action_reset_layout)

        define_menu=menu.addMenu("&Define")
        define_menu.addActions([
            self.action_grids,self.action_stories,
            self.action_materials,self.action_sections,
            self.action_slab_sections,
        ])
        define_menu.addSeparator()
        define_menu.addActions([
            self.action_load_patterns,
            self.action_load_combinations,
        ])

        draw_menu=menu.addMenu("&Draw")
        draw_menu.addActions([
            self.action_select,self.action_beam,
            self.action_column,self.action_slab,
        ])
        draw_menu.addSeparator()
        draw_menu.addAction(self.action_mesh_slab)

        select_menu=menu.addMenu("&Select")
        select_menu.addActions([
            self.action_select_all,self.action_clear_selection,
        ])

        assign_menu=menu.addMenu("&Assign")
        assign_menu.addActions([
            self.action_fixed_base,self.action_frame_udl,
            self.action_area_load,self.action_frame_releases,
            self.action_rigid_offsets,self.action_diaphragm,
        ])

        analyze_menu=menu.addMenu("&Analyze")
        analyze_menu.addActions([
            self.action_check,self.action_run,self.action_pdelta,
            self.action_modal,self.action_mode_shape,
        ])

        display_menu=menu.addMenu("&Display")
        display_menu.addActions([
            self.action_none,self.action_deformed,
            self.action_moment,self.action_shear,
            self.action_axial,self.action_torsion,
            self.action_reactions,
        ])
        display_menu.addSeparator()
        display_menu.addActions([
            self.action_animate_deformed,
            self.action_animate_mode,
            self.action_stop_animation,
        ])

        design_menu=menu.addMenu("&Design")
        design_menu.addActions([
            self.action_concrete_design,
            self.action_advanced_design,
            self.action_beam_rebar,
            self.action_slab_rebar_x,
            self.action_slab_rebar_y,
            self.action_slab_as_x,
            self.action_slab_as_y,
        ])

        codes_menu=menu.addMenu("&Codes")
        codes_menu.addActions([
            self.action_code_settings,
            self.action_code_summary,
        ])

        options_menu=menu.addMenu("&Options")
        options_menu.addAction(self.action_reset_layout)

        tools_menu=menu.addMenu("&Tools")
        tools_menu.addAction(self.action_check)

        help_menu=menu.addMenu("&Help")
        help_menu.addAction(self.action_shortcuts)
        help_menu.addSeparator()
        help_menu.addAction(self.action_about)

    def _build_ribbon(self):
        self.ribbon=RibbonWidget()
        self.setMenuWidget(self._menu_with_ribbon())

    def _menu_with_ribbon(self):
        widget=QWidget()
        layout=QVBoxLayout(widget)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        layout.addWidget(self.menuBar())
        layout.addWidget(self.ribbon)
        return widget

    def _build_story_toolbar(self):
        toolbar=QToolBar("Story Navigation",self)
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea,toolbar)

        toolbar.addWidget(QLabel(" Active Story: "))
        self.story_down=QAction("▼",self)
        self.story_up=QAction("▲",self)
        toolbar.addAction(self.story_down)
        self.story_combo=QComboBox()
        self.story_combo.setMinimumWidth(145)
        toolbar.addWidget(self.story_combo)
        toolbar.addAction(self.story_up)
        toolbar.addSeparator()

        toolbar.addWidget(QLabel(" Analysis Case: "))
        self.case_combo=QComboBox()
        self.case_combo.setMinimumWidth(170)
        toolbar.addWidget(self.case_combo)
        toolbar.addSeparator()
        toolbar.addWidget(QLabel(" Animation: "))
        self.animation_speed_combo=QComboBox()
        self.animation_speed_combo.addItems(
            ["0.25×","0.50×","1.00×","1.50×","2.00×"]
        )
        self.animation_speed_combo.setCurrentText("1.00×")
        self.animation_speed_combo.setMaximumWidth(78)
        toolbar.addWidget(self.animation_speed_combo)
        toolbar.setMaximumHeight(30)
        toolbar.setStyleSheet(
            "QToolBar{spacing:3px;padding:1px;border:0;"
            "border-bottom:1px solid #d6dee4}"
        )



    def _build_vertical_toolbar(self):
        toolbar=QToolBar("Professional Tools",self)
        toolbar.setObjectName("ProfessionalLeftTools")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setOrientation(Qt.Orientation.Vertical)
        toolbar.setStyleSheet("""
            QToolBar {
                spacing: 2px;
                padding: 3px 2px;
                background: #eef3f6;
                border-right: 1px solid #c6d0d8;
            }
            QToolButton {
                min-width: 31px;
                min-height: 31px;
                max-width: 31px;
                max-height: 31px;
                border: 1px solid transparent;
                border-radius: 6px;
                font-size: 17pt;
                font-weight: 700;
                background: #ffffff;
            }
            QToolButton:hover {
                border-color: #4da3d1;
                background: #e1f2fc;
            }
            QToolButton:pressed {
                background: #cbe8f8;
            }
            QToolButton:checked {
                border-color: #087fb8;
                background: #cceafb;
            }
        """)

        def add(symbol,tooltip,callback,color="#155e75",checkable=False):
            button=QToolButton(toolbar)
            button.setText(symbol)
            button.setToolTip(tooltip)
            button.setStatusTip(tooltip)
            button.setCheckable(checkable)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(
                f"QToolButton{{color:{color};}}"
                "QToolButton:hover{color:#0b3954;}"
            )
            button.clicked.connect(callback)
            toolbar.addWidget(button)
            return button

        # File / project
        self.left_new=add("＋","New project",self.action_new.trigger,"#0f766e")
        self.left_open=add("⌂","Open project",self.action_open.trigger,"#2563eb")
        self.left_save=add("▣","Save project",self.action_save.trigger,"#7c3aed")
        toolbar.addSeparator()

        # Model creation and selection
        self.left_select=add(
            "↖","Select / window selection",
            lambda:self.set_draw_mode("Select"),"#1565c0",True
        )
        self.left_beam=add(
            "╱","Draw beam",lambda:self.set_draw_mode("Beam"),
            "#0277bd",True
        )
        self.left_column=add(
            "■","Draw column",lambda:self.set_draw_mode("Column"),
            "#8e24aa",True
        )
        self.left_slab=add(
            "▰","Draw slab",lambda:self.set_draw_mode("Slab"),
            "#00897b",True
        )
        self.left_mesh=add(
            "▦","Divide selected slab into shell mesh",
            self.mesh_selected_slabs,"#ef6c00"
        )
        self.left_delete=add(
            "×","Delete selected objects",
            self.plan.delete_selected,"#c62828"
        )
        toolbar.addSeparator()

        # Definitions / assignments
        self.left_grids=add("#","Define grids",self.define_grids,"#455a64")
        self.left_sections=add("▭","Define frame sections",self.define_sections,"#5d4037")
        self.left_loads=add("⇩","Assign frame load",self.assign_frame_udl,"#2e7d32")
        self.left_slab_load=add("⇊","Assign slab load",self.assign_area_load,"#388e3c")
        self.left_codes=add("§","Codes and standards",self.edit_code_settings,"#6a1b9a")
        toolbar.addSeparator()

        # Analysis / display
        self.left_fit=add("⛶","Fit full plan grid",self.plan.fit_view,"#37474f")
        self.left_iso=add("◇","Isometric 3D view",self.view3d.view_isometric,"#00695c")
        self.left_check=add("✓","Check model",self.check_model,"#2e7d32")
        self.left_run=add("▶","Run static analysis",self.run_analysis,"#d84315")
        self.left_animate=add(
            "〰","Animate deformed shape",
            self.start_deformed_animation,"#e65100"
        )
        self.left_modal=add(
            "∿","Animate current mode shape",
            self.start_mode_animation,"#ad1457"
        )
        self.left_stop=add("■","Stop animation",self.stop_animation,"#424242")

        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea,toolbar)
        self.compact_toolbar=toolbar

    def _build_central(self):
        splitter=QSplitter(Qt.Orientation.Horizontal)
        self.plan=PlanViewport(self.project)
        self.view3d=Viewport3D(self.project)
        splitter.addWidget(self.plan)
        splitter.addWidget(self.view3d)
        splitter.setSizes([800,800])
        self.setCentralWidget(splitter)

    def _build_docks(self):
        self.explorer=ModelExplorer()
        self.explorer_dock=QDockWidget("Model Explorer",self)
        self.explorer_dock.setObjectName("ModelExplorerDock")
        self.explorer_dock.setWidget(self.explorer)
        self.addDockWidget(
            Qt.DockWidgetArea.LeftDockWidgetArea,self.explorer_dock
        )

        self.properties=PropertyGrid()
        self.properties_dock=QDockWidget(
            "Properties of Object",self
        )
        self.properties_dock.setObjectName("PropertiesDock")
        self.properties_dock.setWidget(self.properties)
        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea,self.properties_dock
        )

        self.output=QTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumHeight(160)
        self.output_dock=QDockWidget("Output",self)
        self.output_dock.setObjectName("OutputDock")
        self.output_dock.setWidget(self.output)
        self.addDockWidget(
            Qt.DockWidgetArea.BottomDockWidgetArea,self.output_dock
        )

        self.results_panel=ResultsPanel()
        self.results_dock=QDockWidget("Analysis Results",self)
        self.results_dock.setObjectName("ResultsDock")
        self.results_dock.setWidget(self.results_panel)
        self.addDockWidget(
            Qt.DockWidgetArea.BottomDockWidgetArea,
            self.results_dock,
        )
        self.tabifyDockWidget(
            self.output_dock,self.results_dock
        )
        self.results_dock.raise_()

        self.design_panel=ConcreteDesignPanel()
        self.design_dock=QDockWidget("Concrete Design",self)
        self.design_dock.setObjectName("ConcreteDesignDock")
        self.design_dock.setWidget(self.design_panel)
        self.addDockWidget(
            Qt.DockWidgetArea.BottomDockWidgetArea,
            self.design_dock,
        )
        self.tabifyDockWidget(
            self.results_dock,self.design_dock
        )

        self.modal_panel=ModalResultsPanel()
        self.modal_dock=QDockWidget("Modal Analysis",self)
        self.modal_dock.setObjectName("ModalDock")
        self.modal_dock.setWidget(self.modal_panel)
        self.addDockWidget(
            Qt.DockWidgetArea.BottomDockWidgetArea,
            self.modal_dock,
        )
        self.tabifyDockWidget(
            self.results_dock,self.modal_dock
        )
        self.advanced_design_panel=AdvancedDesignPanel()
        self.advanced_design_dock=QDockWidget("Advanced Concrete Checks",self)
        self.advanced_design_dock.setObjectName("AdvancedConcreteChecksDock")
        self.advanced_design_dock.setWidget(self.advanced_design_panel)
        self.addDockWidget(
            Qt.DockWidgetArea.BottomDockWidgetArea,
            self.advanced_design_dock,
        )
        self.tabifyDockWidget(
            self.design_dock,self.advanced_design_dock
        )


    def _build_code_dock(self):
        self.code_widget=CodeSettingsWidget(self.project,self)
        self.code_dock=QDockWidget("Codes & Standards",self)
        self.code_dock.setObjectName("CodesStandardsDock")
        self.code_dock.setWidget(self.code_widget)
        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea,self.code_dock
        )
        self.tabifyDockWidget(
            self.properties_dock,self.code_dock
        )

    def _build_status(self):
        status=QStatusBar()
        self.setStatusBar(status)
        self.status_mode=QLabel("Ready")
        self.status_coord=QLabel(
            "X: 0.000   Y: 0.000   Z: 0.000"
        )
        self.status_snap=QLabel("Snap: ON")
        status.addWidget(self.status_mode,1)
        status.addPermanentWidget(self.status_coord)
        status.addPermanentWidget(self.status_snap)
        self.unit_status=UnitStatusWidget(self.unit_system,self)
        status.addPermanentWidget(self.unit_status)

    def _wire(self):
        self.plan.set_unit_system(self.unit_system)
        self.view3d.set_unit_system(self.unit_system)
        self.results_panel.set_unit_system(self.unit_system)
        self.unit_system.changed.connect(self._refresh_unit_dependent_text)
        self.action_select.triggered.connect(
            lambda:self.set_draw_mode("Select")
        )
        self.action_beam.triggered.connect(
            lambda:self.set_draw_mode("Beam")
        )
        self.action_column.triggered.connect(
            lambda:self.set_draw_mode("Column")
        )
        self.action_slab.triggered.connect(
            lambda:self.set_draw_mode("Slab")
        )
        self.action_delete.triggered.connect(
            self.plan.delete_selected
        )
        self.action_select_all.triggered.connect(
            self.plan.select_all_visible
        )
        self.action_clear_selection.triggered.connect(
            self.plan.clear_selection
        )
        self.action_mesh_slab.triggered.connect(
            self.mesh_selected_slabs
        )
        self.action_import_dxf.triggered.connect(
            self.import_dxf_dialog
        )

        self.ribbon.select_btn.clicked.connect(
            lambda:self.set_draw_mode("Select")
        )
        self.ribbon.beam_btn.clicked.connect(
            lambda:self.set_draw_mode("Beam")
        )
        self.ribbon.column_btn.clicked.connect(
            lambda:self.set_draw_mode("Column")
        )
        self.ribbon.slab_btn.clicked.connect(
            lambda:self.set_draw_mode("Slab")
        )
        self.ribbon.draw_beam_btn.clicked.connect(
            lambda:self.set_draw_mode("Beam")
        )
        self.ribbon.draw_column_btn.clicked.connect(
            lambda:self.set_draw_mode("Column")
        )
        self.ribbon.draw_slab_btn.clicked.connect(
            lambda:self.set_draw_mode("Slab")
        )
        self.ribbon.delete_btn.clicked.connect(
            self.plan.delete_selected
        )

        self.ribbon.snap_btn.toggled.connect(self._set_snap)
        self.ribbon.ortho_btn.toggled.connect(self._set_ortho)
        self.ribbon.fit_btn.clicked.connect(self.plan.fit_view)
        self.ribbon.reset3d_btn.clicked.connect(
            self.view3d.view_isometric
        )

        self.story_combo.currentTextChanged.connect(
            self._story_changed
        )
        self.story_up.triggered.connect(
            lambda:self._step_story(1)
        )
        self.story_down.triggered.connect(
            lambda:self._step_story(-1)
        )

        self.plan.cursor_world_changed.connect(
            self._cursor_changed
        )
        self.view3d.status_message.connect(
            self.status_mode.setText
        )
        self.view3d.object_selected.connect(
            self._selection_changed
        )
        self.plan.selection_changed.connect(
            self._selection_changed
        )
        self.plan.model_changed.connect(self._model_changed)
        self.explorer.object_requested.connect(
            self._selection_changed
        )

        self.action_grids.triggered.connect(self.define_grids)
        self.action_stories.triggered.connect(self.define_stories)
        self.action_materials.triggered.connect(
            self.define_materials
        )
        self.action_sections.triggered.connect(
            self.define_sections
        )
        self.ribbon.grid_btn.clicked.connect(self.define_grids)
        self.ribbon.story_btn.clicked.connect(
            self.define_stories
        )
        self.ribbon.material_btn.clicked.connect(
            self.define_materials
        )
        self.ribbon.section_btn.clicked.connect(
            self.define_sections
        )
        self.action_slab_sections.triggered.connect(
            self.define_slab_sections
        )
        self.ribbon.slabsection_btn.clicked.connect(
            self.define_slab_sections
        )
        self.action_load_patterns.triggered.connect(
            self.define_load_patterns
        )
        self.action_load_combinations.triggered.connect(
            self.define_load_combinations
        )
        self.ribbon.pattern_btn.clicked.connect(
            self.define_load_patterns
        )
        self.ribbon.combo_btn.clicked.connect(
            self.define_load_combinations
        )

        self.action_check.triggered.connect(self.check_model)
        self.action_run.triggered.connect(self.run_analysis)
        self.action_fixed_base.triggered.connect(
            self.assign_fixed_base
        )
        self.action_frame_udl.triggered.connect(
            self.assign_frame_udl
        )
        self.ribbon.check_btn.clicked.connect(self.check_model)
        self.ribbon.run_btn.clicked.connect(self.run_analysis)
        self.ribbon.analyze_check_btn.clicked.connect(
            self.check_model
        )
        self.ribbon.analyze_run_btn.clicked.connect(
            self.run_analysis
        )
        self.ribbon.pdelta_btn.clicked.connect(
            self.run_pdelta_analysis
        )
        self.ribbon.support_btn.clicked.connect(
            self.assign_fixed_base
        )
        self.ribbon.load_btn.clicked.connect(
            self.assign_frame_udl
        )
        self.action_area_load.triggered.connect(
            self.assign_area_load
        )
        self.ribbon.area_load_btn.clicked.connect(
            self.assign_area_load
        )
        self.ribbon.release_btn.clicked.connect(
            self.assign_frame_releases
        )
        self.ribbon.offset_btn.clicked.connect(
            self.assign_rigid_offsets
        )
        self.ribbon.diaphragm_btn.clicked.connect(
            self.assign_rigid_diaphragm
        )

        self.action_none.triggered.connect(
            lambda:self.display_results("None")
        )
        self.action_deformed.triggered.connect(
            lambda:self.display_results("Deformed")
        )
        self.action_moment.triggered.connect(
            lambda:self.display_results("Moment")
        )
        self.action_shear.triggered.connect(
            lambda:self.display_results("Shear")
        )
        self.action_axial.triggered.connect(
            lambda:self.display_results("Axial")
        )
        self.action_torsion.triggered.connect(
            lambda:self.display_results("Torsion")
        )
        self.action_reactions.triggered.connect(
            lambda:self.display_results("Reactions")
        )
        self.results_panel.result_mode_changed.connect(
            self.display_results
        )
        self.ribbon.deformed_btn.clicked.connect(
            lambda:self.display_results("Deformed")
        )
        self.ribbon.moment_btn.clicked.connect(
            lambda:self.display_results("Moment")
        )
        self.ribbon.shear_btn.clicked.connect(
            lambda:self.display_results("Shear")
        )

        self.action_fit_plan.triggered.connect(
            self.plan.fit_view
        )
        self.action_fit_3d.triggered.connect(
            self.view3d.fit_view
        )
        self.action_iso.triggered.connect(
            self.view3d.view_isometric
        )
        self.action_top.triggered.connect(
            self.view3d.view_top
        )
        self.action_front.triggered.connect(
            self.view3d.view_front
        )
        self.action_right.triggered.connect(
            self.view3d.view_right
        )
        self.action_reset_layout.triggered.connect(
            self.reset_dock_layout
        )
        self.action_concrete_design.triggered.connect(
            self.run_concrete_design
        )
        self.action_advanced_design.triggered.connect(
            self.run_advanced_design
        )
        self.action_beam_rebar.triggered.connect(
            lambda:self.display_results("Beam Rebar")
        )
        self.action_slab_rebar_x.triggered.connect(
            lambda:self.display_results("Slab Rebar X")
        )
        self.action_slab_rebar_y.triggered.connect(
            lambda:self.display_results("Slab Rebar Y")
        )
        self.action_slab_as_x.triggered.connect(
            lambda:self.display_results("Slab As X")
        )
        self.action_slab_as_y.triggered.connect(
            lambda:self.display_results("Slab As Y")
        )
        self.ribbon.concrete_design_btn.clicked.connect(
            self.run_concrete_design
        )
        self.ribbon.advanced_design_btn.clicked.connect(
            self.run_advanced_design
        )
        self.ribbon.beam_rebar_btn.clicked.connect(
            lambda:self.display_results("Beam Rebar")
        )
        self.ribbon.slab_rebar_x_btn.clicked.connect(
            lambda:self.display_results("Slab Rebar X")
        )
        self.ribbon.slab_rebar_y_btn.clicked.connect(
            lambda:self.display_results("Slab Rebar Y")
        )
        self.ribbon.slab_as_x_btn.clicked.connect(
            lambda:self.display_results("Slab As X")
        )
        self.ribbon.slab_as_y_btn.clicked.connect(
            lambda:self.display_results("Slab As Y")
        )
        self.ribbon.contour_mx_btn.clicked.connect(
            lambda:self.display_results("Slab Mx")
        )
        self.ribbon.contour_my_btn.clicked.connect(
            lambda:self.display_results("Slab My")
        )
        self.ribbon.contour_qx_btn.clicked.connect(
            lambda:self.display_results("Slab Qx")
        )
        self.ribbon.contour_def_btn.clicked.connect(
            lambda:self.display_results("Slab Deflection")
        )
        self.action_modal.triggered.connect(self.run_modal_analysis)
        self.action_mode_shape.triggered.connect(
            lambda:self.show_mode_shape(
                max(self.modal_panel.mode_combo.currentIndex()+1,1)
            )
        )
        self.ribbon.modal_run_btn.clicked.connect(
            self.run_modal_analysis
        )
        self.ribbon.mode_shape_btn.clicked.connect(
            lambda:self.show_mode_shape(
                max(self.modal_panel.mode_combo.currentIndex()+1,1)
            )
        )
        self.modal_panel.mode_changed.connect(self.show_mode_shape)
        self.action_animate_deformed.triggered.connect(
            self.start_deformed_animation
        )
        self.action_animate_mode.triggered.connect(
            self.start_mode_animation
        )
        self.action_stop_animation.triggered.connect(
            self.stop_animation
        )
        self.action_code_settings.triggered.connect(
            self.edit_code_settings
        )
        self.action_code_summary.triggered.connect(
            self.show_code_summary
        )
        self.ribbon.animate_deformed_btn.clicked.connect(
            self.start_deformed_animation
        )
        self.ribbon.animate_mode_btn.clicked.connect(
            self.start_mode_animation
        )
        self.ribbon.stop_animation_btn.clicked.connect(
            self.stop_animation
        )
        self.ribbon.code_settings_btn.clicked.connect(
            self.edit_code_settings
        )
        self.ribbon.code_summary_btn.clicked.connect(
            self.show_code_summary
        )
        self.animation_timer.timeout.connect(
            self._advance_animation
        )
        self.animation_speed_combo.currentTextChanged.connect(
            self._set_animation_speed
        )
        self.action_show_nodes.toggled.connect(
            lambda value:self._set_display_option("show_nodes",value)
        )
        self.action_show_node_labels.toggled.connect(
            lambda value:self._set_display_option("show_node_labels",value)
        )
        self.action_show_frame_labels.toggled.connect(
            lambda value:self._set_display_option("show_frame_labels",value)
        )
        self.action_show_3d_grid.toggled.connect(
            lambda value:self._set_display_option("show_base_grid",value)
        )
        self.action_show_3d_axes.toggled.connect(
            lambda value:self._set_display_option("show_axes",value)
        )
        self.action_show_3d_pivot.toggled.connect(
            lambda value:self._set_display_option("show_pivot",value)
        )
        self.action_shortcuts.triggered.connect(self.show_shortcuts)
        self.action_frame_releases.triggered.connect(
            self.assign_frame_releases
        )
        self.action_diaphragm.triggered.connect(
            self.assign_rigid_diaphragm
        )
        self.action_rigid_offsets.triggered.connect(
            self.assign_rigid_offsets
        )
        self.action_pdelta.triggered.connect(
            self.run_pdelta_analysis
        )
        self.action_about.triggered.connect(self.show_about)

    def set_project(self,project):
        self.project=project
        self.analysis_result=None
        self.plan.set_project(project)
        self.view3d.set_project(project)
        self.results_panel.clear_results()
        if hasattr(self,"code_widget"):
            self.code_widget.project=project
            self.code_widget.load_from_project()
        self.concrete_design_result=None
        self.design_panel.clear_design()
        self.plan.set_concrete_design_result(None)
        self.view3d.set_concrete_design_result(None)
        self.refresh_model()

    def set_draw_mode(self,mode):
        self.plan.set_mode(mode)
        self.status_mode.setText(f"Mode: {mode}")
        mapping={
            "Select":(
                self.action_select,
                [self.ribbon.select_btn],
            ),
            "Beam":(
                self.action_beam,
                [self.ribbon.beam_btn,
                 self.ribbon.draw_beam_btn],
            ),
            "Column":(
                self.action_column,
                [self.ribbon.column_btn,
                 self.ribbon.draw_column_btn],
            ),
            "Slab":(
                self.action_slab,
                [self.ribbon.slab_btn,
                 self.ribbon.draw_slab_btn],
            ),
        }
        for name,(action,buttons) in mapping.items():
            active=name==mode
            action.setChecked(active)
            for button in buttons:
                button.setChecked(active)
        for name,button in {
            "Select":getattr(self,"left_select",None),
            "Beam":getattr(self,"left_beam",None),
            "Column":getattr(self,"left_column",None),
            "Slab":getattr(self,"left_slab",None),
        }.items():
            if button is not None:
                button.setChecked(name==mode)

    def _set_snap(self,on):
        self.plan.snap_enabled=on
        self.status_snap.setText(
            "Snap: ON" if on else "Snap: OFF"
        )

    def _set_ortho(self,on):
        self.plan.ortho=on

    def _cursor_changed(self,x,y,z,snap):
        unit=self.unit_system.unit("length")
        self.status_coord.setText(
            f"X: {self.unit_system.convert(x,'length'):.3f} {unit}   "
            f"Y: {self.unit_system.convert(y,'length'):.3f} {unit}   "
            f"Z: {self.unit_system.convert(z,'length'):.3f} {unit}"
        )
        self.status_snap.setText(
            f"Snap: {snap or ('ON' if self.plan.snap_enabled else 'OFF')}"
        )

    def _selection_changed(self,kind,obj_id):
        self.properties.show_object(
            self.project,kind,obj_id
        )

    def _model_changed(self):
        self.project.dirty=True
        self.analysis_result=None
        self.view3d.set_analysis_result(None)
        self.plan.set_analysis_result(None)
        self.results_panel.clear_results()
        self.refresh_model()

    def _story_changed(self,name):
        story=self.project.story_by_name(name)
        if story:
            self.project.active_story_id=story.id
            self.plan.clear_selection()
            self.plan.fit_view()
            self.view3d.update()

    def _step_story(self,step):
        names=[s.name for s in self.project.ordered_stories()]
        if not names:
            return
        index=max(0,names.index(self.story_combo.currentText()))
        self.story_combo.setCurrentIndex(
            max(0,min(len(names)-1,index+step))
        )

    def refresh_model(self):
        current=self.project.active_story.name
        self.story_combo.blockSignals(True)
        self.story_combo.clear()
        self.story_combo.addItems(
            [s.name for s in self.project.ordered_stories()]
        )
        self.story_combo.setCurrentText(current)
        self.story_combo.blockSignals(False)

        current_case=self.case_combo.currentText()
        cases=list(self.project.load_patterns)+list(
            self.project.load_combinations
        )
        self.case_combo.blockSignals(True)
        self.case_combo.clear()
        self.case_combo.addItems(cases)
        if current_case in cases:
            self.case_combo.setCurrentText(current_case)
        elif "ULS 1.2D+1.6L" in cases:
            self.case_combo.setCurrentText("ULS 1.2D+1.6L")
        self.case_combo.blockSignals(False)

        self.explorer.set_project(self.project)
        self.plan.update()
        self.view3d.update()

    def _run_dialog(self,dialog):
        if dialog.exec():
            self.analysis_result=None
            self.view3d.set_analysis_result(None)
            self.refresh_model()

    def define_grids(self):
        self._run_dialog(GridDialog(self.project,self))

    def define_stories(self):
        self._run_dialog(StoryDialog(self.project,self))

    def define_materials(self):
        self._run_dialog(MaterialDialog(self.project,self))

    def define_sections(self):
        self._run_dialog(FrameSectionDialog(self.project,self))

    def define_slab_sections(self):
        self._run_dialog(SlabSectionDialog(self.project,self))

    def define_load_patterns(self):
        self._run_dialog(LoadPatternDialog(self.project,self))

    def define_load_combinations(self):
        self._run_dialog(LoadCombinationDialog(self.project,self))


    def mesh_selected_slabs(self):
        selected=sorted(self.plan.selected_areas)
        if not selected:
            QMessageBox.information(
                self,"Divide Slab",
                "Select one or more slab areas in Plan View."
            )
            return
        nx,ok=QInputDialog.getInt(
            self,"Divide Slab","Divisions along local X:",
            4,1,100,1
        )
        if not ok:return
        ny,ok=QInputDialog.getInt(
            self,"Divide Slab","Divisions along local Y:",
            4,1,100,1
        )
        if not ok:return
        generated=[]
        try:
            for area_id in selected:
                generated.extend(
                    self.project.subdivide_area(area_id,nx,ny)
                )
        except Exception as exc:
            QMessageBox.critical(self,"Divide Slab",str(exc))
            return
        self.plan.selected_areas=set(generated)
        self.analysis_result=None
        self.modal_result=None
        self.animation_timer=QTimer(self)
        self.animation_timer.setInterval(40)
        self.animation_angle=0.0
        self.animation_target="None"
        self.animation_speed=1.0
        self.plan.set_analysis_result(None)
        self.view3d.set_analysis_result(None)
        self.plan.set_modal_result(None)
        self.view3d.set_modal_result(None)
        self.results_panel.clear_results()
        self.modal_panel.clear_results()
        self.refresh_model()
        self.log_message(
            f"Generated {len(generated)} shell elements "
            f"using {nx} x {ny} divisions."
        )

    def import_dxf_dialog(self):
        filename,_=QFileDialog.getOpenFileName(
            self,"Import DXF","","DXF Drawing (*.dxf)"
        )
        if not filename:return
        unit,ok=QInputDialog.getItem(
            self,"DXF Units","Drawing coordinate unit:",
            ["m","mm","cm","ft","in"],1,False
        )
        if not ok:return
        scale={
            "m":1.0,"mm":0.001,"cm":0.01,
            "ft":0.3048,"in":0.0254,
        }[unit]
        try:
            report=import_dxf(
                self.project,filename,
                self.project.active_story_id,scale,True
            )
        except Exception as exc:
            QMessageBox.critical(self,"Import DXF",str(exc))
            return
        self.refresh_model()
        self.plan.fit_view()
        self.view3d.view_isometric()
        message=(
            f"Imported {report.beams} beam segments and "
            f"{report.slabs} slab outlines. "
            f"Skipped {report.skipped} entities."
        )
        if report.warnings:
            message+="\n\nWarnings:\n"+"\n".join(report.warnings[:10])
        QMessageBox.information(self,"Import DXF",message)
        self.log_message(message)

    def check_model(self):
        report=check_model(self.project)
        self.log_message(report.as_text())
        if report.is_valid:
            QMessageBox.information(
                self,"Check Model",report.as_text()
            )
        else:
            QMessageBox.critical(
                self,"Check Model",report.as_text()
            )
        return report.is_valid

    def assign_fixed_base(self):
        count=self.project.assign_fixed_base()
        self.log_message(
            f"Fixed restraints assigned to {count} base joint(s)."
        )
        self.plan.update()
        self.view3d.update()

    def assign_frame_udl(self):
        selected=sorted(self.plan.selected_frames)
        if not selected:
            QMessageBox.warning(
                self,"Assign Frame UDL",
                "Select one or more frames in Plan View."
            )
            return
        pattern,ok=QInputDialog.getItem(
            self,"Frame Uniform Load","Load pattern:",
            list(self.project.load_patterns),0,False
        )
        if not ok:
            return
        magnitude,ok=QInputDialog.getDouble(
            self,"Frame Uniform Load",
            "Downward global Z load magnitude (kN/m):",
            10.0,0.0,1.0e9,4
        )
        if not ok:
            return
        for frame_id in selected:
            self.project.assign_frame_udl(
                frame_id,pattern,(0.0,0.0,-magnitude)
            )
        self.log_message(
            f"Assigned {magnitude:.4f} kN/m downward "
            f"{pattern} UDL to {len(selected)} frame(s)."
        )
        self.plan.update()
        self.view3d.update()

    def assign_area_load(self):
        selected=sorted(self.plan.selected_areas)
        if not selected:
            QMessageBox.warning(
                self,"Assign Slab Load",
                "Select one or more slab areas in Plan View."
            )
            return
        pattern,ok=QInputDialog.getItem(
            self,"Slab Surface Load","Load pattern:",
            list(self.project.load_patterns),0,False
        )
        if not ok:
            return
        pressure,ok=QInputDialog.getDouble(
            self,"Slab Surface Load",
            "Downward surface load (kN/m²):",
            5.0,0.0,1.0e9,4
        )
        if not ok:
            return
        for area_id in selected:
            self.project.assign_area_surface_load(
                area_id,pattern,pressure
            )
        self.analysis_result=None
        self.plan.set_analysis_result(None)
        self.view3d.set_analysis_result(None)
        self.results_panel.clear_results()
        self.log_message(
            f"Assigned {pressure:.4f} kN/m² downward "
            f"{pattern} load to {len(selected)} slab(s)."
        )
        self.plan.update()
        self.view3d.update()


    def assign_frame_releases(self):
        frame_ids=sorted(self.plan.selected_frames)
        if not frame_ids:
            QMessageBox.information(
                self,"Frame End Releases",
                "Select one or more frame objects in Plan View."
            )
            return
        dialog=FrameReleaseDialog(
            self.project,frame_ids,self
        )
        if dialog.exec():
            self.analysis_result=None
            self.plan.set_analysis_result(None)
            self.view3d.set_analysis_result(None)
            self.results_panel.clear_results()
            self.refresh_model()
            self.log_message(
                f"Frame end releases assigned to "
                f"{len(frame_ids)} frame(s)."
            )

    def assign_rigid_offsets(self):
        frame_ids=sorted(self.plan.selected_frames)
        if not frame_ids:
            QMessageBox.information(
                self,"Rigid End Offsets",
                "Select one or more frame objects in Plan View."
            )
            return
        dialog=RigidEndOffsetDialog(self.project,frame_ids,self)
        if dialog.exec():
            self.analysis_result=None
            self.modal_result=None
            self.plan.set_analysis_result(None)
            self.view3d.set_analysis_result(None)
            self.results_panel.clear_results()
            self.refresh_model()
            self.log_message(
                f"Rigid end offsets assigned to {len(frame_ids)} frame(s)."
            )

    def assign_rigid_diaphragm(self):
        node_ids=set()
        for frame_id in self.plan.selected_frames:
            frame=self.project.frames[frame_id]
            node_ids.update((frame.i,frame.j))
        for area_id in self.plan.selected_areas:
            node_ids.update(self.project.areas[area_id].nodes)
        if len(node_ids)<2:
            QMessageBox.information(
                self,"Rigid Diaphragm",
                "Select slab or frame objects containing at least "
                "two joints on the same floor."
            )
            return
        elevations={
            round(self.project.nodes[nid].z,8)
            for nid in node_ids
        }
        if len(elevations)>1:
            QMessageBox.warning(
                self,"Rigid Diaphragm",
                "Selected joints must lie on one horizontal story."
            )
            return
        dialog=DiaphragmDialog(
            self.project,sorted(node_ids),self
        )
        if dialog.exec():
            self.analysis_result=None
            self.results_panel.clear_results()
            self.log_message(
                f"Rigid diaphragm assigned to "
                f"{len(node_ids)} joints."
            )

    def run_pdelta_analysis(self):
        if not self.check_model():
            return
        case_name=self.case_combo.currentText()
        iterations,ok=QInputDialog.getInt(
            self,"P-Delta Analysis",
            "Maximum iterations:",20,2,100,1
        )
        if not ok:
            return
        tolerance,ok=QInputDialog.getDouble(
            self,"P-Delta Analysis",
            "Relative convergence tolerance:",
            1.0e-5,1.0e-9,1.0e-2,8
        )
        if not ok:
            return
        try:
            self.analysis_result=PDeltaSolver(
                self.project
            ).solve(case_name,iterations,tolerance)
        except Exception as exc:
            QMessageBox.critical(
                self,"P-Delta Analysis Error",str(exc)
            )
            return
        self.view3d.set_analysis_result(self.analysis_result)
        self.plan.set_analysis_result(self.analysis_result)
        self.results_panel.set_results(
            self.project,self.analysis_result
        )
        self.results_dock.show()
        self.results_dock.raise_()
        self.results_panel.mode_combo.setCurrentText(
            "Deformed"
        )
        self.log_message(
            f"P-Delta completed in "
            f"{self.analysis_result.iterations} iterations; "
            f"relative error="
            f"{self.analysis_result.convergence_error:.3e}."
        )

    def run_analysis(self):
        if not self.check_model():
            return
        case_name=self.case_combo.currentText()
        try:
            self.analysis_result=LinearStaticSolver(
                self.project
            ).solve(case_name)
        except Exception as exc:
            QMessageBox.critical(
                self,"Analysis Error",str(exc)
            )
            self.log_message(f"Analysis failed: {exc}")
            return

        self.view3d.set_analysis_result(
            self.analysis_result
        )
        self.plan.set_analysis_result(
            self.analysis_result
        )
        self.results_panel.set_results(
            self.project,self.analysis_result
        )
        self.concrete_design_result=None
        self.design_panel.clear_design()
        self.plan.set_concrete_design_result(None)
        self.view3d.set_concrete_design_result(None)
        self.results_dock.show()
        self.code_dock.show()
        self.design_dock.show()
        self.results_dock.raise_()
        self.log_message(
            f"Analysis completed: {case_name}. "
            f"Maximum translation = "
            f"{self.analysis_result.max_translation*1000.0:.6f} mm"
        )
        # Show deformed shape immediately without a pop-up window.
        self.results_panel.mode_combo.setCurrentText(
            "Deformed"
        )

    def run_concrete_design(self, show_notice=True):
        if self.analysis_result is None:
            self.run_analysis()
            if self.analysis_result is None:
                return False
        code=self.project.design_codes
        settings=ConcreteDesignSettings(
            strength_reduction_factor=code.concrete_phi_flexure,
        )
        self.concrete_design_result=design_concrete(
            self.project,self.analysis_result,settings
        )
        self.design_panel.set_design(
            self.concrete_design_result
        )
        self.plan.set_concrete_design_result(
            self.concrete_design_result
        )
        self.view3d.set_concrete_design_result(
            self.concrete_design_result
        )
        self.design_dock.show()
        self.design_dock.raise_()
        if show_notice:
            QMessageBox.warning(
                self,"Preliminary Concrete Design",
                "The reinforcement calculation is preliminary only and "
                "must be independently verified by a qualified structural engineer."
            )
        return True

    def run_advanced_design(self):
        if self.analysis_result is None:
            QMessageBox.information(
                self,"Advanced Concrete Checks",
                "Run structural analysis first."
            )
            return
        self.advanced_design_result=run_advanced_design(
            self.project,self.analysis_result
        )
        self.advanced_design_panel.set_design(
            self.advanced_design_result
        )
        self.advanced_design_dock.show()
        self.advanced_design_dock.raise_()
        QMessageBox.warning(
            self,"Advanced Preliminary Checks",
            "These checks are preliminary and must be independently verified."
        )


    def edit_code_settings(self):
        dialog=CodeSettingsDialog(self.project,self)
        if dialog.exec():
            self.code_widget.load_from_project()
            self.log_message(
                "Project code settings updated: "
                f"{self.project.design_codes.concrete_code}; "
                f"{self.project.design_codes.loading_code}."
            )

    def show_code_summary(self):
        c=self.project.design_codes
        QMessageBox.information(
            self,"Project Code Summary",
            f"Concrete: {c.concrete_code}\n"
            f"Loading: {c.loading_code}\n"
            f"Steel: {c.steel_code}\n"
            f"Seismic: {c.seismic_code}\n"
            f"Wind: {c.wind_code}\n"
            f"Importance factor: {c.importance_factor:.3f}\n"
            f"φ flexure: {c.concrete_phi_flexure:.3f}\n"
            f"φ shear: {c.concrete_phi_shear:.3f}\n"
            f"Steel method: {c.steel_resistance_method}\n\n"
            f"{c.notes}"
        )

    def _set_animation_speed(self,text):
        try:
            self.animation_speed=float(
                text.replace("×","")
            )
        except ValueError:
            self.animation_speed=1.0

    def start_deformed_animation(self):
        if self.analysis_result is None:
            QMessageBox.information(
                self,"Deformed Animation",
                "Run static analysis first."
            )
            return
        self.display_results("Deformed")
        self.animation_target="Deformed"
        self.animation_angle=0.0
        self.animation_timer.start()
        self.status_mode.setText(
            "Animating static deformed shape"
        )

    def start_mode_animation(self):
        if self.modal_result is None:
            QMessageBox.information(
                self,"Mode Animation",
                "Run modal analysis first."
            )
            return
        self.animation_target="Mode"
        self.animation_angle=0.0
        self.animation_timer.start()
        self.status_mode.setText(
            f"Animating mode {self.view3d.modal_mode_number}"
        )

    def stop_animation(self):
        self.animation_timer.stop()
        self.animation_target="None"
        self.view3d.set_animation_state("None",1.0)
        self.status_mode.setText("Animation stopped")

    def _advance_animation(self):
        import math
        self.animation_angle=(
            self.animation_angle+0.12*self.animation_speed
        )%(2.0*math.pi)
        if self.animation_target=="Deformed":
            factor=0.5*(1.0-math.cos(self.animation_angle))
        else:
            factor=math.sin(self.animation_angle)
        self.view3d.set_animation_state(
            self.animation_target,factor
        )

    def display_results(self,mode):
        reinforcement_modes=(
            "Beam Rebar","Slab Rebar X","Slab Rebar Y",
            "Slab As X","Slab As Y",
        )
        if mode in reinforcement_modes and self.concrete_design_result is None:
            if not self.run_concrete_design(show_notice=False):
                return
        if mode!="None" and self.analysis_result is None:
            QMessageBox.information(
                self,"Display Results",
                "Run the analysis before displaying results."
            )
            self.action_none.setChecked(True)
            return
        self.view3d.set_result_mode(mode)
        self.plan.set_result_mode(mode)
        if self.results_panel.mode_combo.currentText()!=mode:
            self.results_panel.mode_combo.blockSignals(True)
            self.results_panel.mode_combo.setCurrentText(mode)
            self.results_panel.mode_combo.blockSignals(False)
        self.status_mode.setText(f"Display: {mode}")

    def reset_dock_layout(self):
        self.explorer_dock.show()
        self.properties_dock.show()
        self.output_dock.show()
        self.results_dock.show()
        self.addDockWidget(
            Qt.DockWidgetArea.LeftDockWidgetArea,
            self.explorer_dock,
        )
        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea,
            self.properties_dock,
        )
        self.addDockWidget(
            Qt.DockWidgetArea.BottomDockWidgetArea,
            self.output_dock,
        )
        self.addDockWidget(
            Qt.DockWidgetArea.BottomDockWidgetArea,
            self.results_dock,
        )
        self.tabifyDockWidget(
            self.output_dock,self.results_dock
        )

    def _set_display_option(self,name,value):
        if hasattr(self.plan,name):
            setattr(self.plan,name,bool(value))
            self.plan.update()
        if hasattr(self.view3d,name):
            setattr(self.view3d,name,bool(value))
            self.view3d.update()

    def show_shortcuts(self):
        QMessageBox.information(
            self,"AIDESIGN Keyboard Shortcuts",
            "Project\n"
            "Ctrl+N  New\nCtrl+O  Open\nCtrl+S  Save\n"
            "Ctrl+Shift+D  Import DXF\n\n"
            "Modeling\n"
            "V  Select / Window Select\nB  Beam\nC  Column\n"
            "S  Slab\nM  Mesh Slab\nDelete  Delete\nCtrl+A  Select All\n"
            "Ctrl+G  Grids\nCtrl+Shift+F  Frame Sections\n\n"
            "Analysis and Results\n"
            "F5  Run Static Analysis\nF6  Check Model\nF7  Modal Analysis\n"
            "F8  Moment\nF9  Shear\nF10  Deformed Shape\n"
            "Ctrl+F10  Animate Deformed\nShift+F10  Stop Animation\n\n"
            "Views\n"
            "F4  Fit Plan\nCtrl+I  Isometric\nCtrl+1  Top\n"
            "Ctrl+2  Front\nCtrl+3  Right\nCtrl+Shift+C  Codes"
        )

    def show_about(self):
        QMessageBox.about(
            self,"About AIDESIGN",
            "AIDESIGN Structural Analysis Platform\n"
            "Version 1.4\n\n"
            "Private engineering software project."
        )

    def run_modal_analysis(self):
        count,ok=QInputDialog.getInt(
            self,"Modal Analysis","Number of modes:",
            12,1,100,1
        )
        if not ok:
            return
        try:
            self.modal_result=ModalSolver(
                self.project
            ).solve(count)
        except Exception as exc:
            QMessageBox.critical(
                self,"Modal Analysis Error",str(exc)
            )
            return
        self.modal_panel.set_results(self.modal_result)
        self.modal_dock.show()
        self.modal_dock.raise_()
        self.show_mode_shape(1)
        self.log_message(
            f"Modal analysis completed: "
            f"{len(self.modal_result.modes)} modes."
        )

    def show_mode_shape(self,mode_number):
        if self.modal_result is None:
            QMessageBox.information(
                self,"Mode Shape",
                "Run modal analysis first."
            )
            return
        mode_number=max(
            1,min(mode_number,len(self.modal_result.modes))
        )
        self.plan.set_modal_result(
            self.modal_result,mode_number
        )
        self.view3d.set_modal_result(
            self.modal_result,mode_number
        )
        mode=self.modal_result.modes[mode_number-1]
        self.status_mode.setText(
            f"Mode {mode_number}: "
            f"T={mode.period_s:.5f}s, "
            f"f={mode.frequency_hz:.5f}Hz"
        )

    def _refresh_unit_dependent_text(self):
        self.plan.update()
        self.view3d.update()
        if self.analysis_result is not None:
            self.results_panel.set_results(self.project,self.analysis_result)
        self.status_mode.setText(
            "Display units updated; internal solver units remain kN-m."
        )

    def log_message(self,text):
        self.output.append(text)
