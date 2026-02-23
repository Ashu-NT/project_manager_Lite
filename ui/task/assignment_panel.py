from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.models import TaskAssignment
from core.services.resource import ResourceService
from core.services.task import TaskService
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG
from ui.task.assignment_models import (
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
    btn_assign: QPushButton
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
        self.assignment_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

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
            """
        )
        panel_layout = QVBoxLayout(panel)
        panel_layout.setSpacing(CFG.SPACING_SM)
        panel_layout.setContentsMargins(
            CFG.MARGIN_SM,
            CFG.MARGIN_SM,
            CFG.MARGIN_SM,
            CFG.MARGIN_SM,
        )

        title = QLabel("Assignments")
        title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        panel_layout.addWidget(title)

        self.assignment_title_label = QLabel("Select a task to view assignments.")
        self.assignment_title_label.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.assignment_title_label.setWordWrap(True)
        panel_layout.addWidget(self.assignment_title_label)

        self.assignment_summary_label = QLabel("")
        self.assignment_summary_label.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        self.assignment_summary_label.setWordWrap(True)
        panel_layout.addWidget(self.assignment_summary_label)

        self.assignment_table = QTableView()
        self.assignment_model = AssignmentTableModel()
        self.assignment_table.setModel(self.assignment_model)
        self.assignment_table.setSelectionBehavior(QTableView.SelectRows)
        self.assignment_table.setSelectionMode(QTableView.SingleSelection)
        self.assignment_table.setEditTriggers(QTableView.NoEditTriggers)
        self.assignment_table.setMinimumHeight(240)
        style_table(self.assignment_table)
        self.assignment_model.modelReset.connect(self._configure_assignment_table_columns)
        self.assignment_model.layoutChanged.connect(self._configure_assignment_table_columns)
        QTimer.singleShot(0, self._configure_assignment_table_columns)
        panel_layout.addWidget(self.assignment_table)

        button_row = QHBoxLayout()
        self.btn_assignment_add = QPushButton("Add")
        self.btn_assignment_remove = QPushButton("Remove")
        self.btn_assignment_set_alloc = QPushButton("Set Allocation")
        self.btn_assignment_log_hours = QPushButton("Log Hours")

        for btn in (
            self.btn_assignment_add,
            self.btn_assignment_remove,
            self.btn_assignment_set_alloc,
            self.btn_assignment_log_hours,
        ):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)

        button_row.addWidget(self.btn_assignment_add)
        button_row.addWidget(self.btn_assignment_remove)
        button_row.addWidget(self.btn_assignment_set_alloc)
        button_row.addWidget(self.btn_assignment_log_hours)
        button_row.addStretch()
        panel_layout.addLayout(button_row)

        self.assignment_table.selectionModel().selectionChanged.connect(
            self._on_assignment_selection_changed
        )
        self.btn_assignment_add.clicked.connect(self.add_assignment_inline)
        self.btn_assignment_remove.clicked.connect(self.remove_assignment_inline)
        self.btn_assignment_set_alloc.clicked.connect(self.set_assignment_allocation_inline)
        self.btn_assignment_log_hours.clicked.connect(self.log_assignment_hours_inline)

        self._set_assignment_panel_actions_state(task_selected=False, assignment_selected=False)
        return panel

    def _on_task_selection_changed(self, *_args) -> None:
        self._reload_assignment_panel_for_selected_task()

    def _on_assignment_selection_changed(self, *_args) -> None:
        self._set_assignment_panel_actions_state(
            task_selected=self._get_selected_task() is not None,
            assignment_selected=self._get_selected_assignment() is not None,
        )

    def _reload_assignment_panel_for_selected_task(self) -> None:
        task = self._get_selected_task()
        if not task:
            self.assignment_model.set_rows([])
            self.assignment_title_label.setText("Select a task to view assignments.")
            self.assignment_summary_label.setText("")
            self._set_assignment_panel_actions_state(
                task_selected=False,
                assignment_selected=False,
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
        self.assignment_title_label.setText(f"Task: {task.name}")
        self.assignment_summary_label.setText(
            f"{len(rows)} assigned | Total allocation: {total_alloc:.1f}% | "
            f"Hours logged: {total_hours:.2f}"
        )
        self._set_assignment_panel_actions_state(
            task_selected=True,
            assignment_selected=bool(rows),
        )

    def _set_assignment_panel_actions_state(
        self,
        task_selected: bool,
        assignment_selected: bool,
    ) -> None:
        self.btn_assignment_add.setEnabled(task_selected)
        self.btn_assignment_remove.setEnabled(task_selected and assignment_selected)
        self.btn_assignment_set_alloc.setEnabled(task_selected and assignment_selected)
        self.btn_assignment_log_hours.setEnabled(task_selected and assignment_selected)

    def _get_selected_assignment(self) -> TaskAssignment | None:
        indexes = self.assignment_table.selectionModel().selectedRows()
        if not indexes:
            return None
        return self.assignment_model.get_assignment(indexes[0].row())
