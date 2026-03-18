from __future__ import annotations

from PySide6.QtWidgets import QWidget

from core.platform.notifications.domain_events import domain_events
from core.platform.common.models import Project, Task
from core.platform.auth import UserSessionContext
from core.modules.project_management.services.cost import CostService
from core.modules.project_management.services.project import ProjectService
from core.modules.project_management.services.reporting import ReportingService
from core.modules.project_management.services.resource import ResourceService
from core.modules.project_management.services.task import TaskService
from ui.modules.project_management.cost.actions import CostActionsMixin
from ui.modules.project_management.cost.layout import CostLayoutMixin
from ui.modules.project_management.cost.labor_summary import CostLaborSummaryMixin
from ui.modules.project_management.cost.models import CostTableModel  # noqa: F401
from ui.modules.project_management.cost.project_flow import CostProjectFlowMixin
from ui.modules.project_management.cost.surface import CostSurfaceMixin
from ui.platform.shared.deferred_call import DeferredCall
from ui.platform.shared.guards import can_execute_governed_action


class CostTab(
    CostProjectFlowMixin,
    CostSurfaceMixin,
    CostLayoutMixin,
    CostLaborSummaryMixin,
    CostActionsMixin,
    QWidget,
):
    def __init__(
        self,
        project_service: ProjectService,
        task_service: TaskService,
        cost_service: CostService,
        reporting_service: ReportingService,
        resource_service: ResourceService,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._project_service: ProjectService = project_service
        self._task_service: TaskService = task_service
        self._cost_service: CostService = cost_service
        self._reporting_service: ReportingService = reporting_service
        self._resource_service: ResourceService = resource_service
        self._user_session = user_session
        self._can_create_cost = can_execute_governed_action(
            user_session=self._user_session,
            manage_permission="cost.manage",
            governance_action="cost.add",
        )
        self._can_edit_cost = can_execute_governed_action(
            user_session=self._user_session,
            manage_permission="cost.manage",
            governance_action="cost.update",
        )
        self._can_delete_cost = can_execute_governed_action(
            user_session=self._user_session,
            manage_permission="cost.manage",
            governance_action="cost.delete",
        )
        self._current_project: Project | None = None
        self._project_tasks: list[Task] = []
        self._loaded_cost_snapshot = None
        self._cost_reload_inflight = False
        self._cost_reload_pending = False
        self._cost_reload_pending_preferred_cost_id = None
        self._cost_filter_refresher = DeferredCall(
            self,
            lambda: self.reload_costs(refresh_remote=False),
            delay_ms=140,
        )
        self._setup_ui()
        self._load_projects()
        self._sync_cost_actions()
        domain_events.costs_changed.connect(self._on_costs_or_tasks_changed)
        domain_events.tasks_changed.connect(self._on_costs_or_tasks_changed)
        domain_events.project_changed.connect(self._on_project_changed_event)
        domain_events.resources_changed.connect(self._on_resources_changed)
