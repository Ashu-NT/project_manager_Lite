"""Shared policy helpers for Task-owned WBS commands and queries."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

from sqlalchemy.exc import IntegrityError

from src.core.modules.project_management.contracts.repositories.task import (
    AssignmentRepository,
    DependencyRepository,
    TaskRepository,
)
from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError


class TaskHierarchySupportMixin:
    _task_repo: TaskRepository
    _assignment_repo: AssignmentRepository
    _dependency_repo: DependencyRepository

    @staticmethod
    def _is_task_wbs_integrity_error(exc: IntegrityError) -> bool:
        message = " ".join(
            str(part or "")
            for part in (getattr(exc, "orig", ""), getattr(exc, "statement", ""), exc)
        ).lower()
        return (
            "uq_tasks_project_wbs_code" in message
            or "tasks.project_id, tasks.wbs_code" in message
            or "fk_tasks_wbs_same_project_parent" in message
        )

    @staticmethod
    def _children_by_parent(tasks: list[Task]) -> dict[str | None, list[Task]]:
        children: dict[str | None, list[Task]] = defaultdict(list)
        for task in tasks:
            children[task.parent_task_id].append(task)
        for siblings in children.values():
            siblings.sort(key=lambda item: (item.sort_order, item.wbs_code, item.id))
        return children

    def _require_wbs_parent(
        self,
        *,
        project_id: str,
        parent_task_id: str | None,
        moving_task_id: str | None = None,
        tasks: list[Task] | None = None,
    ) -> Task | None:
        if parent_task_id is None:
            return None
        project_tasks = tasks if tasks is not None else self._task_repo.list_by_project(project_id)
        tasks_by_id = {task.id: task for task in project_tasks}
        parent = tasks_by_id.get(parent_task_id) or self._task_repo.get(parent_task_id)
        if parent is None:
            raise NotFoundError("Parent task not found.", code="TASK_WBS_PARENT_NOT_FOUND")
        if parent.project_id != project_id:
            raise BusinessRuleError(
                "Parent and child tasks must belong to the same project.",
                code="TASK_WBS_PARENT_PROJECT_MISMATCH",
            )
        visited: set[str] = set()
        current: Task | None = parent
        while current is not None:
            if current.id == moving_task_id:
                raise BusinessRuleError(
                    "Moving this task would create a WBS cycle.",
                    code="TASK_WBS_CYCLE",
                )
            if current.id in visited:
                raise BusinessRuleError(
                    "The stored WBS hierarchy contains a cycle.",
                    code="TASK_WBS_CORRUPT_CYCLE",
                )
            visited.add(current.id)
            current = tasks_by_id.get(current.parent_task_id)
        return parent

    def _assert_parent_has_no_direct_execution(self, parent: Task) -> None:
        if self._task_repo.list_children(parent.project_id, parent.id):
            return
        has_execution = (
            parent.status != TaskStatus.TODO
            or float(parent.percent_complete or 0.0) > 0
            or parent.actual_start is not None
            or parent.actual_end is not None
            or bool(self._assignment_repo.list_by_task(parent.id))
            or bool(self._dependency_repo.list_by_task(parent.id))
        )
        if has_execution:
            raise BusinessRuleError(
                "A task with execution, dependency, or assignment activity cannot become a summary task.",
                code="TASK_WBS_PARENT_HAS_EXECUTION",
            )

    @staticmethod
    def _next_wbs_code(parent: Task | None, siblings: list[Task]) -> str:
        prefix = f"{parent.wbs_code}." if parent is not None else ""
        numeric_suffixes: list[int] = []
        for sibling in siblings:
            suffix = sibling.wbs_code[len(prefix) :] if sibling.wbs_code.startswith(prefix) else ""
            if suffix.isdigit() and "." not in suffix:
                numeric_suffixes.append(int(suffix))
        return f"{prefix}{max(numeric_suffixes, default=0) + 1}"

    @staticmethod
    def _validate_wbs_code_for_parent(code: str, parent: Task | None) -> str:
        normalized = replace(
            Task(id="WBS-VALIDATION", project_id="WBS-VALIDATION", name="WBS validation"),
            wbs_code=code,
        ).wbs_code
        if parent is not None and not normalized.startswith(f"{parent.wbs_code}."):
            raise ValidationError(
                f"Child WBS code must begin with '{parent.wbs_code}.'.",
                code="TASK_WBS_PARENT_PREFIX_REQUIRED",
            )
        return normalized

    def _prepare_new_task_hierarchy(
        self,
        task: Task,
        *,
        parent_task_id: str | None,
        wbs_code: str,
        sort_order: int | None,
    ) -> Task:
        tasks = self._task_repo.list_by_project(task.project_id)
        parent = self._require_wbs_parent(
            project_id=task.project_id,
            parent_task_id=parent_task_id,
            tasks=tasks,
        )
        if parent is not None:
            self._assert_parent_has_no_direct_execution(parent)
        siblings = [item for item in tasks if item.parent_task_id == parent_task_id]
        resolved_wbs = self._validate_wbs_code_for_parent(
            wbs_code or self._next_wbs_code(parent, siblings), parent
        )
        if any(item.wbs_code == resolved_wbs for item in tasks):
            raise ValidationError(
                f"WBS code '{resolved_wbs}' already exists in this project.",
                code="TASK_WBS_CODE_DUPLICATE",
            )
        resolved_order = (
            max((item.sort_order for item in siblings), default=-1) + 1
            if sort_order is None
            else sort_order
        )
        return replace(
            task,
            parent_task_id=parent_task_id,
            wbs_code=resolved_wbs,
            sort_order=resolved_order,
        )

    def _require_leaf_task(self, task: Task, *, operation_label: str) -> None:
        if self._task_repo.list_children(task.project_id, task.id):
            raise BusinessRuleError(
                f"Summary tasks cannot {operation_label}; update their execution leaves instead.",
                code="TASK_WBS_SUMMARY_EXECUTION_FORBIDDEN",
            )

    def _resequence_for_new_task(self, task: Task) -> Task:
        siblings = self._task_repo.list_children(task.project_id, task.parent_task_id)
        target_index = max(0, min(task.sort_order, len(siblings)))
        ordered: list[Task | None] = list(siblings)
        ordered.insert(target_index, None)
        for index, sibling in enumerate(ordered):
            if sibling is not None and sibling.sort_order != index:
                self._task_repo.update(replace(sibling, sort_order=index))
        return replace(task, sort_order=target_index)


__all__ = ["TaskHierarchySupportMixin"]
