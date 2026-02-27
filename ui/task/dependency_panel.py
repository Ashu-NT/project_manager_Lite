from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.models import Task
from core.services.task import TaskService
from ui.shared.guards import apply_permission_hint, make_guarded_slot
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG
from ui.task.dependency_add_dialog import DependencyAddDialog
from ui.task.dependency_shared import dependency_direction as _dependency_direction


class TaskDependencyPanelMixin:
    dependency_table: QTableWidget
    dependency_title_label: QLabel
    dependency_summary_label: QLabel
    btn_dependency_add: QPushButton
    btn_dependency_remove: QPushButton

    _task_service: TaskService

    def _configure_dependency_table_columns(self) -> None:
        header = self.dependency_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)

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
        self.btn_dependency_add.clicked.connect(
            make_guarded_slot(self, title="Dependency", callback=self.add_dependency_inline)
        )
        self.btn_dependency_remove.clicked.connect(
            make_guarded_slot(self, title="Dependency", callback=self.remove_dependency_inline)
        )
        can_add_dep = bool(getattr(self, "_can_add_dependencies", True))
        can_remove_dep = bool(getattr(self, "_can_remove_dependencies", can_add_dep))
        apply_permission_hint(
            self.btn_dependency_add,
            allowed=can_add_dep,
            missing_permission="task.manage or approval.request",
        )
        apply_permission_hint(
            self.btn_dependency_remove,
            allowed=can_remove_dep,
            missing_permission="task.manage or approval.request",
        )
        return box

    def _on_dependency_selection_changed(self, *_args) -> None:
        self._set_assignment_panel_actions_state(
            task_selected=self._get_selected_task() is not None,
            assignment_selected=self._get_selected_assignment() is not None,
            dependency_selected=self._get_selected_dependency_id() is not None,
        )

    def _clear_dependency_panel_for_no_task(self) -> None:
        self.dependency_table.setRowCount(0)
        self.dependency_title_label.setText("Select a task to view dependencies.")
        self.dependency_summary_label.setText("")

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


__all__ = ["TaskDependencyPanelMixin"]
