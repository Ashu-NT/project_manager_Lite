from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QDialog,
    QSplitter,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.models import Task, TaskAssignment
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
from ui.task.dependency_add_dialog import DependencyAddDialog
from ui.task.dependency_shared import dependency_direction as _dependency_direction


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
        self.assignment_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def _configure_dependency_table_columns(self) -> None:
        header = self.dependency_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)

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
        panel_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)

        title = QLabel("Task Work")
        title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        panel_layout.addWidget(title)

        self.panel_splitter = QSplitter(Qt.Vertical)
        self.panel_splitter.setChildrenCollapsible(False)
        self.panel_splitter.setHandleWidth(8)
        self.panel_splitter.addWidget(self._build_assignment_section())
        self.panel_splitter.addWidget(self._build_dependency_section())
        self.panel_splitter.setStretchFactor(0, 3)
        self.panel_splitter.setStretchFactor(1, 2)
        self.panel_splitter.setSizes([360, 260])
        panel_layout.addWidget(self.panel_splitter, 1)

        self._set_assignment_panel_actions_state(
            task_selected=False,
            assignment_selected=False,
            dependency_selected=False,
        )
        return panel

    def _build_assignment_section(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(CFG.SPACING_SM)

        section_title = QLabel("Assignments")
        section_title.setStyleSheet("font-weight: 700;")
        layout.addWidget(section_title)

        self.assignment_title_label = QLabel("Select a task to view assignments.")
        self.assignment_title_label.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.assignment_title_label.setWordWrap(True)
        layout.addWidget(self.assignment_title_label)

        self.assignment_summary_label = QLabel("")
        self.assignment_summary_label.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        self.assignment_summary_label.setWordWrap(True)
        layout.addWidget(self.assignment_summary_label)

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
        layout.addLayout(button_row)

        self.assignment_table.selectionModel().selectionChanged.connect(
            self._on_assignment_selection_changed
        )
        self.btn_assignment_add.clicked.connect(self.add_assignment_inline)
        self.btn_assignment_remove.clicked.connect(self.remove_assignment_inline)
        self.btn_assignment_set_alloc.clicked.connect(self.set_assignment_allocation_inline)
        self.btn_assignment_log_hours.clicked.connect(self.log_assignment_hours_inline)
        return box

    def _build_dependency_section(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(CFG.SPACING_SM)

        section_title = QLabel("Dependencies")
        section_title.setStyleSheet("font-weight: 700;")
        layout.addWidget(section_title)

        self.dependency_title_label = QLabel("Select a task to view dependencies.")
        self.dependency_title_label.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.dependency_title_label.setWordWrap(True)
        layout.addWidget(self.dependency_title_label)

        self.dependency_summary_label = QLabel("")
        self.dependency_summary_label.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        self.dependency_summary_label.setWordWrap(True)
        layout.addWidget(self.dependency_summary_label)

        self.dependency_table = QTableWidget(0, 5)
        self.dependency_table.setHorizontalHeaderLabels(
            ["Direction", "Linked Task", "Type", "Lag (d)", "Relationship"]
        )
        self.dependency_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.dependency_table.setSelectionMode(QTableWidget.SingleSelection)
        self.dependency_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.dependency_table.setWordWrap(False)
        self.dependency_table.setMinimumHeight(150)
        style_table(self.dependency_table)
        self._configure_dependency_table_columns()
        layout.addWidget(self.dependency_table)

        button_row = QHBoxLayout()
        self.btn_dependency_add = QPushButton("Add")
        self.btn_dependency_remove = QPushButton("Remove")
        for btn in (self.btn_dependency_add, self.btn_dependency_remove):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
        button_row.addWidget(self.btn_dependency_add)
        button_row.addWidget(self.btn_dependency_remove)
        button_row.addStretch()
        layout.addLayout(button_row)

        self.dependency_table.itemSelectionChanged.connect(self._on_dependency_selection_changed)
        self.btn_dependency_add.clicked.connect(self.add_dependency_inline)
        self.btn_dependency_remove.clicked.connect(self.remove_dependency_inline)
        return box

    def _on_task_selection_changed(self, *_args) -> None:
        self._reload_assignment_panel_for_selected_task()

    def _on_assignment_selection_changed(self, *_args) -> None:
        self._set_assignment_panel_actions_state(
            task_selected=self._get_selected_task() is not None,
            assignment_selected=self._get_selected_assignment() is not None,
            dependency_selected=self._get_selected_dependency_id() is not None,
        )

    def _on_dependency_selection_changed(self, *_args) -> None:
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
            self.assignment_summary_label.setText("")

            self.dependency_table.setRowCount(0)
            self.dependency_title_label.setText("Select a task to view dependencies.")
            self.dependency_summary_label.setText("")
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
        self.assignment_title_label.setText(f"Task: {task.name}")
        self.assignment_summary_label.setText(
            f"{len(rows)} assigned | Total allocation: {total_alloc:.1f}% | "
            f"Hours logged: {total_hours:.2f}"
        )

        self._reload_dependency_panel_for_selected_task(task)
        self._set_assignment_panel_actions_state(
            task_selected=True,
            assignment_selected=self._get_selected_assignment() is not None,
            dependency_selected=self._get_selected_dependency_id() is not None,
        )

    def _reload_dependency_panel_for_selected_task(self, task: Task) -> None:
        deps = self._task_service.list_dependencies_for_task(task.id)
        tasks_by_id = {t.id: t for t in self._task_service.list_tasks_for_project(task.project_id)}
        rows: list[tuple[str, str, str, int, str, str]] = []

        for dep in deps:
            direction, linked_id = _dependency_direction(task.id, dep)
            if not direction:
                continue
            linked_task = tasks_by_id.get(linked_id)
            linked_name = linked_task.name if linked_task else linked_id

            pred = tasks_by_id.get(dep.predecessor_task_id)
            succ = tasks_by_id.get(dep.successor_task_id)
            pred_name = pred.name if pred else dep.predecessor_task_id
            succ_name = succ.name if succ else dep.successor_task_id
            rows.append(
                (
                    direction,
                    linked_name,
                    dep.dependency_type.value,
                    dep.lag_days,
                    f"{pred_name} -> {succ_name}",
                    dep.id,
                )
            )

        rows.sort(key=lambda r: (r[0] != "Predecessor", r[1].lower()))
        self.dependency_table.setRowCount(len(rows))
        pred_count = 0
        for r, (direction, linked, dep_type, lag, relation, dep_id) in enumerate(rows):
            if direction == "Predecessor":
                pred_count += 1
            for c, value in enumerate((direction, linked, dep_type, str(lag), relation)):
                item = QTableWidgetItem(value)
                if c == 3:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.dependency_table.setItem(r, c, item)
            self.dependency_table.item(r, 0).setData(Qt.UserRole, dep_id)

        succ_count = len(rows) - pred_count
        self.dependency_title_label.setText(f"Task: {task.name}")
        self.dependency_summary_label.setText(
            f"Dependencies: {len(rows)} | Predecessors: {pred_count} | Successors: {succ_count}"
        )
        self.dependency_table.clearSelection()

    def _set_assignment_panel_actions_state(
        self,
        task_selected: bool,
        assignment_selected: bool,
        dependency_selected: bool = False,
    ) -> None:
        self.btn_assignment_add.setEnabled(task_selected)
        self.btn_assignment_remove.setEnabled(task_selected and assignment_selected)
        self.btn_assignment_set_alloc.setEnabled(task_selected and assignment_selected)
        self.btn_assignment_log_hours.setEnabled(task_selected and assignment_selected)
        self.btn_dependency_add.setEnabled(task_selected)
        self.btn_dependency_remove.setEnabled(task_selected and dependency_selected)

    def _get_selected_assignment(self) -> TaskAssignment | None:
        indexes = self.assignment_table.selectionModel().selectedRows()
        if not indexes:
            return None
        return self.assignment_model.get_assignment(indexes[0].row())

    def _get_selected_dependency_id(self) -> str | None:
        row = self.dependency_table.currentRow()
        if row < 0:
            return None
        item = self.dependency_table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def add_dependency_inline(self) -> None:
        task = self._get_selected_task()
        if not task:
            QMessageBox.information(self, "Dependencies", "Please select a task.")
            return
        project_tasks = self._task_service.list_tasks_for_project(task.project_id)
        dlg = DependencyAddDialog(
            self,
            tasks=project_tasks,
            current_task=task,
            task_service=self._task_service,
        )
        if dlg.exec() != QDialog.Accepted:
            return
        try:
            self._task_service.add_dependency(
                predecessor_id=dlg.predecessor_id,
                successor_id=dlg.successor_id,
                dependency_type=dlg.dependency_type,
                lag_days=dlg.lag_days,
            )
        except (ValidationError, BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Dependency", str(exc))
            return
        self.reload_tasks()
        self._select_task_by_id(task.id)

    def remove_dependency_inline(self) -> None:
        task = self._get_selected_task()
        if not task:
            QMessageBox.information(self, "Dependencies", "Please select a task.")
            return
        dep_id = self._get_selected_dependency_id()
        if not dep_id:
            QMessageBox.information(self, "Dependencies", "Please select a dependency.")
            return
        if QMessageBox.question(self, "Remove dependency", "Remove selected dependency?") != QMessageBox.Yes:
            return
        try:
            self._task_service.remove_dependency(dep_id)
        except (ValidationError, BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Dependency", str(exc))
            return
        self.reload_tasks()
        self._select_task_by_id(task.id)
