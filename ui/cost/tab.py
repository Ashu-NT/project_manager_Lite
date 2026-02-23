from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableView,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from core.events.domain_events import domain_events
from core.models import Project, Task
from core.services.cost import CostService
from core.services.project import ProjectService
from core.services.reporting import ReportingService
from core.services.resource import ResourceService
from core.services.task import TaskService
from ui.cost.actions import CostActionsMixin
from ui.cost.labor_summary import CostLaborSummaryMixin
from ui.cost.models import CostTableModel
from ui.cost.project_flow import CostProjectFlowMixin
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class CostTab(CostProjectFlowMixin, CostLaborSummaryMixin, CostActionsMixin, QWidget):
    def __init__(
        self,
        project_service: ProjectService,
        task_service: TaskService,
        cost_service: CostService,
        reporting_service: ReportingService,
        resource_service: ResourceService,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._project_service: ProjectService = project_service
        self._task_service: TaskService = task_service
        self._cost_service: CostService = cost_service
        self._reporting_service: ReportingService = reporting_service
        self._resource_service: ResourceService = resource_service

        self._current_project: Project | None = None
        self._project_tasks: list[Task] = []

        self._setup_ui()
        self._load_projects()
        domain_events.costs_changed.connect(self._on_costs_or_tasks_changed)
        domain_events.tasks_changed.connect(self._on_costs_or_tasks_changed)
        domain_events.project_changed.connect(self._on_project_changed_event)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )
        self.setMinimumSize(self.sizeHint())

        top = QHBoxLayout()
        top.addWidget(QLabel("Project:"))
        self.project_combo = QComboBox()
        self.project_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.project_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.btn_reload_projects = QPushButton(CFG.RELOAD_PROJECTS_LABEL)
        top.addWidget(self.project_combo)
        top.addWidget(self.btn_reload_projects)
        top.addStretch()
        layout.addLayout(top)

        toolbar = QHBoxLayout()
        self.btn_new = QPushButton(CFG.NEW_COST_ITEM_LABEL)
        self.btn_edit = QPushButton(CFG.EDIT_LABEL)
        self.btn_delete = QPushButton(CFG.DELETE_LABEL)
        self.btn_labor_details = QPushButton(CFG.LABOR_DETAILS_BUTTON_LABEL)
        self.btn_refresh_costs = QPushButton(CFG.REFRESH_COSTS_LABEL)

        for btn in (
            self.btn_reload_projects,
            self.btn_new,
            self.btn_edit,
            self.btn_delete,
            self.btn_refresh_costs,
        ):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)

        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh_costs)
        layout.addLayout(toolbar)

        self.grp_budget = QGroupBox("Budget Summary")
        self.grp_budget.setFont(CFG.GROUPBOX_TITLE_FONT)

        self.lbl_budget_summary = QLabel("")
        self.lbl_budget_summary.setWordWrap(True)
        self.lbl_budget_summary.setStyleSheet(CFG.NOTE_STYLE_SHEET)

        g = QGridLayout()
        g.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        g.addWidget(self.lbl_budget_summary, 0, 0)
        self.grp_budget.setLayout(g)
        layout.addWidget(self.grp_budget)

        self.tbl_labor_summary = QTableWidget()
        self.tbl_labor_summary.setColumnCount(len(CFG.LABOR_SUMMARY_HEADERS))
        self.tbl_labor_summary.setHorizontalHeaderLabels(CFG.LABOR_SUMMARY_HEADERS)
        self.tbl_labor_summary.verticalHeader().setVisible(False)
        self.tbl_labor_summary.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_labor_summary.setSelectionMode(QTableWidget.NoSelection)
        self.tbl_labor_summary.horizontalHeader().setStretchLastSection(True)
        self.tbl_labor_summary.setMinimumHeight(80)
        self.tbl_labor_summary.setSizePolicy(CFG.INPUT_POLICY)
        style_table(self.tbl_labor_summary)

        self.btn_labor_details.setText(CFG.LABOR_DETAILS_BUTTON_LABEL)
        self.btn_labor_details.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_labor_details.setFixedHeight(CFG.BUTTON_HEIGHT)

        self.grp_labor = QGroupBox(CFG.LABOR_GROUP_TITLE)
        self.grp_labor.setFont(CFG.GROUPBOX_TITLE_FONT)

        grid = QGridLayout()
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 0)
        grid.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )
        grid.addWidget(self.tbl_labor_summary, 0, 0)
        grid.addWidget(self.btn_labor_details, 0, 1, alignment=Qt.AlignTop)

        self.lbl_labor_note = QLabel("")
        self.lbl_labor_note.setWordWrap(True)
        self.lbl_labor_note.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        grid.addWidget(self.lbl_labor_note, 1, 0, 1, 2)

        self.grp_labor.setLayout(grid)
        layout.addWidget(self.grp_labor)

        self.table = QTableView()
        self.model = CostTableModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        style_table(self.table)
        layout.addWidget(self.table)

        self.btn_reload_projects.clicked.connect(self._load_projects)
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        self.btn_refresh_costs.clicked.connect(self.reload_costs)
        self.btn_new.clicked.connect(self.create_cost_item)
        self.btn_edit.clicked.connect(self.edit_cost_item)
        self.btn_delete.clicked.connect(self.delete_cost_item)
        self.btn_labor_details.clicked.connect(self.show_labor_details)
        self.tbl_labor_summary.itemSelectionChanged.connect(self._on_labor_table_selected)
