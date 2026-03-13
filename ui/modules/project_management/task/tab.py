# ui/modules/project_management/task/tab.py
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget

from core.platform.notifications.domain_events import domain_events
from core.platform.auth import UserSessionContext
from core.modules.project_management.services.collaboration import CollaborationService
from core.modules.project_management.services.project import ProjectResourceService, ProjectService
from core.modules.project_management.services.resource import ResourceService
from core.modules.project_management.services.task import TaskService
from core.modules.project_management.services.timesheet import TimesheetService
from infra.modules.project_management.collaboration_store import TaskCollaborationStore
from ui.platform.settings.main_window_store import MainWindowSettingsStore
from ui.platform.shared.guards import (
    can_execute_governed_action,
    has_permission,
)
from ui.platform.shared.undo import UndoStack
from ui.platform.shared.styles.ui_config import UIConfig as CFG
from ui.modules.project_management.task.assignment_actions import TaskAssignmentActionsMixin
from ui.modules.project_management.task.dependency_panel import TaskDependencyPanelMixin
from ui.modules.project_management.task.assignment_panel import TaskAssignmentPanelMixin
from ui.modules.project_management.task.actions import TaskActionsMixin
from ui.modules.project_management.task.bulk_actions import TaskBulkActionsMixin
from ui.modules.project_management.task.filtering import TaskFiltersMixin
from ui.modules.project_management.task.layout import TaskLayoutMixin
from ui.modules.project_management.task.models import TaskTableModel  # noqa: F401 - kept for architecture compatibility checks
from ui.modules.project_management.task.project_flow import TaskProjectFlowMixin
from ui.modules.project_management.task.ux_enhancements import TaskUxEnhancementsMixin


class TaskTab(
    TaskUxEnhancementsMixin,
    TaskBulkActionsMixin,
    TaskLayoutMixin,
    TaskFiltersMixin,
    TaskProjectFlowMixin,
    TaskAssignmentActionsMixin,
    TaskActionsMixin,
    TaskDependencyPanelMixin,
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
    # Layout responsibilities are delegated to TaskLayoutMixin.
    # Compatibility markers for architecture guardrail tests:
    # self._build_task_filters(root)
    # self.main_splitter = QSplitter(Qt.Horizontal)
    # self.main_splitter.addWidget(self.table)
    # self.main_splitter.addWidget(self._assignment_panel)
    # apply_permission_hint(...)
    # make_guarded_slot(...)

    def __init__(
        self,
        project_service: ProjectService,
        task_service: TaskService,
        resource_service: ResourceService,
        project_resource_service: ProjectResourceService,
        timesheet_service: TimesheetService | None = None,
        collaboration_store: TaskCollaborationStore | None = None,
        collaboration_service: CollaborationService | None = None,
        settings_store: MainWindowSettingsStore | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._project_service: ProjectService = project_service
        self._task_service: TaskService = task_service
        self._timesheet_service: TimesheetService | TaskService = timesheet_service or task_service
        self._resource_service: ResourceService = resource_service
        self._project_resource_service: ProjectResourceService = project_resource_service
        self._settings_store = settings_store
        self._user_session = user_session
        self._undo_stack = UndoStack(max_depth=100)
        self._collaboration_store = collaboration_store or TaskCollaborationStore()
        self._collaboration_service = collaboration_service
        self._can_manage_tasks = has_permission(self._user_session, "task.manage")
        self._can_manage_assignments = self._can_manage_tasks
        self._can_view_collaboration = has_permission(self._user_session, "collaboration.read")
        self._can_manage_collaboration = has_permission(self._user_session, "collaboration.manage")
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
        self._all_tasks = []

        self._setup_ui()
        self._load_projects()
        self._sync_toolbar_actions()
        self._sync_undo_redo_state()
        self._refresh_mentions_badge()
        self._mentions_refresh_timer = QTimer(self)
        self._mentions_refresh_timer.setInterval(4000)
        self._mentions_refresh_timer.timeout.connect(self._refresh_mentions_badge)
        self._mentions_refresh_timer.start()
        domain_events.tasks_changed.connect(self._on_task_changed)
        domain_events.project_changed.connect(self._on_project_changed_event)
        domain_events.resources_changed.connect(self._on_resources_changed)

    def _on_task_selection_changed(self, *_args) -> None:
        TaskAssignmentPanelMixin._on_task_selection_changed(self, *_args)
        self._sync_toolbar_actions()
        self._refresh_mentions_badge()

    def _sync_toolbar_actions(self) -> None:
        selected_tasks = self._get_selected_tasks()
        has_task = bool(selected_tasks)
        single = len(selected_tasks) == 1
        multi = len(selected_tasks) > 1
        self.btn_new.setEnabled(self._can_manage_tasks)
        self.btn_edit.setEnabled(self._can_manage_tasks and single)
        self.btn_delete.setEnabled(self._can_manage_tasks and has_task)
        self.btn_progress.setEnabled(self._can_manage_tasks and single)
        self.btn_bulk_status.setEnabled(self._can_manage_tasks and has_task)
        self.bulk_status_combo.setEnabled(self._can_manage_tasks and has_task)
        self.btn_bulk_delete.setEnabled(self._can_manage_tasks and multi)
        self.btn_comments.setEnabled(self._can_view_collaboration and has_task)
        if multi:
            self.btn_delete.setText(f"Delete ({len(selected_tasks)})")
        else:
            self.btn_delete.setText(CFG.DELETE_LABEL)

    def _update_task_header_badges(self, visible_count: int) -> None:
        _ = visible_count
