from __future__ import annotations

import logging
from dataclasses import replace
from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.task import TaskRepository
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.platform.access.authorization import require_project_permission
from src.core.shared.activity import record_activity
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.shared.events.domain_events import domain_events
from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol

logger = logging.getLogger(__name__)


class TaskLifecycleMixin:
    _session: Session
    _task_repo: TaskRepository
    _work_calendar_engine: CalendarProtocol

    def create_task(
        self,
        project_id: str,
        name: str,
        description: str = "",
        start_date: date | None = None,
        duration_days: int | None = None,
        status: TaskStatus = TaskStatus.TODO,
        priority: int = 0,
        deadline: date | None = None,
        code: str = "",
        parent_task_id: str | None = None,
        wbs_code: str = "",
        sort_order: int | None = None,
    ) -> Task:
        require_permission(self._user_session, "task.manage", operation_label="create task")
        require_project_permission(
            self._user_session,
            project_id,
            "task.manage",
            operation_label="create task",
        )
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
        task.code = self._resolve_task_code(code, project_id, task.name)
        task = self._prepare_new_task_hierarchy(
            task,
            parent_task_id=parent_task_id,
            wbs_code=wbs_code,
            sort_order=sort_order,
        )
        if start_date and duration_days is not None:
            task.end_date = self._work_calendar_engine.add_working_days(start_date, int(duration_days))

        self._validate_task_within_project_dates(project_id, task.start_date, task.end_date)

        try:
            task = self._resequence_for_new_task(task)
            self._task_repo.add(task)
            self._session.commit()
            record_activity(
                self,
                action="task.create",
                entity_type="task",
                entity_id=task.id,
                module="project_management",
                workspace_id=project_id,
                details={"name": task.name},
            )
            logger.info("Created task %s - %s for project %s", task.id, task.name, project_id)
            domain_events.tasks_changed.emit(project_id)
            return task
        except IntegrityError as exc:
            self._session.rollback()
            if self._is_task_code_integrity_error(exc):
                self._raise_task_code_duplicate(task.code, exc)
            if self._is_task_wbs_integrity_error(exc):
                raise ValidationError(
                    "The WBS code or parent conflicts with another task.",
                    code="TASK_WBS_CONFLICT",
                ) from exc
            logger.error("Error creating task: %s", exc)
            raise
        except Exception as exc:
            self._session.rollback()
            logger.error("Error creating task: %s", exc)
            raise

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
        code: str | None = None,
    ) -> Task:
        require_permission(self._user_session, "task.manage", operation_label="update task")
        task = self._task_repo.get(task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        require_project_permission(
            self._user_session,
            task.project_id,
            "task.manage",
            operation_label="update task",
        )
        if expected_version is not None and task.version != expected_version:
            raise ConcurrencyError(
                "Task changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        if self._task_repo.list_children(task.project_id, task.id):
            schedule_changed = (
                (start_date is not None and start_date != task.start_date)
                or (duration_days is not None and duration_days != task.duration_days)
                or (status is not None and status != task.status)
            )
            if schedule_changed:
                raise BusinessRuleError(
                    "Summary task schedule and status are rolled up from execution leaves.",
                    code="TASK_WBS_SUMMARY_EXECUTION_FORBIDDEN",
                )

        next_name = task.name if name is None else name
        next_start_date = task.start_date if start_date is None else start_date
        next_duration_days = task.duration_days if duration_days is None else duration_days
        next_end_date = task.end_date
        if (start_date is not None or duration_days is not None) and (
            next_start_date and next_duration_days is not None
        ):
            next_end_date = self._work_calendar_engine.add_working_days(
                next_start_date,
                int(next_duration_days),
            )

        next_code = task.code
        if code is not None and code.strip():
            next_code = self._resolve_task_code(
                code,
                task.project_id,
                next_name,
                exclude_id=task.id,
            )

        candidate = replace(
            task,
            name=next_name,
            description=task.description if description is None else description,
            start_date=next_start_date,
            end_date=next_end_date,
            duration_days=next_duration_days,
            status=task.status if status is None else status,
            priority=task.priority if priority is None else priority,
            deadline=task.deadline if deadline is None else deadline,
            code=next_code,
        )

        self._validate_task_within_project_dates(
            candidate.project_id,
            candidate.start_date,
            candidate.end_date,
        )

        try:
            self._task_repo.update(candidate)
            self._session.commit()
            record_activity(
                self,
                action="task.update",
                entity_type="task",
                entity_id=candidate.id,
                module="project_management",
                workspace_id=candidate.project_id,
                details={"name": candidate.name, "status": candidate.status.value},
            )
        except IntegrityError as exc:
            self._session.rollback()
            if self._is_task_code_integrity_error(exc):
                self._raise_task_code_duplicate(candidate.code, exc)
            raise
        except Exception as exc:
            self._session.rollback()
            raise exc
        domain_events.tasks_changed.emit(candidate.project_id)
        return candidate

__all__ = ["TaskLifecycleMixin"]
