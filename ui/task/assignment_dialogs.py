from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.models import Task
from core.services.project import ProjectResourceService
from core.services.resource import ResourceService
from core.services.task import TaskService
from ui.styles.formatting import fmt_percent
from ui.styles.ui_config import UIConfig as CFG


class AssignmentAddDialog(QDialog):
    def __init__(self, parent=None, project_resources=None, resources_by_id=None):
        super().__init__(parent)
        self.setWindowTitle("Assign resource")
        self._project_resources = project_resources or []
        self._resources_by_id = resources_by_id or {}

        self.resource_combo = QComboBox()
        self.resource_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.resource_combo.setFixedHeight(CFG.INPUT_HEIGHT)

        for project_resource in self._project_resources:
            resource = self._resources_by_id.get(project_resource.resource_id)
            if not resource:
                continue
            if not getattr(project_resource, "is_active", True):
                continue
            if not getattr(resource, "is_active", True):
                continue

            rate = (
                project_resource.hourly_rate
                if project_resource.hourly_rate is not None
                else getattr(resource, "hourly_rate", None)
            )
            cur = (project_resource.currency_code or getattr(resource, "currency_code", "") or "").upper()

            label = resource.name
            if rate is not None:
                label += f" ({rate:.2f} {cur}/hr)"

            self.resource_combo.addItem(label, userData=project_resource.id)

        self.alloc_spin = QDoubleSpinBox()
        self.alloc_spin.setSizePolicy(CFG.INPUT_POLICY)
        self.alloc_spin.setMinimum(CFG.MONEY_MIN)
        self.alloc_spin.setMaximum(CFG.PERCENTAGE_MAX)
        self.alloc_spin.setDecimals(CFG.PERCENT_DECIMALS)
        self.alloc_spin.setValue(CFG.ALLOC_SET_VALUE)

        form = QFormLayout()
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.DontWrapRows)
        form.addRow("Project resource", self.resource_combo)
        form.addRow("Allocation (%)", self.alloc_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    @property
    def project_resource_id(self) -> str:
        return self.resource_combo.currentData()

    @property
    def allocation_percent(self) -> float:
        return self.alloc_spin.value()


class AssignmentListDialog(QDialog):
    def __init__(
        self,
        parent,
        task_service: TaskService,
        resource_service: ResourceService,
        project_resource_service: ProjectResourceService,
        task: Task,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Assignments for: {task.name}")
        self._task_service = task_service
        self._resource_service = resource_service
        self._task = task
        self._project_resource_service = project_resource_service

        self.list_widget = QListWidget()
        self.btn_add = QPushButton(CFG.ADD_BUTTON_LABEL)
        self.btn_remove = QPushButton(CFG.REMOVE_SELECTED_LABEL)
        self.btn_edit_hours = QPushButton(CFG.EDIT_HOURS_LABEL)

        button = QDialogButtonBox(QDialogButtonBox.Close)
        button.rejected.connect(self.reject)

        for btn in (self.btn_add, self.btn_remove, self.btn_edit_hours, button):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)

        layout = QVBoxLayout(self)
        layout.addWidget(self.list_widget)
        layout.addSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )
        self.setMinimumSize(self.sizeHint())
        self.setMinimumWidth(CFG.MIN_ASSIGNMENTS_WIDTH)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_edit_hours)
        btn_row.addWidget(self.btn_remove)
        btn_row.addStretch()
        btn_row.addWidget(button)
        layout.addLayout(btn_row)

        self.btn_add.clicked.connect(self.add_assignment)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_edit_hours.clicked.connect(self.edit_selected_hours)

        self.reload_assignments()

    def reload_assignments(self):
        self.list_widget.clear()

        assignments = self._task_service.list_assignments_for_task(self._task.id)
        resources = {r.id: r for r in self._resource_service.list_resources()}

        for assignment in assignments:
            pr_id = getattr(assignment, "project_resource_id", None)

            rname = assignment.resource_id
            if pr_id:
                pr = self._project_resource_service.get(pr_id)
                if pr:
                    res = resources.get(pr.resource_id)
                    rname = res.name if res else pr.resource_id
            else:
                res = resources.get(assignment.resource_id)
                rname = res.name if res else assignment.resource_id

            hours = float(getattr(assignment, "hours_logged", 0.0))
            txt = f"{rname} ({fmt_percent(assignment.allocation_percent)}, {hours:.1f}h logged)"
            self.list_widget.addItem(txt)
            self.list_widget.item(self.list_widget.count() - 1).setData(Qt.UserRole, assignment.id)

    def add_assignment(self):
        prs = self._project_resource_service.list_by_project(self._task.project_id)
        if not prs:
            QMessageBox.information(
                self,
                "Assignments",
                "No project resources found.\n\nAdd resources in Project -> Project Resources first.",
            )
            return

        resources = self._resource_service.list_resources()
        resources_by_id = {r.id: r for r in resources}

        dlg = AssignmentAddDialog(self, project_resources=prs, resources_by_id=resources_by_id)
        if dlg.exec() == QDialog.Accepted:
            pr_id = dlg.project_resource_id
            if not pr_id:
                QMessageBox.warning(self, "Assignments", "Please select a project resource.")
                return

            try:
                self._task_service.assign_project_resource(
                    task_id=self._task.id,
                    project_resource_id=pr_id,
                    allocation_percent=dlg.allocation_percent,
                )
            except (ValidationError, BusinessRuleError, NotFoundError) as exc:
                QMessageBox.warning(self, "Error", str(exc))
                return

            self.reload_assignments()

    def remove_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        assign_id = item.data(Qt.UserRole)
        if not assign_id:
            return
        confirm = QMessageBox.question(
            self,
            "Remove assignment",
            "Remove selected assignment?",
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self._task_service.unassign_resource(assign_id)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Error", str(exc))
            return
        self.reload_assignments()

    def edit_selected_hours(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.information(self, "Edit hours", "Please select an assignment.")
            return

        assignment_id = item.data(Qt.UserRole)
        if not assignment_id:
            QMessageBox.warning(self, "Edit hours", "Failed to locate assignment.")
            return

        assignment = self._task_service.get_assignment(assignment_id)
        if not assignment:
            QMessageBox.warning(self, "Edit hours", "Failed to locate assignment.")
            return

        current = getattr(assignment, "hours_logged", 0.0)
        value, ok = QInputDialog.getDouble(
            self,
            "Edit hours",
            "Hours logged:",
            current,
            0.0,
            1000000.0,
            2,
        )
        if not ok:
            return
        try:
            self._task_service.set_assignment_hours(assignment_id, value)
        except Exception as exc:
            QMessageBox.warning(self, "Error", str(exc))
            return
        self.reload_assignments()


__all__ = ["AssignmentAddDialog", "AssignmentListDialog"]
