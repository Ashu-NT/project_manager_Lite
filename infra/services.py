from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from core.services.baseline import BaselineService
from core.services.calendar import CalendarService
from core.services.cost import CostService
from core.services.dashboard import DashboardService
from core.services.project import ProjectResourceService, ProjectService
from core.services.reporting import ReportingService
from core.services.resource import ResourceService
from core.services.scheduling import SchedulingEngine
from core.services.task import TaskService
from core.services.work_calendar import WorkCalendarEngine, WorkCalendarService
from infra.db.repositories import (
    SqlAlchemyAssignmentRepository,
    SqlAlchemyBaselineRepository,
    SqlAlchemyCalendarEventRepository,
    SqlAlchemyCostRepository,
    SqlAlchemyDependencyRepository,
    SqlAlchemyProjectRepository,
    SqlAlchemyProjectResourceRepository,
    SqlAlchemyResourceRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyWorkingCalendarRepository,
)


@dataclass(frozen=True)
class ServiceGraph:
    session: Session
    project_service: ProjectService
    task_service: TaskService
    calendar_service: CalendarService
    resource_service: ResourceService
    cost_service: CostService
    work_calendar_engine: WorkCalendarEngine
    work_calendar_service: WorkCalendarService
    scheduling_engine: SchedulingEngine
    reporting_service: ReportingService
    baseline_service: BaselineService
    dashboard_service: DashboardService
    project_resource_service: ProjectResourceService

    def as_dict(self) -> dict[str, Any]:
        return {
            "session": self.session,
            "project_service": self.project_service,
            "task_service": self.task_service,
            "calendar_service": self.calendar_service,
            "resource_service": self.resource_service,
            "cost_service": self.cost_service,
            "work_calendar_engine": self.work_calendar_engine,
            "work_calendar_service": self.work_calendar_service,
            "scheduling_engine": self.scheduling_engine,
            "reporting_service": self.reporting_service,
            "baseline_service": self.baseline_service,
            "dashboard_service": self.dashboard_service,
            "project_resource_service": self.project_resource_service,
        }


def build_service_graph(session: Session) -> ServiceGraph:
    project_repo = SqlAlchemyProjectRepository(session)
    task_repo = SqlAlchemyTaskRepository(session)
    resource_repo = SqlAlchemyResourceRepository(session)
    assignment_repo = SqlAlchemyAssignmentRepository(session)
    dependency_repo = SqlAlchemyDependencyRepository(session)
    cost_repo = SqlAlchemyCostRepository(session)
    calendar_repo = SqlAlchemyCalendarEventRepository(session)
    work_calendar_repo = SqlAlchemyWorkingCalendarRepository(session)
    baseline_repo = SqlAlchemyBaselineRepository(session)
    project_resource_repo = SqlAlchemyProjectResourceRepository(session)

    work_calendar_engine = WorkCalendarEngine(work_calendar_repo, calendar_id="default")

    project_service = ProjectService(
        session,
        project_repo,
        task_repo,
        dependency_repo,
        assignment_repo,
        calendar_repo,
        cost_repo,
    )
    project_resource_service = ProjectResourceService(
        project_resource_repo=project_resource_repo,
        resource_repo=resource_repo,
        session=session,
    )
    task_service = TaskService(
        session,
        task_repo,
        dependency_repo,
        assignment_repo,
        resource_repo,
        cost_repo,
        calendar_repo,
        work_calendar_engine,
        project_resource_repo,
        project_repo,
    )
    calendar_service = CalendarService(session, calendar_repo, task_repo)
    resource_service = ResourceService(session, resource_repo, assignment_repo, project_resource_repo)
    cost_service = CostService(session, cost_repo, project_repo, task_repo)
    work_calendar_service = WorkCalendarService(session, work_calendar_repo, work_calendar_engine)
    scheduling_engine = SchedulingEngine(session, task_repo, dependency_repo, work_calendar_engine)
    reporting_service = ReportingService(
        session=session,
        project_repo=project_repo,
        task_repo=task_repo,
        resource_repo=resource_repo,
        assignment_repo=assignment_repo,
        cost_repo=cost_repo,
        scheduling_engine=scheduling_engine,
        calendar=work_calendar_engine,
        baseline_repo=baseline_repo,
        project_resource_repo=project_resource_repo,
    )
    baseline_service = BaselineService(
        session=session,
        project_repo=project_repo,
        task_repo=task_repo,
        cost_repo=cost_repo,
        baseline_repo=baseline_repo,
        scheduling=scheduling_engine,
        calendar=work_calendar_engine,
        project_resource_repo=project_resource_repo,
        resource_repo=resource_repo,
    )
    dashboard_service = DashboardService(
        reporting_service=reporting_service,
        task_service=task_service,
        project_service=project_service,
        resource_service=resource_service,
        scheduling_engine=scheduling_engine,
        work_calendar_engine=work_calendar_engine,
    )

    return ServiceGraph(
        session=session,
        project_service=project_service,
        task_service=task_service,
        calendar_service=calendar_service,
        resource_service=resource_service,
        cost_service=cost_service,
        work_calendar_engine=work_calendar_engine,
        work_calendar_service=work_calendar_service,
        scheduling_engine=scheduling_engine,
        reporting_service=reporting_service,
        baseline_service=baseline_service,
        dashboard_service=dashboard_service,
        project_resource_service=project_resource_service,
    )


def build_service_dict(session: Session) -> dict[str, Any]:
    return build_service_graph(session).as_dict()
