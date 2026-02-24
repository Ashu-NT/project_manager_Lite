from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
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


def _kpi_card(title: str, value: str = "-") -> tuple[QFrame, QLabel]:
    card = QFrame()
    card.setStyleSheet(CFG.PROJECT_SUMMARY_BOX_STYLE)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
    layout.setSpacing(2)
    lbl_title = QLabel(title)
    lbl_title.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
    lbl_value = QLabel(value)
    lbl_value.setStyleSheet(CFG.DASHBOARD_KPI_VALUE_TEMPLATE.format(color=CFG.COLOR_ACCENT))
    layout.addWidget(lbl_title)
    layout.addWidget(lbl_value)
    return card, lbl_value


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
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        title = QLabel("Cost Control")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel("Track budget health, labor usage, and detailed project costs.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        root.addWidget(title)
        root.addWidget(subtitle)

        top = QHBoxLayout()
        top.addWidget(QLabel("Project:"))
        self.project_combo = QComboBox()
        self.project_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.project_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.btn_reload_projects = QPushButton(CFG.RELOAD_PROJECTS_LABEL)
        self.btn_reload_projects.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_reload_projects.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        top.addWidget(self.project_combo, 1)
        top.addWidget(self.btn_reload_projects)
        top.addSpacing(CFG.SPACING_MD)

        self.btn_new = QPushButton(CFG.NEW_COST_ITEM_LABEL)
        self.btn_edit = QPushButton(CFG.EDIT_LABEL)
        self.btn_delete = QPushButton(CFG.DELETE_LABEL)
        self.btn_refresh_costs = QPushButton(CFG.REFRESH_COSTS_LABEL)
        for btn in (self.btn_new, self.btn_edit, self.btn_delete, self.btn_refresh_costs):
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)

        top.addWidget(self.btn_new)
        top.addWidget(self.btn_edit)
        top.addWidget(self.btn_delete)
        top.addStretch()
        top.addWidget(self.btn_refresh_costs)
        root.addLayout(top)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(CFG.SPACING_SM)
        budget_card, self.lbl_kpi_budget = _kpi_card("Budget")
        planned_card, self.lbl_kpi_planned = _kpi_card("Planned")
        actual_card, self.lbl_kpi_actual = _kpi_card("Actual")
        remaining_card, self.lbl_kpi_remaining = _kpi_card("Remaining")
        kpi_row.addWidget(budget_card)
        kpi_row.addWidget(planned_card)
        kpi_row.addWidget(actual_card)
        kpi_row.addWidget(remaining_card)
        root.addLayout(kpi_row)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        root.addWidget(splitter, 1)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(CFG.SPACING_SM)

        grp_costs = QGroupBox("Cost Items")
        grp_costs.setFont(CFG.GROUPBOX_TITLE_FONT)
        costs_layout = QVBoxLayout(grp_costs)
        costs_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        costs_layout.setSpacing(CFG.SPACING_SM)

        self.table = QTableView()
        self.model = CostTableModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        style_table(self.table)
        costs_layout.addWidget(self.table)
        left_layout.addWidget(grp_costs)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(CFG.SPACING_SM)

        grp_labor = QGroupBox("Labor Snapshot")
        grp_labor.setFont(CFG.GROUPBOX_TITLE_FONT)
        labor_layout = QVBoxLayout(grp_labor)
        labor_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        labor_layout.setSpacing(CFG.SPACING_MD)

        self.tbl_labor_summary = QTableWidget()
        self.tbl_labor_summary.setColumnCount(len(CFG.LABOR_SUMMARY_HEADERS))
        self.tbl_labor_summary.setHorizontalHeaderLabels(CFG.LABOR_SUMMARY_HEADERS)
        self.tbl_labor_summary.verticalHeader().setVisible(False)
        self.tbl_labor_summary.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_labor_summary.setSelectionMode(QTableWidget.NoSelection)
        self.tbl_labor_summary.horizontalHeader().setStretchLastSection(True)
        self.tbl_labor_summary.setMinimumHeight(160)
        style_table(self.tbl_labor_summary)
        labor_layout.addWidget(self.tbl_labor_summary)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.btn_labor_details = QPushButton(CFG.LABOR_DETAILS_BUTTON_LABEL)
        self.btn_labor_details.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_labor_details.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        button_row.addWidget(self.btn_labor_details)
        labor_layout.addLayout(button_row)

        self.lbl_labor_note = QLabel("")
        self.lbl_labor_note.setWordWrap(True)
        self.lbl_labor_note.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        labor_layout.addWidget(self.lbl_labor_note)
        right_layout.addWidget(grp_labor, 1)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([820, 420])

        self.btn_reload_projects.clicked.connect(self._load_projects)
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        self.btn_refresh_costs.clicked.connect(self.reload_costs)
        self.btn_new.clicked.connect(self.create_cost_item)
        self.btn_edit.clicked.connect(self.edit_cost_item)
        self.btn_delete.clicked.connect(self.delete_cost_item)
        self.btn_labor_details.clicked.connect(self.show_labor_details)
        self.tbl_labor_summary.itemSelectionChanged.connect(self._on_labor_table_selected)
