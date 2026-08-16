"""Transactional move and recode commands for the Task-owned WBS."""

from __future__ import annotations

from dataclasses import replace

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.tasks.task import TaskRepository
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.shared.activity import record_activity
from src.core.shared.events.domain_events import domain_events


class TaskHierarchyMixin:
    _session: Session
    _task_repo: TaskRepository

    def move_task(
        self,
        task_id: str,
        *,
        parent_task_id: str | None,
        wbs_code: str | None = None,
        sort_order: int | None = None,
        expected_version: int | None = None,
    ) -> Task:
        require_permission(self._user_session, "task.manage", operation_label="move task in WBS")
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        require_project_permission(
            self._user_session,
            task.project_id,
            "task.manage",
            operation_label="move task in WBS",
        )
        if expected_version is not None and task.version != expected_version:
            raise ConcurrencyError(
                "Task changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        tasks = self._task_repo.list_by_project(task.project_id)
        parent = self._require_wbs_parent(
            project_id=task.project_id,
            parent_task_id=parent_task_id,
            moving_task_id=task.id,
            tasks=tasks,
        )
        if parent is not None:
            self._assert_parent_has_no_direct_execution(parent)
        children = self._children_by_parent(tasks)
        subtree_ids: set[str] = set()

        def collect(parent_id: str) -> None:
            for child in children.get(parent_id, []):
                subtree_ids.add(child.id)
                collect(child.id)

        collect(task.id)
        subtree_ids.add(task.id)
        corrupt_descendant = next(
            (
                item
                for item in tasks
                if item.id in subtree_ids
                and item.id != task.id
                and not item.wbs_code.startswith(f"{task.wbs_code}.")
            ),
            None,
        )
        if corrupt_descendant is not None:
            raise BusinessRuleError(
                "The stored WBS subtree has an invalid code path and must be repaired before moving it.",
                code="TASK_WBS_CORRUPT_CODE_PATH",
            )
        siblings = [
            item
            for item in tasks
            if item.parent_task_id == parent_task_id and item.id not in subtree_ids
        ]
        resolved_wbs = self._validate_wbs_code_for_parent(
            wbs_code
            or (
                task.wbs_code
                if task.parent_task_id == parent_task_id
                else self._next_wbs_code(parent, siblings)
            ),
            parent,
        )
        old_prefix = task.wbs_code
        replacement_codes = {
            item.id: (
                resolved_wbs
                if item.id == task.id
                else f"{resolved_wbs}{item.wbs_code[len(old_prefix):]}"
            )
            for item in tasks
            if item.id in subtree_ids
        }
        occupied = {item.wbs_code for item in tasks if item.id not in subtree_ids}
        if occupied.intersection(replacement_codes.values()):
            raise ValidationError(
                "The requested WBS move conflicts with an existing WBS code.",
                code="TASK_WBS_CODE_DUPLICATE",
            )
        default_index = (
            task.sort_order
            if task.parent_task_id == parent_task_id
            else len(siblings)
        )
        target_index = max(
            0,
            min(default_index if sort_order is None else sort_order, len(siblings)),
        )
        target_siblings = list(siblings)
        target_siblings.insert(target_index, task)
        old_siblings = [
            item
            for item in tasks
            if item.parent_task_id == task.parent_task_id and item.id not in subtree_ids
        ]
        updates: dict[str, Task] = {}
        for index, sibling in enumerate(old_siblings):
            if sibling.sort_order != index:
                updates[sibling.id] = replace(sibling, sort_order=index)
        for index, sibling in enumerate(target_siblings):
            updates[sibling.id] = replace(
                sibling,
                parent_task_id=parent_task_id if sibling.id == task.id else sibling.parent_task_id,
                wbs_code=replacement_codes.get(sibling.id, sibling.wbs_code),
                sort_order=index,
            )
        for item in tasks:
            if item.id in subtree_ids and item.id != task.id:
                updates[item.id] = replace(item, wbs_code=replacement_codes[item.id])
        original_by_id = {item.id: item for item in tasks}
        ordered_updates = sorted(
            updates.values(),
            key=lambda candidate: (
                candidate.id in subtree_ids,
                -original_by_id[candidate.id].wbs_code.count("."),
            ),
        )
        try:
            # Deepest-first subtree writes avoid transient unique-code conflicts.
            for candidate in ordered_updates:
                self._task_repo.update(candidate)
            record_activity(
                self,
                action="task.wbs_move",
                entity_type="task",
                entity_id=task.id,
                module="project_management",
                workspace_id=task.project_id,
                details={
                    "parent_task_id": parent_task_id,
                    "wbs_code": resolved_wbs,
                    "sort_order": target_index,
                },
                commit=False,
            )
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "The requested WBS move conflicts with another task.",
                code="TASK_WBS_CONFLICT",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        domain_events.tasks_changed.emit(task.project_id)
        return self._task_repo.get(task.id) or updates[task.id]

    def recode_task(
        self,
        task_id: str,
        wbs_code: str,
        *,
        expected_version: int | None = None,
    ) -> Task:
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        return self.move_task(
            task_id,
            parent_task_id=task.parent_task_id,
            wbs_code=wbs_code,
            sort_order=task.sort_order,
            expected_version=expected_version,
        )


__all__ = ["TaskHierarchyMixin"]
