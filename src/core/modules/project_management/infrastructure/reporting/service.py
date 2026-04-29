from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.project import (
    ProjectRepository,
    ProjectResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.contracts.repositories.cost_calendar import CostRepository
from src.core.modules.project_management.contracts.repositories.baseline import BaselineRepository
from src.core.platform.access.authorization import require_project_permission
from src.core.platform.auth.authorization import require_permission
from src.core.modules.project_management.application.scheduling.engine import SchedulingEngine
from src.core.modules.project_management.application.scheduling.work_calendar_engine import (
    WorkCalendarEngine,
)
from core.modules.project_management.services.common.base import ServiceBase
from core.modules.project_management.services.common.module_guard import ProjectManagementModuleGuardMixin

from .baseline_compare import ReportingBaselineCompareMixin
from .cost_breakdown import ReportingCostBreakdownMixin
from .evm import ReportingEvmMixin
from .kpi import ReportingKpiMixin
from .labor import ReportingLaborMixin
from .variance import ReportingVarianceMixin


class ReportingService(
    ProjectManagementModuleGuardMixin,
    ReportingCostBreakdownMixin,
    ReportingBaselineCompareMixin,
    ReportingVarianceMixin,
    ReportingEvmMixin,
    ReportingLaborMixin,
    ReportingKpiMixin,
    ServiceBase,
):
    def __init__(
        self,
        session: Session,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        resource_repo: ResourceRepository,
        assignment_repo: AssignmentRepository,
        cost_repo: CostRepository,
        scheduling_engine: SchedulingEngine,
        calendar: WorkCalendarEngine,
        baseline_repo: BaselineRepository,
        project_resource_repo: ProjectResourceRepository,
        user_session=None,
        module_catalog_service=None,
    ):
        super().__init__(session)
        self._project_repo: ProjectRepository = project_repo
        self._task_repo: TaskRepository = task_repo
        self._resource_repo: ResourceRepository = resource_repo
        self._assignment_repo: AssignmentRepository = assignment_repo
        self._cost_repo: CostRepository = cost_repo
        self._scheduling_engine: SchedulingEngine = scheduling_engine
        self._calendar: WorkCalendarEngine = calendar
        self._baseline_repo: BaselineRepository = baseline_repo
        self._project_resource_repo: ProjectResourceRepository = project_resource_repo
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def _require_view(self, operation_label: str, *, project_id: str | None = None) -> None:
        require_permission(self._user_session, "report.view", operation_label=operation_label)
        if project_id is not None:
            require_project_permission(
                self._user_session,
                project_id,
                "report.view",
                operation_label=operation_label,
            )
