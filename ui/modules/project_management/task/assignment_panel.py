from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTableView,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from core.modules.project_management.domain.task import TaskAssignment
from core.modules.project_management.services.resource import ResourceService
from core.modules.project_management.services.task import TaskService
from ui.modules.project_management.dashboard.styles import dashboard_action_button_style, dashboard_meta_chip_style
from src.ui.shared.widgets.guards import apply_permission_hint, make_guarded_slot
from src.ui.shared.formatting.style_utils import style_table
from src.ui.shared.formatting.ui_config import UIConfig as CFG
from ui.modules.project_management.task.assignment_models import (
    AssignmentRow,
    AssignmentTableModel,
    _assignment_allocation,
    _assignment_hours_logged,
)


class TaskAssignmentPanelMixin:
    table: QTableView
    assignment_table: QTableView
    assignment_model: AssignmentTableModel
    assignment_title_label: QLabel
    assignment_summary_label: QLabel
    btn_assignment_add: QPushButton
    btn_assignment_remove: QPushButton
    btn_assignment_set_alloc: QPushButton
    btn_assignment_log_hours: QPushButton

    dependency_table: QTableWidget
    dependency_title_label: QLabel
    dependency_summary_label: QLabel
    btn_dependency_add: QPushButton
    btn_dependency_remove: QPushButton

    _task_service: TaskService
    _resource_service: ResourceService

    def _configure_assignment_table_columns(self) -> None:
        header = self.assignment_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.resizeSection(1, 110)
        header.resizeSection(2, 120)
        self.assignment_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def _build_assignment_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("taskAssignmentsPanel")
        panel.setStyleSheet(
            f"""
            QWidget#taskAssignmentsPanel {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 10px;
            }}
            QWidget#taskAssignmentsPanel QLabel {{
                color: {CFG.COLOR_TEXT_PRIMARY};
            }}
            QWidget#taskWorkSection {{
                background-color: {CFG.COLOR_BG_SURFACE_ALT};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            QTabWidget#taskWorkTabs::pane {{
                border: none;
                background: transparent;
            }}
            QTabWidget#taskWorkTabs QTabBar::tab {{
                background: {CFG.COLOR_BG_SURFACE_ALT};
                color: {CFG.COLOR_TEXT_SECONDARY};
                border: 1px solid {CFG.COLOR_BORDER};
                border-bottom: none;
                min-width: 120px;
                padding: 6px 12px;
                margin-right: 4px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                font-weight: 600;
            }}
            QTabWidget#taskWorkTabs QTabBar::tab:selected {{
                background: {CFG.COLOR_BG_SURFACE};
                color: {CFG.COLOR_TEXT_PRIMARY};
                border-color: {CFG.COLOR_BORDER_STRONG};
                border-top: 3px solid {CFG.COLOR_ACCENT};
            }}
            """
        )
        panel_layout = QVBoxLayout(panel)
        panel_layout.setSpacing(CFG.SPACING_MD)
        panel_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)

        title = QLabel("Execution Workspace")
        title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        panel_layout.addWidget(title)

        self.work_tabs = QTabWidget()
        self.work_tabs.setObjectName("taskWorkTabs")
        self.work_tabs.setDocumentMode(True)
        self.work_tabs.tabBar().setExpanding(True)
        self.work_tabs.addTab(self._build_assignment_section(), "Assignments")
        self.work_tabs.addTab(self._build_dependency_section(), "Dependencies")
        panel_layout.addWidget(self.work_tabs, 1)

        self._set_assignment_panel_actions_state(
            task_selected=False,
            assignment_selected=False,
            dependency_selected=False,
        )
        return panel

    def _build_assignment_section(self) -> QWidget:
        box = QWidget()
        box.setObjectName("taskWorkSection")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        layout.setSpacing(CFG.SPACING_SM)

        eyebrow = QLabel("ASSIGNMENTS")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        layout.addWidget(eyebrow)

        section_title = QLabel("Resource coverage for the selected task")
        section_title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        layout.addWidget(section_title)

        self.assignment_title_label = QLabel("Select a task to view assignments.")
        self.assignment_title_label.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.assignment_title_label.setWordWrap(True)
        layout.addWidget(self.assignment_title_label)

        self.assignment_summary_label = QLabel("Resource coverage, allocation pressure, and logged effort appear here.")
        self.assignment_summary_label.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        self.assignment_summary_label.setWordWrap(True)
        layout.addWidget(self.assignment_summary_label)

        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(CFG.SPACING_SM)
        self.assignment_count_chip = self._build_metric_chip("Resources 0")
        self.assignment_alloc_chip = self._build_metric_chip("Allocation 0.0%")
        self.assignment_hours_chip = self._build_metric_chip("Hours 0.00")
        metrics_row.addWidget(self.assignment_count_chip)
        metrics_row.addWidget(self.assignment_alloc_chip)
        metrics_row.addWidget(self.assignment_hours_chip)
        metrics_row.addStretch()
        layout.addLayout(metrics_row)

        self.assignment_table = QTableView()
        self.assignment_model = AssignmentTableModel()
        self.assignment_table.setModel(self.assignment_model)
        self.assignment_table.setSelectionBehavior(QTableView.SelectRows)
        self.assignment_table.setSelectionMode(QTableView.SingleSelection)
        self.assignment_table.setEditTriggers(QTableView.NoEditTriggers)
        self.assignment_table.setMinimumHeight(180)
        style_table(self.assignment_table)
        self.assignment_model.modelReset.connect(self._configure_assignment_table_columns)
        self.assignment_model.layoutChanged.connect(self._configure_assignment_table_columns)
        QTimer.singleShot(0, self._configure_assignment_table_columns)
        layout.addWidget(self.assignment_table)

        actions_label = QLabel("Actions")
        actions_label.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        layout.addWidget(actions_label)
        action_grid = QGridLayout()
        action_grid.setHorizontalSpacing(CFG.SPACING_SM)
        action_grid.setVerticalSpacing(CFG.SPACING_SM)
        self.btn_assignment_add = QPushButton("Assign Resource")
        self.btn_assignment_remove = QPushButton("Remove Assignment")
        self.btn_assignment_set_alloc = QPushButton("Adjust Allocation")
        self.btn_assignment_log_hours = QPushButton("Open Timesheet")
        for btn in (
            self.btn_assignment_add,
            self.btn_assignment_remove,
            self.btn_assignment_set_alloc,
            self.btn_assignment_log_hours,
        ):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_assignment_add.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_assignment_remove.setStyleSheet(dashboard_action_button_style("danger"))
        self.btn_assignment_set_alloc.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_assignment_log_hours.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_assignment_add.setToolTip("Assign a project resource to the selected task")
        self.btn_assignment_remove.setToolTip("Remove the selected task assignment")
        self.btn_assignment_set_alloc.setToolTip("Adjust allocation for the selected assignment")
        self.btn_assignment_log_hours.setToolTip("Open the timesheet for the selected assignment")
        action_grid.addWidget(self.btn_assignment_add, 0, 0)
        action_grid.addWidget(self.btn_assignment_set_alloc, 0, 1)
        action_grid.addWidget(self.btn_assignment_log_hours, 1, 0)
        action_grid.addWidget(self.btn_assignment_remove, 1, 1)
        action_grid.setColumnStretch(0, 1)
        action_grid.setColumnStretch(1, 1)
        layout.addLayout(action_grid)

        self.assignment_table.selectionModel().selectionChanged.connect(
            self._on_assignment_selection_changed
        )
        self.btn_assignment_add.clicked.connect(
            make_guarded_slot(self, title="Assignments", callback=self.add_assignment_inline)
        )
        self.btn_assignment_remove.clicked.connect(
            make_guarded_slot(self, title="Assignments", callback=self.remove_assignment_inline)
        )
        self.btn_assignment_set_alloc.clicked.connect(
            make_guarded_slot(
                self,
                title="Assignments",
                callback=self.set_assignment_allocation_inline,
            )
        )
        self.btn_assignment_log_hours.clicked.connect(
            make_guarded_slot(self, title="Assignments", callback=self.log_assignment_hours_inline)
        )
        can_manage = bool(getattr(self, "_can_manage_assignments", True))
        apply_permission_hint(
            self.btn_assignment_add,
            allowed=can_manage,
            missing_permission="task.manage",
        )
        apply_permission_hint(
            self.btn_assignment_remove,
            allowed=can_manage,
            missing_permission="task.manage",
        )
        apply_permission_hint(
            self.btn_assignment_set_alloc,
            allowed=can_manage,
            missing_permission="task.manage",
        )
        apply_permission_hint(
            self.btn_assignment_log_hours,
            allowed=can_manage,
            missing_permission="task.manage",
        )
        return box

    def _build_metric_chip(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(dashboard_meta_chip_style())
        return label

    def _on_task_selection_changed(self, *_args) -> None:
        self._reload_assignment_panel_for_selected_task()

    def _on_assignment_selection_changed(self, *_args) -> None:
        self._set_assignment_panel_actions_state(
            task_selected=self._get_selected_task() is not None,
            assignment_selected=self._get_selected_assignment() is not None,
            dependency_selected=self._get_selected_dependency_id() is not None,
        )

    def _reload_assignment_panel_for_selected_task(self) -> None:
        task = self._get_selected_task()
        if not task:
            self.assignment_model.set_rows([])
            self.assignment_title_label.setText("Select a task to view assignments.")
            self.assignment_summary_label.setText(
                "Resource coverage, allocation pressure, and logged effort appear here."
            )
            self.assignment_count_chip.setText("Resources 0")
            self.assignment_alloc_chip.setText("Allocation 0.0%")
            self.assignment_hours_chip.setText("Hours 0.00")
            self._clear_dependency_panel_for_no_task()
            self._set_assignment_panel_actions_state(
                task_selected=False,
                assignment_selected=False,
                dependency_selected=False,
            )
            return

        assignments = self._task_service.list_assignments_for_tasks([task.id])
        resources = {r.id: r for r in self._resource_service.list_resources()}
        rows: list[AssignmentRow] = []
        total_alloc = 0.0
        total_hours = 0.0
        for assignment in assignments:
            resource = resources.get(assignment.resource_id)
            name = resource.name if resource else assignment.resource_id
            rows.append(AssignmentRow(assignment=assignment, resource_name=name))
            total_alloc += _assignment_allocation(assignment)
            total_hours += _assignment_hours_logged(assignment)

        rows.sort(key=lambda row: row.resource_name.lower())
        self.assignment_model.set_rows(rows)
        self.assignment_title_label.setText(task.name)
        self.assignment_summary_label.setText(
            "Resource coverage, allocation pressure, and logged effort for the active task."
        )
        self.assignment_count_chip.setText(f"Resources {len(rows)}")
        self.assignment_alloc_chip.setText(f"Allocation {total_alloc:.1f}%")
        self.assignment_hours_chip.setText(f"Hours {total_hours:.2f}")

        self._reload_dependency_panel_for_selected_task(task)
        self._set_assignment_panel_actions_state(
            task_selected=True,
            assignment_selected=self._get_selected_assignment() is not None,
            dependency_selected=self._get_selected_dependency_id() is not None,
        )

    def _set_assignment_panel_actions_state(
        self,
        task_selected: bool,
        assignment_selected: bool,
        dependency_selected: bool = False,
    ) -> None:
        can_manage_assignments = bool(getattr(self, "_can_manage_assignments", True))
        can_add_dependencies = bool(getattr(self, "_can_add_dependencies", True))
        can_remove_dependencies = bool(
            getattr(self, "_can_remove_dependencies", can_add_dependencies)
        )
        self.btn_assignment_add.setEnabled(can_manage_assignments and task_selected)
        self.btn_assignment_remove.setEnabled(
            can_manage_assignments and task_selected and assignment_selected
        )
        self.btn_assignment_set_alloc.setEnabled(
            can_manage_assignments and task_selected and assignment_selected
        )
        self.btn_assignment_log_hours.setEnabled(
            can_manage_assignments and task_selected and assignment_selected
        )
        self.btn_dependency_add.setEnabled(can_add_dependencies and task_selected)
        self.btn_dependency_remove.setEnabled(
            can_remove_dependencies and task_selected and dependency_selected
        )

    def _get_selected_assignment(self) -> TaskAssignment | None:
        indexes = self.assignment_table.selectionModel().selectedRows()
        if not indexes:
            return None
        return self.assignment_model.get_assignment(indexes[0].row())


__all__ = ["TaskAssignmentPanelMixin"]
