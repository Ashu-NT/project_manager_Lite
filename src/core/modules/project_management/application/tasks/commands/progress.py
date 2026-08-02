"""Task execution-progress commands."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.task import TaskRepository
from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.platform.access.authorization import require_project_permission
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError
from src.core.shared.activity import record_activity
from src.core.shared.events.domain_events import domain_events


class TaskProgressMixin:
    _session: Session
    _task_repo: TaskRepository

    def set_status(self, task_id: str, status: TaskStatus) -> None:
        self.set_tasks_status((task_id,), status)

    def set_tasks_status(
        self,
        task_ids: tuple[str, ...],
        status: TaskStatus,
        *,
        reopen_percent_complete: float | None = None,
    ) -> list[Task]:
        require_permission(self._user_session, "task.manage", operation_label="set task status")
        normalized_ids = tuple(
            task_id
            for task_id in dict.fromkeys(
                str(task_id or "").strip() for task_id in task_ids
            )
            if task_id
        )
        tasks: list[Task] = []
        for task_id in normalized_ids:
            task = self._task_repo.get(task_id)
            if task is None:
                continue
            require_project_permission(
                self._user_session,
                task.project_id,
                "task.manage",
                operation_label="set task status",
            )
            self._require_leaf_task(task, operation_label="change execution status")
            tasks.append(task)

        candidates: list[Task] = []
        for task in tasks:
            if task.status == status:
                continue
            percent_complete = task.percent_complete
            if (
                task.status == TaskStatus.DONE
                and status == TaskStatus.IN_PROGRESS
                and reopen_percent_complete is not None
            ):
                percent_complete = replace(
                    task,
                    percent_complete=reopen_percent_complete,
                ).percent_complete
            elif status == TaskStatus.DONE:
                percent_complete = 100.0
            elif status == TaskStatus.TODO:
                percent_complete = 0.0
            elif status == TaskStatus.IN_PROGRESS and not 0.0 < percent_complete < 100.0:
                percent_complete = 50.0 if task.status == TaskStatus.DONE else 1.0
            candidates.append(
                replace(task, status=status, percent_complete=percent_complete)
            )

        try:
            for candidate in candidates:
                self._task_repo.update(candidate)
                record_activity(
                    self,
                    action="task.set_status",
                    entity_type="task",
                    entity_id=candidate.id,
                    module="project_management",
                    workspace_id=candidate.project_id,
                    details={"status": candidate.status.value},
                    commit=False,
                )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        for project_id in {candidate.project_id for candidate in candidates}:
            domain_events.tasks_changed.emit(project_id)
        return candidates

    def update_progress(
        self,
        task_id: str,
        percent_complete: float | None = None,
        actual_start: date | None = None,
        actual_end: date | None = None,
        status: TaskStatus | None = None,
        expected_version: int | None = None,
    ) -> Task:
        require_permission(self._user_session, "task.manage", operation_label="update task progress")
        task = self._task_repo.get(task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        require_project_permission(
            self._user_session,
            task.project_id,
            "task.manage",
            operation_label="update task progress",
        )
        if expected_version is not None and task.version != expected_version:
            raise ConcurrencyError(
                "Task changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        self._require_leaf_task(task, operation_label="record progress")

        next_percent_complete = task.percent_complete
        next_status = task.status
        if percent_complete is not None:
            next_percent_complete = replace(task, percent_complete=percent_complete).percent_complete
            if next_percent_complete == 0 and task.status != TaskStatus.TODO:
                next_status = TaskStatus.TODO
            elif 0 < next_percent_complete < 100 and task.status == TaskStatus.TODO:
                next_status = TaskStatus.IN_PROGRESS
            elif next_percent_complete == 100:
                next_status = TaskStatus.DONE
            elif next_percent_complete < 100 and task.status == TaskStatus.DONE:
                next_status = TaskStatus.IN_PROGRESS

        candidate = replace(
            task,
            percent_complete=next_percent_complete,
            actual_start=task.actual_start if actual_start is None else actual_start,
            actual_end=task.actual_end if actual_end is None else actual_end,
            status=next_status if status is None else status,
        )
        self._validate_task_within_project_dates(
            candidate.project_id,
            candidate.actual_start,
            candidate.actual_end,
        )
        try:
            self._task_repo.update(candidate)
            self._session.commit()
            record_activity(
                self,
                action="task.update_progress",
                entity_type="task",
                entity_id=candidate.id,
                module="project_management",
                workspace_id=candidate.project_id,
                details={
                    "percent_complete": candidate.percent_complete,
                    "status": candidate.status.value,
                },
            )
        except Exception:
            self._session.rollback()
            raise
        domain_events.tasks_changed.emit(candidate.project_id)
        return candidate


__all__ = ["TaskProgressMixin"]
