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
)

from core.exceptions import BusinessRuleError, ValidationError
from core.models import Task
from core.services.task import TaskService
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG
from ui.task.dependency_add_dialog import DependencyAddDialog
from ui.task.dependency_shared import dependency_direction as _dependency_direction


class DependencyListDialog(QDialog):
    def __init__(self, parent, task_service: TaskService, project_tasks: list[Task], current_task: Task):
        super().__init__(parent)
        self.setWindowTitle(f"Task Dependencies - {current_task.name}")
        self._task_service = task_service
        self._tasks = {task.id: task for task in project_tasks}
        self._task = current_task

        self.lbl_summary = QLabel("")
        self.lbl_summary.setStyleSheet(CFG.NOTE_STYLE_SHEET)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Direction", "Linked Task", "Type", "Lag (d)", "Relationship"]
        )
        style_table(self.table)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)

        self.btn_add = QPushButton(CFG.ADD_BUTTON_LABEL)
        self.btn_remove = QPushButton(CFG.REMOVE_SELECTED_LABEL)
        self.btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        for btn in (self.btn_add, self.btn_remove, self.btn_close):
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)

        row = QHBoxLayout()
        row.addWidget(self.btn_add)
        row.addWidget(self.btn_remove)
        row.addStretch()
        row.addWidget(self.btn_close)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_SM)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.addWidget(self.lbl_summary)
        layout.addWidget(self.table, 1)
        layout.addLayout(row)

        self.setMinimumSize(860, 420)

        self.btn_add.clicked.connect(self.add_dependency)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_close.clicked.connect(self.reject)
        self.table.itemSelectionChanged.connect(self._sync_actions)
        self.reload_dependencies()

    def reload_dependencies(self) -> None:
        deps = self._task_service.list_dependencies_for_task(self._task.id)
        rows: list[tuple[str, str, str, int, str, str]] = []
        for dep in deps:
            direction, linked_id = _dependency_direction(self._task.id, dep)
            if not direction:
                continue
            linked = self._tasks.get(linked_id).name if self._tasks.get(linked_id) else linked_id
            pred = self._tasks.get(dep.predecessor_task_id)
            succ = self._tasks.get(dep.successor_task_id)
            pred_name = pred.name if pred else dep.predecessor_task_id
            succ_name = succ.name if succ else dep.successor_task_id
            rows.append(
                (direction, linked, dep.dependency_type.value, dep.lag_days, f"{pred_name} -> {succ_name}", dep.id)
            )

        rows.sort(key=lambda r: (r[0] != "Predecessor", r[1].lower()))
        self.table.setRowCount(len(rows))
        pred_count = 0
        for r, (direction, linked, dep_type, lag, relation, dep_id) in enumerate(rows):
            pred_count += 1 if direction == "Predecessor" else 0
            for c, value in enumerate((direction, linked, dep_type, str(lag), relation)):
                item = QTableWidgetItem(value)
                if c == 3:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(r, c, item)
            self.table.item(r, 0).setData(Qt.UserRole, dep_id)

        succ_count = len(rows) - pred_count
        self.lbl_summary.setText(
            f"Dependencies: {len(rows)} | Predecessors: {pred_count} | Successors: {succ_count}"
        )
        self._sync_actions()

    def add_dependency(self) -> None:
        dlg = DependencyAddDialog(
            self,
            tasks=list(self._tasks.values()),
            current_task=self._task,
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
        except (ValidationError, BusinessRuleError) as exc:
            QMessageBox.warning(self, "Dependency", str(exc))
            return
        self.reload_dependencies()

    def remove_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        dep_id = self.table.item(row, 0).data(Qt.UserRole)
        if not dep_id:
            return
        if QMessageBox.question(self, "Remove dependency", "Remove selected dependency?") != QMessageBox.Yes:
            return
        try:
            self._task_service.remove_dependency(dep_id)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Dependency", str(exc))
            return
        self.reload_dependencies()

    def _sync_actions(self) -> None:
        self.btn_remove.setEnabled(self.table.currentRow() >= 0)


__all__ = ["DependencyListDialog", "_dependency_direction"]
