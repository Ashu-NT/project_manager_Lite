# ui/task/tab.py
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.events.domain_events import domain_events
from core.services.auth import UserSessionContext
from core.services.project import ProjectResourceService, ProjectService
from core.services.resource import ResourceService
from core.services.task import TaskService
from ui.shared.guards import (
    apply_permission_hint,
    can_execute_governed_action,
    has_permission,
    make_guarded_slot,
)
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
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._project_service: ProjectService = project_service
        self._task_service: TaskService = task_service
        self._resource_service: ResourceService = resource_service
        self._project_resource_service: ProjectResourceService = project_resource_service
        self._user_session = user_session
        self._can_manage_tasks = has_permission(self._user_session, "task.manage")
        self._can_manage_assignments = self._can_manage_tasks
        self._can_add_dependencies = can_execute_governed_action(
            user_session=self._user_session,
            manage_permission="task.manage",
            governance_action="dependency.add",
        )
        self._can_remove_dependencies = can_execute_governed_action(
            user_session=self._user_session,
            manage_permission="task.manage",
            governance_action="dependency.remove",
        )

        self._setup_ui()
        self._load_projects()
        self._sync_toolbar_actions()
        domain_events.tasks_changed.connect(self._on_task_changed)
        domain_events.project_changed.connect(self._on_project_changed_event)
        domain_events.resources_changed.connect(self._on_resources_changed)

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
        self.btn_refresh_tasks = QPushButton(CFG.REFRESH_TASKS_LABEL)

        for btn in [
            self.btn_reload_projects,
            self.btn_new,
            self.btn_edit,
            self.btn_delete,
            self.btn_progress,
            self.btn_refresh_tasks,
        ]:
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)

        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(self.btn_progress)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh_tasks)
        root.addLayout(toolbar)

        self.table = QTableView()
        self.model = TaskTableModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        style_table(self.table)

        self._assignment_panel = self._build_assignment_panel()
        self._assignment_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._assignment_panel.setMinimumWidth(320)

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(8)
        self.main_splitter.addWidget(self.table)
        self.main_splitter.addWidget(self._assignment_panel)
        self.main_splitter.setStretchFactor(0, 5)
        self.main_splitter.setStretchFactor(1, 3)
        self.main_splitter.setSizes([980, 520])
        root.addWidget(self.main_splitter, 1)

        self.btn_reload_projects.clicked.connect(self._load_projects)
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        self.btn_refresh_tasks.clicked.connect(self.reload_tasks)
        self.btn_new.clicked.connect(
            make_guarded_slot(self, title="Tasks", callback=self.create_task)
        )
        self.btn_edit.clicked.connect(
            make_guarded_slot(self, title="Tasks", callback=self.edit_task)
        )
        self.btn_delete.clicked.connect(
            make_guarded_slot(self, title="Tasks", callback=self.delete_task)
        )
        self.btn_progress.clicked.connect(
            make_guarded_slot(self, title="Tasks", callback=self.update_progress)
        )
        self.table.selectionModel().selectionChanged.connect(self._on_task_selection_changed)

        apply_permission_hint(
            self.btn_new,
            allowed=self._can_manage_tasks,
            missing_permission="task.manage",
        )
        apply_permission_hint(
            self.btn_edit,
            allowed=self._can_manage_tasks,
            missing_permission="task.manage",
        )
        apply_permission_hint(
            self.btn_delete,
            allowed=self._can_manage_tasks,
            missing_permission="task.manage",
        )
        apply_permission_hint(
            self.btn_progress,
            allowed=self._can_manage_tasks,
            missing_permission="task.manage",
        )
        self._sync_toolbar_actions()

    def _on_task_selection_changed(self, *_args) -> None:
        TaskAssignmentPanelMixin._on_task_selection_changed(self, *_args)
        self._sync_toolbar_actions()

    def _sync_toolbar_actions(self) -> None:
        has_task = self._get_selected_task() is not None
        self.btn_new.setEnabled(self._can_manage_tasks)
        self.btn_edit.setEnabled(self._can_manage_tasks and has_task)
        self.btn_delete.setEnabled(self._can_manage_tasks and has_task)
        self.btn_progress.setEnabled(self._can_manage_tasks and has_task)
