from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from core.events.domain_events import domain_events
from core.exceptions import ConcurrencyError, NotFoundError, ValidationError
from core.interfaces import (
    AssignmentRepository,
    CalendarEventRepository,
    CostRepository,
    DependencyRepository,
    TaskRepository,
)
from core.models import Task, TaskStatus
from core.services.audit.helpers import record_audit
from core.services.auth.authorization import require_permission
from core.services.work_calendar.engine import WorkCalendarEngine


logger = logging.getLogger(__name__)


class TaskLifecycleMixin:
    _session: Session
    _task_repo: TaskRepository
    _dependency_repo: DependencyRepository
    _assignment_repo: AssignmentRepository
    _calendar_repo: CalendarEventRepository
    _cost_repo: CostRepository
    _work_calendar_engine: WorkCalendarEngine

    def create_task(
        self,
        project_id: str,
        name: str,
        description: str = "",
        start_date: Optional[date] = None,
        duration_days: Optional[int] = None,
        status: TaskStatus = TaskStatus.TODO,
        priority: int = 0,
        deadline: Optional[date] = None,
    ) -> Task:
        require_permission(self._user_session, "task.manage", operation_label="create task")
        self._validate_dates(start_date, deadline, duration_days)
        self._validate_task_name(name)

        task = Task.create(
            project_id=project_id,
            name=name,
            description=description,
            start_date=start_date,
            duration_days=duration_days,
            status=status,
            priority=priority,
            deadline=deadline,
        )
        task.start_date = start_date
        task.duration_days = duration_days
        if start_date and duration_days is not None:
            task.end_date = self._work_calendar_engine.add_working_days(start_date, int(duration_days))

        self._validate_task_within_project_dates(project_id, task.start_date, task.end_date)

        try:
            self._task_repo.add(task)
            self._session.commit()
            record_audit(
                self,
                action="task.create",
                entity_type="task",
                entity_id=task.id,
                project_id=project_id,
                details={"name": task.name},
            )
            logger.info(f"Created task {task.id} - {task.name} for project {project_id}")
            domain_events.tasks_changed.emit(project_id)
            return task
        except Exception as exc:
            self._session.rollback()
            logger.error(f"Error creating task: {exc}")
            raise

    def set_status(self, task_id: str, status: TaskStatus) -> None:
        require_permission(self._user_session, "task.manage", operation_label="set task status")
        task = self._task_repo.get(task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        task.status = status
        try:
            self._task_repo.update(task)
            self._session.commit()
            record_audit(
                self,
                action="task.set_status",
                entity_type="task",
                entity_id=task.id,
                project_id=task.project_id,
                details={"status": task.status.value},
            )
        except Exception as exc:
            self._session.rollback()
            raise exc
        domain_events.tasks_changed.emit(task.project_id)

    def delete_task(self, task_id: str) -> None:
        require_permission(self._user_session, "task.manage", operation_label="delete task")
        task = self._task_repo.get(task_id)
        if not task:
            raise NotFoundError("Task not found")

        try:
            self._dependency_repo.delete_for_task(task_id)
            self._assignment_repo.delete_by_task(task_id)
            self._calendar_repo.delete_for_task(task_id)

            cost_items = self._cost_repo.list_by_project(task.project_id)
            for c in cost_items:
                if c.task_id == task_id:
                    self._cost_repo.delete(c.id)

            self._task_repo.delete(task_id)
            self._session.commit()
            record_audit(
                self,
                action="task.delete",
                entity_type="task",
                entity_id=task_id,
                project_id=task.project_id,
                details={"name": task.name},
            )
        except Exception as exc:
            self._session.rollback()
            raise exc

        domain_events.tasks_changed.emit(task.project_id)

    def update_task(
        self,
        task_id: str,
        name: str | None = None,
        description: str | None = None,
        start_date: date | None = None,
        duration_days: int | None = None,
        status: TaskStatus | None = None,
        priority: int | None = None,
        deadline: date | None = None,
        expected_version: int | None = None,
    ) -> Task:
        require_permission(self._user_session, "task.manage", operation_label="update task")
        task = self._task_repo.get(task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        if expected_version is not None and task.version != expected_version:
            raise ConcurrencyError(
                "Task changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )

        if name is not None:
            self._validate_task_name(name)
            task.name = name.strip()
        if description is not None:
            task.description = description.strip()
        if start_date is not None:
            task.start_date = start_date
        if duration_days is not None:
            if duration_days < 0:
                raise ValidationError("Task duration cannot be negative.")
            task.duration_days = duration_days

        if task.start_date and task.duration_days is not None:
            task.end_date = self._work_calendar_engine.add_working_days(
                task.start_date, task.duration_days
            )

        if status is not None:
            task.status = status
        if priority is not None:
            task.priority = priority

        if deadline is not None:
            if deadline and task.start_date and deadline < task.start_date:
                raise ValidationError("Task deadline cannot be before start_date.")
            task.deadline = deadline

        self._validate_task_within_project_dates(task.project_id, task.start_date, task.end_date)

        try:
            self._task_repo.update(task)
            self._session.commit()
            record_audit(
                self,
                action="task.update",
                entity_type="task",
                entity_id=task.id,
                project_id=task.project_id,
                details={"name": task.name, "status": task.status.value},
            )
        except Exception as exc:
            self._session.rollback()
            raise exc

        domain_events.tasks_changed.emit(task.project_id)
        return task

    def update_progress(
        self,
        task_id: str,
        percent_complete: float | None = None,
        actual_start: date | None = None,
        actual_end: date | None = None,
        expected_version: int | None = None,
    ) -> Task:
        require_permission(self._user_session, "task.manage", operation_label="update task progress")
        task = self._task_repo.get(task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        if expected_version is not None and task.version != expected_version:
            raise ConcurrencyError(
                "Task changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )

        if percent_complete is not None:
            if percent_complete < 0 or percent_complete > 100:
                raise ValidationError("percent_complete must be between 0 and 100.")

            task.percent_complete = percent_complete

            if percent_complete == 0 and task.status != TaskStatus.TODO:
                task.status = TaskStatus.TODO
            elif 0 < percent_complete < 100 and task.status == TaskStatus.TODO:
                task.status = TaskStatus.IN_PROGRESS
            elif percent_complete == 100:
                task.status = TaskStatus.DONE
            elif percent_complete < 100 and task.status == TaskStatus.DONE:
                task.status = TaskStatus.IN_PROGRESS

        if actual_start is not None:
            task.actual_start = actual_start
        if actual_end is not None:
            check_start = actual_start if actual_start is not None else task.actual_start
            if check_start and actual_end < check_start:
                raise ValidationError("Actual end date cannot be before actual start.")
            task.actual_end = actual_end

        self._validate_task_within_project_dates(task.project_id, task.actual_start, task.actual_end)

        try:
            self._task_repo.update(task)
            self._session.commit()
            record_audit(
                self,
                action="task.update_progress",
                entity_type="task",
                entity_id=task.id,
                project_id=task.project_id,
                details={"percent_complete": task.percent_complete},
            )
        except Exception as exc:
            self._session.rollback()
            raise exc

        domain_events.tasks_changed.emit(task.project_id)
        return task
