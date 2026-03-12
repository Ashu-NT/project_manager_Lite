from __future__ import annotations

from PySide6.QtWidgets import QWidget

from core.events.domain_events import domain_events
from core.models import Project, Task
from core.services.auth import UserSessionContext
from core.services.cost import CostService
from core.services.project import ProjectService
from core.services.reporting import ReportingService
from core.services.resource import ResourceService
from core.services.task import TaskService
from ui.cost.actions import CostActionsMixin
from ui.cost.layout import CostLayoutMixin
from ui.cost.labor_summary import CostLaborSummaryMixin
from ui.cost.project_flow import CostProjectFlowMixin
from ui.cost.surface import CostSurfaceMixin
from ui.shared.guards import can_execute_governed_action


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
        self._setup_ui()
        self._load_projects()
        self._sync_cost_actions()
        domain_events.costs_changed.connect(self._on_costs_or_tasks_changed)
        domain_events.tasks_changed.connect(self._on_costs_or_tasks_changed)
        domain_events.project_changed.connect(self._on_project_changed_event)
        domain_events.resources_changed.connect(self._on_resources_changed)
