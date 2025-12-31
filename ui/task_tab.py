# ui/task_tab.py
from __future__ import annotations
from datetime import date
from typing import Optional

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTableView, QDialog, QFormLayout, QLineEdit, QTextEdit, QDateEdit,
    QSpinBox, QDoubleSpinBox, QDialogButtonBox, QCheckBox, QMessageBox,
    QInputDialog
)
from PySide6.QtCore import QDate

from core.services.project_service import ProjectService
from core.services.project_resource_service import ProjectResourceService
from core.services.task_service import TaskService
from core.services.resource_service import ResourceService
from core.exceptions import ValidationError, BusinessRuleError, NotFoundError
from core.models import Task, TaskStatus, DependencyType
from ui.styles.style_utils import style_table
from ui.styles.formatting import fmt_percent
from ui.styles.ui_config import UIConfig as CFG

# ---------------- Task table model ---------------- #

class TaskTableModel(QAbstractTableModel):
    HEADERS = ["Name", "Status", "Start", "End", "Duration", "%", "Deadline", "Priority", "Actual Start","Actual End"]

    def __init__(self, tasks: list[Task] | None = None, parent=None):
        super().__init__(parent)
        self._tasks: list[Task] = tasks or []

    def set_tasks(self, tasks: list[Task]):
        self.beginResetModel()
        self._tasks = tasks or []
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._tasks)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        t = self._tasks[index.row()]
        col = index.column()

        if col == 0:
            return t.name
        elif col == 1:
            return getattr(t.status, "value", str(t.status))
        elif col == 2:
            return t.start_date.isoformat() if t.start_date else ""
        elif col == 3:
            return t.end_date.isoformat() if t.end_date else ""
        elif col == 4:
            return t.duration_days if t.duration_days is not None else ""
        elif col == 5:
            return f"{(t.percent_complete or 0.0):.0f}"
        elif col == 6:
            return t.deadline.isoformat() if getattr(t, "deadline", None) else ""
        elif col == 7:
            return t.priority if t.priority is not None else ""
        elif col == 8:
            return t.actual_start.isoformat() if getattr(t, "actual_start", None) else ""
        elif col == 9:
            return t.actual_end.isoformat() if getattr(t, "actual_end", None) else ""
        return None

    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return super().headerData(section, orientation, role)

    def get_task(self, row: int) -> Optional[Task]:
        if 0 <= row < len(self._tasks):
            return self._tasks[row]
        return None

# ---------------- Task edit dialog ---------------- #

class TaskEditDialog(QDialog):
    def __init__(self, parent=None, task: Task | None = None):
        super().__init__(parent)
        self.setWindowTitle("Task" + (" - Edit" if task else " - New"))
        self._task = task

        self.name_edit = QLineEdit()
        self.name_edit.setSizePolicy(CFG.INPUT_POLICY)
        self.name_edit.setFixedHeight(CFG.INPUT_HEIGHT)
        self.name_edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)
        
        self.desc_edit = QTextEdit()
        self.desc_edit.setSizePolicy(CFG.TEXTEDIT_POLICY)
        self.desc_edit.setMinimumHeight(CFG.TEXTEDIT_MIN_HEIGHT)
        
        # Status combo
        self.status_combo = QComboBox()
        self.status_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.status_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        
        self._status_values: list[TaskStatus] = [
            TaskStatus.TODO,
            TaskStatus.IN_PROGRESS,
            TaskStatus.DONE,
            TaskStatus.BLOCKED,
        ]
        for s in self._status_values:
            self.status_combo.addItem(s.value, userData=s)

        # Start date & deadline
        self.start_date_edit = QDateEdit()
        self.deadline_edit = QDateEdit()
        for date_edit in (self.start_date_edit, self.deadline_edit):
            date_edit.setSizePolicy(CFG.INPUT_POLICY)
            date_edit.setFixedHeight(CFG.INPUT_HEIGHT)
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat(CFG.DATE_FORMAT)

        # Duration & priority
        self.duration_spin = QSpinBox()
        self.duration_spin.setSizePolicy(CFG.INPUT_POLICY)
        self.duration_spin.setFixedHeight(CFG.INPUT_HEIGHT)
        self.duration_spin.setMinimum(CFG.MIN_VALUE)
        self.duration_spin.setMaximum(CFG.DURATION_MAX)

        self.priority_spin = QSpinBox()
        self.priority_spin.setSizePolicy(CFG.INPUT_POLICY)
        self.priority_spin.setFixedHeight(CFG.INPUT_HEIGHT)
        self.priority_spin.setMinimum(CFG.MIN_VALUE)
        self.priority_spin.setMaximum(CFG.PRIORITY_MAX)

        if task:
            self.name_edit.setText(task.name)
            self.desc_edit.setPlainText(task.description or "")
            # status
            for i, s in enumerate(self._status_values):
                if s == task.status:
                    self.status_combo.setCurrentIndex(i)
                    break
            if task.start_date:
                self.start_date_edit.setDate(QDate(task.start_date.year, task.start_date.month, task.start_date.day))
            if getattr(task, "deadline", None):
                d = task.deadline
                self.deadline_edit.setDate(QDate(d.year, d.month, d.day))
            if task.duration_days is not None:
                self.duration_spin.setValue(task.duration_days)
            if task.priority is not None:
                self.priority_spin.setValue(task.priority)
        else:
            today = QDate.currentDate()
            self.start_date_edit.setDate(today)
            self.deadline_edit.setDate(today)
            self.status_combo.setCurrentIndex(0)

        form = QFormLayout()
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.DontWrapRows)
        
        form.addRow("Name:", self.name_edit)
        form.addRow("Description:", self.desc_edit)
        form.addRow("Status:", self.status_combo)
        form.addRow("Start date:", self.start_date_edit)
        form.addRow("Duration (working days):", self.duration_spin)
        form.addRow("Deadline:", self.deadline_edit)
        form.addRow("Priority:", self.priority_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.setCenterButtons(False)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_LG)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )
        
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setMinimumSize(self.sizeHint())

    @property
    def name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def description(self) -> str:
        return self.desc_edit.toPlainText().strip()

    @property
    def status(self) -> TaskStatus:
        idx = self.status_combo.currentIndex()
        if 0 <= idx < len(self._status_values):
            return self._status_values[idx]
        return TaskStatus.TODO

    @property
    def start_date(self) -> date | None:
        qd = self.start_date_edit.date()
        if not qd.isValid():
            return None
        return date(qd.year(), qd.month(), qd.day())

    @property
    def duration_days(self) -> int | None:
        val = self.duration_spin.value()
        return val if val > 0 else None

    @property
    def deadline(self) -> date | None:
        qd = self.deadline_edit.date()
        if not qd.isValid():
            return None
        return date(qd.year(), qd.month(), qd.day())

    @property
    def priority(self) -> int | None:
        val = self.priority_spin.value()
        return val if val > 0 else None

# ---------------- Progress dialog ---------------- #

class TaskProgressDialog(QDialog):
    def __init__(self, parent=None, task: Task | None = None):
        super().__init__(parent)
        self.setWindowTitle("Update progress")
        self._task = task

        # Percent widget with an enable checkbox
        self.percent_check = QCheckBox()
        self.percent_check.setToolTip("Enable to update percent complete")

        self.percent_spin = QDoubleSpinBox()
        self.percent_spin.setSizePolicy(CFG.INPUT_POLICY)
        self.percent_spin.setFixedHeight(CFG.INPUT_HEIGHT)
        self.percent_spin.setMinimum(CFG.MONEY_MIN)
        self.percent_spin.setMaximum(CFG.PERCENTAGE_MAX)
        self.percent_spin.setDecimals(CFG.PERCENT_DECIMALS)
        self.percent_spin.setSingleStep(CFG.PERCENTAGE_STEP)
        self.percent_spin.setAlignment(CFG.ALIGN_RIGHT)

        # Actual start / end with enable checkboxes
        self.actual_start_check = QCheckBox()
        self.actual_start_check.setToolTip("Enable to update actual start date")
        self.actual_end_check = QCheckBox()
        self.actual_end_check.setToolTip("Enable to update actual end date")

        self.actual_start_edit = QDateEdit()
        self.actual_end_edit = QDateEdit()
        today = QDate.currentDate()
        for date_edit in (self.actual_start_edit, self.actual_end_edit):
            date_edit.setSizePolicy(CFG.INPUT_POLICY)
            date_edit.setFixedHeight(CFG.INPUT_HEIGHT)
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat(CFG.DATE_FORMAT)
            date_edit.setDate(today)

        for chkbox in (self.percent_check, self.actual_start_check, self.actual_end_check):
            chkbox.setSizePolicy(CFG.CHECKBOX_POLICY)
            chkbox.setFixedHeight(CFG.CHECKBOX_HEIGHT)
        
        # Initialize values & enabled state
        # default: percent enabled (users commonly update percent), dates enabled only when existing
        self.percent_check.setChecked(True)
        if task:
            if task.percent_complete is not None:
                self.percent_spin.setValue(task.percent_complete)
            if task.actual_start:
                self.actual_start_edit.setDate(QDate(task.actual_start.year, task.actual_start.month, task.actual_start.day))
                self.actual_start_check.setChecked(False)
            else:
                self.actual_start_check.setChecked(False)
            if task.actual_end:
                self.actual_end_edit.setDate(QDate(task.actual_end.year, task.actual_end.month, task.actual_end.day))
                self.actual_end_check.setChecked(False)
            else:
                self.actual_end_check.setChecked(False)
        else:
            self.actual_start_check.setChecked(False)
            self.actual_end_check.setChecked(False)

        # Connect toggles to enable/disable corresponding inputs
        self.percent_check.toggled.connect(self.percent_spin.setEnabled)
        self.actual_start_check.toggled.connect(self.actual_start_edit.setEnabled)
        self.actual_end_check.toggled.connect(self.actual_end_edit.setEnabled)

        # Apply initial enabled state
        self.percent_spin.setEnabled(self.percent_check.isChecked())
        self.actual_start_edit.setEnabled(self.actual_start_check.isChecked())
        self.actual_end_edit.setEnabled(self.actual_end_check.isChecked())

        form = QFormLayout()
        
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.DontWrapRows)

        # Add rows using small horizontal layouts so checkbox and input sit together
        h1 = QHBoxLayout()
        h1.setSpacing(CFG.SPACING_SM)
        h1.addWidget(self.percent_spin)
        h1.addWidget(self.percent_check)
        
        form.addRow("Percent complete:", h1)

        h2 = QHBoxLayout()
        h2.setSpacing(CFG.SPACING_SM)
        h2.addWidget(self.actual_start_edit)
        h2.addWidget(self.actual_start_check)
        
        form.addRow("Actual start:", h2)

        h3 = QHBoxLayout()
        h3.setSpacing(CFG.SPACING_SM)
        h3.addWidget(self.actual_end_edit)
        h3.addWidget(self.actual_end_check)
        
        
        form.addRow("Actual end:", h3)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.setCenterButtons(False)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_LG)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )
        layout.addLayout(form)
        layout.addWidget(buttons)
        
        self.setMinimumSize(self.sizeHint())

    @property
    def percent_set(self) -> bool:
        return bool(self.percent_check.isChecked())

    @property
    def actual_start_set(self) -> bool:
        return bool(self.actual_start_check.isChecked())

    @property
    def actual_end_set(self) -> bool:
        return bool(self.actual_end_check.isChecked())

    @property
    def percent_complete(self) -> float | None:
        if not self.percent_set:
            return None
        return self.percent_spin.value()

    @property
    def actual_start(self) -> date | None:
        if not self.actual_start_set:
            return None
        qd = self.actual_start_edit.date()
        if not qd.isValid():
            return None
        return date(qd.year(), qd.month(), qd.day())

    @property
    def actual_end(self) -> date | None:
        if not self.actual_end_set:
            return None
        qd = self.actual_end_edit.date()
        if not qd.isValid():
            return None
        return date(qd.year(), qd.month(), qd.day())

# ---------------- Dependency dialogs ---------------- #

class DependencyAddDialog(QDialog):
    def __init__(self, parent=None, tasks: list[Task] | None = None, current_task: Task | None = None):
        super().__init__(parent)
        self.setWindowTitle("Add dependency")
        self._tasks = tasks or []
        self._current_task = current_task

        # predecessor and successor combos
        self.pred_combo = QComboBox()
        self.succ_combo = QComboBox()
        
        for combo in (self.pred_combo, self.succ_combo):
            combo.setSizePolicy(CFG.INPUT_POLICY)
            combo.setFixedHeight(CFG.INPUT_HEIGHT)

        # Fill task combos
        for t in self._tasks:
            self.pred_combo.addItem(t.name, userData=t.id)
            self.succ_combo.addItem(t.name, userData=t.id)

        # If current_task is provided, set it as successor by default
        if current_task:
            for i in range(self.succ_combo.count()):
                if self.succ_combo.itemData(i) == current_task.id:
                    self.succ_combo.setCurrentIndex(i)
                    break

        # dependency type
        self.type_combo = QComboBox()
        self._dep_types: list[DependencyType] = [
            DependencyType.FINISH_TO_START,
            DependencyType.START_TO_START,
            DependencyType.FINISH_TO_FINISH,
            DependencyType.START_TO_FINISH,
        ]
        for d in self._dep_types:
            self.type_combo.addItem(d.value, userData=d)

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
        layout.setContentsMargins(  
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )
        
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
    """
    Shows dependencies for a given task (as successor + predecessor roles).
    Lets the user add or remove dependencies.
    We assume TaskService has:
      - add_dependency(predecessor_id, successor_id, dep_type, lag_days)
      - remove_dependency(dep_id)
      - list_dependencies_for_task(task_id) -> list[TaskDependency]
    """
    def __init__(self, parent, task_service: TaskService, project_tasks: list[Task], current_task: Task):
        super().__init__(parent)
        self.setWindowTitle(f"Dependencies for: {current_task.name}")
        self._task_service = task_service
        self._tasks = {t.id: t for t in project_tasks}
        self._task = current_task

        self.list_widget = QTableView()  # or simpler: QListWidget
        # for simplicity, we’ll use a text list in a QTextEdit-like representation
        # but here we’ll just show in a list widget alternative

        from PySide6.QtWidgets import QListWidget
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
        from core.models import TaskDependency  # adjust import if needed
        self.list_widget.clear()
        deps = self._task_service.list_dependencies_for_task(self._task.id)
        # show as human-readable text
        for d in deps:
            pred = self._tasks.get(d.predecessor_task_id)
            succ = self._tasks.get(d.successor_task_id)
            pred_name = pred.name if pred else d.predecessor_task_id
            succ_name = succ.name if succ else d.successor_task_id
            txt = f"{pred_name} -> {succ_name} ({d.dependency_type.value}, lag={d.lag_days})"
            item = self.list_widget.addItem(txt)
            # store dep id in item data - if using QListWidgetItem:
            self.list_widget.item(self.list_widget.count() - 1).setData(Qt.UserRole, d.id)

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
            except (ValidationError, BusinessRuleError) as e:
                QMessageBox.warning(self, "Error", str(e))
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
        except BusinessRuleError as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        self.reload_dependencies()


# ---------------- Assignment dialogs ---------------- #
class AssignmentAddDialog(QDialog):
    """
    Assign a PROJECT resource (ProjectResource) to a task.
    Combo stores project_resource_id.
    """
    def __init__(self, parent=None, project_resources=None, resources_by_id=None):
        super().__init__(parent)
        self.setWindowTitle("Assign resource")
        self._project_resources = project_resources or []
        self._resources_by_id = resources_by_id or {}

        self.resource_combo = QComboBox()
        self.resource_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.resource_combo.setFixedHeight(CFG.INPUT_HEIGHT)

        # Populate combo with project resources
        for pr in self._project_resources:
            res = self._resources_by_id.get(pr.resource_id)
            if not res:
                continue

            # hide inactive project resources (and inactive master resources)
            if not getattr(pr, "is_active", True):
                continue
            if not getattr(res, "is_active", True):
                continue

            # resolved display: project override else resource default
            rate = pr.hourly_rate if pr.hourly_rate is not None else getattr(res, "hourly_rate", None)
            cur = (pr.currency_code or getattr(res, "currency_code", "") or "").upper()

            label = res.name
            if rate is not None:
                label += f" ({rate:.2f} {cur}/hr)"

            # IMPORTANT: store project_resource_id
            self.resource_combo.addItem(label, userData=pr.id)

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
    """
    Manage assignments for a task.
    We assume TaskService has:
      - list_assignments_for_task(task_id)
      - assign_resource(task_id, resource_id, allocation_percent)
      - unassign_resource(assignment_id)
    ResourceService must have list_resources().
    """
    def __init__(self, parent, 
                 task_service: TaskService, 
                 resource_service: ResourceService, 
                 project_resource_service: ProjectResourceService,
                 task: Task
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Assignments for: {task.name}")
        self._task_service = task_service
        self._resource_service = resource_service
        self._task = task
        self._project_resource_service = project_resource_service

        from PySide6.QtWidgets import QListWidget
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

        for a in assignments:
            # prefer project_resource_id when present
            pr_id = getattr(a, "project_resource_id", None)

            rname = a.resource_id
            if pr_id:
                pr = self._project_resource_service.get(pr_id)
                if pr:
                    res = resources.get(pr.resource_id)
                    rname = res.name if res else pr.resource_id
            else:
                res = resources.get(a.resource_id)
                rname = res.name if res else a.resource_id

            h = float(getattr(a, "hours_logged", 0.0))
            txt = f"{rname} ({fmt_percent(a.allocation_percent)}.{h:.1f}h logged)"
            self.list_widget.addItem(txt)
            self.list_widget.item(self.list_widget.count() - 1).setData(Qt.UserRole, a.id)

    def add_assignment(self):
        # list project resources for THIS task's project
        prs = self._project_resource_service.list_by_project(self._task.project_id)
        if not prs:
            QMessageBox.information(
                self,
                "Assignments",
                "No project resources found.\n\nAdd resources in Project → Project Resources first."
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
            except (ValidationError, BusinessRuleError, NotFoundError) as e:
                QMessageBox.warning(self, "Error", str(e))
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
        except BusinessRuleError as e:
            QMessageBox.warning(self, "Error", str(e))
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

        a = self._task_service.get_assignment(assignment_id)
        if not a:
            QMessageBox.warning(self, "Edit hours", "Failed to locate assignment.")
            return

        current = getattr(a, 'hours_logged', 0.0)
        val , ok = QInputDialog.getDouble(self, "Edit hours", "Hours logged:", current, 0.0, 1000000.0, 2)
        if not ok:
            return
        try:
            self._task_service.set_assignment_hours(assignment_id, val)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        self.reload_assignments()
           
    
# ---------------- TaskTab main widget ---------------- #

class TaskTab(QWidget):
    def __init__(
        self,
        project_service: ProjectService,
        task_service: TaskService,
        resource_service: ResourceService,
        project_resource_service: ProjectResourceService,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._project_service = project_service
        self._task_service = task_service
        self._resource_service = resource_service
        self._project_resource_service = project_resource_service

        self._setup_ui()
        self._load_projects()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )
        self.setMinimumSize(self.sizeHint())
        
        # Top: project selector
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
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_new = QPushButton(CFG.NEW_TASK_LABEL)
        self.btn_edit = QPushButton(CFG.EDIT_LABEL)
        self.btn_delete = QPushButton(CFG.DELETE_LABEL)
        self.btn_progress = QPushButton(CFG.UPDATE_PROGRESS_LABEL)
        self.btn_deps = QPushButton(CFG.DEPENDENCIES_LABEL)
        self.btn_assign = QPushButton(CFG.ASSIGNMENTS_LABEL)
        self.btn_refresh_tasks = QPushButton(CFG.REFRESH_TASKS_LABEL)
        
        for btn in [
            self.btn_reload_projects,
            self.btn_new,
            self.btn_edit,
            self.btn_delete,
            self.btn_progress,
            self.btn_deps,
            self.btn_assign,
            self.btn_refresh_tasks,
        ]:
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
        
        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(self.btn_progress)
        toolbar.addWidget(self.btn_deps)
        toolbar.addWidget(self.btn_assign)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh_tasks)
        layout.addLayout(toolbar)

        # Table of tasks
        self.table = QTableView()
        self.model = TaskTableModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        style_table(self.table)
        layout.addWidget(self.table)

        # Signals
        self.btn_reload_projects.clicked.connect(self._load_projects)
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        self.btn_refresh_tasks.clicked.connect(self.reload_tasks)
        self.btn_new.clicked.connect(self.create_task)
        self.btn_edit.clicked.connect(self.edit_task)
        self.btn_delete.clicked.connect(self.delete_task)
        self.btn_progress.clicked.connect(self.update_progress)
        self.btn_deps.clicked.connect(self.manage_dependencies)
        self.btn_assign.clicked.connect(self.manage_assignments)

    # ------------- Helpers ------------- #

    def _load_projects(self):
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        projects = self._project_service.list_projects()
        for p in projects:
            self.project_combo.addItem(p.name, userData=p.id)
        self.project_combo.blockSignals(False)
        if self.project_combo.count() > 0:
            self.project_combo.setCurrentIndex(0)
            self._on_project_changed(0)

    def _current_project_id(self) -> Optional[str]:
        idx = self.project_combo.currentIndex()
        if idx < 0:
            return None
        return self.project_combo.itemData(idx)

    def _on_project_changed(self, index: int):
        self.reload_tasks()

    def reload_tasks(self):
        pid = self._current_project_id()
        if not pid:
            self.model.set_tasks([])
            return
        tasks = self._task_service.list_tasks_for_project(pid)
        self.model.set_tasks(tasks)

    def _get_selected_task(self) -> Optional[Task]:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        return self.model.get_task(row)

    # ------------- Actions ------------- #

    def create_task(self):
        pid = self._current_project_id()
        if not pid:
            QMessageBox.information(self, "New task", "Please select a project.")
            return

        dlg = TaskEditDialog(self, task=None)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._task_service.create_task(
                    project_id=pid,
                    name=dlg.name,
                    description=dlg.description,
                    start_date=dlg.start_date,
                    duration_days=dlg.duration_days,
                    status=dlg.status,
                    priority=dlg.priority,
                    deadline=dlg.deadline,
                )
            except (ValidationError, BusinessRuleError, NotFoundError) as e:
                    QMessageBox.warning(self, "Error", str(e))
                    continue
            self.reload_tasks()
            return

    def edit_task(self):
        t = self._get_selected_task()
        if not t:
            QMessageBox.information(self, "Edit task", "Please select a task.")
            return

        dlg = TaskEditDialog(self, task=t)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._task_service.update_task(
                    task_id=t.id,
                    name=dlg.name,
                    description=dlg.description,
                    start_date=dlg.start_date,
                    duration_days=dlg.duration_days,
                    status=dlg.status,
                    priority=dlg.priority,
                    deadline=dlg.deadline,
                )
            except (ValidationError, BusinessRuleError, NotFoundError) as e:
                    QMessageBox.warning(self, "Error", str(e))
                    continue
            self.reload_tasks()
            return

    def delete_task(self):
        t = self._get_selected_task()
        if not t:
            QMessageBox.information(self, "Delete task", "Please select a task.")
            return
        confirm = QMessageBox.question(
            self,
            "Delete task",
            f"Delete task '{t.name}' (and its dependencies, assignments, etc.)?",
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self._task_service.delete_task(t.id)
        except BusinessRuleError as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        self.reload_tasks()

    def update_progress(self):
        t = self._get_selected_task()
        if not t:
            QMessageBox.information(self, "Update progress", "Please select a task.")
            return

        dlg = TaskProgressDialog(self, task=t)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                kwargs = {}
                if dlg.percent_set:
                    kwargs["percent_complete"] = dlg.percent_complete
                if dlg.actual_start_set:
                    kwargs["actual_start"] = dlg.actual_start
                if dlg.actual_end_set:
                    kwargs["actual_end"] = dlg.actual_end

                # if nothing selected, warn user
                if not kwargs:
                    QMessageBox.information(self, "Update progress", "Please select at least one field to update.")
                    continue

                self._task_service.update_progress(task_id=t.id, **kwargs)
            except (ValidationError, BusinessRuleError, NotFoundError) as e:
                QMessageBox.warning(self, "Error", str(e))
                continue
            self.reload_tasks()
            return

    def manage_dependencies(self):
        pid = self._current_project_id()
        if not pid:
            QMessageBox.information(self, "Dependencies", "Please select a project.")
            return
        t = self._get_selected_task()
        if not t:
            QMessageBox.information(self, "Dependencies", "Please select a task.")
            return
        project_tasks = self._task_service.list_tasks_for_project(pid)
        dlg = DependencyListDialog(self, self._task_service, project_tasks, t)
        dlg.exec()
        self.reload_tasks()

    def manage_assignments(self):
        t = self._get_selected_task()
        if not t:
            QMessageBox.information(self, "Assignments", "Please select a task.")
            return
        dlg = AssignmentListDialog(self, self._task_service, self._resource_service, self._project_resource_service, t)
        dlg.exec()
        self.reload_tasks()