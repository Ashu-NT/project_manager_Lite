from __future__ import annotations

from sqlalchemy.orm import Session

from core.interfaces import (
    AssignmentRepository,
    CalendarEventRepository,
    CostRepository,
    DependencyRepository,
    ProjectRepository,
    ProjectResourceRepository,
    ResourceRepository,
    TaskRepository,
)
from core.services.task.assignment import TaskAssignmentMixin
from core.services.task.dependency import TaskDependencyMixin
from core.services.task.lifecycle import TaskLifecycleMixin
from core.services.task.query import TaskQueryMixin
from core.services.task.validation import TaskValidationMixin
from core.services.work_calendar.engine import WorkCalendarEngine


class TaskService(
    TaskLifecycleMixin,
    TaskDependencyMixin,
    TaskAssignmentMixin,
    TaskQueryMixin,
    TaskValidationMixin,
):
    def __init__(
        self,
        session: Session,
        task_repo: TaskRepository,
        dependency_repo: DependencyRepository,
        assignment_repo: AssignmentRepository,
        resource_repo: ResourceRepository,
        cost_repo: CostRepository,
        calendar_repo: CalendarEventRepository,
        work_calendar_engine: WorkCalendarEngine,
        project_resource_repo: ProjectResourceRepository | None = None,
        project_repo: ProjectRepository | None = None,
    ):
        self._session = session
        self._task_repo = task_repo
        self._dependency_repo = dependency_repo
        self._assignment_repo = assignment_repo
        self._resource_repo = resource_repo
        self._cost_repo = cost_repo
        self._calendar_repo = calendar_repo
        self._work_calendar_engine = work_calendar_engine
        self._project_resource_repo = project_resource_repo
        self._project_repo = project_repo
