from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from core.events.domain_events import domain_events
from core.exceptions import NotFoundError, ValidationError
from core.interfaces import DependencyRepository, TaskRepository
from core.models import DependencyType, TaskDependency


class TaskDependencyMixin:
    _session: Session
    _task_repo: TaskRepository
    _dependency_repo: DependencyRepository

    def add_dependency(
        self,
        predecessor_id: str,
        successor_id: str,
        dependency_type: DependencyType = DependencyType.FINISH_TO_START,
        lag_days: int = 0,
    ) -> TaskDependency:
        self._validate_not_self_dependency(predecessor_id, successor_id)

        pred = self._task_repo.get(predecessor_id)
        if not pred:
            raise NotFoundError("Predecessor task not found", code="TASK_NOT_FOUND")

        succ = self._task_repo.get(successor_id)
        if not succ:
            raise NotFoundError("Successor task not found", code="TASK_NOT_FOUND")

        if pred.project_id != succ.project_id:
            raise ValidationError(
                "Tasks must be in the same project to create a dependency.",
                code="DEPENDENCY_CROSS_PROJECT",
            )

        existing = self._dependency_repo.list_by_task(predecessor_id)
        if any(d.successor_task_id == successor_id for d in existing):
            raise ValidationError("This dependency already exists.", code="DEPENDENCY_DUPLICATE")

        self._check_no_circular_dependency(
            project_id=pred.project_id,
            predecessor_id=predecessor_id,
            successor_id=successor_id,
        )

        dep = TaskDependency.create(predecessor_id, successor_id, dependency_type, lag_days)
        try:
            self._dependency_repo.add(dep)
            self._session.commit()
        except Exception as exc:
            self._session.rollback()
            raise exc

        domain_events.tasks_changed.emit(pred.project_id)
        return dep

    def remove_dependency(self, dep_id: str) -> None:
        dep = self._dependency_repo.get(dep_id)
        if not dep:
            raise NotFoundError("Dependency not found.", code="DEPENDENCY_NOT_FOUND")
        pred = self._task_repo.get(dep.predecessor_task_id)
        succ = self._task_repo.get(dep.successor_task_id)

        try:
            self._dependency_repo.delete(dep_id)
            self._session.commit()
        except Exception as exc:
            self._session.rollback()
            raise exc

        project_id = None
        if pred:
            project_id = pred.project_id
        elif succ:
            project_id = succ.project_id
        if project_id:
            domain_events.tasks_changed.emit(project_id)

    def list_dependencies_for_task(self, task_id: str) -> List[TaskDependency]:
        return self._dependency_repo.list_by_task(task_id)
