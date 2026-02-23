# ui/task/tab.py
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.events.domain_events import domain_events
from core.services.project import ProjectResourceService, ProjectService
from core.services.resource import ResourceService
from core.services.task import TaskService
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG
from ui.task.assignment_actions import TaskAssignmentActionsMixin
from ui.task.assignment_panel import TaskAssignmentPanelMixin
from ui.task.actions import TaskActionsMixin
from ui.task.models import TaskTableModel
from ui.task.project_flow import TaskProjectFlowMixin


class TaskTab(
    TaskProjectFlowMixin,
    TaskAssignmentActionsMixin,
    TaskActionsMixin,
    TaskAssignmentPanelMixin,
    QWidget,
):
    """
    Task tab coordinator:
    - wires UI controls and signal routing
    - delegates project/task loading to TaskProjectFlowMixin
    - delegates user actions to TaskActionsMixin
    """

    _assignment_panel: QWidget

    def __init__(
        self,
        project_service: ProjectService,
        task_service: TaskService,
        resource_service: ResourceService,
        project_resource_service: ProjectResourceService,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._project_service: ProjectService = project_service
        self._task_service: TaskService = task_service
        self._resource_service: ResourceService = resource_service
        self._project_resource_service: ProjectResourceService = project_resource_service

        self._setup_ui()
        self._load_projects()
        domain_events.tasks_changed.connect(self._on_task_changed)
        domain_events.project_changed.connect(self._on_project_changed_event)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(
            CFG.MARGIN_MD,
            CFG.MARGIN_MD,
            CFG.MARGIN_MD,
            CFG.MARGIN_MD,
        )

        top = QHBoxLayout()
        top.addWidget(QLabel("Project:"))
        self.project_combo = QComboBox()
        self.project_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.project_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.btn_reload_projects = QPushButton(CFG.RELOAD_PROJECTS_LABEL)
        top.addWidget(self.project_combo)
        top.addWidget(self.btn_reload_projects)
        top.addStretch()
        root.addLayout(top)

        toolbar = QHBoxLayout()
        self.btn_new = QPushButton(CFG.NEW_TASK_LABEL)
        self.btn_edit = QPushButton(CFG.EDIT_LABEL)
        self.btn_delete = QPushButton(CFG.DELETE_LABEL)
        self.btn_progress = QPushButton(CFG.UPDATE_PROGRESS_LABEL)
        self.btn_deps = QPushButton(CFG.DEPENDENCIES_LABEL)
        self.btn_refresh_tasks = QPushButton(CFG.REFRESH_TASKS_LABEL)

        for btn in [
            self.btn_reload_projects,
            self.btn_new,
            self.btn_edit,
            self.btn_delete,
            self.btn_progress,
            self.btn_deps,
            self.btn_refresh_tasks,
        ]:
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)

        self.btn_deps.setToolTip("Manage predecessor and successor relationships for the selected task.")

        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(self.btn_progress)
        toolbar.addWidget(self.btn_deps)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh_tasks)
        root.addLayout(toolbar)

        content = QHBoxLayout()
        content.setSpacing(CFG.SPACING_MD)

        self.table = QTableView()
        self.model = TaskTableModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        style_table(self.table)
        content.addWidget(self.table, 5)

        self._assignment_panel = self._build_assignment_panel()
        self._assignment_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._assignment_panel.setMinimumWidth(340)
        self._assignment_panel.setMaximumWidth(520)
        content.addWidget(self._assignment_panel, 3)

        root.addLayout(content, 1)

        self.btn_reload_projects.clicked.connect(self._load_projects)
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        self.btn_refresh_tasks.clicked.connect(self.reload_tasks)
        self.btn_new.clicked.connect(self.create_task)
        self.btn_edit.clicked.connect(self.edit_task)
        self.btn_delete.clicked.connect(self.delete_task)
        self.btn_progress.clicked.connect(self.update_progress)
        self.btn_deps.clicked.connect(self.manage_dependencies)
        self.table.selectionModel().selectionChanged.connect(self._on_task_selection_changed)
