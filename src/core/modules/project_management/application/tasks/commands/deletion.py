"""Atomic single and bulk deletion commands for hierarchical Tasks."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.tasks.task_events import TaskRemoved
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    DependencyRepository,
    TaskRepository,
)
from src.core.modules.project_management.domain.tasks.hierarchy import order_tasks_children_first
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.contract.repositories.time_management.time.contracts import TimeEntryRepository
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry


class TaskDeletionMixin:
    _session: Session
    _task_repo: TaskRepository
    _dependency_repo: DependencyRepository
    _assignment_repo: AssignmentRepository
    _time_entry_repo: TimeEntryRepository | None

    def delete_task(self, task_id: str) -> None:
        if self._task_repo.get(task_id) is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        self.delete_tasks((task_id,))

    def delete_tasks(self, task_ids: tuple[str, ...]) -> tuple[str, ...]:
        require_permission(self._user_session, "task.manage", operation_label="delete tasks")
        normalized_ids = tuple(
            dict.fromkeys(str(task_id or "").strip() for task_id in task_ids)
        )
        normalized_ids = tuple(task_id for task_id in normalized_ids if task_id)
        if not normalized_ids:
            return ()

        selected_tasks: list[Task] = []
        for task_id in normalized_ids:
            task = self._task_repo.get(task_id)
            if task is not None:
                selected_tasks.append(task)
        if not selected_tasks:
            return ()
        existing_ids = tuple(task.id for task in selected_tasks)

        project_ids = {task.project_id for task in selected_tasks}
        for project_id in project_ids:
            require_project_permission(
                self._user_session,
                project_id,
                "task.manage",
                operation_label="delete tasks",
            )

        selected_ids = {task.id for task in selected_tasks}
        project_tasks = {
            project_id: self._task_repo.list_by_project(project_id)
            for project_id in project_ids
        }
        for task in selected_tasks:
            unselected_child = next(
                (
                    child
                    for child in project_tasks[task.project_id]
                    if child.parent_task_id == task.id and child.id not in selected_ids
                ),
                None,
            )
            if unselected_child is not None:
                raise BusinessRuleError(
                    "Select every descendant before deleting a summary task.",
                    code="TASK_WBS_SUMMARY_NOT_EMPTY",
                )

        ordered_tasks = [
            task
            for project_id in sorted(project_ids)
            for task in order_tasks_children_first(project_tasks[project_id])
            if task.id in selected_ids
        ]
        affected_sibling_groups = {
            (task.project_id, task.parent_task_id) for task in selected_tasks
        }

        scope = self._active_task_scope(operation_label="delete tasks")
        with self._task_uow() as uow:
            for task in ordered_tasks:
                assignments = self._assignment_repo.list_by_task(task.id)
                if self._time_entry_repo is not None:
                    for assignment in assignments:
                        self._time_entry_repo.delete_by_assignment(assignment.id)
                    self._session.flush()
                self._dependency_repo.delete_for_task(task.id)
                self._assignment_repo.delete_by_task(task.id)
                uow.tasks.delete_with_version_check(task.id, expected_version=task.version)
                record_audit_entry(
                    uow,
                    operation="delete",
                    entity_type="task",
                    entity_id=task.id,
                    module="project_management",
                    organization_id=scope.organization_id,
                    severity="low",
                    metadata={"action": "task.delete", "name": task.name},
                    commit=False,
                    fail_closed=True,
                )
                record_activity(
                    uow,
                    action="task.delete",
                    entity_type="task",
                    entity_id=task.id,
                    module="project_management",
                    workspace_id=task.project_id,
                    details={"name": task.name},
                    commit=False,
                )
                uow.record_event(
                    TaskRemoved(
                        tenant_id=scope.tenant_id,
                        organization_id=scope.organization_id,
                        project_id=task.project_id,
                        task_id=task.id,
                        occurred_at=datetime.now(timezone.utc),
                    )
                )

            for project_id, parent_task_id in affected_sibling_groups:
                remaining = sorted(
                    (
                        task
                        for task in project_tasks[project_id]
                        if task.parent_task_id == parent_task_id
                        and task.id not in selected_ids
                    ),
                    key=lambda task: (task.sort_order, task.wbs_code, task.id),
                )
                for sort_order, task in enumerate(remaining):
                    if task.sort_order != sort_order:
                        uow.tasks.update(replace(task, sort_order=sort_order))
            uow.commit()

        return existing_ids


__all__ = ["TaskDeletionMixin"]
