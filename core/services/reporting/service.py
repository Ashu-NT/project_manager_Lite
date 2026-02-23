from __future__ import annotations

from sqlalchemy.orm import Session

from core.interfaces import (
    AssignmentRepository,
    BaselineRepository,
    CostRepository,
    ProjectRepository,
    ProjectResourceRepository,
    ResourceRepository,
    TaskRepository,
)
from core.services.common.base import ServiceBase
from core.services.scheduling.engine import SchedulingEngine
from core.services.work_calendar.engine import WorkCalendarEngine

from .cost_breakdown import ReportingCostBreakdownMixin
from .evm import ReportingEvmMixin
from .kpi import ReportingKpiMixin
from .labor import ReportingLaborMixin
from .variance import ReportingVarianceMixin


class ReportingService(
    ReportingCostBreakdownMixin,
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
        baseline_repo : BaselineRepository,
        project_resource_repo: ProjectResourceRepository
    ):
        super().__init__(session)
        self._project_repo = project_repo
        self._task_repo = task_repo
        self._resource_repo = resource_repo
        self._assignment_repo = assignment_repo
        self._cost_repo = cost_repo
        self._scheduling_engine = scheduling_engine
        self._calendar = calendar
        self._baseline_repo = baseline_repo
        self._project_resource_repo = project_resource_repo
