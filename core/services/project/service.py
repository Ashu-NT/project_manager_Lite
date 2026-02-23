from __future__ import annotations

from sqlalchemy.orm import Session

from core.interfaces import (
    AssignmentRepository,
    CalendarEventRepository,
    CostRepository,
    DependencyRepository,
    ProjectRepository,
    TaskRepository,
)
from core.services.project.lifecycle import ProjectLifecycleMixin
from core.services.project.query import ProjectQueryMixin


class ProjectService(ProjectLifecycleMixin, ProjectQueryMixin):
    """Project service orchestrator: wiring repositories + composing mixins."""

    def __init__(
        self,
        session: Session,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        dependency_repo: DependencyRepository,
        assignment_repo: AssignmentRepository,
        calendar_repo: CalendarEventRepository,
        cost_repo: CostRepository,
    ):
        self._session = session
        self._project_repo = project_repo
        self._task_repo = task_repo
        self._dependency_repo = dependency_repo
        self._assignment_repo = assignment_repo
        self._calendar_repo = calendar_repo
        self._cost_repo = cost_repo


__all__ = ["ProjectService"]
