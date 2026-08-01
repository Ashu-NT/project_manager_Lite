from __future__ import annotations

import logging
from dataclasses import replace
from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.cost import (
    CostRepository,
)
from src.core.modules.project_management.contracts.repositories.task import (
    AssignmentRepository,
    DependencyRepository,
    TaskRepository,
)
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.platform.access.authorization import require_project_permission
from src.core.shared.activity import record_activity
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.shared.events.domain_events import domain_events
from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol

logger = logging.getLogger(__name__)


class TaskLifecycleMixin:
    _session: Session
    _task_repo: TaskRepository
    _dependency_repo: DependencyRepository
    _assignment_repo: AssignmentRepository
    _cost_repo: CostRepository
    _work_calendar_engine: CalendarProtocol

    def _resolve_task_code(
        self, code: str, project_id: str, name: str, *, exclude_id: str | None = None
    ) -> str:
        """Normalize a manual code or auto-generate a unique one (per-project scope)."""
        from src.core.platform.common.code_generation import (
            CodeGenerator,
            assert_code_unique,
            normalize_manual_code,
        )

        existing = {
            str(getattr(task, "code", "") or "").upper()
            for task in self._task_repo.list_by_project(project_id)
            if exclude_id is None or task.id != exclude_id
        }
        manual = normalize_manual_code(code)
        if manual:
            assert_code_unique(
                manual,
                exists=lambda candidate: candidate.upper() in existing,
                label="Task code",
            )
            return manual
        return CodeGenerator().generate(
            "task",
            exists=lambda candidate: candidate.upper() in existing,
            name=(name or "").strip() or None,
            use_year=not bool((name or "").strip()),
        )

    @staticmethod
    def _is_task_code_integrity_error(exc: IntegrityError) -> bool:
        message = " ".join(
            part
            for part in [
                str(getattr(exc, "orig", "") or ""),
                str(getattr(exc, "statement", "") or ""),
                str(exc),
            ]
            if part
        ).lower()
        return "ux_tasks_project_code" in message or "tasks.task_code" in message

    @staticmethod
    def _raise_task_code_duplicate(code: str, exc: IntegrityError) -> None:
        raise ValidationError(
            f"Task code '{code}' already exists.",
            code="CODE_DUPLICATE",
        ) from exc

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
        if start_date and duration_days is not None:
            task.end_date = self._work_calendar_engine.add_working_days(start_date, int(duration_days))

        self._validate_task_within_project_dates(project_id, task.start_date, task.end_date)

        try:
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
            logger.error("Error creating task: %s", exc)
            raise
        except Exception as exc:
            self._session.rollback()
            logger.error("Error creating task: %s", exc)
            raise

    def set_status(self, task_id: str, status: TaskStatus) -> None:
        require_permission(self._user_session, "task.manage", operation_label="set task status")
        task = self._task_repo.get(task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        require_project_permission(
            self._user_session,
            task.project_id,
            "task.manage",
            operation_label="set task status",
        )
        prior_status = task.status
        task.status = status
        if status == TaskStatus.DONE:
            task.percent_complete = 100.0
        elif status == TaskStatus.TODO:
            task.percent_complete = 0.0
        elif status == TaskStatus.IN_PROGRESS and not 0.0 < float(task.percent_complete or 0.0) < 100.0:
            task.percent_complete = 50.0 if prior_status == TaskStatus.DONE else 1.0
        try:
            self._task_repo.update(task)
            self._session.commit()
            record_activity(
                self,
                action="task.set_status",
                entity_type="task",
                entity_id=task.id,
                module="project_management",
                workspace_id=task.project_id,
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
        require_project_permission(
            self._user_session,
            task.project_id,
            "task.manage",
            operation_label="delete task",
        )
        try:
            time_entry_repo = getattr(self, "_time_entry_repo", None)
            assignments = self._assignment_repo.list_by_task(task_id)
            if time_entry_repo is not None:
                for assignment in assignments:
                    time_entry_repo.delete_by_assignment(assignment.id)
            self._dependency_repo.delete_for_task(task_id)
            self._assignment_repo.delete_by_task(task_id)
            cost_items = self._cost_repo.list_by_project(task.project_id)
            for cost_item in cost_items:
                if cost_item.task_id == task_id:
                    self._cost_repo.delete(cost_item.id)
            self._task_repo.delete(task_id)
            self._session.commit()
            record_activity(
                self,
                action="task.delete",
                entity_type="task",
                entity_id=task_id,
                module="project_management",
                workspace_id=task.project_id,
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

        next_actual_start = task.actual_start if actual_start is None else actual_start
        next_actual_end = task.actual_end if actual_end is None else actual_end
        if status is not None:
            next_status = status

        candidate = replace(
            task,
            percent_complete=next_percent_complete,
            actual_start=next_actual_start,
            actual_end=next_actual_end,
            status=next_status,
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
        except Exception as exc:
            self._session.rollback()
            raise exc

        domain_events.tasks_changed.emit(candidate.project_id)
        return candidate


__all__ = ["TaskLifecycleMixin"]
