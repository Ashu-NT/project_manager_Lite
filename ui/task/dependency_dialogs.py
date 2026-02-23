from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from core.exceptions import BusinessRuleError, ValidationError
from core.models import DependencyType, Task
from core.services.task import TaskService
from ui.styles.ui_config import UIConfig as CFG


class DependencyAddDialog(QDialog):
    def __init__(
        self,
        parent=None,
        tasks: list[Task] | None = None,
        current_task: Task | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Add dependency")
        self._tasks: list[Task] = tasks or []
        self._current_task: Task | None = current_task

        self.pred_combo = QComboBox()
        self.succ_combo = QComboBox()
        for combo in (self.pred_combo, self.succ_combo):
            combo.setSizePolicy(CFG.INPUT_POLICY)
            combo.setFixedHeight(CFG.INPUT_HEIGHT)

        for t in self._tasks:
            self.pred_combo.addItem(t.name, userData=t.id)
            self.succ_combo.addItem(t.name, userData=t.id)

        if current_task:
            for i in range(self.succ_combo.count()):
                if self.succ_combo.itemData(i) == current_task.id:
                    self.succ_combo.setCurrentIndex(i)
                    break

        self.type_combo = QComboBox()
        self._dep_types: list[DependencyType] = [
            DependencyType.FINISH_TO_START,
            DependencyType.START_TO_START,
            DependencyType.FINISH_TO_FINISH,
            DependencyType.START_TO_FINISH,
        ]
        for dep_type in self._dep_types:
            self.type_combo.addItem(dep_type.value, userData=dep_type)

        self.lag_spin = QSpinBox()
        self.lag_spin.setMinimum(CFG.LAG_MIN)
        self.lag_spin.setMaximum(CFG.LAG_MAX)
        self.lag_spin.setValue(CFG.MIN_VALUE)

        form = QFormLayout()
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.DontWrapRows)
        form.addRow("Predecessor:", self.pred_combo)
        form.addRow("Successor:", self.succ_combo)
        form.addRow("Type:", self.type_combo)
        form.addRow("Lag (days):", self.lag_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.setCenterButtons(False)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_LG)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setMinimumSize(self.sizeHint())

    @property
    def predecessor_id(self) -> str:
        idx = self.pred_combo.currentIndex()
        return self.pred_combo.itemData(idx)

    @property
    def successor_id(self) -> str:
        idx = self.succ_combo.currentIndex()
        return self.succ_combo.itemData(idx)

    @property
    def dependency_type(self) -> DependencyType:
        idx = self.type_combo.currentIndex()
        return self._dep_types[idx]

    @property
    def lag_days(self) -> int:
        return self.lag_spin.value()


class DependencyListDialog(QDialog):
    def __init__(self, parent, task_service: TaskService, project_tasks: list[Task], current_task: Task):
        super().__init__(parent)
        self.setWindowTitle(f"Dependencies for: {current_task.name}")
        self._task_service: TaskService = task_service
        self._tasks: dict[str, Task] = {t.id: t for t in project_tasks}
        self._task: Task = current_task

        self.list_widget = QListWidget()

        self.btn_add = QPushButton(CFG.ADD_BUTTON_LABEL)
        self.btn_remove = QPushButton(CFG.REMOVE_SELECTED_LABEL)
        button = QDialogButtonBox(QDialogButtonBox.Close)
        button.rejected.connect(self.reject)

        for btn in (self.btn_add, self.btn_remove, button):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)

        layout = QVBoxLayout(self)
        layout.addSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )
        self.setMinimumSize(self.sizeHint())
        self.setMinimumWidth(CFG.MIN_DEPENDENCIES_WIDTH)
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_remove)
        btn_row.addStretch()
        btn_row.addWidget(button)
        layout.addLayout(btn_row)

        self.btn_add.clicked.connect(self.add_dependency)
        self.btn_remove.clicked.connect(self.remove_selected)

        self.reload_dependencies()

    def reload_dependencies(self):
        self.list_widget.clear()
        deps = self._task_service.list_dependencies_for_task(self._task.id)
        for dep in deps:
            pred = self._tasks.get(dep.predecessor_task_id)
            succ = self._tasks.get(dep.successor_task_id)
            pred_name = pred.name if pred else dep.predecessor_task_id
            succ_name = succ.name if succ else dep.successor_task_id
            txt = f"{pred_name} -> {succ_name} ({dep.dependency_type.value}, lag={dep.lag_days})"
            self.list_widget.addItem(txt)
            self.list_widget.item(self.list_widget.count() - 1).setData(Qt.UserRole, dep.id)

    def add_dependency(self):
        dlg = DependencyAddDialog(self, tasks=list(self._tasks.values()), current_task=self._task)
        if dlg.exec() == QDialog.Accepted:
            try:
                self._task_service.add_dependency(
                    predecessor_id=dlg.predecessor_id,
                    successor_id=dlg.successor_id,
                    dependency_type=dlg.dependency_type,
                    lag_days=dlg.lag_days,
                )
            except (ValidationError, BusinessRuleError) as exc:
                QMessageBox.warning(self, "Error", str(exc))
                return
            self.reload_dependencies()

    def remove_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        dep_id = item.data(Qt.UserRole)
        if not dep_id:
            return
        confirm = QMessageBox.question(
            self,
            "Remove dependency",
            "Remove selected dependency?",
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self._task_service.remove_dependency(dep_id)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Error", str(exc))
            return
        self.reload_dependencies()


__all__ = ["DependencyAddDialog", "DependencyListDialog"]
