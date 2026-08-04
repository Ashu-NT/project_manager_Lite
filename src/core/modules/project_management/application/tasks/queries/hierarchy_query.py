"""Task-owned WBS hierarchy and rollup queries."""

from __future__ import annotations

from src.core.modules.project_management.contracts.repositories.task import TaskRepository
from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.modules.project_management.domain.tasks.hierarchy import (
    TaskHierarchyNode,
    TaskHierarchyRollup,
)
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.platform.contract.time_management.calendar.calendar_protocol import CalendarProtocol
from src.core.platform.access.authorization import require_project_permission
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError


class TaskHierarchyQueryMixin:
    _task_repo: TaskRepository
    _work_calendar_engine: CalendarProtocol

    def list_task_hierarchy(self, project_id: str) -> list[TaskHierarchyNode]:
        require_permission(self._user_session, "task.read", operation_label="view task hierarchy")
        require_project_permission(
            self._user_session,
            project_id,
            "task.read",
            operation_label="view task hierarchy",
        )
        tasks = self._task_repo.list_by_project(project_id)
        children = self._children_by_parent(tasks)
        nodes: list[TaskHierarchyNode] = []
        visited: set[str] = set()

        def visit(task: Task, depth: int, ancestors: tuple[str, ...]) -> None:
            if task.id in visited:
                raise BusinessRuleError(
                    "The stored WBS hierarchy contains a cycle.",
                    code="TASK_WBS_CORRUPT_CYCLE",
                )
            visited.add(task.id)
            direct_children = children.get(task.id, [])
            nodes.append(
                TaskHierarchyNode(
                    task=task,
                    depth=depth,
                    is_summary=bool(direct_children),
                    child_count=len(direct_children),
                    ancestor_ids=ancestors,
                )
            )
            for child in direct_children:
                visit(child, depth + 1, (*ancestors, task.id))

        for root in children.get(None, []):
            visit(root, 0, ())
        if len(visited) != len(tasks):
            raise BusinessRuleError(
                "The stored WBS hierarchy has an orphan or cycle.",
                code="TASK_WBS_CORRUPT_HIERARCHY",
            )
        return nodes

    def list_leaf_tasks_for_project(self, project_id: str) -> list[Task]:
        return [node.task for node in self.list_task_hierarchy(project_id) if not node.is_summary]

    def get_task_hierarchy_rollup(self, task_id: str) -> TaskHierarchyRollup:
        task = self.get_task(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        nodes = self.list_task_hierarchy(task.project_id)
        return self._build_task_hierarchy_rollup(nodes, task_id)

    def list_task_hierarchy_rollups(
        self,
        project_id: str,
    ) -> dict[str, TaskHierarchyRollup]:
        nodes = self.list_task_hierarchy(project_id)
        return {
            node.task.id: self._build_task_hierarchy_rollup(nodes, node.task.id)
            for node in nodes
        }

    def _build_task_hierarchy_rollup(
        self,
        nodes: list[TaskHierarchyNode],
        task_id: str,
    ) -> TaskHierarchyRollup:
        root = next((node for node in nodes if node.task.id == task_id), None)
        if root is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        descendants = [node for node in nodes if task_id in node.ancestor_ids]
        leaves = [node.task for node in descendants if not node.is_summary]
        if not root.is_summary:
            leaves = [root.task]
        starts = [leaf.start_date for leaf in leaves if leaf.start_date is not None]
        ends = [leaf.end_date for leaf in leaves if leaf.end_date is not None]
        weights = [max(int(leaf.duration_days or 0), 0) for leaf in leaves]
        total_weight = sum(weights)
        percent = (
            sum(float(leaf.percent_complete or 0.0) * weight for leaf, weight in zip(leaves, weights))
            / total_weight
            if total_weight
            else sum(float(leaf.percent_complete or 0.0) for leaf in leaves) / max(len(leaves), 1)
        )
        statuses = {leaf.status for leaf in leaves}
        if leaves and statuses == {TaskStatus.DONE}:
            status = TaskStatus.DONE
        elif TaskStatus.BLOCKED in statuses:
            status = TaskStatus.BLOCKED
        elif any(
            leaf.status == TaskStatus.IN_PROGRESS
            or float(leaf.percent_complete or 0.0) > 0
            for leaf in leaves
        ):
            status = TaskStatus.IN_PROGRESS
        else:
            status = TaskStatus.TODO
        start_date = min(starts) if starts else None
        end_date = max(ends) if ends else None
        duration_days = sum(weights)
        if root.is_summary and start_date is not None and end_date is not None:
            duration_days = max(
                0,
                int(self._work_calendar_engine.working_days_between(start_date, end_date)),
            )
        return TaskHierarchyRollup(
            task_id=task_id,
            descendant_task_ids=tuple(node.task.id for node in descendants),
            leaf_task_ids=tuple(leaf.id for leaf in leaves),
            start_date=start_date,
            end_date=end_date,
            duration_days=duration_days,
            percent_complete=round(percent, 4),
            status=status,
        )


__all__ = ["TaskHierarchyQueryMixin"]
